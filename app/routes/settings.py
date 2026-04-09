"""Routes Paramètres, Alertes & Gestion utilisateurs"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import User, Transaction
from app.services.stats import get_global_stats

bp = Blueprint("settings", __name__)

# ── Alertes ────────────────────────────────────────────────────────────────────
MARGE_SEUIL = 20   # % — alerte si marge < ce seuil

@bp.route("/alerts")
@login_required
def alerts():
    deficits = Transaction.query.filter(
        (Transaction.montant_recu - Transaction.transport - Transaction.autres) < 0
    ).order_by(Transaction.date.desc()).all()

    low_margin = [t for t in Transaction.query.filter(
        Transaction.montant_recu > 0).all()
        if 0 <= t.marge < MARGE_SEUIL]
    low_margin.sort(key=lambda x: x.marge)

    from datetime import date
    mois = date.today().isoformat()[:7]
    ce_mois = Transaction.query.filter(
        Transaction.date.like(f"{mois}%")
    ).order_by(Transaction.date.desc()).all()

    return render_template("settings/alerts.html",
        active="alerts", stats=get_global_stats(),
        deficits=deficits, low_margin=low_margin[:10],
        ce_mois=ce_mois, seuil=MARGE_SEUIL)


# ── Paramètres (profil + mdp) ──────────────────────────────────────────────────
@bp.route("/settings")
@login_required
def settings():
    return render_template("settings/index.html",
        active="settings", stats=get_global_stats(),
        user=current_user)

@bp.route("/settings/password", methods=["POST"])
@login_required
def change_password():
    current_pw = request.form.get("current_password", "")
    new_pw     = request.form.get("new_password", "")
    confirm    = request.form.get("confirm_password", "")
    if not current_user.check_password(current_pw):
        flash("❌ Mot de passe actuel incorrect.", "error")
        return redirect(url_for("settings.settings"))
    if len(new_pw) < 6:
        flash("❌ Nouveau mot de passe trop court (min 6 caractères).", "error")
        return redirect(url_for("settings.settings"))
    if new_pw != confirm:
        flash("❌ Les mots de passe ne correspondent pas.", "error")
        return redirect(url_for("settings.settings"))
    current_user.set_password(new_pw)
    db.session.commit()
    flash("✅ Mot de passe modifié avec succès.", "success")
    return redirect(url_for("settings.settings"))

@bp.route("/settings/profile", methods=["POST"])
@login_required
def update_profile():
    username = request.form.get("username", "").strip()
    email    = request.form.get("email", "").strip()
    if not username or len(username) < 2:
        flash("❌ Nom d'utilisateur invalide.", "error")
        return redirect(url_for("settings.settings"))
    existing = User.query.filter(
        User.username == username, User.id != current_user.id).first()
    if existing:
        flash("❌ Ce nom d'utilisateur est déjà pris.", "error")
        return redirect(url_for("settings.settings"))
    current_user.username = username
    current_user.email    = email
    db.session.commit()
    flash("✅ Profil mis à jour.", "success")
    return redirect(url_for("settings.settings"))


# ── Gestion utilisateurs (admin seulement) ─────────────────────────────────────
@bp.route("/settings/users")
@login_required
def users():
    if current_user.role != "admin":
        flash("❌ Accès réservé à l'administrateur.", "error")
        return redirect(url_for("dashboard.index"))
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template("settings/users.html",
        active="settings", users=all_users)

@bp.route("/settings/users/add", methods=["POST"])
@login_required
def add_user():
    if current_user.role != "admin":
        flash("❌ Accès refusé.", "error")
        return redirect(url_for("dashboard.index"))
    username = request.form.get("username", "").strip()
    email    = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    role     = request.form.get("role", "viewer")

    if not username or len(username) < 2:
        flash("❌ Nom d'utilisateur invalide.", "error")
        return redirect(url_for("settings.users"))
    if len(password) < 6:
        flash("❌ Mot de passe trop court (min 6 caractères).", "error")
        return redirect(url_for("settings.users"))
    if User.query.filter_by(username=username).first():
        flash(f"❌ L'utilisateur « {username} » existe déjà.", "error")
        return redirect(url_for("settings.users"))

    user = User(username=username, email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    flash(f"✅ Utilisateur « {username} » créé ({role}).", "success")
    return redirect(url_for("settings.users"))

@bp.route("/settings/users/<int:uid>/delete", methods=["POST"])
@login_required
def delete_user(uid):
    if current_user.role != "admin":
        flash("❌ Accès refusé.", "error")
        return redirect(url_for("dashboard.index"))
    if uid == current_user.id:
        flash("❌ Tu ne peux pas supprimer ton propre compte.", "error")
        return redirect(url_for("settings.users"))
    user = User.query.get_or_404(uid)
    db.session.delete(user)
    db.session.commit()
    flash(f"✅ Utilisateur « {user.username} » supprimé.", "success")
    return redirect(url_for("settings.users"))

@bp.route("/settings/users/<int:uid>/role", methods=["POST"])
@login_required
def change_role(uid):
    if current_user.role != "admin":
        flash("❌ Accès refusé.", "error")
        return redirect(url_for("dashboard.index"))
    user = User.query.get_or_404(uid)
    new_role = request.form.get("role", "viewer")
    user.role = new_role
    db.session.commit()
    flash(f"✅ Rôle de « {user.username} » changé en {new_role}.", "success")
    return redirect(url_for("settings.users"))

@bp.route("/settings/users/<int:uid>/reset-password", methods=["POST"])
@login_required
def reset_user_password(uid):
    if current_user.role != "admin":
        flash("❌ Accès refusé.", "error")
        return redirect(url_for("dashboard.index"))
    user = User.query.get_or_404(uid)
    new_pw = request.form.get("new_password", "")
    if len(new_pw) < 6:
        flash("❌ Mot de passe trop court (min 6 caractères).", "error")
        return redirect(url_for("settings.users"))
    user.set_password(new_pw)
    db.session.commit()
    flash(f"✅ Mot de passe de « {user.username} » réinitialisé.", "success")
    return redirect(url_for("settings.users"))
