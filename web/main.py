"""
main.py — FastAPI backend for the UFC Fight Predictor.

Loads the pre-trained artifacts (no DuckDB at runtime) and exposes:
    GET  /api/health             service status + model metrics
    GET  /api/fighters           list of fighter names (+ weight class)
    POST /api/predict            {fighter_a, fighter_b} -> winner + probability
    GET  /                       serves the frontend (static/index.html)

Run locally:
    .venv\\Scripts\\python.exe -m uvicorn web.main:app --reload
"""

import json
import pickle
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE = Path(__file__).resolve().parent
ART = BASE / "artifacts"

FEATURE_COLS = [
    "a_fights_before", "a_wins_before", "a_win_rate",
    "b_fights_before", "b_wins_before", "b_win_rate",
    "a_days_since_last", "b_days_since_last",
    "a_age", "b_age",
    "diff_fights_before", "diff_wins_before", "diff_win_rate",
    "diff_age", "diff_reach", "diff_days_since_last",
]

# --- Load artifacts once at import time ---
with open(ART / "model.pkl", "rb") as f:
    MODEL = pickle.load(f)
with open(ART / "scaler.pkl", "rb") as f:
    SCALER = pickle.load(f)
with open(ART / "fighters.json", encoding="utf-8") as f:
    FIGHTERS = json.load(f)
with open(ART / "metrics.json", encoding="utf-8") as f:
    METRICS = json.load(f)

app = FastAPI(title="UFC Fight Predictor", version="1.0.0")


class PredictRequest(BaseModel):
    fighter_a: str
    fighter_b: str


def build_features(fa: dict, fb: dict) -> pd.DataFrame:
    row = {
        "a_fights_before": fa["fights_before"], "a_wins_before": fa["wins_before"], "a_win_rate": fa["win_rate"],
        "b_fights_before": fb["fights_before"], "b_wins_before": fb["wins_before"], "b_win_rate": fb["win_rate"],
        "a_days_since_last": fa["days_since_last"], "b_days_since_last": fb["days_since_last"],
        "a_age": fa["age"], "b_age": fb["age"],
        "diff_fights_before": fa["fights_before"] - fb["fights_before"],
        "diff_wins_before":   fa["wins_before"]   - fb["wins_before"],
        "diff_win_rate":      fa["win_rate"]      - fb["win_rate"],
        "diff_age":           fa["age"]           - fb["age"],
        "diff_reach":         fa["reach"]         - fb["reach"],
        "diff_days_since_last": fa["days_since_last"] - fb["days_since_last"],
    }
    return pd.DataFrame([row])[FEATURE_COLS].fillna(0)


@app.get("/api/health")
def health():
    return {"status": "ok", "metrics": METRICS}


@app.get("/api/fighters")
def list_fighters():
    items = [
        {"name": f["name"], "weight_class": f.get("weight_class")}
        for f in sorted(FIGHTERS.values(), key=lambda x: x["name"])
    ]
    return {"count": len(items), "fighters": items}


@app.post("/api/predict")
def predict(req: PredictRequest):
    fa = FIGHTERS.get(req.fighter_a)
    fb = FIGHTERS.get(req.fighter_b)
    if fa is None:
        raise HTTPException(404, f"Unknown fighter: {req.fighter_a}")
    if fb is None:
        raise HTTPException(404, f"Unknown fighter: {req.fighter_b}")
    if req.fighter_a == req.fighter_b:
        raise HTTPException(400, "Please pick two different fighters.")

    X = build_features(fa, fb)
    proba_a = float(MODEL.predict_proba(SCALER.transform(X))[0][1])
    proba_b = 1 - proba_a
    winner = fa if proba_a >= 0.5 else fb
    win_proba = proba_a if proba_a >= 0.5 else proba_b

    return {
        "winner": winner["name"],
        "win_probability": round(win_proba, 4),
        "probabilities": {
            fa["name"]: round(proba_a, 4),
            fb["name"]: round(proba_b, 4),
        },
        "fighters": {"a": _public(fa), "b": _public(fb)},
        "model": {"accuracy": METRICS["accuracy"], "baseline": METRICS["baseline"]},
    }


def _public(f: dict) -> dict:
    return {
        "name": f["name"],
        "wins": round(f["wins_before"]),
        "fights": round(f["fights_before"]),
        "win_rate": f["win_rate"],
        "age": round(f["age"]) if f["age"] else None,
        "reach": round(f["reach"]) if f["reach"] else None,
        "weight_class": f.get("weight_class"),
        "last_fight": f.get("last_fight"),
    }


# Serve the frontend (mounted last so /api/* takes priority).
app.mount("/", StaticFiles(directory=str(BASE / "static"), html=True), name="static")
