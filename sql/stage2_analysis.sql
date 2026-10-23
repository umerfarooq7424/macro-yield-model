DROP VIEW IF EXISTS modeling_targets;
CREATE VIEW modeling_targets AS
WITH changes AS (
 SELECT *,
  100.0*(y2-LAG(y2) OVER (ORDER BY quarter_end)) AS change_y2_bp,
  100.0*(y5-LAG(y5) OVER (ORDER BY quarter_end)) AS change_y5_bp,
  100.0*(y10-LAG(y10) OVER (ORDER BY quarter_end)) AS change_y10_bp
 FROM quarterly_features
)
SELECT *,
 LEAD(change_y2_bp) OVER (ORDER BY quarter_end) AS next_change_y2_bp,
 LEAD(change_y5_bp) OVER (ORDER BY quarter_end) AS next_change_y5_bp,
 LEAD(change_y10_bp) OVER (ORDER BY quarter_end) AS next_change_y10_bp
FROM changes;

-- Run after model construction; these are KNOWN-BY vintages, not release dates.
-- SELECT * FROM quarterly_features ORDER BY quarter_end DESC LIMIT 4;
-- SELECT * FROM modeling_targets ORDER BY quarter_end DESC LIMIT 4;
