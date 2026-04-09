"""
Assistant IA Pro+ — Digital Services CM
Fonctionnalités :
  1. Données internes de l'utilisateur (transactions, clients, bénéfices)
  2. Connaissances IA générales (business, marketing, finance)
  3. Recherche web externe (tendances, trading, opportunités, actualités)

Priorité : données internes > IA générale > recherche externe
"""
import os, json, re
from app.services.stats import (
    get_global_stats, get_client_stats,
    get_monthly, get_frais_breakdown
)


# ── Mots-clés déclenchant une recherche web externe ─────────────────────────────
EXTERNAL_KEYWORDS = [
    # Trading & investissement
    "trading", "trade", "forex", "crypto", "bitcoin", "investir", "investissement",
    "action", "bourse", "rendement", "placement", "cryptomonnaie", "binance",
    "500 000 fcfa", "stratégie trading", "capital",
    # Business externe
    "business rentable", "niche", "business en 2025", "business en 2026",
    "opportunité", "idée business", "créer une entreprise", "startup",
    "e-commerce", "dropshipping", "freelance", "passive income",
    # Marketing externe
    "tendance marketing", "stratégie marketing", "réseaux sociaux",
    "tiktok", "instagram", "facebook ads", "google ads", "seo",
    "influencer", "viral", "growth hacking",
    # Actualités économiques
    "actualité", "inflation", "dollar", "euro", "fcfa", "taux de change",
    "économie", "cameroun 2026", "afrique", "marché",
    # Conseils financiers généraux
    "épargne", "retraite", "assurance", "banque", "crédit", "prêt",
    "microfinance", "financement", "subvention",
]


def needs_web_search(question: str) -> bool:
    """Détecte si la question nécessite une recherche externe."""
    q = question.lower()
    return any(kw in q for kw in EXTERNAL_KEYWORDS)


def is_internal_question(question: str) -> bool:
    """Détecte si la question porte sur les données internes de l'app."""
    q = question.lower()
    internal = [
        "mon", "mes", "ma", "notre", "nos",
        "client", "transaction", "bénéfice", "vente", "revenu",
        "dépense", "marge", "frais", "profit", "perte",
        "meilleur", "rentable", "ce mois", "aujourd'hui",
    ]
    return any(kw in q for kw in internal)


# ── Contexte données internes ────────────────────────────────────────────────────
def get_business_context() -> str:
    try:
        stats   = get_global_stats()
        clients = get_client_stats(10)
        monthly = get_monthly(6)
        frais   = get_frais_breakdown()

        top_clients = "\n".join([
            f"  - {c['client']}: {c['total_recu']:,.0f} FCFA reçus, "
            f"{c['total_ben']:,.0f} FCFA bénéfice, marge {c['marge_moy']:.1f}%"
            for c in clients[:5]
        ]) or "Aucun client enregistré"

        trend = "\n".join([
            f"  - {m['label']}: revenus {m['revenus']:,.0f} FCFA, "
            f"bénéfice {m['benefice']:,.0f} FCFA"
            for m in monthly
        ]) or "Données insuffisantes"

        return f"""
DONNÉES RÉELLES DE L'ENTREPRISE :

📊 STATISTIQUES GLOBALES :
- Revenus totaux       : {stats['total_recu']:,.0f} FCFA
- Bénéfice net total   : {stats['total_benefice']:,.0f} FCFA
- Total frais          : {stats['total_frais']:,.0f} FCFA
- Marge moyenne        : {stats['marge_moy']:.1f}%
- Transactions         : {stats['total_transactions']}
- Clients actifs       : {stats['clients_count']}
- Meilleur client      : {stats['meilleur_client']}
- Déficits             : {stats['alertes']} transactions
- Bénéfice aujourd'hui : {stats['benefice_jour']:,.0f} FCFA
- Bénéfice ce mois     : {stats['benefice_mois']:,.0f} FCFA

💼 FRAIS :
- Transport  : {frais['transport']:,.0f} FCFA
- Autres     : {frais['autres']:,.0f} FCFA

👥 TOP CLIENTS :
{top_clients}

📈 TENDANCES (6 mois) :
{trend}

Devise : FCFA. Localisation : Cameroun.
""".strip()
    except Exception:
        return "Données internes non disponibles."


