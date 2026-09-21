# PSES Analytics

A reproducible data-engineering and analysis workbench for the **Public Service Employee Survey (PSES)** — the Government of Canada's federal public-service employee survey. The pipeline ingests the published PSES results, maps every question onto a theme/sub-theme taxonomy, and builds a set of analytical tables in DuckDB for longitudinal analysis.

> **Status:** work in progress. The single notebook is the starting point for ongoing feature work; the table-building pipeline is functional and reproducible, with a Survey Results Analysis section for visualization.

![PSES Analytics notebook overview](assets/pses-overview.png)

## What this 12-million-response dataset can answer

The raw PSES release contains **12.2 million response records** — one row per survey question per demographic or organizational slice — covering roughly **287,000 federal public-service respondents** across the **2019, 2020, 2022, and 2024** survey years, organized into **6 themes** and **23 sub-themes**. From this, the pipeline lets you answer questions such as: how positive-response scores on any theme or sub-theme have moved year over year for the whole of government; which of the 59 longitudinal questions show statistically significant change between 2019 and 2024 (chi-square); how strongly any two questions move together (Pearson correlation); and how scores break down by demographic and organizational slice. In short, it turns the published cross-tabulated CSV into a queryable longitudinal database for tracking the health of the federal workforce over time.

## Tech stack

- **DuckDB** — analytical query engine; all tables live in a single `data/pses.duckdb` file
- **Polars** — DataFrame operations
- **marimo** — interactive notebooks (the pipeline and analysis UI is a marimo app)
- **Plotly** — visualization (Survey Results Analysis section)

## Project structure

```
pses-analytics/
├── notebooks/
│   └── pses_analytics.py                 # Canonical pipeline: ingestion → analytical tables → visuals
├── assets/
│   └── pses-overview.png                # README hero screenshot (rendered from the notebook)
├── data/                                # Generated DuckDB database (gitignored)
│   └── pses.duckdb
├── sql/                                # SQL templates (single source of truth for exec + display)
│   ├── 01_raw_pses.sql … 10_chi_fetch.sql
│   └── sample_pses_wog.sql
├── pyproject.toml                       # Dependencies (uv-managed)
├── uv.lock
└── README.md
```

> Older/duplicate notebooks and backups are kept locally under `archive/` (gitignored) and can be deleted once no longer needed.

## Quick start

