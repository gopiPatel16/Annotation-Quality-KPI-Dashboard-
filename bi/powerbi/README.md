# Power BI dashboard

1. **Get Data → Text/CSV**: load from `outputs/bi_extracts/`:
   `fact_annotations.csv` (name it `Annotations`), `annotator_scorecard.csv`, `weekly_trend.csv`,
   `project_agreement.csv`, `recommendations.csv`.
   (Or **Get Data → SQLite/ODBC** on `outputs/annotation_kpi.db`.)
2. Relationships: `Annotations[annotator_id]` → `annotator_scorecard[annotator_id]` (many-to-one);
   `Annotations[project]` → `project_agreement[project]` (many-to-one).
3. Paste the measures from [`measures.dax`](measures.dax).
4. Suggested pages:

| Page | Visuals |
|------|---------|
| **Executive Overview** | KPI cards (Accuracy, Fleiss Kappa, Throughput/hr, Rework Rate) with target conditional colours; weekly line chart of Accuracy & Rework; slicers: Project, Team, Difficulty |
| **Annotator Performance** | Scorecard table (conditional formatting on Accuracy < 90%), scatter *Throughput vs Accuracy* sized by annotations, top/bottom 5 bar |
| **Agreement & Errors** | Kappa/alpha by project (clustered bars), confusion matrix (matrix visual: gold_label × label, from `error_hotspots.csv`), accuracy by difficulty |
| **Actions** | `recommendations.csv` table, capacity-plan line chart (`capacity_plan.csv`) |

5. Theme: use the colours in `bi/theme.json` (File → View → Themes → Browse for themes).
