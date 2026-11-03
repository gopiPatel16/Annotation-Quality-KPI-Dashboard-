"""Turn KPI tables into prioritised, plain-language recommendations."""
from __future__ import annotations

import pandas as pd

from .metrics import TARGETS


def build(overall: dict, scorecard: pd.DataFrame, proj_kpi: pd.DataFrame, proj_agree: pd.DataFrame,
          diff_agree: pd.DataFrame, confusions: pd.DataFrame, capacity: pd.DataFrame) -> pd.DataFrame:
    recs = []

    def add(area, priority, finding, action):
        recs.append({"area": area, "priority": priority, "finding": finding, "recommendation": action})

    low = scorecard[scorecard["accuracy"] < TARGETS["accuracy"]]
    if len(low):
        ids = ", ".join(low["annotator_id"].head(6))
        add("Process optimisation", "High",
            f"{len(low)} of {len(scorecard)} annotators are below the {TARGETS['accuracy']:.0%} accuracy target "
            f"(lowest: {ids}).",
            "Enrol them in targeted re-training, route their work to 100% review until accuracy recovers, "
            "and pair each with a high-scoring mentor from the same team.")
    team = scorecard.groupby("team")["accuracy"].mean()
    if team.max() - team.min() > 0.02:
        add("Process optimisation", "Medium",
            f"Team accuracy spread is {team.max() - team.min():.1%} ({team.idxmax()} best, {team.idxmin()} worst).",
            f"Share {team.idxmax()}'s onboarding and QA checklist with {team.idxmin()}.")

    for r in proj_agree.itertuples():
        if r.fleiss_kappa < TARGETS["kappa"]:
            add("Data management", "High",
                f"Project '{r.project}' agreement is below target (Fleiss kappa {r.fleiss_kappa:.2f} < {TARGETS['kappa']}).",
                "Rewrite the labelling guidelines with edge-case examples and run a calibration session.")
    if len(confusions):
        c = confusions.iloc[0]
        add("Data management", "Medium",
            f"Most frequent gold error: '{c.gold_label}' labelled as '{c.label}' in {c.project} ({c.errors} cases).",
            "Add decision rules and counter-examples for this label pair to the guideline, "
            "and add more gold items covering it.")
    hard = diff_agree.set_index("difficulty")["fleiss_kappa"]
    if "hard" in hard and "easy" in hard and hard["easy"] - hard["hard"] > 0.1:
        add("Data management", "Medium",
            f"Agreement drops from {hard['easy']:.2f} (easy) to {hard['hard']:.2f} (hard tasks).",
            "Send hard tasks to senior annotators or increase overlap to 5 raters with adjudication.")

    rw = overall.get("rework_rate")
    if rw is not None and rw > TARGETS["rework_rate"]:
        add("Process optimisation", "High", f"Rework rate is {rw:.1%} (target {TARGETS['rework_rate']:.0%}).",
            "Add inline validation and a self-check step before submit; sample-review new joiners earlier.")
    slow = scorecard[scorecard["throughput_per_hour"] < scorecard["throughput_per_hour"].quantile(0.2)]
    slow_hi_acc = slow[slow["accuracy"] >= TARGETS["accuracy"]]
    if len(slow_hi_acc):
        add("Process optimisation", "Low",
            f"{len(slow_hi_acc)} slow-but-accurate annotators in the bottom throughput quintile.",
            "Coach on tooling and keyboard shortcuts; do not trade accuracy for speed.")

    x = capacity.set_index("volume_multiplier")["annotators_needed"]
    if 10 in x.index:
        add("Scalability", "Medium",
            f"Assuming 80% utilisation today, 10x volume needs ~{x[10]} annotators (vs {int(overall['annotators'])} today).",
            "Start a hiring/vendor pipeline now, automate pre-labelling for easy tasks, and "
            "reduce overlap on tasks where the first two annotators agree (adaptive overlap).")
    add("Scalability", "Medium",
        "Gold items are ~15% of volume; this is the main accuracy signal.",
        "Keep gold coverage per annotator >= 30 samples/month and refresh the gold set to prevent memorisation.")

    order = {"High": 0, "Medium": 1, "Low": 2}
    out = pd.DataFrame(recs)
    return out.sort_values("priority", key=lambda s: s.map(order), kind="stable").reset_index(drop=True)
