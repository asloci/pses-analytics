# PSES Analytics

A reproducible data engineering and analysis workbench for the Public Service Employee Survey (PSES) — Canada's federal public service employee survey with 287,000+ respondents.

## Overview

This project provides a complete, documented pipeline for ingesting, transforming, and analyzing PSES data using:
- **DuckDB** for analytical query engine
- **Polars** for DataFrame operations  
- **Marimo** for interactive notebooks
- **Altair** for visualization

## Project Structure

```
pses-analytics/
├── notebooks/
│   ├── 01_data_engineering.py   # Data pipeline: ingestion → analysis tables
│   └── 02_exploration.py        # Interactive analysis and visualization
├── data/
│   └── pses.duckdb             # Generated DuckDB database (gitignored)
├── pyproject.toml              # Dependencies
├── .gitignore
└── README.md
```

## Quick Start

### 1. Install Dependencies

```bash
cd pses-analytics
uv sync
```

### 2. Build the Data Pipeline

Run the data engineering notebook to download source data and build all analytical tables:

```bash
uv run marimo edit notebooks/01_data_engineering.py
```

This notebook will:
- Download raw PSES CSV from Canada.ca
- Load theme taxonomy from Subset 1
- Create all analytical tables in `data/pses.duckdb`
- **Note**: If `data/pses.duckdb` already exists, it will be rebuilt from scratch for full reproducibility

### 3. Explore the Data

Run the exploration notebook to analyze the data:

```bash
uv run marimo edit notebooks/02_exploration.py
```

This notebook provides:
- Theme and year selectors
- Trend line charts
- Year-over-year change heatmaps
- Chi-square significance tables
- Question-level drill-down
- Leadership-ready narrative summaries

## Notebook Architecture

### 01_data_engineering.py — Data Pipeline

**Purpose**: Build all analytical tables from source CSVs

**Steps**:
1. **Database Setup**: Connect to DuckDB, create/overwrite `data/pses.duckdb`
2. **Data Ingestion**: Stream main PSES CSV → `raw_pses` table
3. **Theme Mapping**: Load Subset 1 CSV → `theme_map`, `indicator_map` tables
4. **Data Transformation**: Create `pses_wog`, `pses_sliced`, `pses_analysis`
5. **Statistical Analysis**: Create `theme_scores`, `yoy_changes`, `question_correlations`, `chi_square_results`
6. **Validation**: Summary of all tables created

**Output**: `data/pses.duckdb` with 10 tables

### 02_exploration.py — Interactive Analysis

**Purpose**: Explore the analytical tables with interactive visualizations

**Features**:
- **Theme Selector**: Choose from 6 organizational themes
- **Year Selector**: Filter by survey year (2019, 2020, 2022, 2024)
- **Trend Charts**: Line charts of subtheme scores over time
- **Heatmap**: Year-over-year score changes with color-coded deltas
- **Chi-Square Table**: Statistical significance of 2019 vs 2024 changes
- **Drill-Down**: Select a question to see response distribution
- **Narrative**: Auto-generated leadership summary

**Input**: `data/pses.duckdb` (read-only)

## DuckDB Tables

| Table | Rows | Description |
|-------|------|-------------|
| `raw_pses` | ~12.2M | Full ingested dataset, untouched |
| `theme_map` | 207 | Question → theme/subtheme lookup |
| `indicator_map` | 23 | Theme/subtheme reference table |
| `pses_wog` | 772 | Whole-of-govt spine, typed, 9999→NULL |
| `pses_sliced` | ~651K | Demographic/org slices |
| `pses_analysis` | 772 | Primary analytical table (wog + themes) |
| `theme_scores` | 72 | Mean SCORE100 per subtheme per year |
| `yoy_changes` | 54 | Year-over-year deltas |
| `question_correlations` | ~1,711 | Pearson r between question pairs |
| `chi_square_results` | 59 | Chi-square 2019 vs 2024 per question |

## Data Sources

- **Main Dataset**: https://www.canada.ca/content/dam/tbs-sct/documents/datasets/ses-2025/main-principal.csv
- **Theme Taxonomy**: https://www.canada.ca/content/dam/tbs-sct/documents/datasets/ses-2025/subset-1-sous-ensemble-1.csv

## Key Design Principles

1. **Reproducibility**: Any user can run `01_data_engineering.py` from scratch to rebuild all tables
2. **Documentation**: Each pipeline step is documented with markdown in the notebook
3. **Idempotency**: Running the pipeline multiple times produces the same result
4. **Read-Only Exploration**: The exploration notebook opens the database in read-only mode
5. **Government Data Handling**: Uses `fetch_with_bom_strip()` to handle BOM-prefixed, Latin-1 encoded CSV files

## Theme Taxonomy

| ID | Theme | Subthemes |
|----|-------|-----------|
| 1 | Employee engagement | Employee engagement |
| 2 | Leadership | Immediate supervisor, Senior management |
| 3 | Workforce | Performance management, Job fit & development, Empowerment, Work-life balance, Mobility & retention |
| 4 | Workplace | Organizational goals, Organizational performance, Diversity & inclusion, Anti-racism, Ethical workplace, Physical environment, Official languages, Harassment, Discrimination, Duty to accommodate |
| 5 | Workplace well-being | Safe & healthy workplace, Psychologically healthy workplace, Work-related stress |
| 6 | Compensation | Pay issues, Support to resolve pay issues |

## Longitudinal Analysis Notes

- **Stable Questions**: Only questions appearing in all 4 survey years (2019, 2020, 2022, 2024) are included in longitudinal analysis
- **Q73 Exclusion**: Q73a-Q73w are 2024-only stress sub-questions and are excluded; Q74 and Q75 are valid stress trend questions
- **Scoring**: SCORE100 represents percentage of positive/neutral responses on a 0-100 scale

## Statistical Notes

- **Chi-Square**: All 59 longitudinal questions show statistically significant change (p<0.05) between 2019 and 2024. With ~186,000 respondents, even a 1% shift is detectable. Use chi-square magnitude as effect size proxy.
- **Pearson Correlations**: With n=4 years, r values are unreliable for causal inference. Use for identifying question clusters only.
- **Mean Scores**: Simple AVG(SCORE100) across questions in a subtheme per year.

## License

This project is for Government of Canada internal use.
