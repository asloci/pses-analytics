# PSES Analytics — Project Handoff
## Phase 2: Marimo Notebook Development

---

## Who You Are

Adam, data consultant at Treasury Board of Canada Secretariat (OCHRO). Building a
defensible, reproducible HR analytics workbench for the Public Service Employee Survey
(PSES) — 287,000+ federal public service employees. Audience is OCHRO leadership;
outputs must be auditable and explainable.

**Preferences:**
- Concise, modular explanations ("elevator-pitch-sized")
- Polars over Pandas, DuckDB over in-memory dataframes
- Privacy-conscious, open-source tooling
- Government of Canada CSV files are always BOM-prefixed + Latin-1 encoded —
  always use the `fetch_with_bom_strip()` helper in `src/pses/utils.py`

---

## Tech Stack

| Tool | Version | Role |
|---|---|---|
| Python | 3.13 | Language |
| uv | latest | Package/env management |
| DuckDB | latest | Analytical query engine |
| Polars | latest | DataFrame operations |
| Marimo | 0.23.1 | Notebook / dashboard |
| Ollama | 0.20.7 | Local LLM (future layer) |
| scipy | latest | Statistical tests |
| rich | latest | Terminal output |

**Project root:** `~/Projects/pses-analytics/`

---

## Project Structure

```
pses-analytics/
├── pyproject.toml
├── .python-version         (3.13)
├── data/
│   └── pses.duckdb         ← single source of truth (gitignored)
├── src/
│   └── pses/
│       ├── __init__.py
│       ├── utils.py        ← fetch_with_bom_strip() helper
│       ├── ingest.py       ← streams CSV → DuckDB (bulk load)
│       ├── load_themes.py  ← builds theme_map + indicator_map
│       ├── transform.py    ← builds pses_wog, pses_sliced, pses_analysis
│       └── analysis.py     ← builds all analytical tables
└── notebooks/
    └── 01_exploration.py   ← Marimo notebook (to be built)
```

**Pipeline run order (to regenerate from scratch):**
```bash
uv run python src/pses/ingest.py
uv run python src/pses/load_themes.py
uv run python src/pses/transform.py
uv run python src/pses/analysis.py
```

---

## DuckDB Table Inventory (`data/pses.duckdb`)

| Table | Rows | Description |
|---|---|---|
| `raw_pses` | 12,179,345 | Full ingested dataset, untouched |
| `pses_wog` | 772 | Whole-of-govt spine, typed, 9999→NULL |
| `pses_sliced` | 651,295 | Demographic/org slices (BYCOND IS NOT NULL) |
| `theme_map` | 207 | Question → theme/subtheme lookup (2024) |
| `indicator_map` | 23 | Flat theme/subtheme reference table |
| `pses_analysis` | 772 | pses_wog JOIN theme_map — primary analytical table |
| `theme_scores` | 72 | Mean SCORE100 per subtheme per year (longitudinal) |
| `yoy_changes` | 54 | Year-over-year deltas per subtheme |
| `question_correlations` | 1,711 | Pearson r between all question pairs (n=4 caution) |
| `chi_square_results` | 59 | Chi-square 2019 vs 2024 per question |

**Key columns in `pses_analysis`:**
`SURVEYR, QUESTION, answer1–7, POSITIVE, NEUTRAL, NEGATIVE, AGREE, SCORE5,
SCORE100, ANSCOUNT, is_scored, is_stable, TITLE_E, INDICATORID, INDICATORENG,
SUBINDICATORID, SUBINDICATORENG`

**Whole-of-government filter:**
`LEVEL1ID = 0 AND LEVEL2ID = 0 AND BYCOND IS NULL`

**Longitudinal spine filter (use this everywhere):**
```sql
QUESTION IN (
    SELECT QUESTION FROM pses_analysis
    WHERE is_stable = true
    GROUP BY QUESTION
    HAVING COUNT(CASE WHEN SCORE100 IS NOT NULL THEN 1 END) = 4
)
```
This ensures questions are scored in ALL four years (2019, 2020, 2022, 2024).
The Q73 sub-questions (work stress sub-items) only have scores in 2024 and must
be excluded from longitudinal comparisons. Q74 and Q75 are the valid stress
trend questions.

---

## Official Theme Taxonomy (INDICATORID order)

| ID | Theme | Subthemes |
|---|---|---|
| 1 | Employee engagement | Employee engagement |
| 2 | Leadership | Immediate supervisor, Senior management |
| 3 | Workforce | Performance management, Job fit & development, Empowerment, Work-life balance, Mobility & retention |
| 4 | Workplace | Organizational goals, Organizational performance, Diversity & inclusion, Anti-racism, Ethical workplace, Physical environment, Official languages, Harassment, Discrimination, Duty to accommodate |
| 5 | Workplace well-being | Safe & healthy workplace, Psychologically healthy workplace, Work-related stress |
| 6 | Compensation | Pay issues, Support to resolve pay issues |

**Excluded from longitudinal analysis (0 stable scored questions):**
Compensation, Anti-racism, Mobility & retention, A safe and healthy workplace

---

## Key Analytical Findings

### The Headline Story
Every single subtheme declined in the 2022→2024 cycle. No exceptions.

