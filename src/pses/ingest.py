"""
PSES Main Dataset ingestion layer.
Strategy:
  - Bulk load: read CSV directly from TBS open data URL into DuckDB
  - No intermediate file needed; DuckDB streams it
  - Idempotent: drop and recreate raw table on each run
"""

import duckdb
from rich.console import Console

CSV_URL = "https://www.canada.ca/content/dam/tbs-sct/documents/datasets/ses-2025/main-principal.csv"
DB_PATH = "data/pses.duckdb"
RAW_TABLE = "raw_pses"

console = Console()


def ingest(db_path: str = DB_PATH) -> None:
    console.rule("[bold blue]PSES Ingestion Pipeline")
    console.print(f"[cyan]Source: {CSV_URL}")
    console.print("[cyan]Loading into DuckDB via direct CSV read...")

    con = duckdb.connect(db_path)

    con.execute(f"DROP TABLE IF EXISTS {RAW_TABLE}")
    con.execute(f"""
        CREATE TABLE {RAW_TABLE} AS
        SELECT *
        FROM read_csv_auto(
            '{CSV_URL}',
            header = true,
            ignore_errors = true
        )
    """)

    row_count = con.execute(f"SELECT COUNT(*) FROM {RAW_TABLE}").fetchone()[0]
    cols = con.execute(f"DESCRIBE {RAW_TABLE}").fetchall()
    con.close()

    console.print(f"[bold green]✓ {row_count:,} rows loaded into `{RAW_TABLE}`")
    console.print("\n[bold]Schema:[/bold]")
    for col in cols:
        console.print(f"  [dim]{col[0]:<20}[/dim] {col[1]}")

    console.rule()


if __name__ == "__main__":
    ingest()