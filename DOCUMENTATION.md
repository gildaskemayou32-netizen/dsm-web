# 📘 Digital Services CM — Documentation Complète
**Version :** 3.0.0 Web | **Date :** Avril 2026 | **Auteur :** Alex

---

## 📋 Table des matières
1. [Architecture](#1-architecture)
2. [Structure des fichiers](#2-structure)
3. [Modèles de données](#3-modèles-de-données)
4. [Gestion des utilisateurs](#4-gestion-des-utilisateurs)
5. [Système de monétisation](#5-système-de-monétisation)
6. [Intégration Mobile Money](#6-intégration-mobile-money)
7. [Mode Gratuit vs Payant](#7-mode-gratuit-vs-payant)
8. [Déploiement](#8-déploiement)
9. [Stratégie marketing Cameroun](#9-stratégie-marketing-cameroun)
10. [Changer admin + email](#10-changer-admin--email)

---

## 1. Architecture

```
Navigateur (PC / Mobile)
        │
        ▼
  Flask (Python) ← run.py
        │
   ┌────┴─────┐
   │  Routes  │  dashboard, transactions, clients, analytics,
   │          │  alerts, settings, auth, api
   └────┬─────┘
        │
   ┌────┴──────┐
   │ Services  │  stats.py (calculs), export.py (Excel/CSV)
   └────┬──────┘
        │
   ┌────┴──────┐
   │SQLAlchemy │  ORM Python ↔ SQLite (fichier .db local)
   └────┬──────┘
        │
   dsm_enterprise.db  ← fichier base de données
```

---

## 2. Structure des fichiers

```
dsm_web/
├── run.py                    ← Lancement du serveur
├── .env                      ← Variables d'environnement
├── requirements.txt          ← Dépendances Python
├── Procfile                  ← Railway/Render deployment
│
├── app/
│   ├── __init__.py           ← Factory Flask + filtres Jinja2
│   ├── models.py             ← User, Transaction (SQLAlchemy)
│   ├── routes/
│   │   ├── auth.py           ← Login / Logout
│   │   ├── dashboard.py      ← Page principale KPIs
│   │   ├── transactions.py   ← CRUD transactions + exports
│   │   ├── clients.py        ← Fiches clients
│   │   ├── analytics.py      ← Graphiques avancés
│   │   ├── settings.py       ← Profil, utilisateurs, alertes
│   │   └── api.py            ← API JSON pour Chart.js
│   └── services/
│       ├── stats.py          ← Toute la logique statistiques
│       └── export.py         ← Export Excel 3 feuilles + CSV
│
├── static/
│   ├── css/main.css          ← Design système complet
│   └── js/app.js             ← Horloge, sidebar live, alertes
│
└── templates/
    ├── base.html             ← Layout principal (rail + sidebar)
    ├── auth/login.html
    ├── dashboard/index.html  ← KPIs + Chart.js
    ├── transactions/         ← Liste + formulaire
    ├── clients/              ← Grille + fiche détail
    ├── analytics/            ← 4 graphiques
    └── settings/             ← Compte + utilisateurs + alertes
```

---

## 3. Modèles de données

### Transaction
```python
id           : int (auto)
client       : str
montant_recu : float  ≥ 0
transport    : float  ≥ 0
autres       : float  ≥ 0
date         : str    "YYYY-MM-DD"
statut       : str    "soldé" | "partiel" | "déficit"
notes        : str    (optionnel)
created_at   : datetime
updated_at   : datetime

# Propriétés calculées (pas en DB) :
benefice     = montant_recu - transport - autres
total_frais  = transport + autres
marge        = benefice / montant_recu × 100
statut_auto  = "déficit" si benefice < 0, "soldé" sinon
```

### User
```python
id         : int (auto)
username   : str  (unique)
email      : str  (unique)
password_h : str  (hash bcrypt)
role       : str  "admin" | "viewer"
created_at : datetime
last_login : datetime
```

---

## 4. Gestion des utilisateurs

### Rôles

| Action | 👑 Admin | 👁 Viewer |
|--------|----------|-----------|
| Voir dashboard, clients, analytiques | ✅ | ✅ |
| Voir les transactions | ✅ | ✅ |
| Exporter Excel / CSV | ✅ | ✅ |
| Ajouter une transaction | ✅ | ❌ |
| Modifier une transaction | ✅ | ❌ |
| Supprimer une transaction | ✅ | ❌ |
| Gérer les utilisateurs | ✅ | ❌ |
| Changer paramètres app | ✅ | ❌ |

### Ajouter un utilisateur
1. Connecte-toi en **Admin**
2. Va dans **⚙️ Paramètres → 👥 Utilisateurs**
3. Remplis le formulaire : nom, email, mot de passe, rôle
4. Clique **Créer l'utilisateur**

### Cas d'usage multi-utilisateurs
- **Toi (Admin)** : accès total, tu gères tout
- **Comptable** : Viewer → voit les données, exporte, mais ne modifie pas
- **Associé** : Admin → peut aussi ajouter des transactions
- **Client** : Viewer → voit uniquement ses propres données (évolution future)

---

## 5. Système de monétisation

### 💡 Idée principale : SaaS (Software as a Service)

Tu vends un accès à l'application par abonnement mensuel ou annuel.

### Modèle tarifaire suggéré (FCFA)

| Plan | Prix/mois | Fonctionnalités |
|------|-----------|-----------------|
| **Gratuit** | 0 FCFA | 1 utilisateur, 50 transactions/mois, pas d'export |
| **Starter** | 2 000 FCFA | 3 utilisateurs, illimité, export Excel |
| **Business** | 5 000 FCFA | 10 utilisateurs, tout + rapports PDF |
| **Enterprise** | 15 000 FCFA | Illimité, support prioritaire, personnalisation |

### Comment implémenter le freemium dans l'app

Dans `.env`, ajouter :
```env
PLAN=free    # free | starter | business | enterprise
MAX_TX=50    # transactions max pour le plan gratuit
MAX_USERS=1  # utilisateurs max
```

Dans `app/__init__.py` :
```python
@app.context_processor
def inject_plan():
    return {
        'plan': os.getenv('PLAN', 'free'),
        'max_tx': int(os.getenv('MAX_TX', 50)),
    }
```

Dans les routes, vérifier :
```python
if plan == 'free':
    count = Transaction.query.count()
    if count >= max_tx:
        flash("Limite atteinte. Passez au plan Starter.", "warning")
        return redirect(url_for('pricing'))
```

---

## 6. Intégration Mobile Money

### MTN Mobile Money Cameroun

**API MTN MoMo** (https://momodeveloper.mtn.com)

```python
# app/services/payment.py
import requests, uuid

MTN_API_URL  = "https://sandbox.momodeveloper.mtn.com"
MTN_API_KEY  = "TON_API_KEY"
MTN_USER_ID  = "TON_USER_ID"
SUBSCRIPTION = "collections"

def request_payment(phone: str, amount: int, reference: str) -> dict:
    """
    Demande un paiement Mobile Money.
    phone   : numéro au format 237XXXXXXXXX
    amount  : montant en FCFA
    reference: identifiant unique de la transaction
    """
    token = _get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Reference-Id": str(uuid.uuid4()),
        "X-Target-Environment": "sandbox",
        "Ocp-Apim-Subscription-Key": MTN_API_KEY,
        "Content-Type": "application/json",
    }
    body = {
        "amount": str(amount),
        "currency": "XAF",   # FCFA
        "externalId": reference,
        "payer": {"partyIdType": "MSISDN", "partyId": phone},
        "payerMessage": "Abonnement Digital Services CM",
        "payeeNote": f"Plan activé pour {phone}",
    }
    resp = requests.post(
        f"{MTN_API_URL}/{SUBSCRIPTION}/v1_0/requesttopay",
        json=body, headers=headers
    )
    return resp.status_code == 202  # True = demande envoyée

def _get_token() -> str:
    import base64
    creds = base64.b64encode(f"{MTN_USER_ID}:{MTN_API_KEY}".encode()).decode()
    resp = requests.post(
        f"{MTN_API_URL}/{SUBSCRIPTION}/token/",
        headers={"Authorization": f"Basic {creds}",
                 "Ocp-Apim-Subscription-Key": MTN_API_KEY}
    )
    return resp.json()["access_token"]
```

### Orange Money Cameroun

Orange n'a pas d'API publique officielle au Cameroun.
Solutions alternatives :
- **Campay** (https://campay.net) — agrégateur MTN + Orange
- **Notchpay** (https://notchpay.co) — paiements Cameroun
- **PayDunya** — multi-opérateurs Afrique de l'Ouest + Cameroun

### Recommandation : Campay

```python
# Campay — plus simple, supporte MTN + Orange
import requests

def campay_payment(phone: str, amount: int, description: str) -> dict:
    resp = requests.post("https://demo.campay.net/api/collect/", json={
        "amount": str(amount),
        "currency": "XAF",
        "from": phone,
        "description": description,
        "external_reference": str(uuid.uuid4()),
    }, headers={
        "Authorization": "Token TON_TOKEN_CAMPAY",
        "Content-Type": "application/json",
    })
    return resp.json()
```

---

## 7. Mode Gratuit vs Payant

### Architecture freemium recommandée

```
Version GRATUITE (self-hosted)
  → L'utilisateur installe sur son PC
  → Fonctionnalités limitées
  → Pas de support

Version PAYANTE (cloud / SaaS)
  → Hébergé sur Railway/VPS
  → URL personnalisée : ton-entreprise.dsm-app.cm
  → Support WhatsApp
  → Mises à jour automatiques
```

### Limites par plan (à implémenter)

```python
PLANS = {
    "free":       {"tx": 50,        "users": 1,  "export": False, "graphs": False},
    "starter":    {"tx": 500,       "users": 3,  "export": True,  "graphs": True},
    "business":   {"tx": 5000,      "users": 10, "export": True,  "graphs": True},
    "enterprise": {"tx": float('inf'),"users": -1,"export": True,  "graphs": True},
}
```

---

## 8. Déploiement

### Local (PC + téléphone même WiFi)
```bash
pip install -r requirements.txt
python run.py
# → http://192.168.X.X:5000 depuis le téléphone
```

### Railway (gratuit, en ligne)
1. Crée un compte sur https://railway.app
2. New Project → Deploy from GitHub
3. Upload le dossier ou connecte ton repo
4. Railway détecte le `Procfile` automatiquement
5. Variables d'env à configurer dans Railway :
   ```
   SECRET_KEY=un-secret-tres-long-et-aleatoire
   FLASK_ENV=production
   DATABASE_URL=sqlite:///dsm_enterprise.db
   ```
6. Ton app est en ligne en **2 minutes** !

### Render (gratuit)
1. https://render.com → New Web Service
2. Connecte ton GitHub
3. Build Command : `pip install -r requirements.txt`
4. Start Command : `gunicorn run:app`
5. Variables d'env identiques à Railway

### VPS Cameroun (production sérieuse)
- **Hébergeur local** : Camtel, MTN Business, ou DigitalOcean
- Installer Nginx + Gunicorn
- Certificat SSL gratuit avec Let's Encrypt
- Coût estimé : 5 000–15 000 FCFA/mois

---

## 9. Stratégie marketing Cameroun

### Cible principale
- PME et microentreprises : commerçants, prestataires de services, artisans
- Freelancers et consultants indépendants
- Petites agences (communication, IT, transport)

### Canaux de distribution
1. **WhatsApp** — démo vidéo de 60 secondes → lien d'inscription
2. **Facebook / Instagram** — publication de captures d'écran des graphiques
3. **Bouche à oreille** — offrir 1 mois gratuit si tu amènes un ami
4. **Marchés et associations** — présenter en live sur téléphone

### Argument de vente unique
> *"Suis tes bénéfices et frais client par client, depuis ton téléphone, en FCFA."*

### Prix psychologiques suggérés
- **2 000 FCFA/mois** = prix d'une recharge MTN → facilement justifiable
- Paiement via Mobile Money pour zéro friction
- Essai gratuit 30 jours, pas de carte bancaire requise

### Fonctionnalité différenciante à mettre en avant
- Export Excel professionnel pour présenter aux banques / partenaires
- Accès multi-utilisateurs (patron + comptable + associé)
- Accessible depuis le téléphone sans installation

---

## 10. Changer admin + email

### Option 1 — Via l'interface (recommandé)

1. Lance l'app : `python run.py`
2. Connecte-toi avec `admin` / `admin123`
3. Va dans **⚙️ Paramètres → Mon compte**
4. Change le nom d'utilisateur et l'email
5. Va dans **🔒 Changer le mot de passe**
6. Change le mot de passe

### Option 2 — Via le fichier `.env`

Modifie les valeurs par défaut dans `app/__init__.py`, fonction `_seed_admin()` :
```python
def _seed_admin():
    if User.query.count() == 0:
        admin = User(
            username="ton_nom",           # ← change ici
            email="ton@email.com",        # ← change ici
            role="admin"
        )
        admin.set_password("ton_mot_de_passe_fort")  # ← change ici
        db.session.add(admin)
        db.session.commit()
```

> ⚠️ **Important** : Si la base de données existe déjà (fichier `dsm_enterprise.db`),
> supprime-la pour que les nouveaux identifiants soient créés au prochain lancement.

### Option 3 — Script de reset (le plus simple)

Crée un fichier `reset_admin.py` dans le dossier racine :
```python
"""Script pour changer les infos admin — à exécuter une seule fois"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from app.models import User

app = create_app()
with app.app_context():
    admin = User.query.filter_by(role="admin").first()
    if admin:
        admin.username = "alex_dsm"          # ← ton nom
        admin.email    = "alex@example.com"  # ← ton email
        admin.set_password("MonMotDePasse2026!")  # ← ton mdp
        db.session.commit()
        print(f"✅ Admin mis à jour : {admin.username}")
    else:
        print("❌ Aucun admin trouvé")
```

Lance avec : `python reset_admin.py`

---

*Documentation générée le 01 Avril 2026 — Digital Services CM Enterprise v3.0.0*
