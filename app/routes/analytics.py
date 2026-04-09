"""Routes analytiques"""
from flask import Blueprint, render_template
from flask_login import login_required
from app.services.stats import get_global_stats, get_monthly, get_client_stats, get_frais_breakdown

bp = Blueprint("analytics", __name__, url_prefix="/analytics")


@bp.route("/")
@login_required
def index():
    stats   = get_global_stats()
    monthly = get_monthly(12)
    clients = get_client_stats(10)
    frais   = get_frais_breakdown()
    return render_template("analytics/index.html",
                           stats=stats, monthly=monthly,
                           clients=clients, frais=frais,
                           active="analytics")
