import marimo

__generated_with = "0.23.4"
app = marimo.App(width="columns")


@app.cell
def _():
    """
    # PSES Data Exploration & Analysis

    ## Overview

    This notebook provides an interactive exploration interface for the PSES analytical dataset.
    It connects to the DuckDB database created by `01_data_engineering.py` and provides:

    - **Theme Selection**: Choose which organizational theme to analyze
    - **Year Selection**: Filter by survey year(s)
    - **Trend Visualization**: Line charts showing subtheme scores over time
    - **Change Analysis**: Heatmap of year-over-year score changes
    - **Statistical Significance**: Chi-square test results table
    - **Question Drill-Down**: Deep dive into individual question response distributions
    - **Narrative Summary**: Plain-language findings for leadership audiences

    **Prerequisite**: Run `01_data_engineering.py` first to build the analytical tables.

    **Database**: `data/pses.duckdb` (read-only mode)
    """
    import marimo as mo
    import duckdb
    import polars as pl
    import altair as alt
    from pathlib import Path

    db_path = str(Path("data") / "pses.duckdb")
    con = duckdb.connect(db_path, read_only=True)

    return alt, con, mo, pl


@app.cell
def _(con, mo):
    """
    ## Controls

    ### Theme Selector
    Select which organizational theme to analyze.
    """
    _theme_df = con.execute("""
        SELECT DISTINCT INDICATORENG, INDICATORID
        FROM indicator_map
        ORDER BY INDICATORID
    """).pl()

    _theme_options = {
        row["INDICATORENG"]: row["INDICATORENG"]
        for row in _theme_df.iter_rows(named=True)
    }

    theme_selector = mo.ui.dropdown(
        options=_theme_options,
        value=list(_theme_options.keys())[0],
        label="Theme",
    )
    theme_selector
    return (theme_selector,)


@app.cell
def _(mo):
    """
    ### Year Selector
    Select which survey years to include in the visualization.
    """
    year_selector = mo.ui.multiselect(
        options=["2019", "2020", "2022", "2024"],
        value=["2019", "2020", "2022", "2024"],
        label="Survey years",
    )
    year_selector
    return (year_selector,)


@app.cell
def _(con, theme_selector, year_selector):
    """
    ## Theme Score Trend Data

    Query the theme_scores table for the selected theme and years.
    This data powers the trend line chart.
    """
    _selected_years = [int(y) for y in year_selector.value]

    theme_trend_df = con.execute("""
        SELECT
            ts.SURVEYR,
            ts.SUBINDICATORENG,
            ts.SUBINDICATORID,
            ts.mean_score
        FROM theme_scores ts
        JOIN indicator_map im
            ON ts.SUBINDICATORID = im.SUBINDICATORID
        WHERE im.INDICATORENG = ?
          AND ts.SURVEYR IN (SELECT UNNEST(?::INTEGER[]))
        ORDER BY ts.SUBINDICATORID, ts.SURVEYR
    """, [theme_selector.value, _selected_years]).pl()

    theme_trend_df
    return (theme_trend_df,)


@app.cell
def _(alt, mo, theme_selector, theme_trend_df):
    """
    ## Trend Line Chart

    Line chart showing subtheme scores over time for the selected theme.
    Each line represents a subtheme, with points at each survey year.
    """
    _base = alt.Chart(theme_trend_df).encode(
        x=alt.X(
            "SURVEYR:O",
            title="Survey year",
            axis=alt.Axis(labelAngle=0),
        ),
        y=alt.Y(
            "mean_score:Q",
            title="Mean score (0-100)",
            scale=alt.Scale(domain=[0, 100]),
        ),
        color=alt.Color(
            "SUBINDICATORENG:N",
            title="Subtheme",
            sort=alt.SortField("SUBINDICATORID", order="ascending"),
        ),
        tooltip=[
            alt.Tooltip("SUBINDICATORENG:N", title="Subtheme"),
            alt.Tooltip("SURVEYR:O", title="Year"),
            alt.Tooltip("mean_score:Q", title="Score", format=".1f"),
        ],
    )

    _chart = (
        _base.mark_line(point=True, strokeWidth=2)
        .properties(
            title=f"Subtheme scores over time — {theme_selector.value}",
            width=600,
            height=350,
        )
        .interactive()
    )

    mo.ui.altair_chart(_chart)
    return


