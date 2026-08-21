import marimo

__generated_with = "0.23.4"
app = marimo.App(width="columns")


@app.cell
def _(mo):
    mo.md("""
    # PSES Data Engineering Pipeline

    ## Overview

    This notebook builds the complete analytical dataset for the Public Service Employee Survey (PSES).
    It performs the following steps:

    1. **Ingestion**: Downloads the raw PSES CSV from Canada.ca and loads it into DuckDB
    2. **Theme Mapping**: Loads the theme/indicator taxonomy from Subset 1 CSV
    3. **Transformation**: Creates whole-of-government analytical tables
    4. **Statistical Analysis**: Computes theme scores, year-over-year changes, correlations, and chi-square tests

    **Output**: All tables are written to `data/pses.duckdb`

    **Reproducibility**: Any user can run this notebook from scratch to rebuild all analytical tables.
    If `data/pses.duckdb` already exists, it will be overwritten to ensure a clean build.

    **Data Source**: 
    - Main dataset: https://www.canada.ca/content/dam/tbs-sct/documents/datasets/ses-2025/main-principal.csv
    - Theme taxonomy: https://www.canada.ca/content/dam/tbs-sct/documents/datasets/ses-2025/subset-1-sous-ensemble-1.csv

    **Note on Government of Canada CSV files**: They are BOM-prefixed and Latin-1 encoded.
    """)
    return


@app.cell
def _():
    import marimo as mo
    import duckdb
    import polars as pl
    import os
    from pathlib import Path

    # Ensure data directory exists
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    db_path = str(data_dir / "pses.duckdb")
    return db_path, duckdb, mo, os


@app.cell
def _(mo):
    mo.md("""
    ## Step 0: Database Setup

    Connect to DuckDB. If the database file already exists, we'll drop and recreate
    all tables to ensure a clean, reproducible build.
    """)
    return


@app.cell
def _(db_path, duckdb, mo, os):
    # Check if DB exists - if so, we'll rebuild everything
    db_exists = os.path.exists(db_path)

    con = duckdb.connect(db_path)

    if db_exists:
        mo.md(f"**Note**: Database file `{db_path}` already exists. All tables will be recreated.")
    else:
        mo.md(f"**Creating new database**: `{db_path}`")
    return (con,)


@app.cell
def _(mo):
    mo.md("""
    ## Step 1: Data Ingestion

    ### Description
    Download and ingest the main PSES dataset directly from Canada.ca into DuckDB.

    **Source**: `https://www.canada.ca/content/dam/tbs-sct/documents/datasets/ses-2025/main-principal.csv`

    **Approach**: DuckDB's `read_csv_auto` function streams the CSV directly from the URL
    without downloading an intermediate file. This is efficient and handles the
    Government of Canada's BOM-prefixed, Latin-1 encoded files automatically.

    **Output Table**: `raw_pses` - Complete raw dataset with all columns and rows.

    **Note**: The `ignore_errors=true` parameter allows DuckDB to skip malformed rows,
    which is important for government datasets that may have data quality issues.
    """)
    return


@app.cell
def _(con, mo):
    CSV_URL = "https://www.canada.ca/content/dam/tbs-sct/documents/datasets/ses-2025/main-principal.csv"
    RAW_TABLE = "raw_pses"

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

    mo.md(f"**✓ Ingestion Complete**: {row_count:,} rows loaded into `{RAW_TABLE}`")
    return (RAW_TABLE,)


@app.cell
def _(mo):
    mo.md("""
    ### Ingestion Verification

    Let's verify the ingestion by checking the schema and some basic statistics.
    """)
    return


@app.cell
def _(RAW_TABLE, con, mo):
    # Fix Binder Error: The duckdb_columns function might not support VARCHAR arguments. 
    # Using information_schema instead, which is standard SQL.
    cols = con.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{RAW_TABLE}'").fetchall()

    mo.md("**Schema:**")
    for col_name, col_type in cols[:20]:  # Show first 20 columns
        mo.md(f"  - `{col_name}`: {col_type}")
    mo.md(f"  ... and {len(cols) - 20} more columns")

    # Check survey years
    years = con.execute(f"SELECT DISTINCT SURVEYR FROM {RAW_TABLE} ORDER BY SURVEYR").fetchall()
    mo.md(f"**Survey Years**: {[y[0] for y in years]}")
    return


