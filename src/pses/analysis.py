"""
analysis.py
~~~~~~~~~~~
Computes three analytical tables and writes them to data/pses.duckdb:

  theme_scores          – mean SCORE100 per subtheme per year
  yoy_changes           – year-over-year delta in mean_score per subtheme
  question_correlations – Pearson r between every stable question pair
  chi_square_results    – chi-square test on answer1–5 distribution 2019 vs 2024

Depends on: pses_analysis (run transform.py first)

Run:
    python src/pses/analysis.py
"""

from __future__ import annotations

import itertools
from collections import defaultdict
from pathlib import Path

import duckdb
from rich.console import Console
from rich.table import Table
from scipy.stats import chi2_contingency, pearsonr

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parents[2] / "data" / "pses.duckdb"

# Q73a–Q73w are 2024-only stress sub-questions; exclude from stable analysis
Q73_FILTER = "QUESTION NOT LIKE 'Q73%'"

SAMPLE_INDICATORS = ("Leadership", "Workplace well-being")

console = Console()

# ---------------------------------------------------------------------------
# SQL — Table 1: theme_scores
# ---------------------------------------------------------------------------

_THEME_SCORES_SQL = f"""
CREATE OR REPLACE TABLE theme_scores AS
SELECT
    SURVEYR,
    INDICATORID,
    INDICATORENG,
    SUBINDICATORID,
    SUBINDICATORENG,
    AVG(SCORE100) AS mean_score
FROM pses_analysis
WHERE is_stable = true
  AND is_scored = true
  AND {Q73_FILTER}
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
"""

# ---------------------------------------------------------------------------
# SQL — Table 2: yoy_changes
# ---------------------------------------------------------------------------

_YOY_CHANGES_SQL = """
CREATE OR REPLACE TABLE yoy_changes AS
SELECT
    a.SUBINDICATORENG,
    a.INDICATORENG,
    a.SURVEYR          AS year_from,
    b.SURVEYR          AS year_to,
    a.mean_score       AS score_from,
    b.mean_score       AS score_to,
    b.mean_score - a.mean_score AS delta
FROM theme_scores a
JOIN theme_scores b
  ON  a.SUBINDICATORID = b.SUBINDICATORID
  AND (
        (a.SURVEYR = 2019 AND b.SURVEYR = 2020)
     OR (a.SURVEYR = 2020 AND b.SURVEYR = 2022)
     OR (a.SURVEYR = 2022 AND b.SURVEYR = 2024)
      )
ORDER BY
    a.SUBINDICATORENG,
    a.SURVEYR
"""

# ---------------------------------------------------------------------------
# Table 3: question_correlations  (Python-side pivot + scipy)
# ---------------------------------------------------------------------------

def _build_question_correlations(con: duckdb.DuckDBPyConnection) -> None:
    """Pivot pses_analysis wide, compute all pairwise Pearson r, write table."""

    # One row per (SURVEYR, QUESTION) — spine is already unique on this key
    long_rows: list[tuple] = con.execute(
        f"""
        SELECT SURVEYR, QUESTION, SCORE100
        FROM   pses_analysis
        WHERE  is_stable = true
          AND  is_scored = true
          AND  {Q73_FILTER}
        ORDER  BY QUESTION, SURVEYR
        """
    ).fetchall()

    # Build pivot: question → {year: score}
    pivot: dict[str, dict[int, float]] = defaultdict(dict)
    for surveyr, question, score in long_rows:
        pivot[question][surveyr] = float(score)

    years = [2019, 2020, 2022, 2024]

    # Keep only questions present in all 4 years
    questions = sorted(
        q for q, yr_map in pivot.items()
        if all(y in yr_map for y in years)
    )

    console.log(
        f"  Pivoting [cyan]{len(questions)}[/cyan] questions × "
        f"[cyan]{len(years)}[/cyan] years …"
    )

    # Build vectors: question → list[score] aligned to `years`
    vectors: dict[str, list[float]] = {
        q: [pivot[q][y] for y in years]
        for q in questions
    }

    # Compute all pairs
    corr_rows: list[tuple[str, str, float, float]] = []
    for q_a, q_b in itertools.combinations(questions, 2):
        v_a = vectors[q_a]
        v_b = vectors[q_b]
        # pearsonr needs at least 2 non-NaN pairs
        try:
            r, p = pearsonr(v_a, v_b)
            corr_rows.append((q_a, q_b, float(r), float(p)))
        except Exception:
            pass  # skip degenerate pairs

    console.log(
        f"  Computed [cyan]{len(corr_rows):,}[/cyan] correlation pairs."
    )

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

# ---------------------------------------------------------------------------
# Rich output helpers
# ---------------------------------------------------------------------------

