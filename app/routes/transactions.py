"""Routes transactions"""
from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def admin_required(f):
    """Décorateur : refuse l'accès aux viewers."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role == "viewer":
            flash("❌ Accès refusé — compte lecture seule.", "error")
            return redirect(url_for("transactions.index"))
        return f(*args, **kwargs)
    return decorated


from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, Response
from flask_login import login_required
from datetime import datetime, date
from app import db
from app.models import Transaction
from app.services.stats import get_transactions
from app.services.export import export_excel, export_csv

bp = Blueprint("transactions", __name__, url_prefix="/transactions")


@bp.route("/")
@login_required
def index():
    page     = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 25, type=int)
    search   = request.args.get("search", "")
    date_from= request.args.get("date_from", "")
    date_to  = request.args.get("date_to", "")
    statut   = request.args.get("statut", "")
    order_by = request.args.get("order_by", "date")
    desc     = request.args.get("desc", "1") == "1"

    txs, total = get_transactions(
        search=search, date_from=date_from or None,
        date_to=date_to or None, statut=statut or None,
        order_by=order_by, desc=desc,
        page=page, per_page=per_page)

    from math import ceil
    total_pages = max(1, ceil(total / per_page))

    return render_template("transactions/index.html",
        transactions=txs, total=total,
        page=page, per_page=per_page, total_pages=total_pages,
        search=search, date_from=date_from, date_to=date_to,
        statut=statut, order_by=order_by, desc=desc,
        active="transactions")


@bp.route("/add", methods=["GET","POST"])
@login_required
@admin_required
def add():
    error = None
    if request.method == "POST":
        # Vérifier la limite du plan
        from app.services.billing import can_add_transaction
        can, limit_msg, plan, nb_tx, limit = can_add_transaction(current_user.id)
        if not can:
            # Retourner JSON si requête AJAX, sinon redirect
            from flask import jsonify
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"error": "limit", "message": limit_msg}), 403
            flash(f"⚠️ {limit_msg}", "warning")
            return redirect(url_for("billing.pricing"))

        ok, error, data = _validate_form(request.form)
        if ok:
            t = Transaction(**data)
            t.statut = t.statut_auto
            db.session.add(t)
            db.session.commit()
            flash(f"✅ Transaction de « {data['client']} » ajoutée.", "success")
            return redirect(url_for("transactions.index"))
    from datetime import date
    from app.services.stats import get_client_stats
    cl = [c['client'] for c in get_client_stats(100)]
    return render_template("transactions/form.html",
                           mode="add", error=error,
                           tx=None, clients_list=cl,
                           today=date.today().isoformat(),
                           active="transactions")


@bp.route("/edit/<int:tid>", methods=["GET","POST"])
@login_required
@admin_required
def edit(tid):
    tx = Transaction.query.get_or_404(tid)
    error = None
    if request.method == "POST":
        ok, error, data = _validate_form(request.form)
        if ok:
            for k, v in data.items():
                setattr(tx, k, v)
            tx.statut = tx.statut_auto
            db.session.commit()
            flash(f"✅ Transaction modifiée.", "success")
            return redirect(url_for("transactions.index"))
    from datetime import date
    from app.services.stats import get_client_stats
    cl = [c['client'] for c in get_client_stats(100)]
    return render_template("transactions/form.html",
                           mode="edit", error=error,
                           tx=tx, clients_list=cl,
                           today=date.today().isoformat(),
                           active="transactions")


@bp.route("/delete/<int:tid>", methods=["POST"])
@login_required
@admin_required
def delete(tid):
    tx = Transaction.query.get_or_404(tid)
    db.session.delete(tx)
    db.session.commit()
    flash(f"🗑 Transaction supprimée.", "info")
    return redirect(url_for("transactions.index"))


@bp.route("/delete-all", methods=["POST"])
@login_required
@admin_required
def delete_all():
    Transaction.query.delete()
    db.session.commit()
    flash("🚮 Toutes les transactions supprimées.", "warning")
    return redirect(url_for("transactions.index"))


@bp.route("/export/excel")
@login_required
def export_excel_route():
    search   = request.args.get("search","")
    date_from= request.args.get("date_from","") or None
    date_to  = request.args.get("date_to","")   or None
    statut   = request.args.get("statut","")    or None
    txs, _   = get_transactions(search=search, date_from=date_from,
                                 date_to=date_to, statut=statut,
                                 per_page=100_000)
    data = export_excel(txs)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Response(data,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment;filename=DSM_Export_{ts}.xlsx"})


@bp.route("/export/csv")
@login_required
def export_csv_route():
    txs, _ = get_transactions(per_page=100_000)
    data   = export_csv(txs)
    ts     = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Response(data,
        mimetype="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": f"attachment;filename=DSM_Export_{ts}.csv"})


def _validate_form(form) -> tuple:
    errors = []
    client = form.get("client","").strip()
    if not client or len(client) < 2:
        errors.append("Nom client invalide (min 2 caractères).")
    try:
        recu = float(form.get("montant_recu","0").replace(",",".") or "0")
        if recu < 0: errors.append("Montant reçu négatif.")
    except ValueError:
        recu = 0; errors.append("Montant reçu invalide.")
    try:
        transport = float(form.get("transport","0").replace(",",".") or "0")
        if transport < 0: errors.append("Transport négatif.")
    except ValueError:
        transport = 0; errors.append("Transport invalide.")
    try:
        autres = float(form.get("autres","0").replace(",",".") or "0")
        if autres < 0: errors.append("Autres frais négatifs.")
    except ValueError:
        autres = 0; errors.append("Autres frais invalides.")
    d = form.get("date","").strip()
    try:
        datetime.strptime(d, "%Y-%m-%d")
    except ValueError:
        errors.append("Date invalide (AAAA-MM-JJ).")
        d = date.today().isoformat()
    notes = form.get("notes","").strip()
    if errors:
        return False, " | ".join(f"• {e}" for e in errors), None
    return True, None, {
        "client": client, "montant_recu": recu,
        "transport": transport, "autres": autres,
        "date": d, "notes": notes,
    }
