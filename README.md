# 🥊 UFC Fight Predictor — Pipeline Data & Machine Learning

> End-to-end data pipeline that predicts the outcome of UFC fights, from raw CSVs to an interactive dashboard.
> *Pipeline data de bout en bout qui prédit l'issue des combats UFC, des CSV bruts jusqu'à un dashboard interactif.*

---

## 📌 Overview

This project builds a complete, production-style data pipeline and a machine learning model
to predict the winner of UFC fights. It was built as a learning portfolio project, with a
strong focus on **methodology**: data quality testing, leakage-free feature engineering,
honest evaluation, and feature selection by measurement (not assumption).

**Stack:** DuckDB · dbt · Python (pandas, scikit-learn) · Streamlit

---

## 🏗️ Architecture

```
Raw CSVs (GitHub)
      │
      ▼
  DuckDB  ──────────────  storage (OLAP analytical database)
      │
      ▼
   dbt  ─────────────────  transformations, tests & documentation
      │   staging/      → cleaning (stg_*)
      │   marts/        → facts & ML table (fct_*, ml_fight_dataset)
      ▼
scikit-learn  ──────────  logistic regression (time-based split, no leakage)
      │
      ▼
 Streamlit  ────────────  interactive prediction dashboard (app.py)
```

---

## 🔬 Methodology highlights

- **Data quality:** 29 automated dbt tests (not_null, unique, accepted_values) guarantee
  the integrity of the pipeline. A unique `fight_id` (extracted from source URLs) acts as a
  primary key and resolves real edge cases (e.g. two fighters meeting twice on the same night).
- **No data leakage:** all cumulative features use only **past fights**
  (window frame ending at `1 PRECEDING`). The train/test split is done **by time**
  (train on old fights, test on recent ones), mimicking real prediction.
- **Honest evaluation:** model accuracy is always compared to a **baseline** (majority class).
- **Feature selection by measurement:** several features were engineered, tested, and
  **dropped because they added no measurable signal** (fighting style KO/sub rates, stance,
  weight-class change) — a deliberate, data-driven choice.

---

## 📊 Features

The model uses leakage-free features per fighter, combined as differences (A − B):

| Category | Features |
|----------|----------|
| Record   | fights before, wins before, win rate |
| Form     | won previous fight, days since last fight |
| Profile  | age at fight, reach |

*Engineered & tested but not retained in the final model: KO rate, submission rate, stance, weight-class change (up/down/same).*

---

## 📈 Results

| Model | Test accuracy |
|-------|---------------|
| Baseline (majority class) | ~0.51 |
| Logistic Regression (final, 16 features) | **~0.60** |
| Random Forest | 0.59 (overfit) |
| XGBoost | 0.58 (overfit) |

A ~0.60 accuracy is solid for MMA, where outcomes are inherently hard to predict
(professional models typically cap around 0.60–0.65). A simpler model (logistic regression)
generalized better than more complex ones — a reminder that, when signal is limited,
simplicity wins.

---

## 🗂️ Repository structure

```
ufc-pipeline/
├── ufc_dbt/                       # dbt project (models, tests, docs)
│   └── models/
│       ├── staging/               # stg_* : cleaning
│       └── marts/                 # fct_*, ml_fight_dataset
├── 02_machine_learning_final.ipynb # ML notebook (load → train → evaluate → predict)
├── app.py                         # Streamlit dashboard
├── requirements.txt
└── README.md
```

---

## 🚀 Run it locally

```bash
# 1. Create & activate a virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Build the data pipeline (creates the DuckDB database)
cd ufc_dbt
dbt run
dbt test

# 4. Launch the dashboard
cd ..
streamlit run app.py
```

---

## 📚 Data source

Raw fight data from the public repository
[Greco1899/scrape_ufc_stats](https://github.com/Greco1899/scrape_ufc_stats) (GPL-3.0),
read directly from the raw CSVs. No API key required.

---

## ⚠️ Limitations

- Features reflect each fighter's last-known state (proxy for current form).
- No fight-day context (injuries, training camp, short-notice bouts).
- No detailed striking/grappling statistics yet (a planned next step).
- Predictions are a **decision aid**, not a guarantee.

---

## 🔭 Next steps

- Parse detailed fight statistics (`fight_stats`: strikes, takedowns, control time).
- Deploy the dashboard online (Streamlit Community Cloud).
- Add fighter images and a richer visual UI.

---

*Built by [@VOTRE-PSEUDO-GITHUB](https://github.com/VOTRE-PSEUDO-GITHUB) — data engineering & machine learning portfolio project.*