def _print_theme_scores(con: duckdb.DuckDBPyConnection) -> None:
    indicators_sql = " OR ".join(
        f"INDICATORENG = '{ind}'" for ind in SAMPLE_INDICATORS
    )
    rows = con.execute(
        f"""
        SELECT SUBINDICATORENG, SURVEYR, ROUND(mean_score, 1) AS mean_score
        FROM   theme_scores
        WHERE  {indicators_sql}
        ORDER  BY SUBINDICATORENG, SURVEYR
        """
    ).fetchall()

    console.rule("[bold cyan]theme_scores — Leadership & Workplace well-being")
    tbl = Table(header_style="bold magenta", show_lines=False)
    tbl.add_column("Sub-indicator", overflow="fold")
    tbl.add_column("Year",       style="dim",        justify="right")
    tbl.add_column("mean_score",                     justify="right")
    for sub, year, score in rows:
        tbl.add_row(sub, str(year), str(score))
    console.print(tbl)


def _print_yoy_changes(con: duckdb.DuckDBPyConnection) -> None:
    indicators_sql = " OR ".join(
        f"INDICATORENG = '{ind}'" for ind in SAMPLE_INDICATORS
    )
    rows = con.execute(
        f"""
        SELECT SUBINDICATORENG, year_from, year_to,
               ROUND(score_from, 1), ROUND(score_to, 1), ROUND(delta, 1)
        FROM   yoy_changes
        WHERE  {indicators_sql}
        ORDER  BY SUBINDICATORENG, year_from
        """
    ).fetchall()

    console.rule("[bold cyan]yoy_changes — Leadership & Workplace well-being")
    tbl = Table(header_style="bold magenta", show_lines=False)
    tbl.add_column("Sub-indicator", overflow="fold")
    tbl.add_column("From", justify="right", style="dim")
    tbl.add_column("To",   justify="right", style="dim")
    tbl.add_column("score_from", justify="right")
    tbl.add_column("score_to",   justify="right")
    tbl.add_column("delta",      justify="right")
    for sub, yf, yt, sf, st, d in rows:
        delta_str = (
            f"[green]+{d}[/green]" if d > 0
            else f"[red]{d}[/red]" if d < 0
            else str(d)
        )
        tbl.add_row(sub, str(yf), str(yt), str(sf), str(st), delta_str)
    console.print(tbl)


def _print_top_correlations(con: duckdb.DuckDBPyConnection) -> None:
    rows = con.execute(
        """
        SELECT question_a, question_b,
               ROUND(pearson_r, 4) AS r,
               ROUND(p_value,   6) AS p
        FROM   question_correlations
        WHERE  p_value < 0.05
        ORDER  BY ABS(pearson_r) DESC
        LIMIT  10
        """
    ).fetchall()

    console.rule("[bold cyan]question_correlations — Top 10 (p < 0.05)")
    tbl = Table(header_style="bold magenta", show_lines=False)
    tbl.add_column("Question A", justify="center")
    tbl.add_column("Question B", justify="center")
    tbl.add_column("Pearson r",  justify="right")
    tbl.add_column("p-value",    justify="right")
    for q_a, q_b, r, p in rows:
        r_str = (
            f"[green]{r}[/green]" if r > 0
            else f"[red]{r}[/red]"
        )
        tbl.add_row(q_a, q_b, r_str, str(p))
    console.print(tbl)

# ---------------------------------------------------------------------------
# Table 4: chi_square_results  (Python-side, scipy.stats.chi2_contingency)
# ---------------------------------------------------------------------------

def _build_chi_square_results(con: duckdb.DuckDBPyConnection) -> None:
    """Compare answer1–5 distribution between 2019 and 2024 per question."""

    rows = con.execute(
        """
        SELECT QUESTION, SURVEYR,
               answer1, answer2, answer3, answer4, answer5,
               ANSCOUNT
        FROM   pses_analysis
        WHERE  is_stable = true
          AND  is_scored = true
          AND  QUESTION NOT LIKE 'Q73%'
          AND  SURVEYR IN (2019, 2024)
        ORDER  BY QUESTION, SURVEYR
        """
    ).fetchall()

    # Also fetch indicator labels (one row per question is enough)
    labels: dict[str, tuple[str, str]] = {
        q: (ie, se)
        for q, ie, se in con.execute(
            """
            SELECT DISTINCT QUESTION, INDICATORENG, SUBINDICATORENG
            FROM   pses_analysis
            WHERE  is_stable = true AND is_scored = true
              AND  QUESTION NOT LIKE 'Q73%'
            """
        ).fetchall()
    }

    # Collect per-question rows for each year: store (pcts, anscount)
    data: dict[str, dict] = {}
    for q, year, a1, a2, a3, a4, a5, anscount in rows:
        if q not in data:
            data[q] = {"years": {}}
        data[q]["years"][year] = ([a1, a2, a3, a4, a5], anscount)

    chi_rows: list[tuple] = []
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
        # Reconstruct estimated raw counts from percentages × ANSCOUNT
        counts_2019 = [round((pct / 100) * anscount_2019) for pct in pcts_2019]
        counts_2024 = [round((pct / 100) * anscount_2024) for pct in pcts_2024]
        # Skip if either row sums to zero (degenerate table)
        if sum(counts_2019) == 0 or sum(counts_2024) == 0:
            continue
        ind_eng, sub_eng = labels.get(q, ("", ""))
        try:
            chi2, p, dof, _ = chi2_contingency([counts_2019, counts_2024])
            chi_rows.append((
                q,
                ind_eng,
                sub_eng,
                float(chi2),
                float(p),
                int(dof),
                bool(p < 0.05),
            ))
        except Exception:
            pass  # skip degenerate tables

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
    con.executemany(
        "INSERT INTO chi_square_results VALUES (?, ?, ?, ?, ?, ?, ?)",
        chi_rows,
    )
    console.log(f"  Tested [cyan]{len(chi_rows)}[/cyan] questions.")


