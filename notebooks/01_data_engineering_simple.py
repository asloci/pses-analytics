import marimo

__generated_with = "0.24.0"
app = marimo.App(width="columns")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _(mo):
    mo.md("""
    # Data Engineering 🌊🍃 Notebook for the Government of Canada Public Service Employee Survey (PSES)

    ## Summary

    This notebook ingested and built an analytical database to display Public Service Employee Survey (PSES) results for longitudinal analysis across themes and sub-themes.

    It performed the following steps:

    1. **Ingestion**: Downloaded the raw PSES CSV and converted it into [DuckDB](https://duckdb.org/) format
    2. **Theme Mapping**: Loaded the theme/indicator taxonomy from Subset 1 CSV[^1]
    3. **Transformation**: Created whole-of-government analytical tables
    4. **Statistical Analysis**: Computed theme scores, year-over-year changes

    **Output**:

    All tables were written to `data/pses.duckdb`. If you do not see sample data in [Results](#results), you can generate the database using the button below.

    **Data Source**:

    - Main dataset: https://www.canada.ca/content/dam/tbs-sct/documents/datasets/ses-2025/main-principal.csv
    - Theme taxonomy: https://www.canada.ca/content/dam/tbs-sct/documents/datasets/ses-2025/subset-1-sous-ensemble-1.csv

    [^1]: This file contains characters out of range for the UTF-8 encoding. [Annex](#annex) contains the helper function that deals with the BOM-prefixed, Latin-1 encoded file in question.
    """)
    return


@app.cell
def _(mo):
    rundb_button = mo.ui.run_button(label="Generate the PSES Analytical Database (DuckDB format)")
    rundb_button
    return


@app.cell
def _(mo):
    mo.Html(
        """
        <div style="background-color: rgba(255, 204, 0, 0.2); padding: 20px; border-left: 4px solid #ffcc00; border-radius: 4px;">
            &#9888;&#65039; <strong>Attention:</strong> The section below does not describe or analyze the survey results. It shows a sample and statistics of the generated analytical database.
        </div>
        """
    )
    return


@app.cell
def _():
    import duckdb
    import os
    from pathlib import Path

    db_path = str(Path("../data") / "pses.duckdb")
    con = duckdb.connect(db_path)
    return con, db_path, duckdb


@app.cell
def _(con):
    import time

    def get_statistics():
        start = time.time()
        all_tables = con.execute("SHOW TABLES").fetchall()
        stats = []
        for (table_name,) in all_tables:
            count_start = time.time()
            count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            elapsed = time.time() - count_start
            stats.append({
                "Table_name": table_name,
                "Number_of_rows": count,
                "Time_elapsed_in_ms": round(elapsed * 1000, 2)
            })
        total_elapsed = time.time() - start
        return stats, total_elapsed

    table_stats, total_elapsed = get_statistics()

    # Return variables for downstream use
    return table_stats, total_elapsed


@app.cell
def _(table_stats, total_elapsed):
    total_ms = total_elapsed * 1000

    total_rows = sum(stat["Number_of_rows"] for stat in table_stats)
    num_tables = len(table_stats)
    total_ms = total_elapsed * 1000

    summary = (
        f"Over **{total_rows:,}** rows counted across **{num_tables}** tables "
        f"in less than **{total_ms:.1f} ms**."
    )

    # Sort by rows descending for marimo table
    sorted_stats = sorted(table_stats, key=lambda x: x["Number_of_rows"], reverse=True)
    return sorted_stats, summary


@app.cell(hide_code=True)
def _(mo, summary):
    mo.md(f"""
    ##Results\n\n{summary}
    """)
    return


@app.cell
def _(mo, sorted_stats):
    mo.ui.table(data=sorted_stats, label='Query Statistics:')
    return


@app.cell
def _(mo):
    mo.md("""
    Whole-of-government table sample from the database retrieved using the following SQL statement:
    ```sql
    SELECT * FROM pses_wog LIMIT 50
    ```
    """)
    return


