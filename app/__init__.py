"""Factory Flask — Digital Services CM Enterprise"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from dotenv import load_dotenv
import os

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__, template_folder="../templates",
                static_folder="../static")

    # ── Config ────────────────────────────────────────────────────────────────
    app.config["SECRET_KEY"]           = os.getenv("SECRET_KEY", "dev-secret")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL", "sqlite:///dsm_enterprise.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["WTF_CSRF_ENABLED"] = False   # désactivé pour l'API JSON

    # ── Extensions ────────────────────────────────────────────────────────────
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view     = "auth.login"
    login_manager.login_message  = "Connecte-toi pour accéder à cette page."
    login_manager.login_message_category = "warning"

    # ── Filtres Jinja2 personnalisés ──────────────────────────────────────────
    import hashlib as _hs

    _AV_COLORS = [
        "#0ef0c0","#4f8ef7","#8b5cf6","#f59e0b","#ec4899",
        "#06d6a8","#f0504a","#a78bfa","#fde68a","#7ab3ff","#10e080","#f0c040",
    ]

    @app.template_filter('av_color')
    def av_color_filter(name: str) -> str:
        """Couleur avatar unique basée sur le nom."""
        h = int(_hs.md5(str(name).encode()).hexdigest(), 16)
        return _AV_COLORS[h % len(_AV_COLORS)]

    @app.template_filter('initials')
    def initials_filter(name: str) -> str:
        """Initiales d'un nom."""
        parts = str(name).strip().split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        return name[:2].upper() if len(name) >= 2 else name[0].upper()

    @app.template_filter('fmt_money')
    def fmt_money_filter(v) -> str:
        try:
            n = float(v)
            return f"{n:,.0f}".replace(",", "\u202f")
        except Exception:
            return str(v)

    @app.template_filter('fmt_short')
    def fmt_short_filter(v) -> str:
        try:
            n = abs(float(v))
            sign = "-" if float(v) < 0 else ""
            if n >= 1_000_000: return f"{sign}{n/1_000_000:.1f}M"
            if n >= 1_000:     return f"{sign}{n/1_000:.0f}K"
            return f"{sign}{n:.0f}"
        except Exception:
            return str(v)



    # ── User loader ───────────────────────────────────────────────────────────
    from app.models import User

    @login_manager.user_loader
    def load_user(uid):
        return db.session.get(User, int(uid))

    # ── Blueprints ────────────────────────────────────────────────────────────
    from app.routes.auth         import bp as auth_bp
    from app.routes.dashboard    import bp as dash_bp
    from app.routes.transactions import bp as tx_bp
    from app.routes.clients      import bp as cli_bp
    from app.routes.analytics    import bp as ana_bp
    from app.routes.api          import bp as api_bp
    from app.routes.settings      import bp as settings_bp
    from app.routes.billing       import bp as billing_bp
    from app.routes.support       import bp as support_bp
    from app.routes.ai            import bp as ai_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dash_bp)
    app.register_blueprint(tx_bp)
    app.register_blueprint(cli_bp)
    app.register_blueprint(ana_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(support_bp)
    app.register_blueprint(ai_bp)


    # ── Context processors ────────────────────────────────────────────────────
    from datetime import datetime as _dt, date as _date

    @app.context_processor
    def inject_globals():
        from flask_login import current_user as _cu
        plan_ctx = {}
        if _cu.is_authenticated:
            try:
                from app.services.billing import get_plan_context
                plan_ctx = get_plan_context(_cu.id)
            except Exception:
                pass
        return {
            'now':   _dt.now(),
            'today': _date.today().isoformat(),
            'plan_ctx': plan_ctx,
        }

    # ── Init DB ───────────────────────────────────────────────────────────────
    with app.app_context():
        db.create_all()
        db.create_all()   # crée les nouvelles tables si manquantes
        _seed_admin()
        _seed_demo()

    return app


def _seed_admin():
    """Crée l'admin par défaut si aucun user."""
    from app.models import User
    if User.query.count() == 0:
        admin = User(username="admin", email="admin@dsm.cm", role="admin")
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()
        print("✅ Admin créé : admin / admin123")


def _seed_demo():
    """Insère 148 transactions de démo si la DB est vide."""
    from app.models import Transaction
    if Transaction.query.count() > 0:
        return
    import random
    from datetime import date, timedelta
    random.seed(42)
    clients = [
        "Amina Mboyo","Kouam Thierry","Nkemdirim Julius","Beti Francine",
        "Djomo Pascal","Ewane Marie","Tamba Serge","Ngono Claire",
        "Fopa Daniel","Mbarga Sylvie","Abega Eric","Loko Nadège",
    ]
    today = date.today()
    records = []
    for _ in range(148):
        days_ago = random.randint(0, 365)
        d        = (today - timedelta(days=days_ago)).isoformat()
        client   = random.choice(clients)
        recu     = round(random.uniform(15000, 250000) / 500) * 500
        transport= round(random.uniform(500, recu * 0.15) / 100) * 100
        autres   = round(random.uniform(0,   recu * 0.08) / 100) * 100
        ben      = recu - transport - autres
        statut   = "déficit" if ben < 0 else ("partiel" if ben == 0 else "soldé")
        records.append(Transaction(
            client=client, montant_recu=recu,
            transport=transport, autres=autres,
            date=d, statut=statut))
    db.session.bulk_save_objects(records)
    db.session.commit()
    print(f"✅ {len(records)} transactions de démo insérées.")