# ---------------------------------------------------------------------------
# Rich output helpers (chi-square)
# ---------------------------------------------------------------------------

def _print_chi_square(con: duckdb.DuckDBPyConnection) -> None:
    # Top 15 most significant
    rows = con.execute(
        """
        SELECT QUESTION, INDICATORENG, SUBINDICATORENG,
               ROUND(chi2,   2) AS chi2,
               ROUND(p_value, 6) AS p,
               dof,
               significant
        FROM   chi_square_results
        ORDER  BY p_value ASC
        LIMIT  15
        """
    ).fetchall()

    console.rule("[bold cyan]chi_square_results — Top 15 most significant (2019 vs 2024)")
    tbl = Table(header_style="bold magenta", show_lines=False)
    tbl.add_column("Question",       justify="center")
    tbl.add_column("Indicator",      overflow="fold")
    tbl.add_column("Sub-indicator",  overflow="fold")
    tbl.add_column("χ²",             justify="right")
    tbl.add_column("p-value",        justify="right")
    tbl.add_column("dof",            justify="right", style="dim")
    tbl.add_column("sig?",           justify="center")
    for q, ind, sub, chi2, p, dof, sig in rows:
        sig_str = "[green]✓[/green]" if sig else "[dim]✗[/dim]"
        tbl.add_row(q, ind, sub, str(chi2), str(p), str(dof), sig_str)
    console.print(tbl)

    # Significant vs non-significant counts
    n_sig, n_nonsig = con.execute(
        """
        SELECT
            COUNT(*) FILTER (WHERE significant     = true),
            COUNT(*) FILTER (WHERE significant     = false)
        FROM chi_square_results
        """
    ).fetchone()
    console.print(
        f"  [green]Significant (p<0.05):[/green] {n_sig}   "
        f"[dim]Not significant:[/dim] {n_nonsig}"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    con = duckdb.connect(str(DB_PATH))

    # ── Table 1: theme_scores ────────────────────────────────────────────────
    console.log("Building [bold]theme_scores[/bold] …")
    con.execute(_THEME_SCORES_SQL)
    n_theme: int = con.execute("SELECT COUNT(*) FROM theme_scores").fetchone()[0]
    console.log(f"  → {n_theme:,} rows")

    # ── Table 2: yoy_changes ─────────────────────────────────────────────────
    console.log("Building [bold]yoy_changes[/bold] …")
    con.execute(_YOY_CHANGES_SQL)
    n_yoy: int = con.execute("SELECT COUNT(*) FROM yoy_changes").fetchone()[0]
    console.log(f"  → {n_yoy:,} rows")

    # ── Table 3: question_correlations ───────────────────────────────────────
    console.log("Building [bold]question_correlations[/bold] …")
    _build_question_correlations(con)
    n_corr: int = con.execute(
        "SELECT COUNT(*) FROM question_correlations"
    ).fetchone()[0]
    console.log(f"  → {n_corr:,} rows")

    # ── Table 4: chi_square_results ──────────────────────────────────────────
    console.log("Building [bold]chi_square_results[/bold] …")
    _build_chi_square_results(con)
    n_chi: int = con.execute(
        "SELECT COUNT(*) FROM chi_square_results"
    ).fetchone()[0]
    console.log(f"  → {n_chi:,} rows")

    # ── Summary ──────────────────────────────────────────────────────────────
    console.print()
    print(f"theme_scores:          {n_theme:,} rows")
    print(f"yoy_changes:           {n_yoy:,} rows")
    print(f"question_correlations: {n_corr:,} rows")
    print(f"chi_square_results:    {n_chi:,} rows")
    console.print()

    # ── Rich output ──────────────────────────────────────────────────────────
    _print_theme_scores(con)
    _print_yoy_changes(con)
    _print_top_correlations(con)
    _print_chi_square(con)

    con.close()


if __name__ == "__main__":
    main()
