"""API JSON — données pour les graphiques Chart.js"""
from flask import Blueprint, jsonify, request
from flask_login import login_required
from app.services.stats import (get_global_stats, get_monthly,
                                 get_client_stats, get_frais_breakdown)
from app.models import Transaction

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.route("/stats")
@login_required
def stats():
    return jsonify(get_global_stats())


@bp.route("/monthly")
@login_required
def monthly():
    n = request.args.get("months", 12, type=int)
    return jsonify(get_monthly(n))


@bp.route("/clients")
@login_required
def clients():
    n = request.args.get("limit", 10, type=int)
    return jsonify(get_client_stats(n))


@bp.route("/frais")
@login_required
def frais():
    return jsonify(get_frais_breakdown())


@bp.route("/recent")
@login_required
def recent():
    n   = request.args.get("n", 10, type=int)
    txs = Transaction.query.order_by(
        Transaction.created_at.desc()).limit(n).all()
    return jsonify([t.to_dict() for t in txs])


@bp.route("/benefice/live")
@login_required
def benefice_live():
    """Calcule le bénéfice en temps réel depuis les champs du formulaire."""
    recu      = request.args.get("recu",      0, type=float)
    transport = request.args.get("transport", 0, type=float)
    autres    = request.args.get("autres",    0, type=float)
    benefice  = recu - transport - autres
    marge     = round(benefice / recu * 100, 1) if recu else 0
    return jsonify({
        "benefice": round(benefice, 2),
        "marge":    marge,
        "statut":   "déficit" if benefice < 0 else ("partiel" if benefice == 0 else "soldé"),
    })