@app.cell(hide_code=True)
def _(con, mo):
    _df = mo.sql(
        f"""
        SELECT * FROM pses_wog LIMIT 50
        """,
        engine=con
    )
    return


@app.cell
def _(db_path, duckdb, run_pipeline):
    CSV_URL = "https://www.canada.ca/content/dam/tbs-sct/documents/datasets/ses-2025/main-principal.csv"
    RAW_TABLE = "raw_pses"
    if run_pipeline:
        pipe_con_1 = duckdb.connect(db_path)
        pipe_con_1.execute(f"DROP TABLE IF EXISTS {RAW_TABLE}")
        pipe_con_1.execute(f"CREATE TABLE {RAW_TABLE} AS SELECT * FROM read_csv_auto('{CSV_URL}', header=true, ignore_errors=true)")
        row_count_1 = pipe_con_1.execute(f"SELECT COUNT(*) FROM {RAW_TABLE}").fetchone()[0]
        pipe_con_1.close()
        msg_1 = f"**Ingestion Complete**: {row_count_1:,} rows loaded into `{RAW_TABLE}`"
    else:
        try:
            chk_con_1 = duckdb.connect(db_path)
            row_count_1 = chk_con_1.execute(f"SELECT COUNT(*) FROM {RAW_TABLE}").fetchone()[0]
            chk_con_1.close()
            msg_1 = f"**Using existing table**: `{RAW_TABLE}` with {row_count_1:,} rows"
        except Exception:
            msg_1 = f"*Table `{RAW_TABLE}` not found*"
    return RAW_TABLE, msg_1


@app.cell
def _(mo, msg_1):
    mo.md(msg_1)
    return


@app.cell
def _():
    import tempfile
    import httpx
    def fetch_with_bom_strip(url: str) -> str:
        response = httpx.get(url, timeout=60, follow_redirects=True)
        response.raise_for_status()
        content = response.content
        if content.startswith(b'\xef\xbb\xbf'):
            content = content[3:]
        text = content.decode('latin-1')
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.csv', mode='w', encoding='utf-8')
        tmp.write(text)
        tmp.close()
        return tmp.name

    return (fetch_with_bom_strip,)


@app.cell
def _(fetch_with_bom_strip, mo, run_pipeline):
    if run_pipeline:
        SUBSET1_URL = "https://www.canada.ca/content/dam/tbs-sct/documents/datasets/ses-2025/subset-1-sous-ensemble-1.csv"
        csv_path_1 = fetch_with_bom_strip(SUBSET1_URL)
        mo.md(f"**Fetched theme CSV**: {SUBSET1_URL}")
    else:
        csv_path_1 = None
    return (csv_path_1,)


@app.cell
def _():
    INT_COLS = ["SCORE100", "ANSCOUNT", "POSITIVE", "NEUTRAL", "NEGATIVE", "AGREE",
               "answer1", "answer2", "answer3", "answer4", "answer5", "answer6", "answer7"]
    def make_int_expr(col):
        return f"NULLIF(CAST({col} AS INTEGER), 9999) AS {col}"
    def make_double_expr(col):
        return f"NULLIF(CAST({col} AS DOUBLE), 9999.0) AS {col}"

    return INT_COLS, make_double_expr, make_int_expr


