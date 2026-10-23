-- Open data/macro_yield.sqlite in SQLite or DB Browser for SQLite.
SELECT maturity, benchmark, n, ROUND(rmse_bp,2) AS rmse_bp
FROM forecast_comparison
WHERE sample='long_sample' AND spec='macro' AND period='all_evaluation'
ORDER BY maturity, benchmark;

SELECT scenario, maturity, ROUND(effect_bp,2) AS association_bp,
 ROUND(lower90_bp,2) AS lower90, ROUND(upper90_bp,2) AS upper90
FROM conditional_scenarios WHERE mode='same_quarter_association';

SELECT quarter_end, change_y2_bp, next_change_y2_bp,
 change_y10_bp, next_change_y10_bp
FROM modeling_targets ORDER BY quarter_end DESC LIMIT 8;
