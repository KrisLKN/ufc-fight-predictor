"""
export_demo.py — Exporte le modele entraine vers la demo statique du portfolio.

Lit les artefacts (model.pkl, scaler.pkl, metrics.json, fighters.json) et ecrit
deux fichiers consommables directement dans le navigateur :

    <cible>/model.json      coefficients + scaler + metriques (pour le calcul en JS)
    <cible>/fighters.json   profils des combattants

Usage :
    python web/export_demo.py "C:\\...\\PORTFOLIO\\ufc"
"""

import json
import pickle
import shutil
import sys
from pathlib import Path

ART = Path(__file__).resolve().parent / "artifacts"


def main(target_dir: str) -> None:
    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)

    model = pickle.load(open(ART / "model.pkl", "rb"))
    scaler = pickle.load(open(ART / "scaler.pkl", "rb"))
    metrics = json.load(open(ART / "metrics.json", encoding="utf-8"))

    export = {
        "features": metrics["features"],
        "coef": model.coef_[0].tolist(),
        "intercept": float(model.intercept_[0]),
        "mean": scaler.mean_.tolist(),
        "scale": scaler.scale_.tolist(),
        "classes": model.classes_.tolist(),
        "accuracy": metrics["accuracy"],
        "baseline": metrics["baseline"],
        "n_fighters": metrics["n_fighters"],
        "n_fights": metrics["n_fights"],
        "reach_median": metrics.get("reach_median", 72.0),
    }
    (target / "model.json").write_text(json.dumps(export), encoding="utf-8")
    shutil.copyfile(ART / "fighters.json", target / "fighters.json")
    print(f"Demo exportee dans {target} ({export['n_fighters']} combattants, "
          f"accuracy {export['accuracy']:.1%})")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python web/export_demo.py <dossier_cible_ufc>")
        sys.exit(1)
    main(sys.argv[1])
