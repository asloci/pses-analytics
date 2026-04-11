"""
explore_subset.py
~~~~~~~~~~~~~~~~~
Exploration script — fetches the 2025 PSES Subset 1 CSV from Canada.ca,
strips the UTF-8 BOM, and queries it via DuckDB's read_csv_auto().
Nothing is written to the database.

Run:
    python src/pses/explore_subset.py
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

SAMPLE_COLS = [
    "QUESTION",
    "SURVEYR",
    "SCORE100",
    "IndicatorENG",
    "SubIndicatorENG",
    "IndicatorID",
    "SubIndicatorID",
]

console = Console()

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    console.log(f"Fetching [cyan]{SUBSET1_URL}[/cyan] …")
    csv_path = fetch_with_bom_strip(SUBSET1_URL)

    try:
        con = duckdb.connect(str(DB_PATH), read_only=True)

        # ── 1. Column names ─────────────────────────────────────────────────
        cols = con.execute(
            f"SELECT * FROM read_csv_auto('{csv_path}', header = true) LIMIT 0"
        ).description  # list of (name, type_code, ...) tuples
        col_names = [c[0] for c in cols]

        console.rule("[bold cyan]Subset 1 — Column Names")
        col_table = Table(show_header=True, header_style="bold magenta")
        col_table.add_column("#", style="dim", width=4)
        col_table.add_column("Column name")
        for i, name in enumerate(col_names, 1):
            col_table.add_row(str(i), name)
        console.print(col_table)

        # ── 2. Sample rows ──────────────────────────────────────────────────
        select_clause = ", ".join(SAMPLE_COLS)
        rows = con.execute(
            f"""
            SELECT {select_clause}
            FROM   read_csv_auto('{csv_path}', header = true)
            WHERE  LEVEL1ID = '00'
              AND  BYCOND IS NULL
            LIMIT  5
            """
        ).fetchall()

        console.rule("[bold cyan]Subset 1 — 5 Sample Rows (LEVEL1ID='00', no BYCOND)")
        sample_table = Table(show_header=True, header_style="bold green")
        for col in SAMPLE_COLS:
            sample_table.add_column(col, overflow="fold")
        for row in rows:
            sample_table.add_row(*[str(v) if v is not None else "[dim]NULL[/dim]" for v in row])
        console.print(sample_table)

        con.close()

    finally:
        os.unlink(csv_path)


if __name__ == "__main__":
    main()