Prerequisites: Python 3.13+ and [uv](https://docs.astral.sh/uv/).

### 1. Install dependencies

```bash
cd pses-analytics
uv sync
```

### 2. Build the analytical database

```bash
uv run marimo edit notebooks/pses_analytics.py
```

Run this command **from the repository root** so the notebook resolves `data/pses.duckdb` correctly. In the notebook, click the **"Generate the PSES Analytical Database"** button to:

- download the raw PSES CSV from Canada.ca,
- load the theme/indicator taxonomy from the Subset 1 CSV,
- create all analytical tables in `data/pses.duckdb`.

The first run downloads a ~12M-row CSV and builds the database from scratch (a few minutes). If `data/pses.duckdb` already exists, the button rebuilds it for full reproducibility; if you do not click it, the notebook opens the existing database to display samples, statistics, and the Survey Results Analysis visuals — all of which render automatically once the database file is present, no button click required.

## Notebook architecture

### `pses_analytics.py` — data pipeline

Builds all analytical tables from the source CSVs:

1. **Ingestion** — streams the main PSES CSV into the `raw_pses` table
2. **Theme mapping** — loads the Subset 1 CSV into `theme_map` and `indicator_map`
3. **Transformation** — creates `pses_wog` (whole-of-government spine, typed, `9999 → NULL`), `pses_sliced` (demographic/org slices), and `pses_analysis` (wog + themes)
4. **Statistical analysis** — computes `theme_scores`, `yoy_changes`, `question_correlations`, `chi_square_results`
5. **Validation** — summarizes all tables created
6. **Survey Results Analysis** — renders automatically once `data/pses.duckdb` exists (no button required): an overall mean trend line, overall year-over-year delta bar, sub-theme mean heatmap, and a sub-theme year-over-year delta faceted bar chart, with a narrative summary. All visuals are Plotly, wrapped in `mo.ui.plotly()` for browser rendering.

**Output:** `data/pses.duckdb` with 10 tables.

Each transformation step reads its SQL from a `.sql` template in `sql/` and resolves `{token}` placeholders with `str.format()`, so the SQL shown in the notebook's display cells is exactly the SQL that executes — one source of truth per query.

## DuckDB tables

| Table | Rows | Description |
|-------|------|-------------|
| `raw_pses` | 12,179,345 | Full ingested dataset, untouched |
| `theme_map` | 207 | Question → theme/sub-theme lookup |
| `indicator_map` | 23 | Theme/sub-theme reference table |
| `pses_wog` | 772 | Whole-of-government spine, typed, `9999 → NULL` |
| `pses_sliced` | 651,295 | Demographic/org slices |
| `pses_analysis` | 772 | Primary analytical table (wog + themes) |
| `theme_scores` | 72 | Mean SCORE100 per sub-theme per year |
| `yoy_changes` | 54 | Year-over-year deltas |
| `question_correlations` | 1,711 | Pearson r between question pairs |
| `chi_square_results` | 59 | Chi-square 2019 vs 2024 per question |

## Data sources

- **Main dataset:** <https://www.canada.ca/content/dam/tbs-sct/documents/datasets/ses-2025/main-principal.csv>
- **Theme taxonomy:** <https://www.canada.ca/content/dam/tbs-sct/documents/datasets/ses-2025/subset-1-sous-ensemble-1.csv>

The theme taxonomy file is BOM-prefixed and Latin-1 encoded; the pipeline's `fetch_with_bom_strip()` helper normalizes it before loading.

## Theme taxonomy

| ID | Theme | Sub-themes |
|----|-------|-----------|
| 1 | Employee engagement | Employee engagement |
| 2 | Leadership | Immediate supervisor, Senior management |
| 3 | Workforce | Performance management, Job fit & development, Empowerment, Work-life balance, Mobility & retention |
| 4 | Workplace | Organizational goals, Organizational performance, Diversity & inclusion, Anti-racism, Ethical workplace, Physical environment, Official languages, Harassment, Discrimination, Duty to accommodate |
| 5 | Workplace well-being | Safe & healthy workplace, Psychologically healthy workplace, Work-related stress |
| 6 | Compensation | Pay issues, Support to resolve pay issues |

## Analytical notes

- **Longitudinal scope:** only questions appearing in all four survey years (2019, 2020, 2022, 2024) are included in longitudinal analysis.
- **Q73 exclusion:** Q73a–Q73w are 2024-only stress sub-questions and are excluded; Q74 and Q75 are valid stress trend questions.
- **Scoring:** `SCORE100` is the percentage of positive/neutral responses on a 0–100 scale.
- **Chi-square:** all 59 longitudinal questions show statistically significant change (p < 0.05) between 2019 and 2024. With ~186,000 respondents, even a 1% shift is detectable; treat chi-square magnitude as an effect-size proxy.
- **Pearson correlations:** with n = 4 years, r values are unreliable for causal inference; use them only to identify question clusters.
- **Mean scores:** simple `AVG(SCORE100)` across the questions in a sub-theme per year.

## Regenerating the README screenshot (maintainer)

The hero image is rendered from the canonical notebook with marimo's thumbnail exporter, which requires Playwright + Chromium (kept in the optional `docs` dependency group so the default `uv sync` stays lean):

```bash
uv sync --group docs
uv run playwright install chromium
uv run marimo export thumbnail --execute notebooks/pses_analytics.py \
  --output assets/pses-overview.png --width 1280 --height 860 --scale 2 --overwrite
```

This executes the notebook against an existing `data/pses.duckdb` and screenshots the rendered output.