@app.cell
def _(mo):
    mo.md("""
    ## Step 2: Theme Mapping

    ### Description
    Load the theme and indicator taxonomy from PSES Subset 1 CSV.

    **Source**: `https://www.canada.ca/content/dam/tbs-sct/documents/datasets/ses-2025/subset-1-sous-ensemble-1.csv`

    **Output Tables**:
    - `theme_map`: One row per QUESTION with its theme/subtheme labels (207 rows)
    - `indicator_map`: Distinct indicator/sub-indicator combinations - a lookup table (23 rows)

    **Filter**: We only load rows where LEVEL1ID = '00' and BYCOND IS NULL, which gives us
    the whole-of-government (WOG) theme taxonomy.

    **Note**: Government of Canada CSV files require special handling for BOM and encoding.
    We use a helper function to fetch, strip BOM, and decode from Latin-1 to UTF-8.
    """)
    return


@app.cell
def _():
    import tempfile
    import httpx

    def fetch_with_bom_strip(url: str) -> str:
        """Fetch a BOM-prefixed CSV from a URL, strip the BOM, write to temp file, return path."""
        response = httpx.get(url, timeout=60, follow_redirects=True)
        response.raise_for_status()
        content = response.content
        # Strip UTF-8 BOM if present
        if content.startswith(b'\xef\xbb\xbf'):
            content = content[3:]
        # Decode as latin-1 (accepts all bytes), re-encode as clean UTF-8
        text = content.decode('latin-1')
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.csv', mode='w', encoding='utf-8')
        tmp.write(text)
        tmp.close()
        return tmp.name

    return fetch_with_bom_strip,


@app.cell
def _(fetch_with_bom_strip, mo):
    SUBSET1_URL = (
        "https://www.canada.ca/content/dam/tbs-sct/documents/datasets/"
        "ses-2025/subset-1-sous-ensemble-1.csv"
    )

    csv_path = fetch_with_bom_strip(SUBSET1_URL)

    mo.md(f"**✓ Fetched theme CSV**: {SUBSET1_URL}")
    return (csv_path,)


@app.cell
def _(mo):
    mo.md("""
    ### Build theme_map table

    One row per QUESTION with theme/subtheme metadata.
    """)
    return


@app.cell
def _(con, csv_path, mo):
    con.execute("""
        CREATE OR REPLACE TABLE theme_map AS
        SELECT DISTINCT ON (QUESTION)
            QUESTION,
            TITLE_E,
            INDICATORID,
            INDICATORENG,
            SUBINDICATORID,
            SUBINDICATORENG
        FROM read_csv_auto(?, header = true)
        WHERE LEVEL1ID = '00'
          AND BYCOND IS NULL
        ORDER BY QUESTION
    """, [csv_path])

    n_theme_map = con.execute("SELECT COUNT(*) FROM theme_map").fetchone()[0]
    mo.md(f"**✓ theme_map created**: {n_theme_map} rows")
    return


@app.cell
def _(mo):
    mo.md("""
    ### Build indicator_map table

    Distinct indicator/sub-indicator combinations - serves as a lookup reference.
    """)
    return


@app.cell
def _(con, csv_path, mo):
    con.execute("""
        CREATE OR REPLACE TABLE indicator_map AS
        SELECT DISTINCT
            INDICATORID,
            INDICATORENG,
            SUBINDICATORID,
            SUBINDICATORENG
        FROM read_csv_auto(?, header = true)
        WHERE LEVEL1ID = '00'
          AND BYCOND IS NULL
        ORDER BY INDICATORID, SUBINDICATORID
    """, [csv_path])

    n_indicator = con.execute("SELECT COUNT(*) FROM indicator_map").fetchone()[0]
    mo.md(f"**✓ indicator_map created**: {n_indicator} rows")

    # Clean up temp file
    import os
    os.unlink(csv_path)
    return


@app.cell
def _(mo):
    mo.md("""
    ### Theme Taxonomy Summary

    Let's preview the theme structure to verify the mapping loaded correctly.
    """)
    return


