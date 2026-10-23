-- Vintage-aware source store. ISO dates; value units are declared per series.
CREATE TABLE IF NOT EXISTS observations (
    series TEXT NOT NULL,
    period_end TEXT NOT NULL,
    available_date TEXT NOT NULL,
    vintage_date TEXT NOT NULL,
    value REAL NOT NULL,
    units TEXT NOT NULL,
    source_url TEXT NOT NULL,
    PRIMARY KEY (series, period_end, available_date, vintage_date)
);
CREATE TABLE IF NOT EXISTS forecast_origins (
    origin_date TEXT PRIMARY KEY
);
-- Same period can have multiple vintages. Choose only versions available then.
CREATE VIEW IF NOT EXISTS observations_asof AS
WITH eligible AS (
    SELECT f.origin_date, o.*,
           ROW_NUMBER() OVER (
               PARTITION BY f.origin_date, o.series, o.period_end
               ORDER BY o.available_date DESC, o.vintage_date DESC
           ) AS vintage_rank
    FROM forecast_origins f JOIN observations o
      ON o.available_date <= f.origin_date
     AND o.vintage_date <= f.origin_date
)
SELECT origin_date, series, period_end, available_date, vintage_date,
       value, units, source_url
FROM eligible WHERE vintage_rank = 1;

-- Do not use period_end as release date. Survey target dates may be in the future.
-- The feature layer must additionally select the correct period/forecast target.
