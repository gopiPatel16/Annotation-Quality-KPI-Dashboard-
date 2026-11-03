"""KPI computations: accuracy, throughput, rework, inter-annotator agreement."""
from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd

TARGETS = {"accuracy": 0.90, "kappa": 0.70, "rework_rate": 0.10}


# ----------------------------------------------------------------- agreement
def cohen_kappa(a, b) -> float:
    a, b = np.asarray(a), np.asarray(b)
    if len(a) == 0:
        return float("nan")
    po = float(np.mean(a == b))
    labels = np.union1d(a, b)
    pe = sum(float(np.mean(a == l)) * float(np.mean(b == l)) for l in labels)
    return 1.0 if pe >= 1 else (po - pe) / (1 - pe)


def _count_matrix(df: pd.DataFrame, unit="task_id", rater="annotator_id", label="label") -> pd.DataFrame:
    return pd.crosstab(df[unit], df[label])


def fleiss_kappa(df: pd.DataFrame, unit="task_id", label="label") -> float:
    """Fleiss' kappa over units that have the modal number of raters."""
    counts = _count_matrix(df, unit, label=label)
    n_per = counts.sum(axis=1)
    n = int(n_per.mode().iloc[0])
    if n < 2:
        return float("nan")
    m = counts[n_per == n].to_numpy(dtype=float)
    p_i = ((m ** 2).sum(axis=1) - n) / (n * (n - 1))
    p_j = m.sum(axis=0) / m.sum()
    pe = float((p_j ** 2).sum())
    pbar = float(p_i.mean())
    return 1.0 if pe >= 1 else (pbar - pe) / (1 - pe)


def krippendorff_alpha(df: pd.DataFrame, unit="task_id", label="label") -> float:
    """Krippendorff's alpha, nominal level, handles variable raters per unit."""
    counts = _count_matrix(df, unit, label=label).to_numpy(dtype=float)
    m = counts.sum(axis=1)
    keep = m >= 2
    counts, m = counts[keep], m[keep]
    if len(m) == 0:
        return float("nan")
    k = counts.shape[1]
    o = np.zeros((k, k))
    for n_c, mu in zip(counts, m):
        o += (np.outer(n_c, n_c) - np.diag(n_c)) / (mu - 1)
    n_c = o.sum(axis=1)
    n = n_c.sum()
    d_o = o.sum() - np.trace(o)
    d_e = (np.outer(n_c, n_c).sum() - (n_c ** 2).sum()) / (n - 1)
    return 1.0 if d_e == 0 else 1 - d_o / d_e


def pairwise_kappa(df: pd.DataFrame, min_shared: int = 5) -> pd.DataFrame:
    """Cohen's kappa for every annotator pair with >= min_shared shared tasks."""
    wide = df.pivot_table(index="task_id", columns="annotator_id", values="label", aggfunc="first")
    rows = []
    for a, b in combinations(wide.columns, 2):
        both = wide[[a, b]].dropna()
        if len(both) >= min_shared:
            rows.append({"annotator_a": a, "annotator_b": b, "shared_tasks": len(both),
                         "kappa": cohen_kappa(both[a], both[b])})
    return pd.DataFrame(rows, columns=["annotator_a", "annotator_b", "shared_tasks", "kappa"])


def annotator_agreement(df: pd.DataFrame) -> pd.DataFrame:
    """Per annotator: how often they match the majority of the *other* raters."""
    maj = []
    for _, g in df.groupby("task_id"):
        for i, r in g.iterrows():
            others = g.drop(index=i)["label"]
            if len(others) < 2:
                continue
            top = others.value_counts()
            if len(top) > 1 and top.iloc[0] == top.iloc[1]:
                continue  # no clear majority among the others
            maj.append((r["annotator_id"], r["label"] == top.index[0]))
    out = pd.DataFrame(maj, columns=["annotator_id", "match"])
    return (out.groupby("annotator_id")["match"].agg(agreement_rate="mean", comparisons="size")
            .reset_index())


# ----------------------------------------------------------------- KPIs
def enrich(annotations: pd.DataFrame, tasks: pd.DataFrame, annotators: pd.DataFrame) -> pd.DataFrame:
    df = (annotations.merge(tasks, on="task_id").merge(annotators, on="annotator_id"))
    for c in ("started_at", "submitted_at", "created_date"):
        df[c] = pd.to_datetime(df[c])
    df["week"] = df["created_date"].dt.to_period("W-SUN").dt.start_time
    df["correct_vs_gold"] = np.where(df["is_gold"].astype(bool), df["label"] == df["gold_label"], np.nan)
    consensus = (df.groupby("task_id")["label"].agg(lambda s: s.value_counts().index[0]))
    df["consensus_label"] = df["task_id"].map(consensus)
    return df