# ── Appel principal à l'API Claude avec web search ───────────────────────────────
def ask_ai(user_message: str, conversation_history: list) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY", "")

    if not api_key:
        return _smart_fallback(user_message)

    try:
        import urllib.request, urllib.error

        # Détecter le type de question
        needs_web  = needs_web_search(user_message)
        is_internal= is_internal_question(user_message)

        business_ctx = get_business_context()

        # Système prompt adapté au type de question
        system_prompt = f"""Tu es l'assistant IA Pro+ de Digital Services CM, une application de gestion des dépenses et revenus au Cameroun.

Tu as TROIS sources d'information que tu utilises selon la question :

1. DONNÉES INTERNES (priorité 1 si pertinentes) :
{business_ctx}

2. CONNAISSANCES GÉNÉRALES IA (priorité 2) :
   - Business, marketing, finance, stratégie
   - Utilise tes connaissances générales pour répondre

3. RECHERCHE EXTERNE (priorité 3 si nécessaire) :
   - Questions sur : trading, investissement, tendances marché, actualités économiques,
     nouvelles stratégies business, idées externes, cryptomonnaies, forex, etc.
   - Dans ces cas, utilise tes connaissances actuelles et indique que c'est basé sur
     les tendances générales du marché

RÈGLES IMPÉRATIVES :
- Si la question concerne les données de l'utilisateur (mes clients, mes ventes, etc.) → utilise les données internes
- Si la question concerne le trading/investissement → donne des stratégies réalistes ET mentionne TOUJOURS les risques
- Si la question concerne un business externe → propose des idées concrètes adaptées au contexte africain/camerounais
- Ne jamais inventer des prix ou données de marché précises en temps réel
- Toujours répondre en français
- Réponses structurées avec titres, points clés, exemples concrets
- Maximum 4 paragraphes ou sections

FORMAT DE RÉPONSE :
- Utilise **gras** pour les points importants
- Utilise des listes avec • pour les éléments
- Mentionne les risques quand c'est pertinent (investissement, trading)
- Adapte au contexte camerounais (Mobile Money, FCFA, marché local)
- Sois direct, pratique et actionnable"""

        # Messages de conversation
        messages = []
        for msg in conversation_history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_message})

        # Préparer les tools (web search si nécessaire)
        tools = []
        if needs_web:
            tools = [{
                "type": "web_search_20250305",
                "name": "web_search"
            }]

        payload_dict = {
            "model":      "claude-sonnet-4-6",
            "max_tokens": 1500,
            "system":     system_prompt,
            "messages":   messages,
        }
        if tools:
            payload_dict["tools"] = tools

        payload = json.dumps(payload_dict).encode("utf-8")

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "Content-Type":      "application/json",
                "x-api-key":         api_key,
                "anthropic-version": "2023-06-01",
                "anthropic-beta":    "web-search-2025-03-05",
            },
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=45) as resp:
            result  = json.loads(resp.read().decode("utf-8"))
            content = result.get("content", [])

            # Extraire le texte de la réponse (peut contenir tool_use blocks)
            text_parts = []
            for block in content:
                if block.get("type") == "text":
                    text_parts.append(block["text"])

            answer = "\n".join(text_parts).strip()

            # Indiquer si une recherche web a été utilisée
            used_web = any(
                b.get("type") in ("tool_use", "tool_result")
                for b in content
            )
            if used_web and answer:
                answer += "\n\n---\n*🌐 Réponse enrichie avec des données web actualisées*"

            return answer if answer else _smart_fallback(user_message)

    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        # Si erreur 400 (tool non supporté), retry sans web search
        if e.code == 400 and "web_search" in err_body:
            return _ask_ai_no_web(user_message, conversation_history, api_key)
        return _smart_fallback(user_message)
    except Exception:
        return _smart_fallback(user_message)


