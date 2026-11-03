-- SQLite schema for annotation operations data
DROP TABLE IF EXISTS annotations;
DROP TABLE IF EXISTS tasks;
DROP TABLE IF EXISTS annotators;

CREATE TABLE annotators (
    annotator_id  TEXT PRIMARY KEY,
    team          TEXT NOT NULL,
    tenure_weeks  INTEGER
);

CREATE TABLE tasks (
    task_id       TEXT PRIMARY KEY,
    project       TEXT NOT NULL,
    task_type     TEXT,
    difficulty    TEXT CHECK (difficulty IN ('easy','medium','hard')),
    true_label    TEXT,
    is_gold       INTEGER NOT NULL DEFAULT 0,
    created_date  TEXT NOT NULL,
    gold_label    TEXT
);

CREATE TABLE annotations (
    annotation_id  INTEGER PRIMARY KEY,
    task_id        TEXT NOT NULL REFERENCES tasks(task_id),
    annotator_id   TEXT NOT NULL REFERENCES annotators(annotator_id),
    label          TEXT NOT NULL,
    started_at     TEXT,
    submitted_at   TEXT,
    duration_sec   REAL,
    review_outcome TEXT CHECK (review_outcome IN ('accepted','rework') OR review_outcome IS NULL)
);

CREATE INDEX idx_ann_task ON annotations(task_id);
CREATE INDEX idx_ann_annotator ON annotations(annotator_id);