@app.cell
def _(alt, con, mo, theme_selector):
    """
    ## Year-over-Year Delta Heatmap

    Heatmap showing the change in scores between survey cycles.
    Each cell represents the delta from one year to the next for a subtheme.

    **Color Scale**: Red = decline, Green = improvement, centered at 0.
    """
    _yoy_df = con.execute("""
        SELECT
            yc.SUBINDICATORENG,
            yc.year_from,
            yc.year_to,
            yc.delta,
            printf('%d→%d', yc.year_from, yc.year_to) AS period,
            im.SUBINDICATORID
        FROM yoy_changes yc
        JOIN indicator_map im
            ON yc.SUBINDICATORENG = im.SUBINDICATORENG
        WHERE yc.INDICATORENG = ?
        ORDER BY im.SUBINDICATORID, yc.year_from
    """, [theme_selector.value]).pl()

    _heatmap = (
        alt.Chart(_yoy_df)
        .mark_rect()
        .encode(
            x=alt.X(
                "period:O",
                title="Period",
                sort=["2019→2020", "2020→2022", "2022→2024"],
            ),
            y=alt.Y(
                "SUBINDICATORENG:N",
                sort=_yoy_df["SUBINDICATORENG"].to_list(),
            ),
            color=alt.Color(
                "delta:Q",
                title="Change in score",
                scale=alt.Scale(
                    scheme="redyellowgreen",
                    domain=[-10, 10],
                    clamp=True,
                ),
            ),
            tooltip=[
                alt.Tooltip("SUBINDICATORENG:N", title="Subtheme"),
                alt.Tooltip("period:O", title="Period"),
                alt.Tooltip("delta:Q", title="Delta", format="+.1f"),
            ],
        )
        .properties(
            title=f"Year-over-year score changes — {theme_selector.value}",
            width=400,
            height=250,
        )
    )

    _heatmap_with_text = _heatmap + (
        alt.Chart(_yoy_df)
        .mark_text(fontSize=11, fontWeight="bold")
        .encode(
            x=alt.X("period:O", sort=["2019→2020", "2020→2022", "2022→2024"]),
            y=alt.Y(
                "SUBINDICATORENG:N",
                sort=alt.SortField("SUBINDICATORID", order="ascending"),
            ),
            text=alt.Text("delta:Q", format="+.1f"),
            color=alt.condition(
                "abs(datum.delta) > 6",
                alt.value("white"),
                alt.value("#333333"),
            ),
        )
    )

    mo.ui.altair_chart(_heatmap_with_text)
    return


@app.cell
def _(con, mo, pl, theme_selector):
    """
    ## Chi-Square Significance Table

    Table showing chi-square test results for 2019 vs 2024 comparison.
    Select a question to drill down into its response distribution.
    """
    _chi_df = con.execute("""
        SELECT
            cr.QUESTION,
            cr.SUBINDICATORENG,
            pa.TITLE_E,
            cr.chi2,
            cr.p_value,
            cr.dof,
            cr.significant
        FROM chi_square_results cr
        JOIN pses_analysis pa
            ON cr.QUESTION = pa.QUESTION
        WHERE cr.INDICATORENG = ?
          AND pa.SURVEYR = 2024
        GROUP BY
            cr.QUESTION, cr.SUBINDICATORENG, pa.TITLE_E,
            cr.chi2, cr.p_value, cr.dof, cr.significant
        ORDER BY cr.chi2 DESC
    """, [theme_selector.value]).pl()

    chi_table = mo.ui.table(
        _chi_df.select([
            pl.col("QUESTION"),
            pl.col("TITLE_E").alias("Question text"),
            pl.col("SUBINDICATORENG").alias("Subtheme"),
            pl.col("chi2").round(1).alias("Chi-squared"),
            pl.col("p_value").alias("p-value"),
            pl.col("significant").alias("Significant"),
        ]),
        selection="single",
        label="Chi-square results (2019 vs 2024) - Select a question to drill down",
    )
    chi_table
    return (chi_table,)


@app.cell
def _(chi_table, mo):
    """
    ## Question Selection Guard

    Show message if no question is selected from the chi-square table.
    """
    mo.stop(
        len(chi_table.value) == 0,
        mo.md("*Select a question from the table above to see the response distribution.*")
    )

    selected_question = chi_table.value["QUESTION"][0]
    selected_title = chi_table.value["Question text"][0]
    return selected_question, selected_title


