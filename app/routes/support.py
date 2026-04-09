"""Routes Support — page publique + dashboard admin"""
from flask import (Blueprint, render_template, request,
                   jsonify, redirect, url_for, flash)
from flask_login import login_required, current_user
from datetime import datetime
from app import db
from app.models import SupportMessage, SUPPORT_TYPES, SUPPORT_STATUS

bp = Blueprint("support", __name__, url_prefix="/support")

# ── Configurer ici ton numéro WhatsApp ────────────────────────────────────────
WHATSAPP_NUMBER = "237620880188"   # ← Remplace par ton vrai numéro (sans +)
WHATSAPP_MSG    = "Bonjour, j'ai besoin d'aide concernant l'application Digital Services CM."


# ── Page support principale ───────────────────────────────────────────────────
@bp.route("/")
@login_required
def index():
    # Compter les messages de l'utilisateur
    user_messages = SupportMessage.query.filter_by(
        user_id=current_user.id
    ).order_by(SupportMessage.created_at.desc()).limit(5).all()

    return render_template("support/index.html",
                           active="support",
                           types=SUPPORT_TYPES,
                           user_messages=user_messages,
                           whatsapp_number=WHATSAPP_NUMBER,
                           whatsapp_msg=WHATSAPP_MSG)


# ── Envoyer un message de support ────────────────────────────────────────────
@bp.route("/send", methods=["POST"])
@login_required
def send():
    name    = request.form.get("name", "").strip()
    email   = request.form.get("email", "").strip()
    type_   = request.form.get("type", "question").strip()
    message = request.form.get("message", "").strip()

    # Validation
    if not message or len(message) < 10:
        flash("❌ Le message doit faire au moins 10 caractères.", "error")
        return redirect(url_for("support.index"))

    if type_ not in SUPPORT_TYPES:
        type_ = "other"

    if len(message) > 2000:
        flash("❌ Message trop long (max 2000 caractères).", "error")
        return redirect(url_for("support.index"))

    # Créer le message
    msg = SupportMessage(
        user_id = current_user.id,
        name    = name or current_user.username,
        email   = email or current_user.email or "",
        type    = type_,
        message = message,
        status  = "new",
    )
    db.session.add(msg)
    db.session.commit()

    flash("✅ Ton message a été envoyé ! Nous te répondrons rapidement.", "success")
    return redirect(url_for("support.index"))


# ── API JSON pour envoi AJAX ──────────────────────────────────────────────────
@bp.route("/api/send", methods=["POST"])
@login_required
def api_send():
    data    = request.get_json() or {}
    name    = data.get("name",    "").strip()
    email   = data.get("email",   "").strip()
    type_   = data.get("type",    "question").strip()
    message = data.get("message", "").strip()

    if not message or len(message) < 10:
        return jsonify({"error": "Message trop court (min 10 caractères)."}), 400
    if type_ not in SUPPORT_TYPES:
        type_ = "other"

    msg = SupportMessage(
        user_id = current_user.id,
        name    = name or current_user.username,
        email   = email or current_user.email or "",
        type    = type_,
        message = message,
        status  = "new",
    )
    db.session.add(msg)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Ton message a été envoyé ! Nous te répondrons rapidement.",
        "id":      msg.id,
    })


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN — Dashboard messages support
# ══════════════════════════════════════════════════════════════════════════════

def _admin_required():
    if current_user.role != "admin":
        flash("❌ Accès réservé à l'administrateur.", "error")
        return redirect(url_for("dashboard.index"))
    return None


@bp.route("/admin")
@login_required
def admin():
    guard = _admin_required()
    if guard: return guard

    status_filter = request.args.get("status", "")
    type_filter   = request.args.get("type",   "")

    q = SupportMessage.query
    if status_filter:
        q = q.filter_by(status=status_filter)
    if type_filter:
        q = q.filter_by(type=type_filter)
    q = q.order_by(SupportMessage.created_at.desc())

    messages   = q.all()
    count_new  = SupportMessage.query.filter_by(status="new").count()
    count_read = SupportMessage.query.filter_by(status="read").count()
    count_done = SupportMessage.query.filter_by(status="resolved").count()

    return render_template("support/admin.html",
                           active="support",
                           messages=messages,
                           count_new=count_new,
                           count_read=count_read,
                           count_done=count_done,
                           types=SUPPORT_TYPES,
                           statuses=SUPPORT_STATUS,
                           status_filter=status_filter,
                           type_filter=type_filter)


@bp.route("/admin/<int:mid>/status", methods=["POST"])
@login_required
def update_status(mid):
    guard = _admin_required()
    if guard: return guard

    msg        = SupportMessage.query.get_or_404(mid)
    new_status = request.form.get("status", "read")
    note       = request.form.get("admin_note", "").strip()

    if new_status not in SUPPORT_STATUS:
        new_status = "read"

    msg.status     = new_status
    msg.updated_at = datetime.utcnow()
    if note:
        msg.admin_note = note
    db.session.commit()

    flash(f"✅ Message #{mid} marqué comme « {SUPPORT_STATUS[new_status]['label']} ».", "success")
    return redirect(url_for("support.admin"))


@bp.route("/admin/<int:mid>/delete", methods=["POST"])
@login_required
def delete_message(mid):
    guard = _admin_required()
    if guard: return guard

    msg = SupportMessage.query.get_or_404(mid)
    db.session.delete(msg)
    db.session.commit()
    flash(f"🗑 Message #{mid} supprimé.", "info")
    return redirect(url_for("support.admin"))


# ── API : nombre de nouveaux messages (pour badge sidebar) ────────────────────
@bp.route("/api/count")
@login_required
def api_count():
    if current_user.role != "admin":
        return jsonify({"count": 0})
    count = SupportMessage.query.filter_by(status="new").count()
    return jsonify({"count": count})
