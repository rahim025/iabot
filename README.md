# Donia

Chatbot conversationnel type ChatGPT/Claude, en Flask + API Anthropic, avec streaming des réponses.
Fonctionne comme site web ET comme application Android (via WebAPK), à partir du même code.

Créée par **Rahim Batchabi**.

## 1. Installation locale

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

export ANTHROPIC_API_KEY="ta_clé_api_ici"
export FLASK_SECRET_KEY="une_chaine_secrete_aleatoire"

python app.py
```

Ouvre `http://localhost:5000`.

Récupère ta clé API sur https://console.anthropic.com

## 2. Déploiement (site web)

GitHub seul ne fait qu'héberger le code, il faut un service qui fait tourner le serveur en continu. Options gratuites/simples :

- **Render.com** : connecte ton repo GitHub, ajoute la variable d'environnement `ANTHROPIC_API_KEY`, commande de démarrage : `gunicorn app:app`
- **Railway.app** : même principe
- **PythonAnywhere** : bon pour les petits projets Flask

Dans tous les cas :
1. Pousse ce code sur GitHub
2. Connecte le repo au service choisi
3. Ajoute la variable d'environnement `ANTHROPIC_API_KEY` (et `FLASK_SECRET_KEY`)
4. Déploie — tu obtiens une URL du type `https://ton-app.onrender.com`

## 3. Transformer le site en application Android (WebAPK)

Une fois le site en ligne avec HTTPS (obligatoire) :

1. Ajoute deux icônes dans `static/` : `icon-192.png` et `icon-512.png` (192x192 et 512x512 px)
2. Ouvre le site dans **Chrome sur Android**
3. Menu (⋮) → **"Installer l'application"** ou **"Ajouter à l'écran d'accueil"**
4. Chrome génère automatiquement un WebAPK — exactement comme l'APK qu'on a analysé plus tôt

Pour générer un vrai fichier `.apk` distribuable (sans passer par Chrome à chaque fois), utilise **[PWABuilder](https://www.pwabuilder.com/)** : colle l'URL de ton site, il génère un `.apk`/`.aab` prêt à publier sur le Play Store.

## Fonctionnalités

- **Authentification** : inscription/connexion (mots de passe hachés), chaque utilisateur voit uniquement ses propres conversations
- **Base de données** : SQLite par défaut (`chatbot.db`, créé automatiquement au premier lancement), historique des conversations conservé entre les sessions
- **Choix du modèle** : menu déroulant (Sonnet / Opus / Haiku), modifiable dans `config_models.py`
- **Résolution de problèmes et maths avancées** : Donia est instruite pour résoudre des exercices de tous niveaux (élèves, lycéens, étudiants) avec explications étape par étape ; les formules sont écrites en LaTeX et rendues visuellement dans le chat grâce à MathJax
- **Export PDF** : bouton "📄 PDF" pour télécharger n'importe quelle conversation en PDF (via `reportlab`)

Pour changer de base de données (ex. PostgreSQL en production), modifie la variable d'environnement `DATABASE_URL`, ex :
```bash
export DATABASE_URL="postgresql://user:password@host:5432/dbname"
```

## Génération d'images (à venir)

Pas encore implémentée — Claude/Anthropic ne génère pas d'images nativement. Pour l'ajouter plus tard, il faudra connecter un service tiers (OpenAI DALL-E ou Stability AI) : une clé API supplémentaire sera nécessaire.

## Structure du projet

```
chatbot-ia/
├── app.py                 # Backend Flask + appel API Claude en streaming + export PDF
├── models.py               # Modèles base de données (User, Conversation, Message)
├── config_models.py        # Liste des modèles IA disponibles
├── requirements.txt
├── templates/
│   ├── index.html
│   ├── login.html
│   └── register.html
└── static/
    ├── style.css
    ├── app.js
    ├── manifest.json      # Manifeste PWA (nécessaire pour le WebAPK)
    ├── icon-192.png / icon-512.png
    └── favicon.png
```

## Limites restantes

- Pas de réinitialisation de mot de passe / email de vérification
- Pas de limite de débit (rate limiting) sur les appels API — à ajouter avant une mise en production publique
- L'export PDF affiche le texte brut des formules (le rendu LaTeX visuel n'est disponible que dans le chat, pas encore dans le PDF)
- Génération d'images : pas encore implémentée
