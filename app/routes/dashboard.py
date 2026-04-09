"""Route dashboard"""
from flask import Blueprint, render_template
from flask_login import login_required
from app.services.stats import get_global_stats, get_monthly, get_client_stats, get_frais_breakdown
from app.models import Transaction

bp = Blueprint("dashboard", __name__)


@bp.route("/")
@bp.route("/dashboard")
@login_required
def index():
    stats   = get_global_stats()
    monthly = get_monthly(12)
    clients = get_client_stats(8)
    frais   = get_frais_breakdown()
    recent  = Transaction.query.order_by(
        Transaction.created_at.desc()).limit(8).all()
    return render_template("dashboard/index.html",
                           stats=stats, monthly=monthly,
                           clients=clients, frais=frais,
                           recent=recent, active="dashboard")
