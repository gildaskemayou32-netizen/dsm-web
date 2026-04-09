"""
Suggestions automatiques intelligentes — Plan Pro
Analyse les données de l'utilisateur et génère des recommandations
sans IA externe (logique métier pure, fonctionne offline).
"""
from datetime import date, timedelta
from app import db
from app.models import Transaction
from app.services.stats import get_global_stats, get_client_stats, get_monthly


def generate_suggestions() -> list[dict]:
    """
    Génère toutes les suggestions basées sur les données réelles.
    Retourne une liste de suggestions triées par priorité.
    """
    suggestions = []

    try:
        stats   = get_global_stats()
        clients = get_client_stats(20)
        monthly = get_monthly(6)
        txs     = Transaction.query.order_by(Transaction.date.desc()).limit(100).all()

        if not txs:
            return [{
                "type": "info", "icon": "📝",
                "title": "Commencez à enregistrer vos transactions",
                "text": "Ajoutez vos premières transactions pour recevoir des suggestions personnalisées.",
                "priority": 1
            }]

        # ── 1. Analyse des marges ──────────────────────────────────────────────
        suggestions += _analyse_marges(stats, txs)

        # ── 2. Analyse des clients ────────────────────────────────────────────
        suggestions += _analyse_clients(clients, stats)

        # ── 3. Analyse des dépenses ───────────────────────────────────────────
        suggestions += _analyse_depenses(stats, txs)

        # ── 4. Analyse des tendances mensuelles ───────────────────────────────
        suggestions += _analyse_tendances(monthly)

        # ── 5. Alertes financières ────────────────────────────────────────────
        suggestions += _alertes_financieres(stats, txs)

        # Trier par priorité (1 = urgent, 5 = info)
        suggestions.sort(key=lambda x: x.get("priority", 5))

    except Exception as e:
        suggestions = [{
            "type": "info", "icon": "ℹ️",
            "title": "Analyse en cours",
            "text": "Les suggestions seront disponibles dès que vous aurez plus de données.",
            "priority": 5
        }]

    return suggestions[:12]   # max 12 suggestions affichées


# ── Analyse des marges ─────────────────────────────────────────────────────────
def _analyse_marges(stats, txs) -> list:
    s = []
    marge = stats.get("marge_moy", 0)

    if marge < 20:
        s.append({
            "type": "danger", "icon": "📉",
            "title": "Marge moyenne critique",
            "text": f"Ta marge moyenne est de {marge:.1f}%. C'est en dessous du seuil recommandé de 20%. Revois tes tarifs ou réduis tes frais de transport.",
            "action": "Voir les transactions déficitaires",
            "action_url": "/alerts",
            "priority": 1
        })
    elif marge < 40:
        s.append({
            "type": "warning", "icon": "⚠️",
            "title": "Marge à améliorer",
            "text": f"Ta marge de {marge:.1f}% est acceptable mais peut être améliorée. Essaie d'augmenter tes prix de 10% sur les prochains clients.",
            "priority": 2
        })
    elif marge >= 70:
        s.append({
            "type": "success", "icon": "🏆",
            "title": "Excellente marge !",
            "text": f"Bravo ! Ta marge de {marge:.1f}% est excellente. Tu es dans les meilleures pratiques. Continue ainsi.",
            "priority": 5
        })

    # Transactions avec marge négative
    deficits = [t for t in txs if t.benefice < 0]
    if len(deficits) >= 3:
        clients_deficit = list({t.client for t in deficits})
        s.append({
            "type": "danger", "icon": "🚨",
            "title": f"{len(deficits)} transactions en déficit",
            "text": f"Tu perds de l'argent sur {len(deficits)} transactions ({', '.join(clients_deficit[:3])}...). Augmente tes tarifs ou refuse ces clients peu rentables.",
            "action": "Voir les alertes",
            "action_url": "/alerts",
            "priority": 1
        })
    return s


# ── Analyse des clients ────────────────────────────────────────────────────────
def _analyse_clients(clients, stats) -> list:
    s = []
    if not clients:
        return s

    # Meilleur client
    best = clients[0]
    if best["total_ben"] > 0:
        s.append({
            "type": "success", "icon": "⭐",
            "title": f"Fidélise {best['client']}",
            "text": f"{best['client']} est ton client le plus rentable avec {best['total_ben']:,.0f} FCFA de bénéfice. Propose-lui une offre spéciale ou un tarif préférentiel pour le garder.",
            "priority": 3
        })

    # Client avec beaucoup de transactions mais marge faible
    for c in clients:
        if c["transactions"] >= 5 and c["marge_moy"] < 25 and c["total_ben"] > 0:
            s.append({
                "type": "warning", "icon": "💡",
                "title": f"Renégocier avec {c['client']}",
                "text": f"Tu travailles beaucoup pour {c['client']} ({c['transactions']} transactions) mais ta marge n'est que de {c['marge_moy']:.1f}%. Augmente ton tarif de 15-20%.",
                "priority": 2
            })
            break

    # Concentration risque (1 client = +50% revenus)
    total_recu = stats.get("total_recu", 1)
    if total_recu > 0 and clients[0]["total_recu"] / total_recu > 0.5:
        s.append({
            "type": "warning", "icon": "⚖️",
            "title": "Risque de dépendance client",
            "text": f"{clients[0]['client']} représente plus de 50% de tes revenus. Diversifie ta clientèle pour réduire ce risque.",
            "priority": 2
        })

    # Peu de clients
    if stats.get("clients_count", 0) < 5:
        s.append({
            "type": "info", "icon": "👥",
            "title": "Élargis ta base clients",
            "text": f"Tu as {stats.get('clients_count', 0)} client(s) actif(s). Essaie d'en acquérir au moins 10 pour stabiliser tes revenus.",
            "priority": 3
        })
    return s


