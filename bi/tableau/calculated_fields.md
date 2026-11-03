```
// Accuracy
SUM(IF [is_gold] THEN [is_correct] END) / COUNT(IF [is_gold] THEN [annotation_id] END)

// Throughput per Hour
COUNTD([annotation_id]) / (SUM([duration_sec]) / 3600)

// Rework Rate
SUM(IF NOT ISNULL([is_rework]) THEN [is_rework] END) / COUNT([is_rework])

// Avg Handle Time (s)
AVG([duration_sec])

// Accuracy Status
IF [Accuracy] >= [Accuracy Target] THEN "On target" ELSE "Below target" END

// Week
DATETRUNC('week', [created_date])
```
Fleiss' kappa / Krippendorff's alpha are pre-computed in Python (`project_agreement.csv`).
