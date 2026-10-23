"""Small, explicit transforms for the Stage 2 data pipeline.
Input scalars must be from the named survey vintages / matched financial periods.
"""
import math

def growth_revision_pp(current_rgdp2, current_rgdp3, prior_rgdp3, prior_rgdp4):
    values = [current_rgdp2, current_rgdp3, prior_rgdp3, prior_rgdp4]
    if any(not math.isfinite(x) or x <= 0 for x in values):
        raise ValueError('GDP levels must be finite and positive')
    return 100*((current_rgdp3/current_rgdp2)**4 - (prior_rgdp4/prior_rgdp3)**4)

def inflation_revision_pp(current_cpi3, prior_cpi4):
    if not all(math.isfinite(v) for v in [current_cpi3, prior_cpi4]):
        raise ValueError('Inflation forecasts must be finite')
    return current_cpi3-prior_cpi4

def balance_flow_pct_gdp(current_billions, previous_billions, prior_gdp_billions_saar):
    if not all(math.isfinite(v) for v in [current_billions, previous_billions, prior_gdp_billions_saar]):
        raise ValueError('All inputs must be finite')
    if prior_gdp_billions_saar <= 0:
        raise ValueError('GDP denominator must be positive')
    return 100*(current_billions-previous_billions)/prior_gdp_billions_saar
