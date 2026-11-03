"""Static PNG charts for the README / quick sharing."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from .metrics import TARGETS  # noqa: E402


def make_charts(out: Path, scorecard: pd.DataFrame, weekly: pd.DataFrame, proj_agree: pd.DataFrame) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    paths = []

    sc = scorecard.sort_values("accuracy")
    fig, ax = plt.subplots(figsize=(9, 6))
    colors = ["#d62728" if a < TARGETS["accuracy"] else "#2a9d8f" for a in sc["accuracy"]]
    ax.barh(sc["annotator_id"], sc["accuracy"], color=colors)
    ax.axvline(TARGETS["accuracy"], ls="--", color="k", lw=1, label=f"Target {TARGETS['accuracy']:.0%}")
    ax.set_xlim(0.5, 1.0)
    ax.set_title("Accuracy vs gold, by annotator")
    ax.legend()
    p = out / "accuracy_by_annotator.png"
    fig.tight_layout(); fig.savefig(p, dpi=130); plt.close(fig); paths.append(p)

    fig, ax1 = plt.subplots(figsize=(9, 4.5))
    x = pd.to_datetime(weekly["week_start"])
    ax1.plot(x, weekly["accuracy"], marker="o", color="#264653", label="Accuracy")
    ax1.plot(x, 1 - weekly["rework_rate"], marker="s", color="#e76f51", label="1 - rework rate")
    ax1.set_ylim(0.7, 1.0)
    ax2 = ax1.twinx()
    ax2.bar(x, weekly["annotations"], width=4, alpha=0.2, color="#457b9d")
    ax2.set_ylabel("Annotations")
    ax1.set_title("Weekly quality trend and volume")
    ax1.legend(loc="lower right")
    p = out / "weekly_trend.png"
    fig.tight_layout(); fig.savefig(p, dpi=130); plt.close(fig); paths.append(p)

    fig, ax = plt.subplots(figsize=(7, 4))
    w = 0.35
    idx = range(len(proj_agree))
    ax.bar([i - w / 2 for i in idx], proj_agree["fleiss_kappa"], w, label="Fleiss' kappa")
    ax.bar([i + w / 2 for i in idx], proj_agree["krippendorff_alpha"], w, label="Krippendorff's alpha")
    ax.axhline(TARGETS["kappa"], ls="--", color="k", lw=1)
    ax.set_xticks(list(idx)); ax.set_xticklabels(proj_agree["project"])
    ax.set_title("Inter-annotator agreement by project")
    ax.legend()
    p = out / "agreement_by_project.png"
    fig.tight_layout(); fig.savefig(p, dpi=130); plt.close(fig); paths.append(p)
    return paths