@app.cell
def _(con, mo):
    theme_sample = con.execute("""
        SELECT QUESTION, TITLE_E, INDICATORID, INDICATORENG, SUBINDICATORID, SUBINDICATORENG
        FROM theme_map
        ORDER BY INDICATORID, SUBINDICATORID, QUESTION
        LIMIT 15
    """).fetchall()

    mo.md("**Sample theme_map rows:**")
    mo.md("| Question | Theme | Subtheme | Title |")
    mo.md("|----------|-------|----------|-------|")
    for row in theme_sample:
        mo.md(f"| {row[0]} | {row[3]} | {row[5]} | {row[1][:50]}... |")
    return


@app.cell
def _(mo):
    mo.md("""
    ## Step 3: Data Transformation

    ### Description
    Transform the raw data into analytical tables. This step creates three key tables:

    - **pses_wog**: Whole-of-government spine (LEVEL1ID=0, LEVEL2ID=0, BYCOND IS NULL)
      - Contains typed columns with 9999→NULL conversion for scoring fields
      - Includes `is_scored` and `is_stable` flags
      - ~772 rows (one per question per year for WOG)

    - **pses_sliced**: Whole-of-government demographic/org slices (LEVEL1ID=0, BYCOND IS NOT NULL)
      - Contains the same scoring columns as pses_wog
      - ~651K rows

    - **pses_analysis**: Primary analytical table - joins pses_wog with theme_map
      - Adds theme/subtheme metadata to the WOG spine
      - ~772 rows

    **Scoring Columns**: The following columns use 9999 as a sentinel for "missing" and are
    converted to INTEGER with NULL for 9999:
    - SCORE100, ANSCOUNT, POSITIVE, NEUTRAL, NEGATIVE, AGREE
    - answer1-answer7

    **SCORE5**: Converted to DOUBLE with NULL for 9999.0

    **is_scored**: TRUE when the cleaned SCORE100 is not null
    **is_stable**: TRUE when the question appeared in all survey years
    """)
    return


@app.cell
def _():
    # Columns that use 9999 as "missing" sentinel
    INT_COLS = [
        "SCORE100", "ANSCOUNT", "POSITIVE", "NEUTRAL", "NEGATIVE", "AGREE",
        "answer1", "answer2", "answer3", "answer4", "answer5", "answer6", "answer7"
    ]

    def int_expr(col: str) -> str:
        return f"NULLIF(CAST({col} AS INTEGER), 9999) AS {col}"

    score5_expr = "NULLIF(CAST(SCORE5 AS DOUBLE), 9999.0) AS SCORE5"

    shared_select = (
        "CAST(SURVEYR AS INTEGER) AS SURVEYR, QUESTION," +
        ", ".join(int_expr(c) for c in INT_COLS) +
        f", {score5_expr}"
    )

    return INT_COLS, int_expr, score5_expr, shared_select


@app.cell
def _(mo):
    mo.md("""
    ### Create pses_wog table

    Whole-of-government spine with cleaned, typed columns.
    """)
    return


@app.cell
def _(INT_COLS, int_expr, score5_expr, shared_select, con, mo):
    con.execute(f"""
        CREATE OR REPLACE TABLE pses_wog AS
        WITH
          -- rows that form the whole-of-government spine
          base AS (
            SELECT
                {shared_select},
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
            {", ".join(f"b.{c}" for c in INT_COLS)},
            b.SCORE5,
            -- is_scored: true when the cleaned SCORE100 is not null
            NULLIF(CAST(b.SCORE100 AS INTEGER), 9999) IS NOT NULL AS is_scored,
            -- is_stable: true when this question appeared in all survey years
            (b.QUESTION IN (SELECT QUESTION FROM stable_questions)) AS is_stable
        FROM base b
    """)

    wog_total = con.execute("SELECT COUNT(*) FROM pses_wog").fetchone()[0]
    wog_scored = con.execute("SELECT COUNT(DISTINCT QUESTION) FROM pses_wog WHERE is_scored").fetchone()[0]
    wog_stable = con.execute("SELECT COUNT(DISTINCT QUESTION) FROM pses_wog WHERE is_stable").fetchone()[0]

    mo.md(f"**✓ pses_wog created**: {wog_total:,} rows")
    mo.md(f"  - Scored questions: {wog_scored}")
    mo.md(f"  - Stable across all years: {wog_stable}")
    return (INT_COLS,)


@app.cell
def _(mo):
    mo.md("""
    ### Create pses_sliced table

    Whole-of-government demographic/org slices.
    """)
    return


