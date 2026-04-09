"""Service statistiques — compatible SQLAlchemy 1.x ET 2.x"""
from datetime import date
from sqlalchemy import func, text, distinct
from app import db
from app.models import Transaction


# ── Helpers ────────────────────────────────────────────────────────────────────
def _scalar(val, default=0.0):
    """Extrait une valeur scalaire d'un résultat SQLAlchemy peu importe la version."""
    if val is None:
        return default
    # SQLAlchemy 2 peut retourner un Row d'un seul élément
    try:
        return float(val)
    except (TypeError, ValueError):
        try:
            return float(val[0])
        except Exception:
            return default


# ── Stats globales ─────────────────────────────────────────────────────────────
def get_global_stats() -> dict:
    today = date.today().isoformat()
    mois  = today[:7]          # "YYYY-MM"

    # On utilise des requêtes séparées simples — 100% compatibles
    total_recu = db.session.query(
        func.coalesce(func.sum(Transaction.montant_recu), 0)
    ).scalar() or 0

    total_frais = db.session.query(
        func.coalesce(func.sum(Transaction.transport + Transaction.autres), 0)
    ).scalar() or 0

    total_benefice = db.session.query(
        func.coalesce(
            func.sum(Transaction.montant_recu - Transaction.transport - Transaction.autres), 0)
    ).scalar() or 0

    total_tx = db.session.query(func.count(Transaction.id)).scalar() or 0
    nb_clients = db.session.query(func.count(distinct(Transaction.client))).scalar() or 0

    # Aujourd'hui
    ben_jour = db.session.query(
        func.coalesce(
            func.sum(Transaction.montant_recu - Transaction.transport - Transaction.autres), 0)
    ).filter(Transaction.date == today).scalar() or 0

    tx_jour = db.session.query(func.count(Transaction.id))\
        .filter(Transaction.date == today).scalar() or 0

    # Ce mois
    ben_mois = db.session.query(
        func.coalesce(
            func.sum(Transaction.montant_recu - Transaction.transport - Transaction.autres), 0)
    ).filter(Transaction.date.like(f"{mois}%")).scalar() or 0

    # Marge moyenne
    txs = Transaction.query.filter(Transaction.montant_recu > 0).all()
    marges = [t.marge for t in txs]
    marge_moy = round(sum(marges) / len(marges), 1) if marges else 0.0

    # Meilleur client
    best = db.session.query(
        Transaction.client,
        func.sum(
            Transaction.montant_recu - Transaction.transport - Transaction.autres
        ).label("b")
    ).group_by(Transaction.client)\
     .order_by(text("b DESC"))\
     .first()

    # Alertes (transactions en déficit)
    alertes = db.session.query(func.count(Transaction.id)).filter(
        (Transaction.montant_recu - Transaction.transport - Transaction.autres) < 0
    ).scalar() or 0

    return {
        "total_benefice":     round(float(total_benefice), 2),
        "benefice_jour":      round(float(ben_jour), 2),
        "benefice_mois":      round(float(ben_mois), 2),
        "total_transactions": int(total_tx),
        "transactions_jour":  int(tx_jour),
        "total_recu":         round(float(total_recu), 2),
        "total_frais":        round(float(total_frais), 2),
        "clients_count":      int(nb_clients),
        "marge_moy":          marge_moy,
        "meilleur_client":    best[0] if best else "—",
        "alertes":            int(alertes),
    }


# ── Stats mensuelles ───────────────────────────────────────────────────────────
def get_monthly(months: int = 12) -> list:
    MONTHS_FR = {
        "01":"Jan","02":"Fév","03":"Mar","04":"Avr",
        "05":"Mai","06":"Jun","07":"Jul","08":"Aoû",
        "09":"Sep","10":"Oct","11":"Nov","12":"Déc",
    }

    rows = db.session.query(
        func.strftime("%Y-%m", Transaction.date).label("month"),
        func.coalesce(func.sum(Transaction.montant_recu), 0).label("revenus"),
        func.coalesce(func.sum(
            Transaction.montant_recu - Transaction.transport - Transaction.autres
        ), 0).label("benefice"),
        func.coalesce(func.sum(
            Transaction.transport + Transaction.autres
        ), 0).label("frais"),
        func.count(Transaction.id).label("transactions"),
    ).group_by(text("month"))\
     .order_by(text("month DESC"))\
     .limit(months)\
     .all()

    result = []
    for r in reversed(rows):
        m = r.month or ""
        result.append({
            "month":        m,
            "label":        MONTHS_FR.get(m[5:7] if len(m) >= 7 else "", m),
            "revenus":      round(float(r.revenus   or 0), 2),
            "benefice":     round(float(r.benefice  or 0), 2),
            "frais":        round(float(r.frais     or 0), 2),
            "transactions": int(r.transactions or 0),
        })
    return result


# ── Stats clients ──────────────────────────────────────────────────────────────
def get_client_stats(limit: int = 10) -> list:
    rows = db.session.query(
        Transaction.client,
        func.count(Transaction.id).label("transactions"),
        func.coalesce(func.sum(Transaction.montant_recu), 0).label("total_recu"),
        func.coalesce(func.sum(
            Transaction.montant_recu - Transaction.transport - Transaction.autres
        ), 0).label("total_ben"),
        func.max(Transaction.date).label("derniere"),
    ).group_by(Transaction.client)\
     .order_by(text("total_ben DESC"))\
     .limit(limit)\
     .all()

    result = []
    for r in rows:
        total_recu = float(r.total_recu or 0)
        total_ben  = float(r.total_ben  or 0)
        marge_moy  = round(total_ben / total_recu * 100, 1) if total_recu > 0 else 0.0
        result.append({
            "client":       r.client,
            "transactions": int(r.transactions or 0),
            "total_recu":   round(total_recu, 2),
            "total_ben":    round(total_ben, 2),
            "marge_moy":    marge_moy,
            "derniere":     r.derniere or "",
        })
    return result


# ── Répartition frais ──────────────────────────────────────────────────────────
def get_frais_breakdown() -> dict:
    """Retourne le total transport et autres séparément."""
    transport = db.session.query(
        func.coalesce(func.sum(Transaction.transport), 0)
    ).scalar() or 0

    autres = db.session.query(
        func.coalesce(func.sum(Transaction.autres), 0)
    ).scalar() or 0

    return {
        "transport": round(float(transport), 2),
        "autres":    round(float(autres), 2),
    }


# ── Transactions filtrées + paginées ──────────────────────────────────────────
def get_transactions(
    search:    str  = "",
    date_from: str  = None,
    date_to:   str  = None,
    statut:    str  = None,
    order_by:  str  = "date",
    desc:      bool = True,
    page:      int  = 1,
    per_page:  int  = 25,
):
    q = Transaction.query

    if search:
        q = q.filter(Transaction.client.ilike(f"%{search}%"))
    if date_from:
        q = q.filter(Transaction.date >= date_from)
    if date_to:
        q = q.filter(Transaction.date <= date_to)
    if statut:
        q = q.filter(Transaction.statut == statut)

    # Tri sécurisé (pas d'injection SQL)
    safe_cols = {"date", "client", "montant_recu", "transport", "autres", "created_at"}
    col_name  = order_by if order_by in safe_cols else "date"
    col_attr  = getattr(Transaction, col_name)
    q = q.order_by(col_attr.desc() if desc else col_attr.asc())

    paginated = q.paginate(page=page, per_page=per_page, error_out=False)
    return paginated.items, paginated.total