@app.cell
def _(
    INT_COLS,
    RAW_TABLE,
    db_path,
    duckdb,
    make_double_expr,
    make_int_expr,
    mo,
    run_pipeline,
):
    if run_pipeline:
        pipe_con_2 = duckdb.connect(db_path)
        int_exprs = ", ".join(make_int_expr(c) for c in INT_COLS)
        score5_expr = make_double_expr("SCORE5")
        shared_select = f"CAST(SURVEYR AS INTEGER) AS SURVEYR, QUESTION, {int_exprs}, {score5_expr}"
        pipe_con_2.execute(f"""
            CREATE OR REPLACE TABLE pses_wog AS
            WITH base AS (SELECT {shared_select}, SCORE100 FROM {RAW_TABLE} WHERE LEVEL1ID = 0 AND LEVEL2ID = 0 AND BYCOND IS NULL),
            stable_questions AS (SELECT QUESTION FROM {RAW_TABLE} WHERE LEVEL1ID = 0 AND LEVEL2ID = 0 AND BYCOND IS NULL GROUP BY QUESTION HAVING COUNT(DISTINCT SURVEYR) = (SELECT COUNT(DISTINCT SURVEYR) FROM {RAW_TABLE}))
            SELECT b.SURVEYR, b.QUESTION, {int_exprs}, b.SCORE5,
                NULLIF(CAST(b.SCORE100 AS INTEGER), 9999) IS NOT NULL AS is_scored,
                (b.QUESTION IN (SELECT QUESTION FROM stable_questions)) AS is_stable FROM base b
        """)
        wog_total = pipe_con_2.execute("SELECT COUNT(*) FROM pses_wog").fetchone()[0]
        pipe_con_2.close()
        mo.md(f"**pses_wog created**: {wog_total:,} rows")
    return


@app.cell
def _(csv_path_1, db_path, duckdb, mo, run_pipeline):
    if run_pipeline and csv_path_1:
        pipe_con_3 = duckdb.connect(db_path)
        pipe_con_3.execute("""
            CREATE OR REPLACE TABLE theme_map AS
            SELECT DISTINCT ON (QUESTION) QUESTION, TITLE_E, INDICATORID, INDICATORENG, SUBINDICATORID, SUBINDICATORENG
            FROM read_csv_auto(?, header=true) WHERE LEVEL1ID = '00' AND BYCOND IS NULL ORDER BY QUESTION""", [csv_path_1])
        n_theme = pipe_con_3.execute("SELECT COUNT(*) FROM theme_map").fetchone()[0]
        mo.md(f"**theme_map created**: {n_theme} rows")
        pipe_con_3.execute("""
            CREATE OR REPLACE TABLE indicator_map AS
            SELECT DISTINCT INDICATORID, INDICATORENG, SUBINDICATORID, SUBINDICATORENG
            FROM read_csv_auto(?, header=true) WHERE LEVEL1ID = '00' AND BYCOND IS NULL ORDER BY INDICATORID, SUBINDICATORID""", [csv_path_1])
        n_indicator = pipe_con_3.execute("SELECT COUNT(*) FROM indicator_map").fetchone()[0]
        mo.md(f"**indicator_map created**: {n_indicator} rows")
        import os as _os
        _os.unlink(csv_path_1)
        pipe_con_3.close()
    return


@app.cell
def _(db_path, duckdb, mo, run_pipeline):
    if run_pipeline:
        pipe_con_4 = duckdb.connect(db_path)
        pipe_con_4.execute("""
            CREATE OR REPLACE TABLE pses_analysis AS
            SELECT w.*, t.TITLE_E, t.INDICATORID, t.INDICATORENG, t.SUBINDICATORID, t.SUBINDICATORENG
            FROM pses_wog w INNER JOIN theme_map t ON w.QUESTION = t.QUESTION""")
        n_analysis = pipe_con_4.execute("SELECT COUNT(*) FROM pses_analysis").fetchone()[0]
        pipe_con_4.close()
        mo.md(f"**pses_analysis created**: {n_analysis:,} rows")
    return


