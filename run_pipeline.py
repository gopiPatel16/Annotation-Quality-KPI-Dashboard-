"""End-to-end pipeline: generate data -> SQLite/SQL KPIs -> pandas KPIs -> Excel, BI extracts, charts.

Usage:  python run_pipeline.py [--seed 42] [--tasks 2400]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from aqkpi import charts, excel_report, generate_data, metrics, recommendations, sql_layer  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--tasks", type=int, default=2400)
    ap.add_argument("--annotators", type=int, default=24)
    args = ap.parse_args()

    raw, out = ROOT / "data" / "raw", ROOT / "outputs"
    bi = out / "bi_extracts"
    for d in (raw, bi):
        d.mkdir(parents=True, exist_ok=True)

    # 1. data
    ann, tasks, notes = generate_data.generate(args.tasks, args.annotators, args.seed)
    ann.drop(columns=["skill_hidden"]).to_csv(raw / "annotators.csv", index=False)
    tasks.to_csv(raw / "tasks.csv", index=False)
    notes.to_csv(raw / "annotations.csv", index=False)

    # 2. SQL layer
    conn = sql_layer.build_db(raw, out / "annotation_kpi.db")
    sql_out = sql_layer.run_all(conn)
    conn.close()

    # 3. pandas KPIs
    df = metrics.enrich(notes, tasks, ann.drop(columns=["skill_hidden"]))
    overall = metrics.overall_kpis(df)
    scorecard = metrics.annotator_scorecard(df)
    weekly = metrics.kpi_by(df, "week").rename(columns={"week": "week_start"})
    proj_kpi = metrics.kpi_by(df, "project")
    proj_agree = metrics.agreement_by_project(df)
    diff_agree = metrics.agreement_by_difficulty(df)
    pair = metrics.pairwise_kappa(df)
    conf = metrics.confusion_pairs(df)
    cap = metrics.capacity_plan(df)
    recs = recommendations.build(overall, scorecard, proj_kpi, proj_agree, diff_agree, conf, cap)

    # 4. outputs
    excel_report.write_report(out / "Annotation_KPI_Report.xlsx", overall, scorecard, weekly, proj_kpi,
                              proj_agree, pair, conf, cap, recs)
    for name, frame in {"annotator_scorecard": scorecard, "weekly_trend": weekly, "project_kpis": proj_kpi,
                        "project_agreement": proj_agree, "pairwise_kappa": pair, "error_hotspots": conf,
                        "capacity_plan": cap, "recommendations": recs}.items():
        frame.to_csv(bi / f"{name}.csv", index=False)
    # flat fact table for Power BI / Tableau (one row per annotation)
    fact = df.drop(columns=["consensus_label"]).assign(
        is_correct=lambda d: d["correct_vs_gold"],
        is_rework=lambda d: d["review_outcome"].map({"rework": 1, "accepted": 0}))
    fact.to_csv(bi / "fact_annotations.csv", index=False)
    (out / "sql_results").mkdir(exist_ok=True)
    for name, frame in sql_out.items():
        frame.to_csv(out / "sql_results" / f"{name}.csv", index=False)
    charts.make_charts(out / "charts", scorecard, weekly, proj_agree)

    (out / "overall_kpis.json").write_text(json.dumps({k: (None if pd.isna(v) else round(float(v), 4)) for k, v in overall.items()}, indent=2))
    print(json.dumps({k: round(float(v), 3) for k, v in overall.items()}, indent=2))
    print(f"\n{len(recs)} recommendations; outputs in {out}")


if __name__ == "__main__":
    main()
