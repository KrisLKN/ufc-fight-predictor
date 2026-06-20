"""
train.py — Build step (run once, offline).

Reads the DuckDB database, trains the logistic-regression model, and writes
lightweight artifacts to web/artifacts/ so the API never needs DuckDB at runtime:

    artifacts/model.pkl     trained LogisticRegression
    artifacts/scaler.pkl    fitted StandardScaler
    artifacts/fighters.json latest known features for every fighter
    artifacts/metrics.json  accuracy / baseline / fighter count

Run from the project root:
    .venv\\Scripts\\python.exe web/train.py
"""

import json
import os
import pickle
from pathlib import Path

import duckdb
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("UFC_DUCKDB", ROOT / "data" / "ufc.duckdb"))
OUT_DIR = Path(__file__).resolve().parent / "artifacts"

FEATURE_COLS = [
    "a_fights_before", "a_wins_before", "a_win_rate",
    "b_fights_before", "b_wins_before", "b_win_rate",
    "a_days_since_last", "b_days_since_last",
    "a_age", "b_age",
    "diff_fights_before", "diff_wins_before", "diff_win_rate",
    "diff_age", "diff_reach", "diff_days_since_last",
]


def main() -> None:
    print(f"Reading {DB_PATH} ...")
    con = duckdb.connect(str(DB_PATH), read_only=True)
    df = con.sql("SELECT * FROM ml_fight_dataset").df()
    latest = con.sql(
        """
        SELECT * FROM (
            SELECT *, ROW_NUMBER() OVER (
                PARTITION BY fighter ORDER BY event_date DESC
            ) AS rn
            FROM fct_fighter_features
        ) WHERE rn = 1
        """
    ).df()
    con.close()

    # --- Fill + engineer features (same logic as the original app) ---
    for col in ["a_age", "b_age", "a_reach", "b_reach"]:
        df[col] = df[col].fillna(df[col].median())
    df["a_days_since_last"] = df["a_days_since_last"].fillna(9999)
    df["b_days_since_last"] = df["b_days_since_last"].fillna(9999)

    df["diff_fights_before"]   = df["a_fights_before"] - df["b_fights_before"]
    df["diff_wins_before"]     = df["a_wins_before"]   - df["b_wins_before"]
    df["diff_win_rate"]        = df["a_win_rate"]      - df["b_win_rate"]
    df["diff_age"]             = df["a_age"]           - df["b_age"]
    df["diff_reach"]           = df["a_reach"]         - df["b_reach"]
    df["diff_days_since_last"] = df["a_days_since_last"] - df["b_days_since_last"]

    # --- Time-based split (train on old fights, test on recent ones) ---
    df_sorted = df.sort_values("event_date").reset_index(drop=True)
    X = df_sorted[FEATURE_COLS]
    y = df_sorted["a_won"]
    split = int(len(df_sorted) * 0.8)
    X_train, y_train = X.iloc[:split], y.iloc[:split]
    X_test,  y_test  = X.iloc[split:], y.iloc[split:]

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    model = LogisticRegression(max_iter=1000)
    model.fit(X_train_scaled, y_train)

    acc = accuracy_score(y_test, model.predict(scaler.transform(X_test)))
    baseline = float(y_test.value_counts(normalize=True).max())

    # --- Build the per-fighter profile used at prediction time ---
    reach_median = float(latest["reach"].median())
    fighters = {}
    for _, r in latest.iterrows():
        name = r["fighter"]
        if not isinstance(name, str) or not name.strip():
            continue
        fighters[name] = {
            "name": name,
            "fights_before": _num(r["fights_before"]),
            "wins_before": _num(r["wins_before"]),
            "win_rate": _num(r["win_rate"]),
            "days_since_last": _num(r["days_since_last_fight"], 9999),
            "age": _num(r["age_at_fight"]),
            "reach": _num(r["reach"], reach_median),
            "weight_class": (r["wc_clean"] if isinstance(r["wc_clean"], str) else None),
            "last_fight": str(r["event_date"])[:10] if pd.notna(r["event_date"]) else None,
        }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIR / "model.pkl", "wb") as f:
        pickle.dump(model, f)
    with open(OUT_DIR / "scaler.pkl", "wb") as f:
        pickle.dump(scaler, f)
    with open(OUT_DIR / "fighters.json", "w", encoding="utf-8") as f:
        json.dump(fighters, f, ensure_ascii=False)
    with open(OUT_DIR / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "accuracy": round(float(acc), 4),
                "baseline": round(baseline, 4),
                "n_fighters": len(fighters),
                "n_fights": int(len(df_sorted)),
                "features": FEATURE_COLS,
                "reach_median": reach_median,
            },
            f,
        )

    print(f"Done. {len(fighters)} fighters · accuracy {acc:.1%} (baseline {baseline:.1%})")
    print(f"Artifacts written to {OUT_DIR}")


def _num(value, default=0.0):
    """Return a JSON-safe float, replacing NaN/None with a default."""
    if value is None or pd.isna(value):
        return float(default)
    return float(value)


if __name__ == "__main__":
    main()