def _ask_ai_no_web(user_message: str, conversation_history: list, api_key: str) -> str:
    """Fallback sans web search si l'outil n'est pas disponible."""
    import urllib.request
    business_ctx = get_business_context()
    system = f"""Tu es l'assistant IA Pro+ de Digital Services CM (Cameroun).
Données internes : {business_ctx}
Réponds en français. Sois pratique et concret. Max 4 sections.
Pour les questions de trading/investissement : donne des stratégies réalistes et mentionne les risques.
Pour les questions business externes : adapte au contexte camerounais."""

    messages = [{"role": m["role"], "content": m["content"]}
                for m in conversation_history[-10:]]
    messages.append({"role": "user", "content": user_message})

    payload = json.dumps({
        "model": "claude-sonnet-4-6",
        "max_tokens": 1200,
        "system": system,
        "messages": messages,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type":      "application/json",
            "x-api-key":         api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            for block in result.get("content", []):
                if block.get("type") == "text":
                    return block["text"]
    except Exception:
        pass
    return _smart_fallback(user_message)


# ── Fallback intelligent (sans API) ─────────────────────────────────────────────
def _smart_fallback(question: str) -> str:
    """
    Répond intelligemment sans API externe.
    Couvre les données internes ET les questions externes courantes.
    """
    q = question.lower()

    try:
        stats   = get_global_stats()
        clients = get_client_stats(5)
        monthly = get_monthly(3)
        frais   = get_frais_breakdown()
    except Exception:
        stats   = {}
        clients = []
        monthly = []
        frais   = {"transport": 0, "autres": 0}

    # ── Questions INTERNES ───────────────────────────────────────────────────────

    if any(w in q for w in ["meilleur client", "client rentable", "top client"]):
        if clients:
            b = clients[0]
            return (
                f"🏆 **{b['client']}** est ton client le plus rentable.\n\n"
                f"• **Bénéfice net** : {b['total_ben']:,.0f} FCFA\n"
                f"• **Revenus générés** : {b['total_recu']:,.0f} FCFA\n"
                f"• **Transactions** : {b['transactions']}\n"
                f"• **Marge moyenne** : {b['marge_moy']:.1f}%\n\n"
                f"💡 **Conseil** : Propose-lui un tarif préférentiel ou un service supplémentaire "
                f"pour renforcer cette relation. C'est ton actif le plus précieux."
            )

    if any(w in q for w in ["bénéfice baisse", "revenus baissent", "pourquoi baisse", "moins qu"]):
        if len(monthly) >= 2:
            last, prev = monthly[-1], monthly[-2]
            diff = last["benefice"] - prev["benefice"]
            if diff < 0:
                return (
                    f"📉 **Baisse de {abs(diff):,.0f} FCFA** entre {prev['label']} et {last['label']}.\n\n"
                    f"**Causes probables :**\n"
                    f"• Moins de transactions ce mois ({last['transactions']} vs {prev['transactions']})\n"
                    f"• Frais plus élevés ou clients moins rentables\n"
                    f"• Période creuse saisonnière\n\n"
                    f"**Actions immédiates :**\n"
                    f"• Contacte tes 3 meilleurs clients pour de nouveaux besoins\n"
                    f"• Lance une promotion courte durée\n"
                    f"• Vérifie si tes frais de transport ont augmenté"
                )

    if any(w in q for w in ["augmenter ventes", "augmenter revenus", "plus de clients", "croître"]):
        marge = stats.get("marge_moy", 0)
        nb    = stats.get("clients_count", 0)
        return (
            f"📈 **3 stratégies pour augmenter tes revenus :**\n\n"
            f"**1. Fidélise tes clients actuels**\n"
            f"Tu as {nb} client(s). Chacun peut commander 2× plus si tu proposes des services complémentaires.\n\n"
            f"**2. Augmente tes tarifs progressivement**\n"
            f"Ta marge est de {marge:.1f}%. Une hausse de 10–15% sur les nouveaux clients est souvent acceptée sans perte.\n\n"
            f"**3. Système de parrainage**\n"
            f"Offre 1 service gratuit à tout client qui t'amène un nouveau client. "
            f"C'est la méthode la plus économique pour croître au Cameroun."
        )

    if any(w in q for w in ["réduire frais", "dépenses", "transport", "coûts"]):
        ratio = frais["transport"] / max(stats.get("total_recu", 1), 1) * 100
        return (
            f"💸 **Tes frais représentent {ratio:.1f}% de tes revenus.**\n\n"
            f"**Stratégies pour réduire :**\n"
            f"• **Regroupe tes déplacements** par zone géographique (même quartier, même journée)\n"
            f"• **Négocie des forfaits** avec tes clients réguliers (transport inclus dans le prix)\n"
            f"• **Appels/WhatsApp** d'abord pour les petites demandes — évite les déplacements inutiles\n"
            f"• **Tarif minimum** : fixe un montant en dessous duquel tu ne te déplaces pas\n\n"
            f"💡 Objectif : garder tes frais en dessous de **25% de tes revenus**."
        )

    # ── Questions TRADING / INVESTISSEMENT ───────────────────────────────────────

    if any(w in q for w in ["trading", "forex", "crypto", "bitcoin", "bourse"]):
        return (
            f"📊 **Stratégies trading — contexte Afrique/Cameroun**\n\n"
            f"**⚠️ AVERTISSEMENT** : Le trading comporte des risques importants. "
            f"Ne jamais investir plus que ce qu'on peut se permettre de perdre.\n\n"
            f"**1. Forex (devises) — Le plus accessible**\n"
            f"• Paires recommandées pour débutants : EUR/USD, GBP/USD\n"
            f"• Plateformes : MetaTrader 4/5, accessible depuis le Cameroun\n"
            f"• Capital minimum recommandé : 100 000 FCFA\n"
            f"• Stratégie : trading en tendance (suivre la direction principale)\n\n"
            f"**2. Crypto — Potentiel élevé, risque élevé**\n"
            f"• Bitcoin et Ethereum sont les plus stables des cryptos\n"
            f"• Stratégie DCA (Dollar Cost Averaging) : investir une somme fixe chaque mois\n"
            f"• Plateformes accessibles depuis le Cameroun : Binance, Yellow Card\n\n"
            f"**3. Règles de gestion du capital**\n"
            f"• Ne jamais risquer plus de 2% du capital par trade\n"
            f"• Toujours utiliser un stop-loss\n"
            f"• Commencer en mode démo avant le vrai argent\n\n"
            f"*🌐 Pour les prix en temps réel, consulte TradingView ou Binance.*"
        )

    if any(w in q for w in ["investir", "investissement", "placer", "épargne", "500 000"]):
        return (
            f"💰 **Comment investir intelligemment en 2026 (contexte Cameroun)**\n\n"
            f"**Option 1 : Développer ton activité actuelle (meilleur ROI)**\n"
            f"• Investi dans du matériel ou des compétences pour offrir plus de services\n"
            f"• Coût marketing (Facebook Ads) : 20 000–50 000 FCFA/mois\n"
            f"• ROI potentiel : 200–400% si bien exécuté\n\n"
            f"**Option 2 : Microfinance / Tontine numérique**\n"
            f"• Rejoins ou crée un groupe d'épargne (njangi)\n"
            f"• Taux de rendement : 10–20% selon les accords\n\n"
            f"**Option 3 : Immobilier locatif**\n"
            f"• Terrain à Douala/Yaoundé en périphérie : bonne valorisation sur 5 ans\n"
            f"• Rendement locatif : 8–15% par an\n\n"
            f"**Option 4 : Crypto (avec prudence)**\n"
            f"• Allouer max 10–20% de l'épargne\n"
            f"• Stratégie DCA sur Bitcoin uniquement\n\n"
            f"⚠️ *Ces conseils sont informatifs. Consulte un conseiller financier pour des décisions importantes.*"
        )

    # ── Questions BUSINESS EXTERNE ────────────────────────────────────────────────

    if any(w in q for w in ["business rentable", "niche", "idée business", "business en 2026", "gagner argent"]):
        return (
            f"🚀 **Niches business rentables en 2026 — Cameroun & Afrique**\n\n"
            f"**1. Services numériques (forte croissance)**\n"
            f"• Création de sites web / applications\n"
            f"• Gestion des réseaux sociaux pour PME\n"
            f"• Formation en ligne (YouTube, TikTok, WhatsApp)\n"
            f"• Design graphique et identité visuelle\n\n"
            f"**2. Commerce & Distribution**\n"
            f"• Revente de produits chinois (Aliexpress → marché local)\n"
            f"• Agro-business (transformation alimentaire locale)\n"
            f"• Import-export de produits cosmétiques\n\n"
            f"**3. Services à la personne**\n"
            f"• Traiteur / livraison de repas\n"
            f"• Coiffure / esthétique à domicile\n"
            f"• Cours particuliers (math, langues, informatique)\n\n"
            f"**4. Fintech / Mobile Money**\n"
            f"• Point de retrait Mobile Money dans quartiers mal couverts\n"
            f"• Vente de crédit téléphonique en gros\n\n"
            f"💡 **Meilleur conseil** : Commence par ce que tu sais déjà faire, "
            f"puis numé­rise-le pour toucher plus de clients.\n\n"
            f"*🌐 Tendances basées sur les marchés émergents africains 2025-2026.*"
        )

    if any(w in q for w in ["marketing", "stratégie marketing", "tiktok", "instagram", "publicité", "vendre plus"]):
        return (
            f"📣 **Stratégies marketing qui fonctionnent en 2026**\n\n"
            f"**1. TikTok & Vidéo courte (tendance #1)**\n"
            f"• Montre ton travail en coulisses (avant/après)\n"
            f"• 1 vidéo par jour = croissance organique gratuite\n"
            f"• Hashtags locaux : #Cameroun #Douala #Yaoundé\n\n"
            f"**2. WhatsApp Business (le plus efficace localement)**\n"
            f"• Catalogue de tes services avec prix\n"
            f"• Statuts WhatsApp = publicité gratuite quotidienne\n"
            f"• Groupes clients pour fidélisation\n\n"
            f"**3. Facebook Ads (ROI mesurable)**\n"
            f"• Budget : 5 000–20 000 FCFA/semaine pour commencer\n"
            f"• Ciblage : Cameroun + intérêts liés à ton secteur\n"
            f"• Objectif : messages WhatsApp (pas de site requis)\n\n"
            f"**4. Bouche à oreille gamifiée**\n"
            f"• Programme parrainage : -10% pour toi et ton filleul\n"
            f"• Demande des avis Google/Facebook à chaque client satisfait\n\n"
            f"*🌐 Basé sur les tendances marketing Afrique francophone 2026.*"
        )

    # ── Réponse générique avec données internes ───────────────────────────────────
    ben    = stats.get("total_benefice", 0)
    marge  = stats.get("marge_moy", 0)
    meilleur = stats.get("meilleur_client", "—")
    alertes  = stats.get("alertes", 0)

    return (
        f"📊 **Résumé de ta situation actuelle :**\n\n"
        f"• Bénéfice total : **{ben:,.0f} FCFA** (marge {marge:.1f}%)\n"
        f"• Meilleur client : **{meilleur}**\n"
        f"• Alertes à surveiller : **{alertes}** transaction(s) en déficit\n\n"
        f"Je peux t'aider sur :\n"
        f"• 📈 **Tes données** : clients, ventes, bénéfices, marges\n"
        f"• 💼 **Business** : idées rentables, niches, stratégies\n"
        f"• 📊 **Trading** : forex, crypto, investissement\n"
        f"• 📣 **Marketing** : TikTok, WhatsApp, Facebook Ads\n"
        f"• 💰 **Finance** : épargne, placement, gestion du capital\n\n"
        f"**Pose ta question — je suis là pour t'aider !**"
    )
