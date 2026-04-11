"""
load_themes.py
~~~~~~~~~~~~~~
Builds two theme/indicator mapping tables in data/pses.duckdb from the
2025 PSES Subset 1 CSV hosted on Canada.ca:

  theme_map     – one row per QUESTION with its indicator/sub-indicator labels
  indicator_map – distinct indicator / sub-indicator combinations (lookup table)

Run:
    python src/pses/load_themes.py
"""

from __future__ import annotations

import os
from pathlib import Path

import duckdb
from rich.console import Console
from rich.table import Table

from pses.utils import fetch_with_bom_strip

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parents[2] / "data" / "pses.duckdb"

SUBSET1_URL = (
    "https://www.canada.ca/content/dam/tbs-sct/documents/datasets/"
    "ses-2025/subset-1-sous-ensemble-1.csv"
)

console = Console()

# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

def _theme_map_sql(csv_path: str) -> str:
    return f"""
    CREATE OR REPLACE TABLE theme_map AS
    SELECT DISTINCT ON (QUESTION)
        QUESTION,
        TITLE_E,
        INDICATORID,
        INDICATORENG,
        SUBINDICATORID,
        SUBINDICATORENG
    FROM read_csv_auto('{csv_path}', header = true)
    WHERE LEVEL1ID = '00'
      AND BYCOND   IS NULL
    ORDER BY QUESTION
    """


def _indicator_map_sql(csv_path: str) -> str:
    return f"""
    CREATE OR REPLACE TABLE indicator_map AS
    SELECT DISTINCT
        INDICATORID,
        INDICATORENG,
        SUBINDICATORID,
        SUBINDICATORENG
    FROM read_csv_auto('{csv_path}', header = true)
    WHERE LEVEL1ID = '00'
      AND BYCOND   IS NULL
    ORDER BY INDICATORID, SUBINDICATORID
    """


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    console.log(f"Fetching [cyan]{SUBSET1_URL}[/cyan] …")
    csv_path = fetch_with_bom_strip(SUBSET1_URL)

    try:
        con = duckdb.connect(str(DB_PATH))

        # ── Build tables ────────────────────────────────────────────────────
        console.log("Building [bold]theme_map[/bold] …")
        con.execute(_theme_map_sql(csv_path))

        console.log("Building [bold]indicator_map[/bold] …")
        con.execute(_indicator_map_sql(csv_path))

        # ── Row counts ──────────────────────────────────────────────────────
        n_theme: int     = con.execute("SELECT COUNT(*) FROM theme_map").fetchone()[0]
        n_indicator: int = con.execute("SELECT COUNT(*) FROM indicator_map").fetchone()[0]

        console.print(f"\n[bold green]theme_map[/bold green]:     {n_theme:,} rows")
        console.print(f"[bold green]indicator_map[/bold green]: {n_indicator:,} rows\n")

        # ── Sample of theme_map ─────────────────────────────────────────────
        sample_cols = [
            "QUESTION", "TITLE_E", "INDICATORID", "INDICATORENG",
            "SUBINDICATORID", "SUBINDICATORENG",
        ]
        rows = con.execute(
            """
            SELECT QUESTION, TITLE_E, INDICATORID, INDICATORENG,
                   SUBINDICATORID, SUBINDICATORENG
            FROM   theme_map
            ORDER BY INDICATORID, SUBINDICATORID, QUESTION
            LIMIT  10
            """
        ).fetchall()

        console.rule("[bold cyan]theme_map — 10 sample rows")
        tbl = Table(show_header=True, header_style="bold magenta")
        for col in sample_cols:
            tbl.add_column(col, overflow="fold")
        for row in rows:
            tbl.add_row(*[str(v) if v is not None else "[dim]NULL[/dim]" for v in row])
        console.print(tbl)

        con.close()

    finally:
        os.unlink(csv_path)


if __name__ == "__main__":
    main()
