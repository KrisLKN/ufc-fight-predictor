"""
load_raw.py — Etape 1 du pipeline : charger les CSV bruts dans DuckDB.

Lit les fichiers publics du depot Greco1899/scrape_ufc_stats et cree les
tables raw_* dans la base DuckDB (que dbt consommera ensuite comme sources).

Le chemin de la base est lu depuis la variable d'environnement UFC_DUCKDB
(par defaut : data/ufc.duckdb a la racine du projet), pour que le script
fonctionne aussi bien en local qu'en CI (GitHub Actions).

Usage :
    python load_raw.py
"""

import os
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent
DB_PATH = os.environ.get("UFC_DUCKDB", str(ROOT / "data" / "ufc.duckdb"))

BASE_URL = "https://raw.githubusercontent.com/Greco1899/scrape_ufc_stats/main/"

# table DuckDB -> fichier CSV source
SOURCES = {
    "raw_fight_results": "ufc_fight_results.csv",
    "raw_fight_stats":   "ufc_fight_stats.csv",
    "raw_event_details": "ufc_event_details.csv",
    "raw_fighter_tott":  "ufc_fighter_tott.csv",
}


def main() -> None:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(DB_PATH)
    for table, file_name in SOURCES.items():
        con.sql(
            f"""
            CREATE OR REPLACE TABLE {table} AS
            SELECT * FROM read_csv('{BASE_URL}{file_name}', all_varchar = true)
            """
        )
        n = con.sql(f"SELECT count(*) FROM {table}").fetchone()[0]
        print(f"Loaded {table:<20} {n:>6} lignes")
    con.close()
    print(f"Tables brutes pretes dans {DB_PATH}")


if __name__ == "__main__":
    main()
