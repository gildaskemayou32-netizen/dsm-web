"""Routes clients"""
from flask import Blueprint, render_template, request
from flask_login import login_required
from app.models import Transaction
from app.services.stats import get_client_stats
from app import db
from sqlalchemy import func

bp = Blueprint("clients", __name__, url_prefix="/clients")


@bp.route("/")
@login_required
def index():
    clients = get_client_stats(50)
    return render_template("clients/index.html",
                           clients=clients, active="clients")


@bp.route("/<string:client_name>")
@login_required
def detail(client_name):
    txs = Transaction.query.filter(
        Transaction.client.ilike(client_name)
    ).order_by(Transaction.date.desc()).all()

    if not txs:
        from flask import abort
        abort(404)

    stats = {
        "client":       client_name,
        "transactions": len(txs),
        "total_recu":   sum(t.montant_recu for t in txs),
        "total_ben":    sum(t.benefice for t in txs),
        "marge_moy":    round(sum(t.marge for t in txs) / len(txs), 1) if txs else 0,
        "derniere":     max(t.date for t in txs),
    }
    return render_template("clients/detail.html",
                           client_stats=stats, transactions=txs,
                           active="clients")