@app.cell
def _(mo):
    mo.md("""
    ## Explanation

    Python and SQL are used to ingest and transform the survey data into an analytical database.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ### Ingestion: Raw Data

    Loads the main PSES dataset from CSV into DuckDB.

    ```sql
    DROP TABLE IF EXISTS raw_pses
    CREATE TABLE raw_pses AS SELECT *
    FROM read_csv_auto('https://www.canada.ca/content/dam/tbs-sct/documents/datasets/ses-2025/main-principal.csv', header=true, ignore_errors=true)
    ```
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ### Ingestion: Theme Taxonomy

    Loads the theme/indicator taxonomy from Subset 1 CSV.

    ```sql
    CREATE OR REPLACE TABLE theme_map AS
    SELECT DISTINCT ON (QUESTION) QUESTION, TITLE_E, INDICATORID, INDICATORENG, SUBINDICATORID, SUBINDICATORENG
    FROM read_csv_auto(?, header=true) WHERE LEVEL1ID = '00' AND BYCOND IS NULL ORDER BY QUESTION

    CREATE OR REPLACE TABLE indicator_map AS
    SELECT DISTINCT INDICATORID, INDICATORENG, SUBINDICATORID, SUBINDICATORENG
    FROM read_csv_auto(?, header=true) WHERE LEVEL1ID = '00' AND BYCOND IS NULL ORDER BY INDICATORID, SUBINDICATORID
    ```
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ### Transformation: Whole-of-Government Spine

    A combination of Python and SQL is used for this transformation step. A list is created in Python and two helper functions that do the `NULLIF CAST` to a `cols` variable for `9999` and `9999.0`. These are applied to build and execute the SQL that creates the `pses_wog` table.

    ```sql
    CREATE OR REPLACE TABLE pses_wog AS
    WITH base AS (SELECT CAST(SURVEYR AS INTEGER) AS SURVEYR, QUESTION, NULLIF(CAST(SCORE100 AS INTEGER), 9999) AS SCORE100, NULLIF(CAST(ANSCOUNT AS INTEGER), 9999) AS ANSCOUNT, NULLIF(CAST(POSITIVE AS INTEGER), 9999) AS POSITIVE, NULLIF(CAST(NEUTRAL AS INTEGER), 9999) AS NEUTRAL, NULLIF(CAST(NEGATIVE AS INTEGER), 9999) AS NEGATIVE, NULLIF(CAST(AGREE AS INTEGER), 9999) AS AGREE, NULLIF(CAST(answer1 AS INTEGER), 9999) AS answer1, NULLIF(CAST(answer2 AS INTEGER), 9999) AS answer2, NULLIF(CAST(answer3 AS INTEGER), 9999) AS answer3, NULLIF(CAST(answer4 AS INTEGER), 9999) AS answer4, NULLIF(CAST(answer5 AS INTEGER), 9999) AS answer5, NULLIF(CAST(answer6 AS INTEGER), 9999) AS answer6, NULLIF(CAST(answer7 AS INTEGER), 9999) AS answer7, NULLIF(CAST(SCORE5 AS DOUBLE), 9999.0) AS SCORE5 FROM raw_pses WHERE LEVEL1ID = 0 AND LEVEL2ID = 0 AND BYCOND IS NULL),
    stable_questions AS (SELECT QUESTION FROM raw_pses WHERE LEVEL1ID = 0 AND LEVEL2ID = 0 AND BYCOND IS NULL GROUP BY QUESTION HAVING COUNT(DISTINCT SURVEYR) = (SELECT COUNT(DISTINCT SURVEYR) FROM raw_pses))
    SELECT b.SURVEYR, b.QUESTION, NULLIF(CAST(SCORE100 AS INTEGER), 9999) AS SCORE100, NULLIF(CAST(ANSCOUNT AS INTEGER), 9999) AS ANSCOUNT, NULLIF(CAST(POSITIVE AS INTEGER), 9999) AS POSITIVE, NULLIF(CAST(NEUTRAL AS INTEGER), 9999) AS NEUTRAL, NULLIF(CAST(NEGATIVE AS INTEGER), 9999) AS NEGATIVE, NULLIF(CAST(AGREE AS INTEGER), 9999) AS AGREE, NULLIF(CAST(answer1 AS INTEGER), 9999) AS answer1, NULLIF(CAST(answer2 AS INTEGER), 9999) AS answer2, NULLIF(CAST(answer3 AS INTEGER), 9999) AS answer3, NULLIF(CAST(answer4 AS INTEGER), 9999) AS answer4, NULLIF(CAST(answer5 AS INTEGER), 9999) AS answer5, NULLIF(CAST(answer6 AS INTEGER), 9999) AS answer6, NULLIF(CAST(answer7 AS INTEGER), 9999) AS answer7, NULLIF(CAST(b.SCORE100 AS INTEGER), 9999) IS NOT NULL AS is_scored, (b.QUESTION IN (SELECT QUESTION FROM stable_questions)) AS is_stable FROM base b
    ```
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ### Modern Alternative: Simplified NULL Handling

    Instead of individual `NULLIF(CAST(...))` for each column, modern SQL offers cleaner approaches:

    **Option 1: CASE statement**
    ```sql
    CASE WHEN SCORE100 = 9999 THEN NULL ELSE CAST(SCORE100 AS INTEGER) END AS SCORE100
    ```

    **Option 2: TRY_CAST (DuckDB-specific)**
    ```sql
    TRY_CAST(SCORE100 AS INTEGER) AS SCORE100
    ```
    Note: This only works if 9999 is outside the target type's valid domain.

    **Option 3: Declarative transform with a mapping**
    ```python
    # Define once in Python, apply to all columns
    transform = lambda col, sentinel=9999: f"CASE WHEN {col} = {sentinel} THEN NULL ELSE CAST({col} AS INTEGER) END AS {col}"
    ```

    These approaches reduce verbosity while maintaining the same data cleaning logic.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ### Transformation: Theme Lookup Table

    ```sql
    CREATE OR REPLACE TABLE theme_map AS
    SELECT DISTINCT ON (QUESTION) QUESTION, TITLE_E, INDICATORID, INDICATORENG, SUBINDICATORID, SUBINDICATORENG
    FROM read_csv_auto(?, header=true) WHERE LEVEL1ID = '00' AND BYCOND IS NULL ORDER BY QUESTION
    ```
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ### Transformation: Indicator Lookup Table

    ```sql
    CREATE OR REPLACE TABLE indicator_map AS
    SELECT DISTINCT INDICATORID, INDICATORENG, SUBINDICATORID, SUBINDICATORENG
    FROM read_csv_auto(?, header=true) WHERE LEVEL1ID = '00' AND BYCOND IS NULL ORDER BY INDICATORID, SUBINDICATORID
    ```
    """)
    return


