"""Routes facturation — pricing, paiement, activation"""
import uuid
from flask import (Blueprint, render_template, request,
                   redirect, url_for, flash, jsonify, session)
from flask_login import login_required, current_user
from app import db
from app.models import PLANS, Payment
from app.services.billing import (
    get_active_sub, activate_plan, record_payment,
    confirm_payment, get_plan_context
)

bp = Blueprint("billing", __name__, url_prefix="/billing")


# ── Page pricing ───────────────────────────────────────────────────────────────
@bp.route("/pricing")
@login_required
def pricing():
    ctx = get_plan_context(current_user.id)
    return render_template("billing/pricing.html",
                           active="billing", plans=PLANS, ctx=ctx)


# ── Page paiement ──────────────────────────────────────────────────────────────
@bp.route("/checkout/<string:plan>")
@login_required
def checkout(plan):
    if plan not in PLANS or plan == "free":
        flash("Plan invalide.", "error")
        return redirect(url_for("billing.pricing"))

    plan_info = PLANS[plan]
    ctx       = get_plan_context(current_user.id)
    return render_template("billing/checkout.html",
                           active="billing",
                           plan=plan,
                           plan_info=plan_info,
                           ctx=ctx)


# ── Initier le paiement ────────────────────────────────────────────────────────
@bp.route("/pay", methods=["POST"])
@login_required
def pay():
    plan   = request.form.get("plan", "")
    method = request.form.get("method", "")
    phone  = request.form.get("phone", "").strip()
    months = int(request.form.get("months", 1))

    if plan not in PLANS or plan == "free":
        flash("Plan invalide.", "error")
        return redirect(url_for("billing.pricing"))

    plan_info = PLANS[plan]
    amount    = plan_info["price_month"] * months

    # Validation
    if method in ("mtn_momo", "orange") and not phone:
        flash("❌ Numéro de téléphone requis pour Mobile Money.", "error")
        return redirect(url_for("billing.checkout", plan=plan))

    if method in ("mtn_momo", "orange"):
        phone = phone.replace(" ", "").replace("-", "")
        if not phone.startswith("237"):
            phone = "237" + phone

    # Créer le paiement en base
    ref = str(uuid.uuid4())[:12].upper()
    pay = record_payment(
        user_id=current_user.id,
        plan=plan,
        amount=amount,
        method=method,
        phone=phone or None,
        reference=ref,
    )

    # ── Simulation paiement (remplacer par vraie API en prod) ────────────────
    # En production : appeler l'API Campay / MTN MoMo ici
    # Pour la démo : on simule le succès directement
    if method == "demo":
        confirmed = confirm_payment(pay.id)
        flash(f"✅ Plan {plan_info['name']} activé avec succès ! Merci.", "success")
        return redirect(url_for("billing.success", plan=plan))

    # Mobile Money / Visa → page d'attente de confirmation
    session["pending_payment_id"] = pay.id
    return redirect(url_for("billing.pending", payment_id=pay.id))


# ── Page attente paiement ──────────────────────────────────────────────────────
@bp.route("/pending/<int:payment_id>")
@login_required
def pending(payment_id):
    pay = Payment.query.get_or_404(payment_id)
    if pay.user_id != current_user.id:
        flash("Accès refusé.", "error")
        return redirect(url_for("billing.pricing"))

    plan_info = PLANS.get(pay.plan, PLANS["free"])
    return render_template("billing/pending.html",
                           active="billing",
                           pay=pay, plan_info=plan_info)


# ── Confirmer paiement (webhook ou manuel) ────────────────────────────────────
@bp.route("/confirm/<int:payment_id>", methods=["POST"])
@login_required
def confirm(payment_id):
    """
    En prod : appelé par webhook MTN MoMo / Campay.
    En démo : bouton manuel sur la page pending.
    """
    pay = Payment.query.get_or_404(payment_id)
    if pay.status == "success":
        flash("Ce paiement a déjà été confirmé.", "info")
        return redirect(url_for("billing.success", plan=pay.plan))

    confirmed = confirm_payment(pay.id)
    flash(f"✅ Paiement confirmé ! Plan {PLANS[pay.plan]['name']} activé.", "success")
    return redirect(url_for("billing.success", plan=pay.plan))


# ── Succès ────────────────────────────────────────────────────────────────────
@bp.route("/success/<string:plan>")
@login_required
def success(plan):
    plan_info = PLANS.get(plan, PLANS["free"])
    ctx       = get_plan_context(current_user.id)
    return render_template("billing/success.html",
                           active="billing",
                           plan=plan, plan_info=plan_info, ctx=ctx)


# ── Historique paiements ───────────────────────────────────────────────────────
@bp.route("/history")
@login_required
def history():
    payments = Payment.query.filter_by(
        user_id=current_user.id
    ).order_by(Payment.created_at.desc()).all()
    sub = get_active_sub(current_user.id)
    return render_template("billing/history.html",
                           active="billing",
                           payments=payments, sub=sub,
                           plans=PLANS)


# ── API : vérifier statut plan (pour JS) ──────────────────────────────────────
@bp.route("/api/status")
@login_required
def api_status():
    ctx = get_plan_context(current_user.id)
    return jsonify({
        "plan":      ctx["plan"],
        "nb_tx":     ctx["nb_tx"],
        "tx_limit":  ctx["tx_limit"],
        "tx_pct":    ctx["tx_pct"],
        "near_limit":ctx["near_limit"],
        "at_limit":  ctx["at_limit"],
        "is_free":   ctx["is_free"],
        "days_left": ctx["days_left"],
    })
