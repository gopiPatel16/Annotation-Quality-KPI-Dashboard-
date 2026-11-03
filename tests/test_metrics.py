import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aqkpi import generate_data, metrics, sql_layer  # noqa: E402


def _df(rows):
    return pd.DataFrame(rows, columns=["task_id", "annotator_id", "label"])


def test_cohen_kappa_perfect_and_chance():
    assert metrics.cohen_kappa(list("aabb"), list("aabb")) == 1.0
    assert abs(metrics.cohen_kappa(list("aabb"), list("abab"))) < 1e-9


def test_fleiss_and_alpha_perfect_agreement():
    rows = [(t, a, l) for t, l in [("1", "x"), ("2", "y"), ("3", "x")] for a in "ABC"]
    df = _df(rows)
    assert metrics.fleiss_kappa(df) == 1.0
    assert abs(metrics.krippendorff_alpha(df) - 1.0) < 1e-9


def test_fleiss_known_value():
    # Wikipedia Fleiss kappa example: 10 subjects, 14 raters, 5 categories -> 0.210
    counts = [[0,0,0,0,14],[0,2,6,4,2],[0,0,3,5,6],[0,3,9,2,0],[2,2,8,1,1],
              [7,7,0,0,0],[3,2,6,3,0],[2,5,3,2,2],[6,5,2,1,0],[0,2,2,3,7]]
    rows = [(i, f"r{j}-{c}", f"c{c}") for i, row in enumerate(counts) for c, n in enumerate(row) for j in range(n)]
    assert abs(metrics.fleiss_kappa(_df(rows)) - 0.210) < 0.002


def test_pipeline_sql_matches_pandas(tmp_path):
    ann, tasks, notes = generate_data.generate(n_tasks=300, n_annotators=10, seed=1)
    raw = tmp_path / "raw"
    raw.mkdir()
    ann.drop(columns=["skill_hidden"]).to_csv(raw / "annotators.csv", index=False)
    tasks.to_csv(raw / "tasks.csv", index=False)
    notes.to_csv(raw / "annotations.csv", index=False)
    conn = sql_layer.build_db(raw, tmp_path / "t.db")
    res = sql_layer.run_all(conn)
    df = metrics.enrich(notes, tasks, ann.drop(columns=["skill_hidden"]))
    sql_acc = res["annotator_accuracy"].set_index("annotator_id")["accuracy"].sort_index()
    pd_acc = df.groupby("annotator_id")["correct_vs_gold"].mean().dropna().sort_index()
    assert np.allclose(sql_acc.values, pd_acc.values, atol=1e-4)
    assert set(res) >= {"weekly_trend", "project_kpis", "annotator_rank_in_team"}


def test_agreement_in_valid_range():
    ann, tasks, notes = generate_data.generate(n_tasks=300, n_annotators=10, seed=2)
    df = metrics.enrich(notes, tasks, ann.drop(columns=["skill_hidden"]))
    k = metrics.fleiss_kappa(df)
    assert 0.3 < k < 1.0