# ── Analyse des dépenses ───────────────────────────────────────────────────────
def _analyse_depenses(stats, txs) -> list:
    s = []
    total_recu  = stats.get("total_recu", 1)
    total_frais = stats.get("total_frais", 0)

    if total_recu > 0:
        ratio_frais = total_frais / total_recu * 100
        if ratio_frais > 40:
            s.append({
                "type": "danger", "icon": "💸",
                "title": "Frais trop élevés",
                "text": f"Tes frais représentent {ratio_frais:.1f}% de tes revenus. C'est trop. Réduis le transport ou groupe tes déplacements pour économiser.",
                "priority": 1
            })
        elif ratio_frais > 25:
            s.append({
                "type": "warning", "icon": "🚗",
                "title": "Optimise tes frais de transport",
                "text": f"Tes frais de déplacement ({ratio_frais:.1f}% des revenus) peuvent être réduits. Regroupe tes visites par zone géographique.",
                "priority": 3
            })

    # Transport vs autres
    transport_total = sum(t.transport for t in txs)
    autres_total    = sum(t.autres for t in txs)
    if transport_total > 0 and autres_total / max(transport_total, 1) > 1.5:
        s.append({
            "type": "info", "icon": "📦",
            "title": "Autres dépenses élevées",
            "text": "Tes autres dépenses dépassent ton transport. Identifie les postes les plus coûteux et cherche des alternatives moins chères.",
            "priority": 4
        })
    return s


# ── Analyse tendances mensuelles ──────────────────────────────────────────────
def _analyse_tendances(monthly) -> list:
    s = []
    if len(monthly) < 2:
        return s

    last  = monthly[-1]
    prev  = monthly[-2]

    # Baisse de revenus
    if prev["revenus"] > 0 and last["revenus"] < prev["revenus"] * 0.8:
        baisse = round((prev["revenus"] - last["revenus"]) / prev["revenus"] * 100)
        s.append({
            "type": "danger", "icon": "📉",
            "title": f"Baisse de revenus de {baisse}% ce mois",
            "text": f"Tes revenus ont baissé de {baisse}% par rapport au mois précédent. Contacte tes anciens clients ou prospecte activement.",
            "action": "Voir les analytiques",
            "action_url": "/analytics",
            "priority": 1
        })

    # Hausse de revenus
    elif prev["revenus"] > 0 and last["revenus"] > prev["revenus"] * 1.2:
        hausse = round((last["revenus"] - prev["revenus"]) / prev["revenus"] * 100)
        s.append({
            "type": "success", "icon": "📈",
            "title": f"Revenus en hausse de {hausse}% !",
            "text": f"Excellente performance ce mois ! Identifie ce qui a bien marché et reproduis-le.",
            "priority": 5
        })

    # Meilleur mois détecté
    if len(monthly) >= 3:
        best_month = max(monthly, key=lambda x: x["benefice"])
        if best_month["label"] != last["label"]:
            s.append({
                "type": "info", "icon": "🗓️",
                "title": f"{best_month['label']} est ton meilleur mois",
                "text": f"Tu as fait {best_month['benefice']:,.0f} FCFA de bénéfice en {best_month['label']}. Analyse ce qui s'est passé et prépare-toi pour cette période.",
                "priority": 4
            })
    return s


# ── Alertes financières ────────────────────────────────────────────────────────
def _alertes_financieres(stats, txs) -> list:
    s = []

    # Pas de transaction aujourd'hui ni hier
    today     = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    recent_tx = [t for t in txs if t.date >= yesterday]
    if not recent_tx and stats.get("total_transactions", 0) > 10:
        s.append({
            "type": "info", "icon": "⏰",
            "title": "Pas d'activité récente",
            "text": "Aucune transaction enregistrée ces 2 derniers jours. Si c'est normal, parfait. Sinon, n'oublie pas de saisir tes données régulièrement.",
            "priority": 4
        })

    # Bénéfice du jour = 0
    if stats.get("benefice_jour", 0) == 0 and stats.get("transactions_jour", 0) == 0:
        s.append({
            "type": "info", "icon": "💡",
            "title": "Suggestion marketing du jour",
            "text": "Journée calme ? C'est le moment parfait pour contacter 2-3 anciens clients et leur proposer tes services.",
            "priority": 4
        })

    # Objectif mensuel (si données suffisantes)
    monthly = get_monthly(3)
    if len(monthly) >= 2:
        avg_monthly = sum(m["benefice"] for m in monthly[:-1]) / len(monthly[:-1])
        current     = monthly[-1]["benefice"]
        if avg_monthly > 0 and current < avg_monthly * 0.5:
            s.append({
                "type": "warning", "icon": "🎯",
                "title": "En retard sur ton objectif mensuel",
                "text": f"Ce mois-ci tu es à {current:,.0f} FCFA vs une moyenne de {avg_monthly:,.0f} FCFA. Il te reste du temps pour rattraper !",
                "priority": 2
            })
    return s