def _agg(g: pd.DataFrame) -> pd.Series:
    gold = g["correct_vs_gold"].dropna()
    rev = g["review_outcome"].dropna()
    hours = g["duration_sec"].sum() / 3600
    return pd.Series({
        "annotations": len(g),
        "gold_samples": len(gold),
        "accuracy": gold.mean() if len(gold) else np.nan,
        "consensus_match": (g["label"] == g["consensus_label"]).mean(),
        "avg_handle_time_sec": g["duration_sec"].mean(),
        "throughput_per_hour": len(g) / hours if hours else np.nan,
        "reviewed": len(rev),
        "rework_rate": (rev == "rework").mean() if len(rev) else np.nan,
    })


def kpi_by(df: pd.DataFrame, *keys: str) -> pd.DataFrame:
    return df.groupby(list(keys)).apply(_agg, include_groups=False).reset_index()


def overall_kpis(df: pd.DataFrame) -> dict:
    s = _agg(df)
    s["fleiss_kappa"] = fleiss_kappa(df)
    s["krippendorff_alpha"] = krippendorff_alpha(df)
    s["tasks"] = df["task_id"].nunique()
    s["annotators"] = df["annotator_id"].nunique()
    return s.to_dict()


def agreement_by_project(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for p, g in df.groupby("project"):
        rows.append({"project": p, "tasks": g["task_id"].nunique(),
                     "fleiss_kappa": fleiss_kappa(g), "krippendorff_alpha": krippendorff_alpha(g),
                     "mean_pairwise_kappa": pairwise_kappa(g)["kappa"].mean()})
    return pd.DataFrame(rows)


def agreement_by_difficulty(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame([{"difficulty": d, "fleiss_kappa": fleiss_kappa(g),
                          "krippendorff_alpha": krippendorff_alpha(g)}
                         for d, g in df.groupby("difficulty")])


def annotator_scorecard(df: pd.DataFrame) -> pd.DataFrame:
    sc = kpi_by(df, "annotator_id").merge(annotator_agreement(df), on="annotator_id")
    sc = sc.merge(df[["annotator_id", "team", "tenure_weeks"]].drop_duplicates(), on="annotator_id")
    sc["accuracy_flag"] = np.where(sc["accuracy"] < TARGETS["accuracy"], "BELOW TARGET", "OK")
    sc["agreement_flag"] = np.where(sc["agreement_rate"] < 0.80, "LOW", "OK")
    return sc.sort_values("accuracy")


def confusion_pairs(df: pd.DataFrame, top: int = 8) -> pd.DataFrame:
    g = df[df["is_gold"].astype(bool) & (df["label"] != df["gold_label"])]
    return (g.groupby(["project", "gold_label", "label"]).size()
            .reset_index(name="errors").sort_values("errors", ascending=False).head(top))


def capacity_plan(df: pd.DataFrame, growth_factors=(1, 2, 5, 10), current_utilisation: float = 0.80,
                  target_utilisation: float = 0.85, target_rework: float = TARGETS["rework_rate"]) -> pd.DataFrame:
    """Headcount needed as volume scales.

    The dataset is a sample, so absolute volume is not used; instead we assume the current team runs at
    `current_utilisation` and scale demand by the growth factor. Observed rework adds effort
    (1 / (1 - rework)), so the plan also shows the headcount saved if rework fell to target.
    """
    headcount = df["annotator_id"].nunique()
    rw = df["review_outcome"].dropna().eq("rework").mean()
    rows = []
    for f in growth_factors:
        base = headcount * current_utilisation * f / target_utilisation
        now = int(np.ceil(base))
        at_target = int(np.ceil(base * (1 - rw) / (1 - min(rw, target_rework)))) if rw > target_rework else now
        rows.append({"volume_multiplier": f, "annotators_needed": now,
                     "annotators_if_rework_at_target": at_target,
                     "assumptions": f"{current_utilisation:.0%} utilisation today, {target_utilisation:.0%} target"})
    return pd.DataFrame(rows)
