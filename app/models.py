"""Modèles SQLAlchemy — Digital Services CM Enterprise"""
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db


# ── Utilisateur ───────────────────────────────────────────────────────────────
class User(UserMixin, db.Model):
    __tablename__ = "users"

    id         = db.Column(db.Integer, primary_key=True)
    username   = db.Column(db.String(80),  unique=True, nullable=False)
    email      = db.Column(db.String(120), unique=True, nullable=False)
    password_h = db.Column(db.String(256), nullable=False)
    role       = db.Column(db.String(20),  default="admin")  # admin | viewer
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    def set_password(self, pw: str):
        self.password_h = generate_password_hash(pw)

    def check_password(self, pw: str) -> bool:
        return check_password_hash(self.password_h, pw)

    def __repr__(self):
        return f"<User {self.username}>"


# ── Transaction ───────────────────────────────────────────────────────────────
class Transaction(db.Model):
    __tablename__ = "transactions"

    id           = db.Column(db.Integer, primary_key=True)
    client       = db.Column(db.String(120), nullable=False, index=True)
    montant_recu = db.Column(db.Float, nullable=False)
    transport    = db.Column(db.Float, default=0.0)
    autres       = db.Column(db.Float, default=0.0)
    date         = db.Column(db.String(10), nullable=False, index=True)
    statut       = db.Column(db.String(20), default="soldé")
    notes        = db.Column(db.Text, default="")
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at   = db.Column(db.DateTime, default=datetime.utcnow,
                             onupdate=datetime.utcnow)

    # ── Propriétés calculées ──────────────────────────────────────────────────
    @property
    def benefice(self) -> float:
        return round(self.montant_recu - self.transport - self.autres, 2)

    @property
    def total_frais(self) -> float:
        return round(self.transport + self.autres, 2)

    @property
    def marge(self) -> float:
        if self.montant_recu == 0:
            return 0.0
        return round(self.benefice / self.montant_recu * 100, 1)

    @property
    def statut_auto(self) -> str:
        if self.benefice < 0:
            return "déficit"
        if self.benefice == 0:
            return "partiel"
        return "soldé"

    def to_dict(self) -> dict:
        return {
            "id":          self.id,
            "client":      self.client,
            "montant_recu":self.montant_recu,
            "transport":   self.transport,
            "autres":      self.autres,
            "benefice":    self.benefice,
            "marge":       self.marge,
            "total_frais": self.total_frais,
            "statut":      self.statut,
            "notes":       self.notes,
            "date":        self.date,
            "created_at":  self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<Transaction {self.client} {self.date}>"


# ── Plans disponibles ──────────────────────────────────────────────────────────
PLANS = {
    "free": {
        "name":        "Gratuit",
        "price_month": 0,
        "tx_limit":    30,
        "users_limit": 1,
        "export":      False,
        "analytics":   False,
        "alerts":      False,
        "suggestions": False,
        "ai_chat":     False,
        "color":       "#8490b0",
        "icon":        "🆓",
        "features": [
            ("✅", "Gestion basique des dépenses"),
            ("✅", "Gestion des revenus"),
            ("✅", "Tableau de bord simple"),
            ("✅", "Historique des transactions"),
            ("❌", "Suggestions intelligentes"),
            ("❌", "Analyse avancée"),
            ("❌", "Export Excel"),
            ("❌", "Assistant IA"),
        ],
    },
    "pro": {
        "name":        "Pro",
        "price_month": 2000,
        "tx_limit":    -1,
        "users_limit": 3,
        "export":      True,
        "analytics":   True,
        "alerts":      True,
        "suggestions": True,
        "ai_chat":     False,
        "color":       "#4f8ef7",
        "icon":        "💼",
        "features": [
            ("✅", "Tout du plan Gratuit"),
            ("✅", "Export Excel 3 feuilles"),
            ("✅", "Analytiques avancées"),
            ("✅", "Alertes déficit & marge faible"),
            ("✅", "3 utilisateurs"),
            ("✅", "Suggestions d'amélioration des ventes"),
            ("✅", "Suggestions d'optimisation des dépenses"),
            ("✅", "Suggestions sur les marges"),
            ("✅", "Suggestions liées aux clients"),
            ("✅", "Alertes basiques automatiques"),
            ("❌", "Assistant IA conversationnel"),
            ("❌", "Chat libre avec l'IA"),
        ],
    },
    "pro_plus": {
        "name":        "Pro+",
        "price_month": 5000,
        "tx_limit":    -1,
        "users_limit": -1,
        "export":      True,
        "analytics":   True,
        "alerts":      True,
        "suggestions": True,
        "ai_chat":     True,
        "color":       "#f0c040",
        "icon":        "🚀",
        "features": [
            ("✅", "Tout du plan Pro"),
            ("✅", "Utilisateurs illimités"),
            ("✅", "Assistant IA interactif"),
            ("✅", "Chat libre — questions illimitées"),
            ("✅", "Réponses basées sur tes données"),
            ("✅", "Recommandations marketing intelligentes"),
            ("✅", "Optimisation des prix & marges"),
            ("✅", "Fidélisation clients"),
            ("✅", "Analyse des tendances avancée"),
            ("✅", "Détection automatique problèmes financiers"),
            ("✅", "Analyse prédictive simple"),
            ("✅", "Suggestions de promotions"),
        ],
    },
}


class Subscription(db.Model):
    """Abonnement d'un utilisateur."""
    __tablename__ = "subscriptions"

    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    plan         = db.Column(db.String(20), default="free", nullable=False)
    status       = db.Column(db.String(20), default="active")  # active | expired | pending
    started_at   = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at   = db.Column(db.DateTime, nullable=True)   # None = illimité
    payment_ref  = db.Column(db.String(100), nullable=True)  # référence paiement
    payment_method = db.Column(db.String(30), nullable=True) # mtn_momo | orange | visa | paypal

    user = db.relationship("User", backref=db.backref("subscriptions", lazy=True))

    @property
    def is_active(self) -> bool:
        if self.status != "active":
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True

    @property
    def plan_info(self) -> dict:
        return PLANS.get(self.plan, PLANS["free"])

    @property
    def tx_limit(self) -> int:
        return self.plan_info["tx_limit"]

    @property
    def days_left(self) -> int:
        if not self.expires_at:
            return 9999
        delta = self.expires_at - datetime.utcnow()
        return max(0, delta.days)

    def __repr__(self):
        return f"<Sub user={self.user_id} plan={self.plan}>"


class Payment(db.Model):
    """Historique des paiements."""
    __tablename__ = "payments"

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    plan        = db.Column(db.String(20), nullable=False)
    amount      = db.Column(db.Float,  nullable=False)
    currency    = db.Column(db.String(5), default="FCFA")
    method      = db.Column(db.String(30), nullable=False)  # mtn_momo | orange | visa | paypal
    phone       = db.Column(db.String(20), nullable=True)
    reference   = db.Column(db.String(100), nullable=True)
    status      = db.Column(db.String(20), default="pending")  # pending | success | failed
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    confirmed_at= db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", backref=db.backref("payments", lazy=True))


# ── Support Messages ────────────────────────────────────────────────────────────
SUPPORT_TYPES = {
    "bug":      {"label": "Problème technique", "icon": "🐛", "color": "#f0504a"},
    "question": {"label": "Question",            "icon": "❓", "color": "#4f8ef7"},
    "feature":  {"label": "Suggestion",          "icon": "💡", "color": "#f0c040"},
    "billing":  {"label": "Facturation",         "icon": "💳", "color": "#0ef0c0"},
    "request":  {"label": "Demande de fonctionnalité", "icon": "🚀", "color": "#8b5cf6"},
    "other":    {"label": "Autre",               "icon": "📝", "color": "#8490b0"},
}

SUPPORT_STATUS = {
    "new":      {"label": "Nouveau",   "color": "#f0c040"},
    "read":     {"label": "Lu",        "color": "#4f8ef7"},
    "resolved": {"label": "Résolu",    "color": "#10e080"},
}


class SupportMessage(db.Model):
    __tablename__ = "support_messages"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    name       = db.Column(db.String(100), nullable=True)
    email      = db.Column(db.String(120), nullable=True)
    type       = db.Column(db.String(30),  nullable=False, default="question")
    message    = db.Column(db.Text,        nullable=False)
    status     = db.Column(db.String(20),  default="new")  # new | read | resolved
    admin_note = db.Column(db.Text,        nullable=True)  # note interne admin
    created_at = db.Column(db.DateTime,    default=datetime.utcnow)
    updated_at = db.Column(db.DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("support_messages", lazy=True))

    @property
    def type_info(self) -> dict:
        return SUPPORT_TYPES.get(self.type, SUPPORT_TYPES["other"])

    @property
    def status_info(self) -> dict:
        return SUPPORT_STATUS.get(self.status, SUPPORT_STATUS["new"])

    def __repr__(self):
        return f"<Support #{self.id} {self.type} {self.status}>"
