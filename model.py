"""Model engine. Stage 2 includes a real macro panel and frozen input snapshots.

python model.py --demo       # synthetic software check, not market evidence
python model.py --input data/quarterly_panel.csv --spec macro

Quarter-end rows describe information available at that quarter-end.
Target is NEXT quarter's yield change in bp. Never use random train/test splits.
"""
from pathlib import Path
import argparse
import json
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.diagnostic import acorr_ljungbox

BASE = Path(__file__).resolve().parent
MATURITIES = [2, 5, 10]
SPECS = {
    'ar': [],
    'macro': ['growth_revision_pp', 'inflation_revision_pp'],
    'supply': ['growth_revision_pp', 'inflation_revision_pp',
               'borrowing_flow_pct_gdp', 'fed_treasury_flow_pct_gdp'],
    'oil': ['growth_revision_pp', 'inflation_revision_pp', 'oil_log_change_pct'],
    'labor': ['unemployment_change_pp', 'inflation_revision_pp'],
    'policy': ['growth_revision_pp', 'inflation_revision_pp', 'policy_revision_pp'],
}

def validate_panel(frame, features, allow_missing_features=False):
    frame = frame.copy()
    required = ['quarter_end'] + [f'y{m}' for m in MATURITIES]
    required += features + [f'{v}_available_date' for v in features]
    missing = set(required) - set(frame.columns)
    if missing:
        raise ValueError(f'Missing columns: {sorted(missing)}')
    frame['quarter_end'] = pd.to_datetime(frame['quarter_end'], errors='raise')
    frame = frame.sort_values('quarter_end').reset_index(drop=True)
    dates = pd.DatetimeIndex(frame.quarter_end)
    if dates.hasnans or dates.has_duplicates:
        raise ValueError('Missing or duplicate quarter-end dates')
    if not (dates == dates.to_period('Q').to_timestamp(how='end').normalize()).all():
        raise ValueError('Dates must be calendar quarter ends')
    if len(dates) < 2 or not np.all(np.diff(dates.to_period('Q').asi8) == 1):
        raise ValueError('Quarter grid must be consecutive; preserve missing rows')
    for name in [f'y{m}' for m in MATURITIES] + features:
        frame[name] = pd.to_numeric(frame[name], errors='raise')
        checked=frame[name].dropna() if allow_missing_features and name in features else frame[name]
        if not np.isfinite(checked).all():
            raise ValueError(f'Missing/nonfinite {name}; no automatic fill or imputation')
    for name in features:
        released = pd.to_datetime(frame[f'{name}_available_date'], errors='raise')
        required=frame[name].notna() if allow_missing_features else pd.Series(True,index=frame.index)
        if released[required].isna().any() or (released[required] > frame.quarter_end[required]).any():
            raise ValueError(f'Look-ahead or missing release date: {name}')
    return frame

def make_design(frame, maturity, features):
    """Compute lags before dropping rows; shift on a validated calendar grid."""
    d = frame[['quarter_end'] + features].copy()
    delta = frame[f'y{maturity}'].diff() * 100.0
    d['lag_change_bp'] = delta
    d['target_change_bp'] = delta.shift(-1)
    d['target_date'] = frame.quarter_end.shift(-1)
    return d.dropna().reset_index(drop=True)

def fit(design, features):
    columns = ['lag_change_bp'] + features
    x = sm.add_constant(design[columns], has_constant='add')
    if np.linalg.matrix_rank(x) != x.shape[1]:
        raise ValueError('Rank-deficient design: remove redundant inputs')
    return sm.OLS(design.target_change_bp, x).fit(
        cov_type='HAC', cov_kwds={'maxlags': 4, 'use_correction': True})

