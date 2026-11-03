# Tableau dashboard

1. **Connect → Text file**: `outputs/bi_extracts/fact_annotations.csv`; add `annotator_scorecard.csv`
   (join on `annotator_id`) and `project_agreement.csv` (relationship on `project`).
2. Create the calculated fields in [`calculated_fields.md`](calculated_fields.md).
3. Build sheets, then assemble two dashboards:
   - **Quality Overview** – KPI BANs (Accuracy, Kappa, Throughput, Rework), weekly trend dual-axis
     (Accuracy line + Annotations bars), project filter action.
   - **Annotator Drill-down** – scatter *Throughput vs Accuracy* (colour = Accuracy Status, detail = annotator),
     highlight table of errors (gold_label × label), recommendations table.
4. Add a parameter **Accuracy Target** (default 0.90) to drive the reference line and status colours.
