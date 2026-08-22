import marimo

__generated_with = "0.24.0"
app = marimo.App(width="columns")


@app.cell
def _(mo):
    mo.md("""
    # Data Engineering 🌊🍃 Notebook for the Government of Canada Public Service Employee Survey (PSES)

    ## Overview

    This notebook ingested and built an analytical dataset for Public Service Employee Survey (PSES) results longitudinal analysis across themes and sub-themes.

    It performed the following steps:

    1. **Ingestion**: Downloaded the raw PSES CSV from Canada.ca and converted it into DuckDB format
    2. **Theme Mapping**: Loaded the theme/indicator taxonomy from Subset 1 CSV[^1]
    3. **Transformation**: Created whole-of-government analytical tables
    4. **Statistical Analysis**: Computed theme scores, year-over-year changes

    **Output**:

    All tables were written to `data/pses.duckdb`. If you do not see a sample at [Section 2: Database Setup](#database-setup), you can generate one using this notebook.

    **Reproducibility**:

    Any user can run this notebook ***insert instructions on uv and code execution***

    **Data Source**:

    - Main dataset: https://www.canada.ca/content/dam/tbs-sct/documents/datasets/ses-2025/main-principal.csv
    - Theme taxonomy: https://www.canada.ca/content/dam/tbs-sct/documents/datasets/ses-2025/subset-1-sous-ensemble-1.csv

    [^1]: This file contains characters out of range for the UTF-8 encoding. [Annex](#annex) contains the helper function that deals with the BOM-prefixed, Latin-1 encoded file in question.
    """)
    return


@app.cell
def _():
    import marimo as mo
    import duckdb
    import os
    from pathlib import Path
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    db_path = str(data_dir / "pses.duckdb")
    return db_path, duckdb, mo, os


@app.cell
def _(mo):
    mo.md("""
    ## Database Setup

    Check for existing database. If it exists, view sample data and download. If not, generate it.
    """)
    return


@app.cell
def _(db_path, duckdb, os):
    db_exists = os.path.exists(db_path)
    if db_exists:
        check_con = duckdb.connect(db_path)
        try:
            sample = check_con.execute("SELECT * FROM pses_analysis LIMIT 5").fetchdf()
            if sample is not None and len(sample) > 0:
                db_status = "exists_with_data"
                sample_table = sample
            else:
                db_status = "exists_empty"
                sample_table = None
        except Exception:
            db_status = "exists_empty"
            sample_table = None
        check_con.close()
    else:
        db_status = "not_exists"
        sample_table = None
    return db_status, sample_table


@app.cell
def _(db_path, db_status, mo, sample_table):
    if db_status == "exists_with_data":
        mo.ui.table(sample_table)
        mo.md(f"**Database exists**: `{db_path}`")
        download_btn = mo.ui.button(label="Download Database", value=False)
        run_btn = None
    elif db_status == "exists_empty":
        mo.md(f"**Database exists but is empty**: `{db_path}`")
        run_btn = mo.ui.button(label="Generate Database", value=False)
        download_btn = None
    else:
        mo.md(f"**Database not found**: `{db_path}`")
        run_btn = mo.ui.button(label="Generate Database", value=False)
        download_btn = None
    return (run_btn,)


@app.cell
def _(db_status, run_btn):
    if db_status == "not_exists" and run_btn is not None:
        run_pipeline = run_btn.value
    else:
        run_pipeline = False
    return (run_pipeline,)


@app.cell
def _(mo):
    mo.md("""
    ### Data Ingestion
    """)
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

    The pipeline creates all tables needed for analysis. If the database already existed, you can view sample data above and download it. If you generated a new database, all tables have been created and are ready for analysis.
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
