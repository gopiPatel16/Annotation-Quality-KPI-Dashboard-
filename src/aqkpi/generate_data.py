"""Generate a realistic synthetic human-annotation dataset.

Each task is labelled by 3 distinct annotators (overlap -> inter-annotator
agreement). A subset of tasks carries a gold label (-> accuracy). Annotator
skill, task difficulty, tenure/learning curve and speed all influence the
outcome so that KPIs show meaningful variation.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

PROJECTS = {
    "Sentiment":    {"labels": ["positive", "neutral", "negative"], "base_sec": 25, "type": "text"},
    "Intent":       {"labels": ["billing", "tech_support", "sales", "cancel", "other"], "base_sec": 40, "type": "text"},
    "ImageClass":   {"labels": ["vehicle", "person", "animal", "object"], "base_sec": 18, "type": "image"},
}
DIFFICULTY = {"easy": 0.0, "medium": 0.08, "hard": 0.22}  # accuracy penalty
START = pd.Timestamp("2026-08-03")  # Monday
WEEKS = 12
OVERLAP = 3


def make_annotators(n: int, rng: np.random.Generator) -> pd.DataFrame:
    teams = ["Alpha", "Beta", "Gamma"]
    df = pd.DataFrame({
        "annotator_id": [f"A{i:03d}" for i in range(1, n + 1)],
        "team": rng.choice(teams, n),
        "tenure_weeks": rng.integers(1, 52, n),
        "skill": np.clip(rng.normal(0.90, 0.05, n), 0.65, 0.99),
        "speed": np.clip(rng.normal(1.0, 0.2, n), 0.55, 1.6),
    })
    # a few deliberately weak performers so the dashboard has something to flag
    weak = rng.choice(n, 3, replace=False)
    df.loc[weak, "skill"] = rng.uniform(0.66, 0.74, 3)
    return df


def generate(n_tasks: int = 2400, n_annotators: int = 24, seed: int = 42):
    rng = np.random.default_rng(seed)
    annotators = make_annotators(n_annotators, rng)
    proj_names = list(PROJECTS)

    task_rows = []
    for t in range(n_tasks):
        p = proj_names[t % len(proj_names)]
        labels = PROJECTS[p]["labels"]
        week = int(rng.integers(0, WEEKS))
        day = week * 7 + int(rng.integers(0, 5))
        task_rows.append({
            "task_id": f"T{t + 1:05d}",
            "project": p,
            "task_type": PROJECTS[p]["type"],
            "difficulty": rng.choice(list(DIFFICULTY), p=[0.5, 0.33, 0.17]),
            "true_label": rng.choice(labels),
            "is_gold": bool(rng.random() < 0.15),
            "created_date": START + pd.Timedelta(days=day),
        })
    tasks = pd.DataFrame(task_rows)
    tasks["gold_label"] = np.where(tasks["is_gold"], tasks["true_label"], None)

    skill = annotators.set_index("annotator_id")["skill"]
    speed = annotators.set_index("annotator_id")["speed"]
    tenure = annotators.set_index("annotator_id")["tenure_weeks"]
    ids = annotators["annotator_id"].to_numpy()

    rows = []
    aid = 0
    for r in tasks.itertuples():
        labels = PROJECTS[r.project]["labels"]
        chosen = rng.choice(ids, OVERLAP, replace=False)
        week_idx = (r.created_date - START).days // 7
        for a in chosen:
            # learning curve: +1% accuracy per ~10 weeks of tenure + weekly drift
            p_ok = skill[a] + min(tenure[a] + week_idx, 60) * 0.0008 - DIFFICULTY[r.difficulty]
            p_ok = float(np.clip(p_ok, 0.25, 0.995))
            if rng.random() < p_ok:
                label = r.true_label
            else:
                label = rng.choice([l for l in labels if l != r.true_label])
            base = PROJECTS[r.project]["base_sec"] * (1 + 0.6 * list(DIFFICULTY).index(r.difficulty))
            dur = float(rng.lognormal(np.log(base / speed[a]), 0.35))
            start = r.created_date + pd.Timedelta(hours=int(rng.integers(8, 17)),
                                                  minutes=int(rng.integers(0, 60)),
                                                  seconds=int(rng.integers(0, 60)))
            reviewed = rng.random() < 0.25
            outcome = None
            if reviewed:
                wrong = label != r.true_label
                outcome = "rework" if (wrong and rng.random() < 0.9) or (not wrong and rng.random() < 0.03) else "accepted"
            aid += 1
            rows.append({
                "annotation_id": aid,
                "task_id": r.task_id,
                "annotator_id": a,
                "label": label,
                "started_at": start,
                "submitted_at": start + pd.Timedelta(seconds=dur),
                "duration_sec": round(dur, 1),
                "review_outcome": outcome,
            })
    annotations = pd.DataFrame(rows)
    return annotators.drop(columns=["skill", "speed"]).assign(
        skill_hidden=annotators["skill"].round(3)), tasks, annotations


if __name__ == "__main__":
    import sys
    from pathlib import Path
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "data/raw")
    out.mkdir(parents=True, exist_ok=True)
    a, t, n = generate()
    a.drop(columns=["skill_hidden"]).to_csv(out / "annotators.csv", index=False)
    t.to_csv(out / "tasks.csv", index=False)
    n.to_csv(out / "annotations.csv", index=False)
    print(f"wrote {len(a)} annotators, {len(t)} tasks, {len(n)} annotations to {out}")
