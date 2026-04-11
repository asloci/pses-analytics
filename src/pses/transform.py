"""
transform.py
~~~~~~~~~~~~
Read raw_pses from data/pses.duckdb and produce two clean analytical tables:

  pses_wog    – whole-of-government spine (LEVEL1ID=0, LEVEL2ID=0, no BYCOND)
  pses_sliced – whole-of-govt demographic/org slices (LEVEL1ID=0, BYCOND IS NOT NULL)

Run:
  uv run python -m pses.transform
  # or
  python src/pses/transform.py
"""

from __future__ import annotations

from pathlib import Path

import duckdb

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parents[2] / "data" / "pses.duckdb"

# Columns that sentinel 9999 as "missing" and should be cast to INTEGER
_INT_COLS = [
    "SCORE100",
    "ANSCOUNT",
    "POSITIVE",
    "NEUTRAL",
    "NEGATIVE",
    "AGREE",
    "answer1",
    "answer2",
    "answer3",
    "answer4",
    "answer5",
    "answer6",
    "answer7",
]


def _int_expr(col: str) -> str:
    """Return a SQL expression that casts *col* to INTEGER and nulls 9999."""
    return f"NULLIF(CAST({col} AS INTEGER), 9999) AS {col}"


def _score5_expr() -> str:
    """Return a SQL expression for SCORE5: cast to DOUBLE, null 9999.0."""
    return "NULLIF(CAST(SCORE5 AS DOUBLE), 9999.0) AS SCORE5"


def _shared_select() -> str:
    """Return the column list shared by both output tables."""
    int_exprs = ",\n        ".join(_int_expr(c) for c in _INT_COLS)
    return f"""
        CAST(SURVEYR AS INTEGER)  AS SURVEYR,
        QUESTION,
        {int_exprs},
        {_score5_expr()}
    """


# ---------------------------------------------------------------------------
# Table builders
# ---------------------------------------------------------------------------

_WOG_SQL = f"""
CREATE OR REPLACE TABLE pses_wog AS
WITH
  -- rows that form the whole-of-government spine
  base AS (
    SELECT
        {_shared_select()},
        SCORE100  -- raw value still needed for is_scored below
    FROM raw_pses
    WHERE LEVEL1ID  = 0
      AND LEVEL2ID  = 0
      AND BYCOND IS NULL
  ),

  -- questions present in every one of the 4 survey years
  stable_questions AS (
    SELECT QUESTION
    FROM raw_pses
    WHERE LEVEL1ID = 0
      AND LEVEL2ID = 0
      AND BYCOND IS NULL
    GROUP BY QUESTION
    HAVING COUNT(DISTINCT SURVEYR) = (
        SELECT COUNT(DISTINCT SURVEYR) FROM raw_pses
    )
  )

SELECT
    b.SURVEYR,
    b.QUESTION,
    {", ".join(f"b.{c}" for c in _INT_COLS)},
    b.SCORE5,
    -- is_scored: true when the cleaned SCORE100 is not null
    NULLIF(CAST(b.SCORE100 AS INTEGER), 9999) IS NOT NULL AS is_scored,
    -- is_stable: true when this question appeared in all survey years
    (b.QUESTION IN (SELECT QUESTION FROM stable_questions))  AS is_stable
FROM base b
"""

_SLICED_SQL = f"""
CREATE OR REPLACE TABLE pses_sliced AS
SELECT
    CAST(SURVEYR AS INTEGER) AS SURVEYR,
    QUESTION,
    BYCOND,
    DEMCODE,
    {", ".join(_int_expr(c) for c in _INT_COLS)},
    {_score5_expr()}
FROM raw_pses
WHERE BYCOND IS NOT NULL
  AND LEVEL1ID = 0
"""

_ANALYSIS_SQL = """
CREATE OR REPLACE TABLE pses_analysis AS
SELECT
    w.*,
    t.TITLE_E,
    t.INDICATORID,
    t.INDICATORENG,
    t.SUBINDICATORID,
    t.SUBINDICATORENG
FROM pses_wog w
INNER JOIN theme_map t ON w.QUESTION = t.QUESTION
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    con = duckdb.connect(str(DB_PATH))

    # --- pses_wog -----------------------------------------------------------
    con.execute(_WOG_SQL)

    wog_total: int = con.execute("SELECT COUNT(*) FROM pses_wog").fetchone()[0]
    wog_scored: int = con.execute(
        "SELECT COUNT(DISTINCT QUESTION) FROM pses_wog WHERE is_scored"
    ).fetchone()[0]
    wog_stable: int = con.execute(
        "SELECT COUNT(DISTINCT QUESTION) FROM pses_wog WHERE is_stable"
    ).fetchone()[0]

    # --- pses_sliced --------------------------------------------------------
    con.execute(_SLICED_SQL)

    sliced_total: int = con.execute("SELECT COUNT(*) FROM pses_sliced").fetchone()[0]

    # --- pses_analysis ------------------------------------------------------
    con.execute(_ANALYSIS_SQL)

    analysis_total: int = con.execute("SELECT COUNT(*) FROM pses_analysis").fetchone()[0]
    by_indicator = con.execute(
        """
        SELECT INDICATORID, INDICATORENG, COUNT(*) AS n
        FROM   pses_analysis
        GROUP  BY INDICATORID, INDICATORENG
        ORDER  BY INDICATORID
        """
    ).fetchall()

    con.close()

    # --- Summary ------------------------------------------------------------
    print(
        f"pses_wog:    {wog_total:,} rows, "
        f"{wog_scored} scored questions, "
        f"{wog_stable} stable across all years"
    )
    print(f"pses_sliced:   {sliced_total:,} rows")
    print(f"pses_analysis: {analysis_total:,} rows")
    print("\nRows by indicator (pses_analysis):")
    for indicator_id, indicator_eng, n in by_indicator:
        print(f"  [{indicator_id}] {indicator_eng}: {n:,}")


if __name__ == "__main__":
    main()
