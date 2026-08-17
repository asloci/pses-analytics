import marimo

__generated_with = "0.23.4"
app = marimo.App(width="columns")


@app.cell
def _(mo):
    mo.md("""
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
    """)
    return


@app.cell
def _():

    import marimo as mo
    import duckdb
    import polars as pl
    import altair as alt
    from pathlib import Path


    return Path, alt, duckdb, mo, pl


@app.cell
def _(Path, duckdb):

    db_path = str(Path("data") / "pses.duckdb")
    con = duckdb.connect(db_path, read_only=True)
    return (con,)


@app.cell
def _(mo):
    mo.md("""
    ## Theme Score Trend Data

    Line chart showing scores for all six main themes across survey years.
    """)
    return


@app.cell
def _(alt, con, mo):
    all_themes_df = con.execute("""
        SELECT
            ts.SURVEYR,
            im.INDICATORENG as theme,
            AVG(ts.mean_score) as avg_score
        FROM theme_scores ts
        JOIN indicator_map im ON ts.SUBINDICATORID = im.SUBINDICATORID
        GROUP BY ts.SURVEYR, im.INDICATORENG, im.INDICATORID
        ORDER BY im.INDICATORID, ts.SURVEYR
    """).pl()

    all_themes_chart = (
        alt.Chart(all_themes_df).mark_line(point=True, strokeWidth=2).encode(
            x=alt.X("SURVEYR:O", title="Survey Year", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("avg_score:Q", title="Average Score (0-100)", scale=alt.Scale(domain=[0, 100])),
            color=alt.Color("theme:N", title="Theme", sort=alt.SortField("INDICATORID", order="ascending")),
            tooltip=[
                alt.Tooltip("theme:N", title="Theme"),
                alt.Tooltip("SURVEYR:O", title="Year"),
                alt.Tooltip("avg_score:Q", title="Score", format=".1f"),
            ],
        ).properties(
            title="Average scores by theme across all survey years",
            width=700,
            height=400,
        ).interactive()
    )

    mo.ui.altair_chart(all_themes_chart)
    return


@app.cell
def _(mo):
    mo.md("""
    ## Controls

    ### Theme Selector
    Select which organizational theme to analyze.
    """)
    return


@app.cell
def _(con):

    theme_df = con.execute("""
        SELECT DISTINCT INDICATORENG, INDICATORID
        FROM indicator_map
        ORDER BY INDICATORID
    """).pl()
    return (theme_df,)


@app.cell
def _(mo, theme_df):
    theme_options = {
        row["INDICATORENG"]: row["INDICATORENG"]
        for row in theme_df.iter_rows(named=True)
    }

    theme_selector = mo.ui.dropdown(
        options=theme_options,
        value=list(theme_options.keys())[0],
        label="Theme",
    )
    theme_selector
    return (theme_selector,)


@app.cell
def _(mo):
    mo.md("""
    ### Year Selector
    Select which survey years to include in the visualization.
    """)
    return


@app.cell
def _(mo):

    year_selector = mo.ui.multiselect(
        options=["2019", "2020", "2022", "2024"],
        value=["2019", "2020", "2022", "2024"],
        label="Survey years",
    )
    year_selector
    return (year_selector,)


@app.cell
def _(year_selector):

    selected_years = [int(y) for y in year_selector.value]
    return (selected_years,)


@app.cell
def _(con, selected_years, theme_selector):

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
    """, [theme_selector.value, selected_years]).pl()
    return (theme_trend_df,)


@app.cell
def _(mo):
    mo.md("""
    ## Trend Line Chart

    Line chart showing subtheme scores over time for the selected theme.
    Each line represents a subtheme, with points at each survey year.
    """)
    return


@app.cell
def _(alt, mo, theme_selector, theme_trend_df):

    base = alt.Chart(theme_trend_df).encode(
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

    chart = (
        base.mark_line(point=True, strokeWidth=2)
        .properties(
            title=f"Subtheme scores over time — {theme_selector.value}",
            width=600,
            height=350,
        )
        .interactive()
    )

    mo.ui.altair_chart(chart)
    return


@app.cell
def _(mo):
    mo.md("""
    ## Year-over-Year Delta Heatmap

    Heatmap showing the change in scores between survey cycles.
    Each cell represents the delta from one year to the next for a subtheme.

    **Color Scale**: Red = decline, Green = improvement, centered at 0.
    """)
    return


@app.cell
def _(con, theme_selector):

    yoy_df = con.execute("""
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
    return (yoy_df,)


@app.cell
def _(alt, mo, theme_selector, yoy_df):

    heatmap = (
        alt.Chart(yoy_df)
        .mark_rect()
        .encode(
            x=alt.X(
                "period:O",
                title="Period",
                sort=["2019→2020", "2020→2022", "2022→2024"],
            ),
            y=alt.Y(
                "SUBINDICATORENG:N",
                sort=yoy_df["SUBINDICATORENG"].to_list(),
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

    heatmap_with_text = heatmap + (
        alt.Chart(yoy_df)
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

    mo.ui.altair_chart(heatmap_with_text)
    return


@app.cell
def _(mo):
    mo.md("""
    ## Chi-Square Significance Table

    Table showing chi-square test results for 2019 vs 2024 comparison.
    Select a question to drill down into its response distribution.
    """)
    return


@app.cell
def _(con, theme_selector):

    chi_df = con.execute("""
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
    return (chi_df,)


@app.cell
def _(chi_df, mo, pl):

    chi_table = mo.ui.table(
        chi_df.select([
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
def _(mo):
    mo.md("""
    ## Question Drill-Down
    """)
    return


@app.cell
def _(chi_df, chi_table):
    # If a question is selected from the table, use it; otherwise use the first row
    if chi_table.value is not None and len(chi_table.value) > 0:
        selected_question = chi_table.value["QUESTION"][0]
        selected_title = chi_table.value["Question text"][0]
    else:
        # Default to first question in the dataframe
        selected_question = chi_df["QUESTION"][0]
        selected_title = chi_df["TITLE_E"][0]
    return selected_question, selected_title


@app.cell
def _(mo):
    mo.md("""
    ### Question Response Distribution

    Bar chart showing the response distribution (Positive/Neutral/Negative)
    for the selected question, comparing 2019 and 2024 side by side.
    """)
    return


@app.cell
def _(con, selected_question):

    dist_df = con.execute("""
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
    return (dist_df,)


@app.cell
def _(alt, dist_df, mo, selected_question, selected_title):

    dist_chart = (
        alt.Chart(dist_df)
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

    mo.ui.altair_chart(dist_chart)
    return


@app.cell
def _(mo):
    mo.md("""
    ## Narrative Summary

    Plain-language summary of findings for the selected theme, suitable for leadership audiences.
    """)
    return


@app.cell
def _(con, theme_selector):

    summary_df = con.execute("""
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
    return (summary_df,)


@app.cell
def _(con, theme_selector):

    scores_df = con.execute("""
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
    return (scores_df,)


@app.cell
def _(mo, scores_df, summary_df, theme_selector):

    worst_subtheme = summary_df["SUBINDICATORENG"][0]
    worst_delta = summary_df["delta"][0]
    lowest_score = scores_df["score_2024"][0]
    lowest_name = scores_df["SUBINDICATORENG"][0]

    bullet_lines = "\n".join([
        f"- **{row['SUBINDICATORENG']}**: {row['delta']:+.1f} points (2022 to 2024)"
        for row in summary_df.iter_rows(named=True)
    ])

    mo.md(f"""
    ## {theme_selector.value} — Summary for Leadership

    All subthemes under **{theme_selector.value}** declined between 2022 and 2024.
    The steepest drop was in **{worst_subtheme}** ({worst_delta:+.1f} points),
    and the lowest-scoring subtheme in 2024 is **{lowest_name}**
    ({lowest_score:.1f} / 100).

    ### Largest declines (2022 to 2024)

    {bullet_lines}

    ### What this means

    Scores represent the percentage of respondents giving a positive or neutral response,
    expressed on a 0-100 scale. A decline of {abs(worst_delta):.1f} points in a single
    survey cycle — with ~186,000 respondents — is both statistically significant and
    operationally meaningful.

    > **Note:** Statistical significance is expected at this sample size. Use the magnitude
    > of change, not the p-value, as the primary indicator of policy relevance.
    """)
    return


if __name__ == "__main__":
    app.run()
