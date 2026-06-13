"""
UFC Fight Predictor — Streamlit dashboard
Run with:  streamlit run app.py
(make sure DBeaver is disconnected so the DuckDB file is readable)
"""

import duckdb
import pandas as pd
import streamlit as st
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

DB_PATH = "data/ufc.duckdb"

# Features used by the model (the cleaned, informative set)
FEATURE_COLS = [
    "a_fights_before", "a_wins_before", "a_win_rate",
    "b_fights_before", "b_wins_before", "b_win_rate",
    "a_days_since_last", "b_days_since_last",
    "a_age", "b_age",
    "diff_fights_before", "diff_wins_before", "diff_win_rate",
    "diff_age", "diff_reach", "diff_days_since_last",
]


# ---------------------------------------------------------------------------
# Data loading + model training (cached so it runs only once)
# ---------------------------------------------------------------------------
@st.cache_resource
def load_and_train():
    """Load data, train the model, and return everything the app needs."""
    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.sql("SELECT * FROM ml_fight_dataset").df()
    latest = con.sql("""
        SELECT * FROM (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY fighter ORDER BY event_date DESC) AS rn
            FROM fct_fighter_features
        ) WHERE rn = 1
    """).df()
    con.close()

    # --- Prepare features ---
    for col in ["a_age", "b_age", "a_reach", "b_reach"]:
        df[col] = df[col].fillna(df[col].median())
    df["a_won_previous"]    = df["a_won_previous"].fillna(0)
    df["b_won_previous"]    = df["b_won_previous"].fillna(0)
    df["a_days_since_last"] = df["a_days_since_last"].fillna(9999)
    df["b_days_since_last"] = df["b_days_since_last"].fillna(9999)

    df["diff_fights_before"]   = df["a_fights_before"]   - df["b_fights_before"]
    df["diff_wins_before"]     = df["a_wins_before"]     - df["b_wins_before"]
    df["diff_win_rate"]        = df["a_win_rate"]        - df["b_win_rate"]
    df["diff_age"]             = df["a_age"]             - df["b_age"]
    df["diff_reach"]           = df["a_reach"]           - df["b_reach"]
    df["diff_days_since_last"] = df["a_days_since_last"] - df["b_days_since_last"]

    # --- Time-based split ---
    df_sorted = df.sort_values("event_date").reset_index(drop=True)
    X = df_sorted[FEATURE_COLS]
    y = df_sorted["a_won"]
    split_index = int(len(df_sorted) * 0.8)
    X_train, y_train = X.iloc[:split_index], y.iloc[:split_index]
    X_test,  y_test  = X.iloc[split_index:], y.iloc[split_index:]

    # --- Standardize + train ---
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    model = LogisticRegression(max_iter=1000)
    model.fit(X_train_scaled, y_train)

    # --- Test accuracy (for display) ---
    from sklearn.metrics import accuracy_score
    acc = accuracy_score(y_test, model.predict(scaler.transform(X_test)))
    baseline = y_test.value_counts(normalize=True).max()

    fighters = sorted(latest["fighter"].dropna().unique().tolist())
    return model, scaler, latest, fighters, acc, baseline


def build_features(fa, fb):
    """Build the model feature row for a matchup between two fighter profiles."""
    reach_a = fa["reach"] if pd.notna(fa["reach"]) else 71
    reach_b = fb["reach"] if pd.notna(fb["reach"]) else 71
    row = {
        "a_fights_before": fa["fights_before"], "a_wins_before": fa["wins_before"], "a_win_rate": fa["win_rate"],
        "b_fights_before": fb["fights_before"], "b_wins_before": fb["wins_before"], "b_win_rate": fb["win_rate"],
        "a_days_since_last": fa["days_since_last_fight"], "b_days_since_last": fb["days_since_last_fight"],
        "a_age": fa["age_at_fight"], "b_age": fb["age_at_fight"],
        "diff_fights_before": fa["fights_before"] - fb["fights_before"],
        "diff_wins_before":   fa["wins_before"]   - fb["wins_before"],
        "diff_win_rate":      fa["win_rate"]      - fb["win_rate"],
        "diff_age":           fa["age_at_fight"]  - fb["age_at_fight"],
        "diff_reach":         reach_a - reach_b,
        "diff_days_since_last": fa["days_since_last_fight"] - fb["days_since_last_fight"],
    }
    return pd.DataFrame([row])[FEATURE_COLS].fillna(0)


# ---------------------------------------------------------------------------
# App layout
# ---------------------------------------------------------------------------
st.set_page_config(page_title="UFC Fight Predictor", page_icon="🥊", layout="centered")

st.title("🥊 UFC Fight Predictor")
st.write(
    "Pick two fighters and the model predicts the winner, "
    "based on historical features (record, form, age, reach)."
)

model, scaler, latest, fighters, acc, baseline = load_and_train()

st.caption(
    f"Model: logistic regression · test accuracy **{acc:.1%}** "
    f"(baseline {baseline:.1%}) · {len(fighters)} fighters available."
)

# --- Fighter selection ---
col1, col2 = st.columns(2)
with col1:
    name_a = st.selectbox("Fighter A", fighters,
                          index=fighters.index("Charles Oliveira") if "Charles Oliveira" in fighters else 0)
with col2:
    name_b = st.selectbox("Fighter B", fighters,
                          index=fighters.index("Ilia Topuria") if "Ilia Topuria" in fighters else 1)

# --- Predict ---
if st.button("Predict the winner", type="primary"):
    if name_a == name_b:
        st.warning("Please pick two different fighters.")
    else:
        fa = latest[latest["fighter"] == name_a].iloc[0]
        fb = latest[latest["fighter"] == name_b].iloc[0]

        X_row = build_features(fa, fb)
        proba_a = model.predict_proba(scaler.transform(X_row))[0][1]

        winner = name_a if proba_a >= 0.5 else name_b
        win_proba = proba_a if proba_a >= 0.5 else 1 - proba_a

        st.markdown("---")
        st.subheader(f"Prediction: **{winner}** wins")
        st.metric("Win probability", f"{win_proba:.1%}")
        st.progress(float(win_proba))

        # --- Comparison table ---
        st.markdown("### Fighter comparison")

        def fmt_reach(v):
            return f"{int(v)} in" if pd.notna(v) else "—"

        comparison = pd.DataFrame({
            "Stat": ["Wins", "Total fights", "Win rate", "Age (last fight)", "Reach"],
            name_a: [
                f"{fa['wins_before']:.0f}",
                f"{fa['fights_before']:.0f}",
                f"{fa['win_rate']:.1%}",
                f"{fa['age_at_fight']:.0f}",
                fmt_reach(fa["reach"]),
            ],
            name_b: [
                f"{fb['wins_before']:.0f}",
                f"{fb['fights_before']:.0f}",
                f"{fb['win_rate']:.1%}",
                f"{fb['age_at_fight']:.0f}",
                fmt_reach(fb["reach"]),
            ],
        })
        st.table(comparison.set_index("Stat"))

        st.caption(
            "Note: features are taken as of each fighter's last fight (proxy for current form). "
            "This is a decision aid, not a guarantee — MMA outcomes are inherently hard to predict."
        )
