"""
╔══════════════════════════════════════════════════╗
║  Digital Services CM — Reset Admin               ║
║  Lance ce script pour changer nom/email/mdp      ║
║  Usage : python reset_admin.py                   ║
╚══════════════════════════════════════════════════╝
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── ✏️ MODIFIE CES VALEURS ─────────────────────────────────────────────────────
NOUVEAU_USERNAME = "alex_dsm"               # ← ton nouveau nom d'utilisateur
NOUVEAU_EMAIL    = "alex@digitalservices.cm"  # ← ton email
NOUVEAU_MDP      = "MonMotDePasse2026!"     # ← ton nouveau mot de passe (min 6 car.)
# ──────────────────────────────────────────────────────────────────────────────

from app import create_app, db
from app.models import User

app = create_app()
with app.app_context():
    admin = User.query.filter_by(role="admin").first()
    if not admin:
        print("❌ Aucun admin trouvé dans la base de données.")
        print("   Lance d'abord run.py pour initialiser la DB.")
        sys.exit(1)

    print(f"Admin actuel : {admin.username} / {admin.email}")
    print()

    admin.username = NOUVEAU_USERNAME
    admin.email    = NOUVEAU_EMAIL
    admin.set_password(NOUVEAU_MDP)
    db.session.commit()

    print(f"✅ Admin mis à jour !")
    print(f"   Nom d'utilisateur : {admin.username}")
    print(f"   Email             : {admin.email}")
    print(f"   Mot de passe      : {'*' * len(NOUVEAU_MDP)}")
    print()
    print("🚀 Tu peux maintenant te connecter avec les nouveaux identifiants.")
