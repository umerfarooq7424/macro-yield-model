# Stage 2 validation - 15 October 2026

The complete offline pipeline was rerun successfully from bundled snapshots using Python 3.12. Exact dependency versions are in tested_versions.json and requirements-tested.txt; requirements.txt permits compatible newer releases.

- 95 quarter-end macro vintage bundles validated; 95-quarter long panel and 62-quarter extension panel reconstructed.
- All 2Y, 5Y and 10Y change and next-quarter target values reconcile between SQLite and Python.
- Ten sample/specification combinations estimated across three maturities.
- Expanding-window runs assert that training target dates do not exceed forecast origins.
- Seven integrity tests passed: target alignment, missing-feature calendar preservation, calendar gap rejection, future feature rejection, SQL future-vintage exclusion, within-vintage GDP rebasing and wrong-vintage header rejection.
- Updated last-12-quarter comparison uses calendar quarters; matched-date comparison is included for cross-specification evaluation.
- Six-page PDF rendered and visually checked; includes real output tables and charts.

See stage2_run.log for the successful analysis and test log. Tests verify implementation safeguards, not causal identification or investment suitability. The baseline does not beat the no-change benchmark on full-evaluation RMSE. Current SPF workbook corrections and current yield history prevent a fully vintage-pure backtest. Historical Stage 1 synthetic examples are clearly labeled and separate.
