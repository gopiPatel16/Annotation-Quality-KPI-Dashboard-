"""Multi-sheet Excel KPI report (openpyxl) with formulas, conditional formats and charts."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.formatting.rule import CellIsRule, ColorScaleRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .metrics import TARGETS

HDR = PatternFill("solid", fgColor="1F3A5F")
RED = PatternFill("solid", bgColor="F8CBAD", fgColor="F8CBAD")
GREEN = PatternFill("solid", bgColor="C6E0B4", fgColor="C6E0B4")


def _write_df(ws, df: pd.DataFrame, start_row=1, pct_cols=(), float_cols=()):
    for j, c in enumerate(df.columns, 1):
        cell = ws.cell(start_row, j, c)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = HDR
        cell.alignment = Alignment(horizontal="center", wrap_text=True)
    for i, row in enumerate(df.itertuples(index=False), start_row + 1):
        for j, v in enumerate(row, 1):
            if isinstance(v, pd.Timestamp):
                v = v.to_pydatetime().date()
            elif pd.isna(v) if not isinstance(v, str) else False:
                v = None
            cell = ws.cell(i, j, v)
            name = df.columns[j - 1]
            if name in pct_cols:
                cell.number_format = "0.0%"
            elif name in float_cols:
                cell.number_format = "0.00"
    for j, c in enumerate(df.columns, 1):
        width = max(len(str(c)), *(len(str(x)) for x in df.iloc[:, j - 1].head(50))) + 2
        ws.column_dimensions[get_column_letter(j)].width = min(width, 70)
    ws.freeze_panes = ws.cell(start_row + 1, 1)


def write_report(path: Path, overall: dict, scorecard: pd.DataFrame, weekly: pd.DataFrame,
                 proj_kpi: pd.DataFrame, proj_agree: pd.DataFrame, pair_kappa: pd.DataFrame,
                 confusions: pd.DataFrame, capacity: pd.DataFrame, recs: pd.DataFrame) -> None:
    wb = Workbook()

    # ---- Summary
    ws = wb.active
    ws.title = "Summary"
    ws["A1"] = "Annotation Quality & KPI Report"
    ws["A1"].font = Font(size=18, bold=True)
    ws.append([])
    ws.append(["KPI", "Value", "Target", "Status"])
    for c in ws[3]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = HDR
    rows = [
        ("Accuracy (vs gold)", overall["accuracy"], TARGETS["accuracy"], ">=", "0.0%"),
        ("Fleiss' kappa", overall["fleiss_kappa"], TARGETS["kappa"], ">=", "0.00"),
        ("Krippendorff's alpha", overall["krippendorff_alpha"], TARGETS["kappa"], ">=", "0.00"),
        ("Rework rate", overall["rework_rate"], TARGETS["rework_rate"], "<=", "0.0%"),
    ]
    for k, (name, val, tgt, op, fmt) in enumerate(rows, 4):
        ws.cell(k, 1, name)
        ws.cell(k, 2, float(val)).number_format = fmt
        ws.cell(k, 3, tgt).number_format = fmt
        ws.cell(k, 4, f'=IF(B{k}{op}C{k},"ON TARGET","OFF TARGET")')  # live formula
    r = 4 + len(rows) + 1
    for label, key, fmt in [("Throughput (annotations / active hour)", "throughput_per_hour", "0.0"),
                            ("Avg handle time (sec)", "avg_handle_time_sec", "0.0"),
                            ("Total annotations", "annotations", "#,##0"),
                            ("Tasks", "tasks", "#,##0"), ("Annotators", "annotators", "0")]:
        ws.cell(r, 1, label)
        ws.cell(r, 2, float(overall[key])).number_format = fmt
        r += 1
    ws.column_dimensions["A"].width = 40
    for col in "BCD":
        ws.column_dimensions[col].width = 16
    ws.conditional_formatting.add("D4:D7", CellIsRule(operator="equal", formula=['"ON TARGET"'], fill=GREEN))
    ws.conditional_formatting.add("D4:D7", CellIsRule(operator="equal", formula=['"OFF TARGET"'], fill=RED))

    # ---- Scorecard
    ws = wb.create_sheet("Annotator Scorecard")
    cols = ["annotator_id", "team", "tenure_weeks", "annotations", "gold_samples", "accuracy",
            "agreement_rate", "avg_handle_time_sec", "throughput_per_hour", "rework_rate",
            "accuracy_flag", "agreement_flag"]
    sc = scorecard[cols]
    _write_df(ws, sc, pct_cols=("accuracy", "agreement_rate", "rework_rate"),
              float_cols=("avg_handle_time_sec", "throughput_per_hour"))
    n = len(sc) + 1
    ws.conditional_formatting.add(f"F2:F{n}", CellIsRule(operator="lessThan", formula=[str(TARGETS["accuracy"])], fill=RED))
    ws.conditional_formatting.add(f"I2:I{n}", ColorScaleRule(start_type="min", start_color="FFFFFF", end_type="max", end_color="63BE7B"))
    ws.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{n}"
    ch = BarChart()
    ch.type = "bar"
    ch.title = "Accuracy by annotator"
    ch.add_data(Reference(ws, min_col=6, min_row=1, max_row=n), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=1, min_row=2, max_row=n))
    ch.height, ch.width = 14, 16
    ws.add_chart(ch, "N2")

    # ---- Weekly trend
    ws = wb.create_sheet("Weekly Trend")
    _write_df(ws, weekly, pct_cols=("accuracy", "rework_rate"), float_cols=("avg_handle_time_sec", "throughput_per_hour"))
    m = len(weekly) + 1
    lc = LineChart()
    lc.title = "Weekly accuracy"
    acc_col = list(weekly.columns).index("accuracy") + 1
    lc.add_data(Reference(ws, min_col=acc_col, min_row=1, max_row=m), titles_from_data=True)
    lc.set_categories(Reference(ws, min_col=1, min_row=2, max_row=m))
    lc.y_axis.scaling.min = 0.7
    lc.y_axis.scaling.max = 1.0
    ws.add_chart(lc, "J2")

    # ---- Projects / agreement
    ws = wb.create_sheet("Projects")
    _write_df(ws, proj_kpi, pct_cols=("accuracy", "rework_rate", "consensus_match"),
              float_cols=("avg_handle_time_sec", "throughput_per_hour"))
    _write_df(ws, proj_agree, start_row=len(proj_kpi) + 4, float_cols=("fleiss_kappa", "krippendorff_alpha", "mean_pairwise_kappa"))
    ws.freeze_panes = None

    ws = wb.create_sheet("Pairwise Agreement")
    _write_df(ws, pair_kappa.sort_values("kappa"), float_cols=("kappa",))
    ws.conditional_formatting.add(f"D2:D{len(pair_kappa) + 1}",
                                  ColorScaleRule(start_type="min", start_color="F8696B", mid_type="percentile", mid_value=50,
                                                 mid_color="FFEB84", end_type="max", end_color="63BE7B"))

    ws = wb.create_sheet("Error Hotspots")
    _write_df(ws, confusions)

    ws = wb.create_sheet("Capacity Plan")
    _write_df(ws, capacity)

    ws = wb.create_sheet("Recommendations")
    _write_df(ws, recs)
    ws.column_dimensions["C"].width = 70
    ws.column_dimensions["D"].width = 90
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")

    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