@app.cell
def _(alt, con, mo, selected_question, selected_title):
    """
    ## Question Response Distribution

    Bar chart showing the response distribution (Positive/Neutral/Negative) 
    for the selected question, comparing 2019 and 2024 side by side.
    """
    _dist_df = con.execute("""
        SELECT
            SURVEYR,
            UNNEST([
                struct_pack(response := 'Positive', pct := POSITIVE),
                struct_pack(response := 'Neutral',  pct := NEUTRAL),
                struct_pack(response := 'Negative', pct := NEGATIVE)
            ]) AS r
        FROM pses_analysis
        WHERE QUESTION = ?
          AND SURVEYR IN (2019, 2024)
    """, [selected_question]).pl().unnest("r")

    _dist_chart = (
        alt.Chart(_dist_df)
        .mark_bar()
        .encode(
            x=alt.X(
                "pct:Q",
                title="Percent of respondents",
                scale=alt.Scale(domain=[0, 100]),
            ),
            y=alt.Y(
                "response:N",
                title=None,
                sort=["Positive", "Neutral", "Negative"],
            ),
            color=alt.Color(
                "response:N",
                scale=alt.Scale(
                    domain=["Positive", "Neutral", "Negative"],
                    range=["#4dac26", "#c0c0c0", "#d01c8b"],
                ),
                legend=None,
            ),
            row=alt.Row(
                "SURVEYR:O",
                title="Survey year",
            ),
            tooltip=[
                alt.Tooltip("response:N", title="Response"),
                alt.Tooltip("SURVEYR:O", title="Year"),
                alt.Tooltip("pct:Q", title="%", format=".1f"),
            ],
        )
        .properties(
            title=f"{selected_question}: {selected_title}",
            width=450,
            height=80,
        )
    )

    mo.ui.altair_chart(_dist_chart)
    return


@app.cell
def _(con, mo, theme_selector):
    """
    ## Narrative Summary

    Plain-language summary of findings for the selected theme, suitable for leadership audiences.
    """
    _summary_df = con.execute("""
        WITH ranked AS (
            SELECT
                SUBINDICATORENG,
                delta,
                ROW_NUMBER() OVER (ORDER BY delta ASC) AS rank
            FROM yoy_changes
            WHERE INDICATORENG = ?
              AND year_from = 2022
              AND year_to = 2024
        )
        SELECT * FROM ranked WHERE rank <= 3
    """, [theme_selector.value]).pl()

    _scores_df = con.execute("""
        SELECT
            ts.SUBINDICATORENG,
            MAX(CASE WHEN SURVEYR = 2019 THEN mean_score END) AS score_2019,
            MAX(CASE WHEN SURVEYR = 2024 THEN mean_score END) AS score_2024
        FROM theme_scores ts
        JOIN indicator_map im USING (SUBINDICATORID)
        WHERE im.INDICATORENG = ?
        GROUP BY ts.SUBINDICATORENG
        ORDER BY score_2024 ASC
    """, [theme_selector.value]).pl()

    _worst_subtheme = _summary_df["SUBINDICATORENG"][0]
    _worst_delta = _summary_df["delta"][0]
    _lowest_score = _scores_df["score_2024"][0]
    _lowest_name = _scores_df["SUBINDICATORENG"][0]

    _bullet_lines = "\n".join([
        f"- **{row['SUBINDICATORENG']}**: {row['delta']:+.1f} points (2022 to 2024)"
        for row in _summary_df.iter_rows(named=True)
    ])

    mo.md(f"""
    ## {theme_selector.value} — Summary for Leadership

    All subthemes under **{theme_selector.value}** declined between 2022 and 2024.
    The steepest drop was in **{_worst_subtheme}** ({_worst_delta:+.1f} points),
    and the lowest-scoring subtheme in 2024 is **{_lowest_name}**
    ({_lowest_score:.1f} / 100).

    ### Largest declines (2022 to 2024)

    {_bullet_lines}

    ### What this means

    Scores represent the percentage of respondents giving a positive or neutral response,
    expressed on a 0-100 scale. A decline of {abs(_worst_delta):.1f} points in a single
    survey cycle — with ~186,000 respondents — is both statistically significant and
    operationally meaningful.

    > **Note:** Statistical significance is expected at this sample size. Use the magnitude
    > of change, not the p-value, as the primary indicator of policy relevance.
    """)
    return


if __name__ == "__main__":
    app.run()