@app.cell
def _(INT_COLS, int_expr, score5_expr, con, mo):
    int_exprs = ", ".join(int_expr(c) for c in INT_COLS)
    score5_expr_sliced = score5_expr

    con.execute(f"""
        CREATE OR REPLACE TABLE pses_sliced AS
        SELECT
            CAST(SURVEYR AS INTEGER) AS SURVEYR,
            QUESTION,
            BYCOND,
            DEMCODE,
            {int_exprs},
            {score5_expr_sliced}
        FROM raw_pses
        WHERE BYCOND IS NOT NULL
          AND LEVEL1ID = 0
    """)

    sliced_total = con.execute("SELECT COUNT(*) FROM pses_sliced").fetchone()[0]
    mo.md(f"**✓ pses_sliced created**: {sliced_total:,} rows")
    return


@app.cell
def _(mo):
    mo.md("""
    ### Create pses_analysis table

    Primary analytical table - joins pses_wog with theme_map to add theme metadata.
    """)
    return


@app.cell
def _(con, mo):
    con.execute("""
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
    """)

    analysis_total = con.execute("SELECT COUNT(*) FROM pses_analysis").fetchone()[0]
    mo.md(f"**✓ pses_analysis created**: {analysis_total:,} rows")
    return


@app.cell
def _(mo):
    mo.md("""
    ## Step 4: Statistical Analysis Tables

    ### Description
    Compute analytical tables that summarize and analyze the data:

    - **theme_scores**: Mean SCORE100 per subtheme per year (72 rows)
      - Used for trend analysis across survey cycles
      - Only includes fully scored questions (SCORE100 non-null in all 4 years)

    - **yoy_changes**: Year-over-year delta in mean_score per subtheme (54 rows)
      - Compares: 2019→2020, 2020→2022, 2022→2024
      - Allows tracking of trends between survey cycles

    - **question_correlations**: Pearson r between every stable question pair (~1,711 rows)
      - Helps identify question clusters and construct validity
      - Note: With only 4 years (n=4), correlations should be interpreted cautiously

    - **chi_square_results**: Chi-square test on answer1-5 distribution 2019 vs 2024 (59 rows)
      - Tests whether response distributions have changed significantly
      - With ~186,000 respondents, even small shifts are detectable

    **Longitudinal Filter**: All analytical tables use the following filter to ensure
    only questions that are scored in ALL four years (2019, 2020, 2022, 2024) are included:
    ```sql
    QUESTION IN (
        SELECT QUESTION FROM pses_analysis
        WHERE is_stable = true
        GROUP BY QUESTION
        HAVING COUNT(CASE WHEN SCORE100 IS NOT NULL THEN 1 END) = 4
    )
    ```

    **Q73 Exclusion**: Q73a-Q73w are 2024-only stress sub-questions and are excluded from
    longitudinal analysis. Only Q74 and Q75 are valid stress trend questions.
    """)
    return


@app.cell
def _():
    # Subquery: questions where SCORE100 is non-null in all 4 survey years
    FSQ = """
        SELECT QUESTION
        FROM pses_analysis
        WHERE is_stable = true
        GROUP BY QUESTION
        HAVING COUNT(CASE WHEN SCORE100 IS NOT NULL THEN 1 END) = 4
    """
    return (FSQ,)


@app.cell
def _(mo):
    mo.md("""
    ### Create theme_scores table

    Mean SCORE100 per subtheme per year for longitudinal analysis.
    """)
    return


@app.cell
def _(FSQ, con, mo):
    con.execute(f"""
        CREATE OR REPLACE TABLE theme_scores AS
        SELECT
            SURVEYR,
            INDICATORID,
            INDICATORENG,
            SUBINDICATORID,
            SUBINDICATORENG,
            AVG(SCORE100) AS mean_score
        FROM pses_analysis
        WHERE QUESTION IN ({FSQ})
          AND QUESTION NOT LIKE 'Q73%'
        GROUP BY
            SURVEYR,
            INDICATORID,
            INDICATORENG,
            SUBINDICATORID,
            SUBINDICATORENG
        ORDER BY
            INDICATORID,
            SUBINDICATORID,
            SURVEYR
    """)

    n_theme_scores = con.execute("SELECT COUNT(*) FROM theme_scores").fetchone()[0]
    mo.md(f"**✓ theme_scores created**: {n_theme_scores} rows")
    return