### Largest 2022→2024 Declines (mean_score delta)
| Subtheme | Delta |
|---|---|
| Physical environment and equipment | **−9.0** |
| Senior management | **−6.5** |
| A psychologically healthy workplace | **−4.7** |
| Employee engagement | **−4.0** |
| Work-related stress | **−3.5** |
| Organizational goals | **−3.5** |
| Discrimination | **−3.5** |
| Empowerment | **−3.5** |

### The Stability Contrast
**Immediate supervisor** declined only −1.0. Every other subtheme fell harder.
This means the problem is institutional/structural, not interpersonal.
Frontline managers are holding steady while senior leadership confidence collapses.

### Your Hypothesis — Confirmed Directionally
Leadership (Senior management) → Psychological health → Harassment all declined
in parallel. Cannot establish causation with 4 data points, but the directional
pattern is consistent and all changes are statistically significant.

### Physical Environment Anomaly
Q04 has the highest chi-square in the dataset (χ²=9,167). The −9.0 point drop
in 2022→2024 almost certainly reflects the return-to-office (RTO) mandate.
This is a policy-driven signal directly relevant to OCHRO.

### Statistical Notes for Stakeholder Communication
- **Chi-square:** All 59 longitudinal questions show statistically significant
  change (p<0.05) between 2019 and 2024. With ~186,000 respondents, even a 1%
  shift in response distribution is detectable. Significance ≠ large change.
  Use χ² magnitude as the effect size proxy.
- **Pearson correlations:** n=4 years makes r values unreliable for causal
  inference. Use for identifying question clusters (construct validity) only.
- **Mean scores:** Simple AVG(SCORE100) across questions in a subtheme per year.
  Subthemes with few questions (Harassment=2, Discrimination=2) should be
  disclosed as thin but defensible.

---

## Marimo Notebook Plan

### How to Launch
```bash
cd ~/Projects/pses-analytics
uv run marimo edit notebooks/01_exploration.py
```

### AI Assistance Setup (Free / Local)
Marimo Pair requires Claude Code (paid). Use instead:

**Option A — Antigravity + --watch mode (recommended for building):**
```bash
uv run marimo edit --watch notebooks/01_exploration.py
```
Antigravity edits the `.py` file; Marimo reacts live in the browser.

**Option B — Ollama inside Marimo editor:**
Configure `marimo.toml` to use `qwen3-coder:latest` via Ollama for
tab completion and the chat sidebar. No API key needed.
Find config location: `uv run marimo config show | head -5`

### Recommended Ollama Model
`qwen3-coder:latest` — best coder in current local lineup.
`granite4:latest` — lightweight fallback.

### Notebook Cell Architecture (build in this order)

**Cell 1 — Imports and DB connection**
```python
import duckdb
import polars as pl
import marimo as mo
con = duckdb.connect("data/pses.duckdb", read_only=True)
```

**Cell 2 — UI controls (year selector, theme selector)**
Use `mo.ui.dropdown()` and `mo.ui.multiselect()`.
These drive all downstream cells reactively.

**Cell 3 — Theme score trend data**
Query `theme_scores`, filtered by selected theme.
Return as Polars DataFrame.

**Cell 4 — Trend line chart**
Line chart: x=SURVEYR, y=mean_score, color=SUBINDICATORENG.
Recommended: `altair` or `plotly`. Add to deps with `uv add altair`.

**Cell 5 — Year-over-year delta heatmap**
Query `yoy_changes`. Heatmap: rows=subtheme, cols=period, values=delta.
This is the GitHub-commit-style heatmap you envisioned.
Color scale: diverging red/green centered at 0.

**Cell 6 — Chi-square significance table**
Query `chi_square_results`. Display as `mo.ui.table()`.
Show question text (join to theme_map for TITLE_E), χ², p_value.
Filter to selected theme.

**Cell 7 — Question detail drill-down**
When user selects a question from Cell 6 table,
show the full response distribution (answer1–5 as % bar chart)
comparing 2019 vs 2024 side by side.

**Cell 8 — Narrative markdown**
`mo.md(f"""...""")` with dynamic values from selected theme.
Plain-language summary of the finding for leadership audience.

### Marimo-Specific Rules (critical for Antigravity)
Tell Antigravity these rules before generating any notebook code:
1. Every cell must be a pure function — no side effects between cells
2. Reactive variables flow down; never mutate a variable from another cell
3. UI elements (mo.ui.*) must be defined in their own cell, returned as the cell value
4. Use `mo.stop()` for conditional early exits, not `return` in the middle of logic
5. Run `uv run marimo check notebooks/01_exploration.py` after each batch of
   cells to catch redefined variable errors before they cause hidden state issues
6. Markdown cells should precede every code cell (good documentation practice)

---

## Package Update Commands
```bash
# Upgrade all deps to latest compatible versions
uv lock --upgrade
uv sync

# Add new packages as needed
uv add altair        # for charts
uv add vegafusion    # for altair performance with large data

# Check marimo notebook for errors
uv run marimo check notebooks/01_exploration.py
```

---

## Data Engineering Patterns to Carry Forward
1. **Streaming CSV to DuckDB:** Use `read_csv_auto(url, header=true)` — no download needed
2. **GC file encoding:** Always use `fetch_with_bom_strip()` from `src/pses/utils.py`
3. **Editable install:** `uv pip install -e .` with hatchling build backend enables cross-module imports
4. **DuckDB read-only in notebook:** Always open with `read_only=True` to prevent notebook from corrupting analytical tables
5. **Longitudinal filter:** Always use the `fully_scored_questions` CTE — never just `is_stable AND is_scored`
