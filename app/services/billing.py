"""Logique de facturation et gestion des plans"""
from datetime import datetime, timedelta
from app import db
from app.models import User, Subscription, Payment, PLANS


# ── Récupérer l'abonnement actif d'un user ─────────────────────────────────────
def get_active_sub(user_id: int) -> Subscription:
    """Retourne l'abonnement actif ou crée un Free par défaut."""
    sub = Subscription.query.filter_by(
        user_id=user_id, status="active"
    ).order_by(Subscription.started_at.desc()).first()

    if not sub:
        sub = Subscription(user_id=user_id, plan="free", status="active")
        db.session.add(sub)
        db.session.commit()
    return sub


# ── Vérifier si l'utilisateur peut ajouter une transaction ────────────────────
def can_add_transaction(user_id: int) -> tuple:
    """
    Retourne (peut_ajouter: bool, message: str, plan_actuel: str, nb_tx: int, limite: int)
    """
    sub   = get_active_sub(user_id)
    plan  = sub.plan_info
    limit = plan["tx_limit"]

    if limit == -1:   # illimité
        return True, "", sub.plan, 0, -1

    from app.models import Transaction
    nb_tx = Transaction.query.count()

    if nb_tx >= limit:
        return False, (
            f"Vous avez atteint la limite de {limit} transactions du plan {plan['name']}. "
            f"Passez au plan Pro pour continuer."
        ), sub.plan, nb_tx, limit

    return True, "", sub.plan, nb_tx, limit


# ── Activer un plan après paiement ────────────────────────────────────────────
def activate_plan(user_id: int, plan: str, months: int,
                  payment_method: str, payment_ref: str = None) -> Subscription:
    """Active un plan pour N mois."""
    if plan not in PLANS:
        raise ValueError(f"Plan inconnu : {plan}")

    # Expire les anciens abonnements
    old_subs = Subscription.query.filter_by(
        user_id=user_id, status="active").all()
    for s in old_subs:
        s.status = "expired"

    expires = datetime.utcnow() + timedelta(days=30 * months)
    sub = Subscription(
        user_id=user_id,
        plan=plan,
        status="active",
        expires_at=expires,
        payment_ref=payment_ref,
        payment_method=payment_method,
    )
    db.session.add(sub)
    db.session.commit()
    return sub


# ── Enregistrer un paiement ────────────────────────────────────────────────────
def record_payment(user_id: int, plan: str, amount: float,
                   method: str, phone: str = None, reference: str = None) -> Payment:
    pay = Payment(
        user_id=user_id, plan=plan, amount=amount,
        method=method, phone=phone, reference=reference,
        status="pending",
    )
    db.session.add(pay)
    db.session.commit()
    return pay


def confirm_payment(payment_id: int) -> Payment:
    """Confirme un paiement et active le plan."""
    pay = Payment.query.get_or_404(payment_id)
    pay.status      = "success"
    pay.confirmed_at= datetime.utcnow()
    db.session.commit()

    # Activer l'abonnement
    activate_plan(pay.user_id, pay.plan, 1,
                  payment_method=pay.method,
                  payment_ref=str(pay.id))
    return pay


# ── Vérifier les permissions features ─────────────────────────────────────────
def has_feature(user_id: int, feature: str) -> bool:
    """Vérifie si le plan actif a accès à une feature."""
    sub = get_active_sub(user_id)
    return sub.plan_info.get(feature, False)


# ── Résumé plan pour le contexte Jinja ────────────────────────────────────────
def get_plan_context(user_id: int) -> dict:
    from app.models import Transaction
    sub   = get_active_sub(user_id)
    plan  = sub.plan_info
    limit = plan["tx_limit"]
    nb_tx = Transaction.query.count()
    pct   = round(nb_tx / limit * 100) if limit > 0 else 0

    return {
        "plan":      sub.plan,
        "plan_info": plan,
        "sub":       sub,
        "nb_tx":     nb_tx,
        "tx_limit":  limit,
        "tx_pct":    min(pct, 100),
        "is_free":   sub.plan == "free",
        "is_pro":    sub.plan in ("pro", "pro_plus"),
        "days_left": sub.days_left,
        "near_limit": limit > 0 and nb_tx >= limit * 0.8,  # 80% de la limite
        "at_limit":   limit > 0 and nb_tx >= limit,
    }