@app.cell
def _(mo):
    mo.md("""
    ### Create yoy_changes table

    Year-over-year delta in mean_score per subtheme.
    """)
    return


@app.cell
def _(con, mo):
    con.execute("""
        CREATE OR REPLACE TABLE yoy_changes AS
        SELECT
            a.SUBINDICATORENG,
            a.INDICATORENG,
            a.SURVEYR AS year_from,
            b.SURVEYR AS year_to,
            a.mean_score AS score_from,
            b.mean_score AS score_to,
            b.mean_score - a.mean_score AS delta
        FROM theme_scores a
        JOIN theme_scores b
          ON a.SUBINDICATORID = b.SUBINDICATORID
          AND (
                (a.SURVEYR = 2019 AND b.SURVEYR = 2020)
             OR (a.SURVEYR = 2020 AND b.SURVEYR = 2022)
             OR (a.SURVEYR = 2022 AND b.SURVEYR = 2024)
              )
        ORDER BY
            a.SUBINDICATORENG,
            a.SURVEYR
    """)

    n_yoy = con.execute("SELECT COUNT(*) FROM yoy_changes").fetchone()[0]
    mo.md(f"**✓ yoy_changes created**: {n_yoy} rows")
    return


@app.cell
def _(mo):
    mo.md("""
    ### Create question_correlations table

    Pearson r between every stable question pair (Python-side computation with scipy).
    """)
    return


@app.cell
def _(FSQ, con, mo):
    import itertools
    from collections import defaultdict
    from scipy.stats import pearsonr

    # One row per (SURVEYR, QUESTION) - spine is already unique on this key
    long_rows = con.execute(f"""
        SELECT SURVEYR, QUESTION, SCORE100
        FROM pses_analysis
        WHERE QUESTION IN ({FSQ})
          AND QUESTION NOT LIKE 'Q73%'
        ORDER BY QUESTION, SURVEYR
    """).fetchall()

    # Build pivot: question -> {year: score}
    pivot = defaultdict(dict)
    for surveyr, question, score in long_rows:
        pivot[question][surveyr] = float(score)

    years_list = [2019, 2020, 2022, 2024]

    # Keep only questions present in all 4 years
    questions = sorted(
        q for q, yr_map in pivot.items()
        if all(y in yr_map for y in years_list)
    )

    # Build vectors: question -> list[score] aligned to years
    vectors = {
        q: [pivot[q][y] for y in years_list]
        for q in questions
    }

    # Compute all pairs
    corr_rows = []
    for q_a, q_b in itertools.combinations(questions, 2):
        v_a = vectors[q_a]
        v_b = vectors[q_b]
        try:
            r, _p = pearsonr(v_a, v_b)
            corr_rows.append((q_a, q_b, float(r), float(_p)))
        except Exception:
            pass  # skip degenerate pairs

    # Write table
    con.execute("""
        CREATE OR REPLACE TABLE question_correlations (
            question_a  VARCHAR,
            question_b  VARCHAR,
            pearson_r   DOUBLE,
            p_value     DOUBLE
        )
    """)
    con.executemany(
        "INSERT INTO question_correlations VALUES (?, ?, ?, ?)",
        corr_rows,
    )

    n_corr = len(corr_rows)
    mo.md(f"**✓ question_correlations created**: {n_corr:,} rows")
    return


@app.cell
def _(mo):
    mo.md("""
    ### Create chi_square_results table

    Chi-square test on answer1-5 distribution between 2019 and 2024 (Python-side with scipy).
    """)
    return


