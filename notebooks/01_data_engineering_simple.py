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
    # End-to-End Analytics 🌊🍃 Notebook for the Government of Canada Public Service Employee Survey (PSES)

    ## Summary

    This notebook ingested and transformed Public Service Employee Survey (PSES) survey data into an analytical database that was used for longitudinal analysis across themes and sub-themes.

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
    return (rundb_button,)


@app.cell
def _(mo):
    mo.Html(
        """
        <div style="background-color: rgba(255, 204, 0, 0.2); padding: 20px; border-left: 4px solid #ffcc00; border-radius: 4px;">
            &#9888;&#65039; <strong>Attention:</strong> The section below does not describe or analyze the survey results. It shows a sample of, and related statistics for, the resulting analytical database.
        </div>
        """
    )
    return


@app.cell
def _():
    import duckdb
    import os
    from pathlib import Path

    Path("data").mkdir(parents=True, exist_ok=True)
    db_path = str(Path("data") / "pses.duckdb")
    con = duckdb.connect(db_path)
    no_db_msg = (
        "Database not built yet. Click **Generate the PSES Analytical Database** "
        "above to download the PSES data and create all analytical tables."
    )
    return Path, con, db_path, duckdb, no_db_msg


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
def _(no_db_msg, table_stats, total_elapsed):
    total_ms = total_elapsed * 1000

    total_rows = sum(stat["Number_of_rows"] for stat in table_stats)
    num_tables = len(table_stats)
    total_ms = total_elapsed * 1000

    if num_tables == 0:
        summary = no_db_msg
    else:
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
    ## Pipeline Results\n\n{summary}
    """)
    return


@app.cell
def _(mo, sorted_stats):
    mo.ui.table(data=sorted_stats, label='Query Statistics:') if sorted_stats else None
    return


@app.cell
def _(Path, mo):
    mo.md(f"""
    Whole-of-government table sample from the database retrieved using the following SQL statement:
    ```sql
    {Path("sql/sample_pses_wog.sql").read_text()}
    ```
    """)
    return


@app.cell(hide_code=True)
def _(Path, con, mo, no_db_msg):
    _tables = [r[0] for r in con.execute("SHOW TABLES").fetchall()]
    (
        mo.sql(
            Path("sql/sample_pses_wog.sql").read_text(),
            engine=con,
        )
        if "pses_wog" in _tables
        else mo.md(no_db_msg)
    )
    return


@app.cell
def _(Path, db_path, duckdb, no_db_msg, rundb_button):
    CSV_URL = "https://www.canada.ca/content/dam/tbs-sct/documents/datasets/ses-2025/main-principal.csv"
    RAW_TABLE = "raw_pses"
    if rundb_button.value:
        pipe_con_1 = duckdb.connect(db_path)
        pipe_con_1.execute(Path("sql/01_raw_pses.sql").read_text())
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
            msg_1 = no_db_msg
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
def _(fetch_with_bom_strip, mo, rundb_button):
    csv_path_1 = None
    _msg = None
    if rundb_button.value:
        SUBSET1_URL = "https://www.canada.ca/content/dam/tbs-sct/documents/datasets/ses-2025/subset-1-sous-ensemble-1.csv"
        csv_path_1 = fetch_with_bom_strip(SUBSET1_URL)
        _msg = mo.md(f"**Fetched theme CSV**: {SUBSET1_URL}")
    _msg
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
    rundb_button,
):
    _msg = None
    if rundb_button.value:
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
        _msg = mo.md(f"**pses_wog created**: {wog_total:,} rows")
    _msg
    return


@app.cell
def _(Path, csv_path_1, db_path, duckdb, mo, rundb_button):
    _msg = None
    if rundb_button.value and csv_path_1:
        pipe_con_3 = duckdb.connect(db_path)
        pipe_con_3.execute(Path("sql/02_theme_map.sql").read_text(), [csv_path_1])
        n_theme = pipe_con_3.execute("SELECT COUNT(*) FROM theme_map").fetchone()[0]
        pipe_con_3.execute(Path("sql/03_indicator_map.sql").read_text(), [csv_path_1])
        n_indicator = pipe_con_3.execute("SELECT COUNT(*) FROM indicator_map").fetchone()[0]
        import os as _os
        _os.unlink(csv_path_1)
        pipe_con_3.close()
        _msg = mo.md(f"**theme_map created**: {n_theme} rows  \n**indicator_map created**: {n_indicator} rows")
    _msg
    return


@app.cell
def _(Path, db_path, duckdb, mo, rundb_button):
    _msg = None
    if rundb_button.value:
        pipe_con_4 = duckdb.connect(db_path)
        pipe_con_4.execute(Path("sql/05_pses_analysis.sql").read_text())
        n_analysis = pipe_con_4.execute("SELECT COUNT(*) FROM pses_analysis").fetchone()[0]
        pipe_con_4.close()
        _msg = mo.md(f"**pses_analysis created**: {n_analysis:,} rows")
    _msg
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
def _(INT_COLS, con, make_double_expr, make_int_expr, mo, no_db_msg, rundb_button):
    _msg = None
    if rundb_button.value:
        int_exprs_sliced = ", ".join(make_int_expr(c) for c in INT_COLS)
        score5_expr_sliced = make_double_expr("SCORE5")

        con.execute(f"""
            CREATE OR REPLACE TABLE pses_sliced AS
            SELECT
                CAST(SURVEYR AS INTEGER) AS SURVEYR,
                QUESTION,
                BYCOND,
                DEMCODE,
                {int_exprs_sliced},
                {score5_expr_sliced}
            FROM raw_pses
            WHERE BYCOND IS NOT NULL
              AND LEVEL1ID = 0
        """)

        sliced_total = con.execute("SELECT COUNT(*) FROM pses_sliced").fetchone()[0]
        _msg = mo.md(f"**✓ pses_sliced created**: {sliced_total:,} rows")
    else:
        # Use existing table if available
        try:
            sliced_total = con.execute("SELECT COUNT(*) FROM pses_sliced").fetchone()[0]
            _msg = mo.md(f"**Using existing pses_sliced**: {sliced_total:,} rows")
        except:
            _msg = mo.md(no_db_msg)
    _msg
    return


@app.cell
def _(FSQ, con, mo, no_db_msg, rundb_button):
    _msg = None
    if rundb_button.value:
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
        _msg = mo.md(f"**✓ theme_scores created**: {n_theme_scores} rows")
    else:
        # Use existing table if available
        try:
            n_theme_scores = con.execute("SELECT COUNT(*) FROM theme_scores").fetchone()[0]
            _msg = mo.md(f"**Using existing theme_scores**: {n_theme_scores} rows")
        except:
            _msg = mo.md(no_db_msg)
    _msg
    return


@app.cell
def _(Path, con, mo, no_db_msg, rundb_button):
    _msg = None
    if rundb_button.value:
        con.execute(Path("sql/08_yoy_changes.sql").read_text())

        n_yoy = con.execute("SELECT COUNT(*) FROM yoy_changes").fetchone()[0]
        _msg = mo.md(f"**✓ yoy_changes created**: {n_yoy} rows")
    else:
        # Use existing table if available
        try:
            n_yoy = con.execute("SELECT COUNT(*) FROM yoy_changes").fetchone()[0]
            _msg = mo.md(f"**Using existing yoy_changes**: {n_yoy} rows")
        except:
            _msg = mo.md(no_db_msg)
    _msg
    return


@app.cell
def _(FSQ, con, mo, no_db_msg, rundb_button):
    _msg = None
    if rundb_button.value:
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
        _msg = mo.md(f"**✓ question_correlations created**: {n_corr:,} rows")
    else:
        # Use existing table if available
        try:
            n_corr = con.execute("SELECT COUNT(*) FROM question_correlations").fetchone()[0]
            _msg = mo.md(f"**Using existing question_correlations**: {n_corr:,} rows")
        except:
            _msg = mo.md(no_db_msg)
    _msg
    return


@app.cell
def _(FSQ, con, mo, no_db_msg, rundb_button):
    _msg = None
    if rundb_button.value:
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

        n_chi = len(chi_rows)
        if n_chi == 0:
            _msg = mo.md("**Note**: No questions met the criteria for chi-square testing. chi_square_results remain empty.")
        else:
            _msg = mo.md(f"**✓ chi_square_results created**: {n_chi} rows")
    else:
        # Use existing table if available
        try:
            n_chi = con.execute("SELECT COUNT(*) FROM chi_square_results").fetchone()[0]
            _msg = mo.md(f"**Using existing chi_square_results**: {n_chi} rows")
        except:
            _msg = mo.md(no_db_msg)
    _msg
    return


@app.cell
def _(mo):
    mo.md("""
    ## Pipeline Explanation

    This section documents the SQL methodology used to build the analytical tables.
    Python and SQL are used to ingest and transform the survey data into an analytical database.
    See the [DuckDB SQL documentation](https://duckdb.org/docs/sql/) for function reference,
    including `read_csv_auto()` and `?` parameter binding used below.
    """)
    return


@app.cell(hide_code=True)
def _(Path, mo):
    mo.md(f"""
    ### Ingestion: Raw Data

    Loads the main PSES dataset from CSV into DuckDB.

    ```sql
    {Path("sql/01_raw_pses.sql").read_text()}
    ```
    """)
    return


@app.cell(hide_code=True)
def _(Path, mo):
    mo.md(f"""
    ### Ingestion: Theme Taxonomy

    Loads the theme/indicator taxonomy from Subset 1 CSV.

    ```sql
    {Path("sql/02_theme_map.sql").read_text()}

    {Path("sql/03_indicator_map.sql").read_text()}
    ```
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ### Transformation: Whole-of-Government Spine (Legacyu)

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
    ### Transformation: Whole-of-Government Spine (Modern Alternatives)

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
def _(Path, mo):
    mo.md(f"""
    ### Transformation: Theme Lookup Table

    ```sql
    {Path("sql/02_theme_map.sql").read_text()}
    ```
    """)
    return


@app.cell(hide_code=True)
def _(Path, mo):
    mo.md(f"""
    ### Transformation: Indicator Lookup Table

    ```sql
    {Path("sql/03_indicator_map.sql").read_text()}
    ```
    """)
    return


@app.cell(hide_code=True)
def _(Path, mo):
    mo.md(f"""
    ### Transformation: Analytical Table

    ```sql
    {Path("sql/05_pses_analysis.sql").read_text()}
    ```
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Transformation: Demographic/Org Slices

    Creates a table with demographic and organizational breakdowns (BYCOND IS NOT NULL).

    ```sql
    CREATE OR REPLACE TABLE pses_sliced AS
    SELECT
        CAST(SURVEYR AS INTEGER) AS SURVEYR,
        QUESTION,
        BYCOND,
        DEMCODE,
        NULLIF(CAST(SCORE100 AS INTEGER), 9999) AS SCORE100,
        NULLIF(CAST(ANSCOUNT AS INTEGER), 9999) AS ANSCOUNT,
        NULLIF(CAST(POSITIVE AS INTEGER), 9999) AS POSITIVE,
        NULLIF(CAST(NEUTRAL AS INTEGER), 9999) AS NEUTRAL,
        NULLIF(CAST(NEGATIVE AS INTEGER), 9999) AS NEGATIVE,
        NULLIF(CAST(AGREE AS INTEGER), 9999) AS AGREE,
        NULLIF(CAST(answer1 AS INTEGER), 9999) AS answer1,
        NULLIF(CAST(answer2 AS INTEGER), 9999) AS answer2,
        NULLIF(CAST(answer3 AS INTEGER), 9999) AS answer3,
        NULLIF(CAST(answer4 AS INTEGER), 9999) AS answer4,
        NULLIF(CAST(answer5 AS INTEGER), 9999) AS answer5,
        NULLIF(CAST(answer6 AS INTEGER), 9999) AS answer6,
        NULLIF(CAST(answer7 AS INTEGER), 9999) AS answer7,
        NULLIF(CAST(SCORE5 AS DOUBLE), 9999.0) AS SCORE5
    FROM raw_pses
    WHERE BYCOND IS NOT NULL
      AND LEVEL1ID = 0
    ```
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Statistical Analysis: Theme Scores

    Computes mean SCORE100 per subtheme per year for longitudinal analysis.

    ```sql
    CREATE OR REPLACE TABLE theme_scores AS
    SELECT
        SURVEYR,
        INDICATORID,
        INDICATORENG,
        SUBINDICATORID,
        SUBINDICATORENG,
        AVG(SCORE100) AS mean_score
    FROM pses_analysis
    WHERE QUESTION IN (
        SELECT QUESTION
        FROM pses_analysis
        WHERE is_stable = true
        GROUP BY QUESTION
        HAVING COUNT(CASE WHEN SCORE100 IS NOT NULL THEN 1 END) = 4
    )
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
    ```
    """)
    return


@app.cell(hide_code=True)
def _(Path, mo):
    mo.md(f"""
    ### Statistical Analysis: Year-over-Year Changes

    Computes year-over-year deltas in mean_score per subtheme.

    ```sql
    {Path("sql/08_yoy_changes.sql").read_text()}
    ```
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Statistical Analysis: Question Correlations

    **FLAG: Mixed Python/SQL** - This table uses Python (scipy.stats.pearsonr) to compute Pearson correlation coefficients between question pairs, then stores results in a SQL table.

    The SQL extracts data from pses_analysis:
    ```sql
    SELECT SURVEYR, QUESTION, SCORE100
    FROM pses_analysis
    WHERE QUESTION IN (
        SELECT QUESTION
        FROM pses_analysis
        WHERE is_stable = true
        GROUP BY QUESTION
        HAVING COUNT(CASE WHEN SCORE100 IS NOT NULL THEN 1 END) = 4
    )
      AND QUESTION NOT LIKE 'Q73%'
    ORDER BY QUESTION, SURVEYR
    ```

    Python then:
    1. Builds a pivot table of scores by question and year
    2. Computes Pearson r for all question pairs using scipy.stats.pearsonr
    3. Creates the table with schema: (question_a, question_b, pearson_r, p_value)

    Final table:
    ```sql
    CREATE OR REPLACE TABLE question_correlations (
        question_a  VARCHAR,
        question_b  VARCHAR,
        pearson_r   DOUBLE,
        p_value     DOUBLE
    )
    ```
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Statistical Analysis: Chi-Square Results

    **FLAG: Mixed Python/SQL** - This table uses Python (scipy.stats.chi2_contingency) to perform chi-square tests, then stores results in a SQL table.

    The SQL extracts answer distribution data:
    ```sql
    SELECT QUESTION, SURVEYR,
           answer1, answer2, answer3, answer4, answer5,
           ANSCOUNT
    FROM pses_analysis
    WHERE QUESTION IN (
        SELECT QUESTION
        FROM pses_analysis
        WHERE is_stable = true
        GROUP BY QUESTION
        HAVING COUNT(CASE WHEN SCORE100 IS NOT NULL THEN 1 END) = 4
    )
      AND QUESTION NOT LIKE 'Q73%'
      AND SURVEYR IN (2019, 2024)
    ORDER BY QUESTION, SURVEYR
    ```

    Python then:
    1. Fetches indicator labels (INDICATORENG, SUBINDICATORENG)
    2. Reconstructs raw counts from percentages x ANSCOUNT
    3. Performs chi-square test between 2019 and 2024 distributions
    4. Creates the table with schema: (QUESTION, INDICATORENG, SUBINDICATORENG, chi2, p_value, dof, significant)

    Final table:
    ```sql
    CREATE OR REPLACE TABLE chi_square_results (
        QUESTION        VARCHAR,
        INDICATORENG    VARCHAR,
        SUBINDICATORENG VARCHAR,
        chi2            DOUBLE,
        p_value         DOUBLE,
        dof             INTEGER,
        significant     BOOLEAN
    )
    ```
    """)
    return


@app.cell
def _(db_path, mo, rundb_button):
    import duckdb as _dd
    summary_con = _dd.connect(db_path)
    tables = ["raw_pses", "theme_map", "indicator_map", "pses_wog", "pses_analysis"]
    d = {"raw_pses": "Full ingested dataset", "theme_map": "Question-theme lookup",
         "indicator_map": "Theme reference", "pses_wog": "WOG spine",
         "pses_analysis": "Primary analytical table"}
    _lines = [
        "**Table Summary:**",
        "| Table | Rows | Description |",
        "|-------|------|-------------|",
    ]
    for t in tables:
        try:
            c = summary_con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            _lines.append(f"| `{t}` | {c:,} | {d.get(t, t)} |")
        except Exception:
            _lines.append(f"| `{t}` | N/A | Not yet created |")
    summary_con.close()
    if rundb_button.value:
        _lines.append("\n**Pipeline complete!** All tables created successfully.")
    mo.md("\n".join(_lines))
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Survey Results Analysis
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Annex

    The BOM-prefix stripper helper function is used to deal with Excel-like artefacts.

    ```python
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