def run(frame, features, out, synthetic=False, min_train=60, allow_missing_features=False):
    frame = validate_panel(frame, features, allow_missing_features=allow_missing_features)
    out.mkdir(parents=True, exist_ok=True)
    coefficients, forecasts, diagnostics = [], [], []
    for maturity in MATURITIES:
        d = make_design(frame, maturity, features)
        if len(d) < min_train + 12:
            raise ValueError(f'Need at least {min_train} training quarters and 12 evaluation quarters')
        result = fit(d, features)
        ci = result.conf_int()
        for term in result.params.index:
            coefficients.append(dict(maturity=maturity, term=term,
                coefficient=float(result.params[term]), hac_se=float(result.bse[term]),
                ci_low=float(ci.loc[term, 0]), ci_high=float(ci.loc[term, 1])))
        columns = ['lag_change_bp'] + features
        for i in range(min_train, len(d)):
            train = d.iloc[:i]
            origin = d.iloc[i]
            # All training target dates must have occurred by this forecast origin.
            if train.target_date.max() > origin.quarter_end:
                raise AssertionError('Training target leaks past forecast origin')
            fitted = fit(train, features)
            x = sm.add_constant(d.iloc[[i]][columns], has_constant='add')
            prediction = float(fitted.predict(x).iloc[0])
            ar = fit(train, [])
            arx = sm.add_constant(d.iloc[[i]][['lag_change_bp']], has_constant='add')
            forecasts.append(dict(maturity=maturity,
                origin_date=str(origin.quarter_end.date()),
                target_date=str(origin.target_date.date()),
                actual_bp=float(origin.target_change_bp), model_bp=prediction,
                ar_bp=float(ar.predict(arx).iloc[0]), random_walk_bp=0.0))
        lb = acorr_ljungbox(result.resid, lags=[4], return_df=True)
        diagnostics.append(dict(maturity=maturity, n=len(d),
            adjusted_r_squared=float(result.rsquared_adj),
            ljung_box_lag4_p=float(lb.lb_pvalue.iloc[0]),
            raw_design_condition_number=float(result.condition_number)))
    predictions = pd.DataFrame(forecasts)
    metrics = []
    for maturity, g in predictions.groupby('maturity'):
        for name in ['model_bp', 'ar_bp', 'random_walk_bp']:
            error = g.actual_bp - g[name]
            metrics.append(dict(maturity=int(maturity), model=name,
                evaluation_quarters=len(g), rmse_bp=float(np.sqrt(np.mean(error**2))),
                mae_bp=float(np.mean(np.abs(error)))))
    # Reconcile the slope using matched endpoint forecasts, never an unrelated fit.
    p2 = predictions[predictions.maturity.eq(2)].set_index('target_date')
    p10 = predictions[predictions.maturity.eq(10)].set_index('target_date')
    slope = pd.DataFrame({'actual_2s10s_change_bp': p10.actual_bp-p2.actual_bp,
                          'predicted_2s10s_change_bp': p10.model_bp-p2.model_bp})
    pd.DataFrame(coefficients).to_csv(out/'coefficients.csv', index=False)
    predictions.to_csv(out/'expanding_window_predictions.csv', index=False)
    pd.DataFrame(metrics).to_csv(out/'forecast_metrics.csv', index=False)
    slope.to_csv(out/'slope_predictions.csv')
    (out/'diagnostics.json').write_text(json.dumps(diagnostics, indent=2))
    (out/'STATUS.txt').write_text(
        ('SYNTHETIC SOFTWARE DEMONSTRATION. NO MARKET INFERENCE.\n' if synthetic else
         'REAL INPUT DATA. See source manifests and panel_quality.json for provenance limits.\n') +
        'Lagged predictive associations, not causal effects or intraday forecasts.\n'
        'HAC intervals cover coefficients, not yield prediction intervals.\n'
        'Stage 2 forecasts and conditional scenarios are in outputs/stage2 when run_stage2.py is used.\n')
    return predictions

def synthetic_panel():
    rng = np.random.default_rng(17)
    n = 120
    dates = pd.period_range('1995Q1', periods=n, freq='Q').to_timestamp(how='end').normalize()
    d = pd.DataFrame({'quarter_end': dates})
    names = sorted(set(sum(SPECS.values(), [])))
    for name in names:
        d[name] = rng.normal(0, 0.4, n)
        d[f'{name}_available_date'] = dates - pd.Timedelta(days=10)
    common_noise = rng.normal(0, 15, n)
    for m in MATURITIES:
        move = np.zeros(n)
        for t in range(1, n):
            move[t] = (0.15*move[t-1] + (18-m)*d.growth_revision_pp.iloc[t-1]
                       + (10+m)*d.inflation_revision_pp.iloc[t-1]
                       + common_noise[t] + rng.normal(0, 6))
        d[f'y{m}'] = 3 + m/10 + np.cumsum(move)/100
    return d

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--demo', action='store_true')
    inputs.add_argument('--input', type=Path)
    parser.add_argument('--spec', choices=SPECS, default='macro')
    args = parser.parse_args()
    if args.demo:
        data = synthetic_panel()
        destination = BASE/'outputs'/'SYNTHETIC_DEMO'/args.spec
    else:
        data = pd.read_csv(args.input)
        destination = BASE/'outputs'/'user_data'/args.spec
    run(data, SPECS[args.spec], destination, synthetic=args.demo)
    print('Saved:', destination)
