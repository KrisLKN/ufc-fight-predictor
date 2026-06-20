# 🥊 UFC Fight Predictor — Web app

Site web propre et déployable : on choisit deux combattants, une API FastAPI
sert un modèle de machine learning (régression logistique, ~60 % de précision)
qui prédit le vainqueur.

```
web/
├── train.py          # build offline : DuckDB -> artefacts (à lancer une fois)
├── main.py           # API FastAPI + sert le frontend
├── static/           # frontend (HTML / CSS / JS, aucun framework)
│   ├── index.html
│   ├── style.css
│   └── app.js
├── artifacts/        # généré par train.py (model.pkl, fighters.json, ...)
├── requirements.txt  # dépendances runtime (pas besoin de DuckDB)
├── Procfile          # déploiement (Railway / Heroku)
└── render.yaml       # déploiement Render
```

## 1. Générer les artefacts (une fois)

Le modèle est entraîné hors-ligne depuis la base DuckDB, ce qui rend le site
déployable partout sans la base.

```bash
.venv\Scripts\python.exe web\train.py
```

Cela crée `web/artifacts/` (model.pkl, scaler.pkl, fighters.json, metrics.json).
**Committe ce dossier** : c'est lui qui est servi en production.

## 2. Lancer en local

```bash
.venv\Scripts\python.exe -m pip install -r web\requirements.txt
.venv\Scripts\python.exe -m uvicorn web.main:app --reload
```

Ouvre http://127.0.0.1:8000

## 3. Déployer (gratuit)

### Render
1. Pousse le repo sur GitHub.
2. Render → *New Web Service* → connecte le repo.
3. Render détecte `web/render.yaml`. Déploie. C'est tout.

### Railway
Pointe le service sur le dossier `web/` (utilise le `Procfile`).

> Le frontend appelle l'API en chemin relatif (`/api/...`), donc aucune
> configuration d'URL n'est nécessaire : front et back sont servis ensemble.

## API

| Méthode | Route            | Description                                  |
|---------|------------------|----------------------------------------------|
| GET     | `/api/health`    | statut + métriques du modèle                 |
| GET     | `/api/fighters`  | liste des combattants                        |
| POST    | `/api/predict`   | `{fighter_a, fighter_b}` → vainqueur + proba |

Après réentraînement de la pipeline dbt, relance `train.py` pour rafraîchir les
artefacts, puis redéploie.
