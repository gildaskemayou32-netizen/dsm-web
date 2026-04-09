"""Routes IA — Suggestions (Pro) et Chat (Pro+)"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import login_required, current_user
from app.services.billing import get_active_sub

bp = Blueprint("ai", __name__, url_prefix="/ai")


def _require_plan(plan: str):
    """Vérifie que l'utilisateur a le bon plan."""
    sub = get_active_sub(current_user.id)
    plans_order = {"free": 0, "pro": 1, "pro_plus": 2}
    required = plans_order.get(plan, 1)
    current  = plans_order.get(sub.plan, 0)
    if current < required:
        return sub.plan
    return None   # OK


# ── Suggestions automatiques (Pro) ────────────────────────────────────────────
@bp.route("/suggestions")
@login_required
def suggestions():
    bad_plan = _require_plan("pro")
    if bad_plan:
        flash("💡 Les suggestions intelligentes sont disponibles à partir du plan Pro.", "warning")
        return redirect(url_for("billing.pricing"))

    from app.services.suggestions import generate_suggestions
    suggs = generate_suggestions()
    sub   = get_active_sub(current_user.id)
    return render_template("ai/suggestions.html",
                           active="ai", suggestions=suggs, sub=sub)


# ── Chat IA (Pro+) ─────────────────────────────────────────────────────────────
@bp.route("/chat")
@login_required
def chat():
    bad_plan = _require_plan("pro_plus")
    if bad_plan:
        flash("🤖 L'assistant IA est disponible uniquement avec le plan Pro+.", "warning")
        return redirect(url_for("billing.pricing"))

    # Initialiser l'historique de conversation en session
    if "chat_history" not in session:
        session["chat_history"] = []

    sub = get_active_sub(current_user.id)
    return render_template("ai/chat.html",
                           active="ai",
                           history=session["chat_history"],
                           sub=sub)


@bp.route("/chat/send", methods=["POST"])
@login_required
def chat_send():
    """Endpoint AJAX pour envoyer un message."""
    bad_plan = _require_plan("pro_plus")
    if bad_plan:
        return jsonify({"error": "Plan Pro+ requis"}), 403

    data    = request.get_json() or {}
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"error": "Message vide"}), 400
    if len(message) > 1000:
        return jsonify({"error": "Message trop long (max 1000 caractères)"}), 400

    # Récupérer l'historique
    history = session.get("chat_history", [])

    # Obtenir la réponse IA
    from app.services.ai_chat import ask_ai
    response = ask_ai(message, history)

    # Mettre à jour l'historique (max 20 échanges)
    history.append({"role": "user",      "content": message})
    history.append({"role": "assistant", "content": response})
    if len(history) > 40:   # 20 échanges × 2
        history = history[-40:]
    session["chat_history"] = history
    session.modified = True

    return jsonify({
        "response": response,
        "message":  message
    })


@bp.route("/chat/clear", methods=["POST"])
@login_required
def chat_clear():
    """Efface l'historique de conversation."""
    session.pop("chat_history", None)
    return jsonify({"status": "cleared"})


@bp.route("/chat/questions")
@login_required
def suggested_questions():
    """Retourne des questions suggérées basées sur les données."""
    bad_plan = _require_plan("pro_plus")
    if bad_plan:
        return jsonify({"error": "Plan Pro+ requis"}), 403

    try:
        from app.services.stats import get_global_stats
        stats = get_global_stats()
        questions = [
            f"Quel est mon client le plus rentable ?",
            f"Comment augmenter mes ventes ce mois ?",
            f"Pourquoi ma marge est de {stats['marge_moy']:.0f}% ? Est-ce bon ?",
            f"Comment réduire mes frais de déplacement ?",
            f"Quelle stratégie marketing appliquer au Cameroun ?",
            f"Quels clients devrais-je fidéliser en priorité ?",
            f"Comment atteindre {stats['benefice_mois']*2:,.0f} FCFA de bénéfice le mois prochain ?",
            f"Analyse mes {stats['alertes']} transactions déficitaires",
        ]
        return jsonify({"questions": questions})
    except Exception:
        return jsonify({"questions": [
            "Comment augmenter mes ventes ?",
            "Quel client est le plus rentable ?",
            "Comment réduire mes dépenses ?",
            "Quelle stratégie marketing appliquer ?",
        ]})
