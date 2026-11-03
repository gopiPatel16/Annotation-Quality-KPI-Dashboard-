-- Named KPI queries. Each block starts with "-- name: <query_name>" and is
-- executed by src/aqkpi/sql_layer.py (also paste-able into any SQL client).

-- name: annotator_accuracy
-- Accuracy vs gold-standard labels per annotator.
SELECT a.annotator_id,
       a.team,
       COUNT(*)                                             AS gold_samples,
       ROUND(AVG(CASE WHEN n.label = t.gold_label THEN 1.0 ELSE 0 END), 4) AS accuracy
FROM annotations n
JOIN tasks t      ON t.task_id = n.task_id AND t.is_gold = 1
JOIN annotators a ON a.annotator_id = n.annotator_id
GROUP BY a.annotator_id, a.team
ORDER BY accuracy;

-- name: throughput_by_annotator
-- Annotations per active hour and average handle time.
SELECT annotator_id,
       COUNT(*)                                   AS annotations,
       ROUND(AVG(duration_sec), 1)                AS avg_handle_time_sec,
       ROUND(COUNT(*) / (SUM(duration_sec) / 3600.0), 1) AS throughput_per_hour
FROM annotations
GROUP BY annotator_id
ORDER BY throughput_per_hour DESC;

-- name: weekly_trend
-- Weekly volume, accuracy, rework (week = Monday of the task creation week).
SELECT DATE(t.created_date, 'weekday 0', '-6 days')            AS week_start,
       COUNT(*)                                                 AS annotations,
       ROUND(AVG(CASE WHEN t.is_gold = 1 THEN (n.label = t.gold_label) END), 4) AS accuracy,
       ROUND(AVG(CASE WHEN n.review_outcome IS NOT NULL
                      THEN (n.review_outcome = 'rework') END), 4)               AS rework_rate,
       ROUND(AVG(n.duration_sec), 1)                            AS avg_handle_time_sec
FROM annotations n JOIN tasks t ON t.task_id = n.task_id
GROUP BY week_start
ORDER BY week_start;

-- name: project_kpis
SELECT t.project,
       COUNT(*)                                   AS annotations,
       COUNT(DISTINCT t.task_id)                  AS tasks,
       ROUND(AVG(CASE WHEN t.is_gold = 1 THEN (n.label = t.gold_label) END), 4) AS accuracy,
       ROUND(AVG(CASE WHEN n.review_outcome IS NOT NULL
                      THEN (n.review_outcome = 'rework') END), 4)               AS rework_rate,
       ROUND(COUNT(*) / (SUM(n.duration_sec) / 3600.0), 1)                       AS throughput_per_hour
FROM annotations n JOIN tasks t ON t.task_id = n.task_id
GROUP BY t.project;

-- name: pairwise_percent_agreement
-- Raw (uncorrected) agreement for every annotator pair on shared tasks.
SELECT x.annotator_id AS annotator_a,
       y.annotator_id AS annotator_b,
       COUNT(*)       AS shared_tasks,
       ROUND(AVG(x.label = y.label), 4) AS percent_agreement
FROM annotations x
JOIN annotations y ON x.task_id = y.task_id AND x.annotator_id < y.annotator_id
GROUP BY x.annotator_id, y.annotator_id
HAVING COUNT(*) >= 5
ORDER BY percent_agreement;

-- name: task_full_agreement_rate
-- Share of tasks where all annotators chose the same label, by project.
WITH per_task AS (
    SELECT t.project, n.task_id, COUNT(DISTINCT n.label) AS distinct_labels
    FROM annotations n JOIN tasks t ON t.task_id = n.task_id
    GROUP BY t.project, n.task_id
)
SELECT project,
       COUNT(*)                                             AS tasks,
       ROUND(AVG(CASE WHEN distinct_labels = 1 THEN 1.0 ELSE 0 END), 4) AS unanimous_rate
FROM per_task GROUP BY project;

-- name: annotator_rank_in_team
-- Window function: rank annotators by accuracy within their team.
WITH acc AS (
    SELECT a.annotator_id, a.team,
           AVG(CASE WHEN n.label = t.gold_label THEN 1.0 ELSE 0 END) AS accuracy
    FROM annotations n
    JOIN tasks t ON t.task_id = n.task_id AND t.is_gold = 1
    JOIN annotators a ON a.annotator_id = n.annotator_id
    GROUP BY a.annotator_id, a.team
)
SELECT annotator_id, team, ROUND(accuracy, 4) AS accuracy,
       RANK() OVER (PARTITION BY team ORDER BY accuracy DESC) AS team_rank
FROM acc
ORDER BY team, team_rank;

-- name: error_by_difficulty
SELECT t.difficulty,
       COUNT(*) AS gold_samples,
       ROUND(1 - AVG(CASE WHEN n.label = t.gold_label THEN 1.0 ELSE 0 END), 4) AS error_rate
FROM annotations n JOIN tasks t ON t.task_id = n.task_id AND t.is_gold = 1
GROUP BY t.difficulty;