@app.cell
def _(db_path, mo, run_pipeline):
    import duckdb as _dd
    summary_con = _dd.connect(db_path)
    tables = ["raw_pses", "theme_map", "indicator_map", "pses_wog", "pses_analysis"]
    mo.md("**Table Summary:**")
    mo.md("| Table | Rows | Description |")
    mo.md("|-------|------|-------------|")
    for t in tables:
        try:
            c = summary_con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            d = {"raw_pses": "Full ingested dataset", "theme_map": "Question-theme lookup", 
                 "indicator_map": "Theme reference", "pses_wog": "WOG spine", 
                 "pses_analysis": "Primary analytical table"}
            mo.md(f"| `{t}` | {c:,} | {d.get(t, t)} |")
        except Exception:
            mo.md(f"| `{t}` | N/A | Not yet created |")
    summary_con.close()
    if run_pipeline:
        mo.md("\n**Pipeline complete!** All tables created successfully.")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Annex

    The BOM-prefix stripper helper function is used to deal with Excel-like artefacts.

    ```
    import tempfile
    import httpx
    def fetch_with_bom_strip(url: str) -> str:
        response = httpx.get(url, timeout=60, follow_redirects=True)
        response.raise_for_status()
        content = response.content
        if content.startswith(b'\xef\xbb\xbf'):
            content = content[3:]
        text = content.decode('latin-1')
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.csv', mode='w', encoding='utf-8')
        tmp.write(text)
        tmp.close()
        return tmp.name
    ```
    """)
    return


if __name__ == "__main__":
    app.run()