@app.cell
def _(FSQ, con, mo):
    from scipy.stats import chi2_contingency

    rows = con.execute(f"""
        SELECT QUESTION, SURVEYR,
               answer1, answer2, answer3, answer4, answer5,
               ANSCOUNT
        FROM pses_analysis
        WHERE QUESTION IN ({FSQ})
          AND QUESTION NOT LIKE 'Q73%'
          AND SURVEYR IN (2019, 2024)
        ORDER BY QUESTION, SURVEYR
    """).fetchall()

    # Fetch indicator labels
    labels = {
        q: (ie, se)
        for q, ie, se in con.execute(f"""
            SELECT DISTINCT QUESTION, INDICATORENG, SUBINDICATORENG
            FROM pses_analysis
            WHERE QUESTION IN ({FSQ})
              AND QUESTION NOT LIKE 'Q73%'
        """).fetchall()
    }

    # Collect per-question rows for each year: store (pcts, anscount)
    data = {}
    for q, year, a1, a2, a3, a4, a5, anscount in rows:
        if q not in data:
            data[q] = {"years": {}}
        data[q]["years"][year] = ([a1, a2, a3, a4, a5], anscount)

    chi_rows = []
    for q, info in sorted(data.items()):
        yr = info["years"]
        if 2019 not in yr or 2024 not in yr:
            continue
        pcts_2019, anscount_2019 = yr[2019]
        pcts_2024, anscount_2024 = yr[2024]
        # Skip if any percentage or anscount is NULL
        if any(v is None for v in pcts_2019 + pcts_2024):
            continue
        if anscount_2019 is None or anscount_2024 is None:
            continue
        # Reconstruct estimated raw counts from percentages x ANSCOUNT
        counts_2019 = [round((pct / 100) * anscount_2019) for pct in pcts_2019]
        counts_2024 = [round((pct / 100) * anscount_2024) for pct in pcts_2024]
        # Skip if either row sums to zero
        if sum(counts_2019) == 0 or sum(counts_2024) == 0:
            continue
        ind_eng, sub_eng = labels.get(q, ("", ""))
        try:
            chi2, p_chi, dof, _ = chi2_contingency([counts_2019, counts_2024])
            chi_rows.append((
                q,
                ind_eng,
                sub_eng,
                float(chi2),
                float(p_chi),
                int(dof),
                bool(p_chi < 0.05),
            ))
        except Exception:
            pass

    con.execute("""
        CREATE OR REPLACE TABLE chi_square_results (
            QUESTION        VARCHAR,
            INDICATORENG    VARCHAR,
            SUBINDICATORENG VARCHAR,
            chi2            DOUBLE,
            p_value         DOUBLE,
            dof             INTEGER,
            significant     BOOLEAN
        )
    """)

    if chi_rows:
        con.executemany(
            "INSERT INTO chi_square_results VALUES (?, ?, ?, ?, ?, ?, ?)",
            chi_rows,
        )
    else:
        mo.md("**Note**: No questions met the criteria for chi-square testing. chi_square_results remain empty.")

    n_chi = len(chi_rows)
    mo.md(f"**✓ chi_square_results created**: {n_chi} rows")
    return


@app.cell
def _(mo):
    mo.md("""
    ## Step 5: Pipeline Validation & Summary

    ### Description
    Verify all tables were created successfully and display summary statistics.
    """)
    return


@app.cell
def _(con, mo):
    tables = [
        "raw_pses", "theme_map", "indicator_map",
        "pses_wog", "pses_sliced", "pses_analysis",
        "theme_scores", "yoy_changes",
        "question_correlations", "chi_square_results"
    ]

    mo.md("**=== PIPELINE COMPLETE ===\n")
    mo.md("**Table Summary:**")
    mo.md("| Table | Rows | Description |")
    mo.md("|-------|------|-------------|")

    for table in tables:
        count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        desc = {
            "raw_pses": "Full ingested dataset, untouched",
            "theme_map": "Question → theme/subtheme lookup (2024)",
            "indicator_map": "Flat theme/subtheme reference table",
            "pses_wog": "Whole-of-govt spine, typed, 9999→NULL",
            "pses_sliced": "Demographic/org slices (BYCOND IS NOT NULL)",
            "pses_analysis": "pses_wog JOIN theme_map — primary analytical table",
            "theme_scores": "Mean SCORE100 per subtheme per year (longitudinal)",
            "yoy_changes": "Year-over-year deltas per subtheme",
            "question_correlations": "Pearson r between all question pairs (n=4 caution)",
            "chi_square_results": "Chi-square 2019 vs 2024 per question",
        }[table]
        mo.md(f"| `{table}` | {count:,} | {desc} |")

    con.close()

    mo.md("\n**✓ All tables created successfully!**")
    mo.md("\n**Next Steps:** Run `02_exploration.py` to analyze the data.")
    return


# Example of pipe command usage for data transformation
# In this notebook, values flow between cells via function parameters (Marimo's reactive system)
# For example: fetch_with_bom_strip function is defined in one cell and used in another
# The SQL expressions use string formatting with f-strings for composition

if __name__ == "__main__":
    app.run()
