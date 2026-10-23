"""Estimate prespecified real-data models, diagnostics and conditional scenarios.
Run build_panel.py first. Outputs are associations, not identified causal effects.
"""
from pathlib import Path
import json, sqlite3
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.diagnostic import acorr_ljungbox, het_breuschpagan
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from model import run, fit, make_design, validate_panel, SPECS, MATURITIES

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'outputs'/'stage2'

def summarize_predictions(predictions, group, spec):
    last=pd.Period(max(predictions.target_date),freq='Q')
    holdout=set(str(q.end_time.date()) for q in pd.period_range(last-11,last,freq='Q'))
    rows=[]
    for label,part in [('all_evaluation',predictions),
        ('last_12_quarters',predictions[predictions.target_date.isin(holdout)]),
        ('earlier_evaluation',predictions[~predictions.target_date.isin(holdout)])]:
        if part.empty:continue
        for m,g in part.groupby('maturity'):
            for name in ['model_bp','ar_bp','random_walk_bp']:
                e=g.actual_bp-g[name]
                rows.append(dict(sample=group,spec=spec,period=label,maturity=m,benchmark=name,
                    n=len(g),first_target=g.target_date.min(),last_target=g.target_date.max(),
                    rmse_bp=float(np.sqrt(np.mean(e**2))),mae_bp=float(np.mean(np.abs(e)))))
    return rows

def explanatory(panel,features):
    d=panel[['quarter_end']+features].copy()
    for m in MATURITIES:
        d[f'd{m}']=panel[f'y{m}'].diff()*100
        d[f'lag{m}']=d[f'd{m}'].shift(1)
    return d.dropna().reset_index(drop=True)

def diagnostics(panel,features,sample,spec):
    rows=[]
    for m in MATURITIES:
        d=make_design(panel,m,features);r=fit(d,features)
        x=sm.add_constant(d[['lag_change_bp']+features],has_constant='add')
        lb=acorr_ljungbox(r.resid,lags=[4],return_df=True)
        bp=het_breuschpagan(r.resid,x)
        rows.append(dict(sample=sample,spec=spec,maturity=m,n=len(d),
             ljung_box_lag4_p=float(lb.lb_pvalue.iloc[0]),breusch_pagan_p=float(bp[1])))
        for j,c in enumerate(x.columns):
            if c=='const':continue
            rows.append(dict(sample=sample,spec=spec,maturity=m,variable=c,
                vif=float(variance_inflation_factor(x.to_numpy(),j)),
                adf_p=float(adfuller(x[c],maxlag=4,autolag='AIC')[1])))
    return rows

def circular_indices(n,rng,block=4):
    starts=rng.integers(0,n,size=int(np.ceil(n/block)))
    return np.concatenate([(s+np.arange(block))%n for s in starts])[:n]

def scenarios(panel,features,shifts,mode,replicates=1000):
    """Fixed-design residual block bootstrap, shared draws across maturities.
    Intervals are conditional mean contrasts; not structural or prediction bounds.
    """
    rng=np.random.default_rng(2031)
    designs=[];betas=[];resids=[];fitted=[];contrasts=[]
    descriptive=explanatory(panel,features) if mode=='same_quarter_association' else None
    for m in MATURITIES:
        if descriptive is None:
            d=make_design(panel,m,features)
            x=sm.add_constant(d[['lag_change_bp']+features],has_constant='add').to_numpy()
            y=d.target_change_bp.to_numpy()
        else:
            x=sm.add_constant(descriptive[[f'lag{m}']+features],has_constant='add').to_numpy()
            y=descriptive[f'd{m}'].to_numpy()
        b=np.linalg.lstsq(x,y,rcond=None)[0]
        c=np.array([0,0]+[shifts.get(f,0) for f in features])
        designs.append(x);betas.append(b);resids.append(y-x@b);fitted.append(x@b);contrasts.append(c)
    e=np.column_stack(resids);e-=e.mean(axis=0)
    draws=np.empty((replicates,3))
    for b in range(replicates):
        ix=circular_indices(len(e),rng)
        for j in range(3):
            estimate=np.linalg.lstsq(designs[j],fitted[j]+e[ix,j],rcond=None)[0]
            draws[b,j]=contrasts[j]@estimate
    point=np.array([c@b for c,b in zip(contrasts,betas)])
    rows=[]
    for j,m in enumerate(MATURITIES):
        rows.append(dict(maturity=str(m),effect_bp=float(point[j]),
            lower90_bp=float(np.quantile(draws[:,j],.05)),upper90_bp=float(np.quantile(draws[:,j],.95))))
    slope=draws[:,2]-draws[:,0]
    rows.append(dict(maturity='2s10s',effect_bp=float(point[2]-point[0]),
        lower90_bp=float(np.quantile(slope,.05)),upper90_bp=float(np.quantile(slope,.95))))
    return rows

def latest_forecast(panel):
    """Preselected macro baseline; origin remains 2026-09-30, not today."""
    features=SPECS['macro'];last=panel.iloc[-1];rws=[]
    for m in MATURITIES:
        d=make_design(panel,m,features);result=fit(d,features)
        lag=100*(panel[f'y{m}'].iloc[-1]-panel[f'y{m}'].iloc[-2])
        x=np.array([1,lag]+[last[f] for f in features])
        pred=float(x@result.params)
        # Forecast uncertainty dominated by residual variance; this simple
        # normal approximation is reported separately from scenario contrasts.
        variance=float(x@result.cov_params().to_numpy()@x + np.var(result.resid,ddof=len(x)))
        half=1.6448536269514722*np.sqrt(max(variance,0))
        rws.append(dict(maturity=m,origin_date=str(last.quarter_end.date()),target_date='2026-12-31',
            origin_yield_pct=float(last[f'y{m}']),predicted_change_bp=pred,
            predicted_yield_pct=float(last[f'y{m}']+pred/100),
            approximate_lower90_pct=float(last[f'y{m}']+(pred-half)/100),
            approximate_upper90_pct=float(last[f'y{m}']+(pred+half)/100)))
    return pd.DataFrame(rws)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    full=pd.read_csv(ROOT/'data/quarterly_panel.csv')
    common=pd.read_csv(ROOT/'data/quarterly_panel_common.csv')
    metrics=[];diags=[];effects=[];allpred=[];coefficients=[]
    for group,panel,specs,min_train in [
        ('long_sample',full,['ar','macro','labor','policy'],60),
        ('common_vintage_sample',common,list(SPECS),40)]:
        for spec in specs:
            fs=SPECS[spec]
            panel=validate_panel(panel,fs,allow_missing_features=True)
            dest=OUT/group/spec
            pred=run(panel,fs,dest,min_train=min_train,allow_missing_features=True)
            metrics+=summarize_predictions(pred,group,spec)
            pred['sample']=group;pred['spec']=spec;allpred.append(pred)
            diags+=diagnostics(panel,fs,group,spec)
            coeff=pd.read_csv(dest/'coefficients.csv');coeff['sample']=group;coeff['spec']=spec
            coefficients.append(coeff)
            print('Estimated',group,spec,flush=True)
    full=validate_panel(full,SPECS['macro'])
    common=validate_panel(common,sorted(set(sum(SPECS.values(),[]))),allow_missing_features=True)
    scenario_specs=[
        ('Growth outlook +0.5 pp',full,'long_sample','macro',{'growth_revision_pp':.5}),
        ('Inflation outlook +0.5 pp',full,'long_sample','macro',{'inflation_revision_pp':.5}),
        ('Borrowing flow +1% of GDP',common,'common_vintage_sample','supply',{'borrowing_flow_pct_gdp':1}),
        ('Fed holdings flow -1% of GDP',common,'common_vintage_sample','supply',{'fed_treasury_flow_pct_gdp':-1}),
        ('Brent price +10%',common,'common_vintage_sample','oil',{'oil_log_change_pct':100*np.log(1.1)}),
        ('Unemployment change +0.5 pp',full,'long_sample','labor',{'unemployment_change_pp':.5})]
    for label,p,group,spec,shifts in scenario_specs:
        for mode in ['next_quarter_predictive','same_quarter_association']:
            for row in scenarios(p,SPECS[spec],shifts,mode):
                effects.append(dict(scenario=label,sample=group,spec=spec,mode=mode,**row))
    metrics=pd.DataFrame(metrics);metrics.to_csv(OUT/'forecast_comparison.csv',index=False)
    combined=pd.concat(allpred)
    combined.to_csv(OUT/'all_predictions.csv',index=False)
    matched=[]
    for group,g in combined.groupby('sample'):
        sets=[set(part.target_date) for _,part in g.groupby('spec')]
        dates=set.intersection(*sets)
        for spec,part in g.groupby('spec'):
            matched+=summarize_predictions(part[part.target_date.isin(dates)],group,spec)
    pd.DataFrame(matched).to_csv(OUT/'matched_date_comparison.csv',index=False)
    pd.concat(coefficients).to_csv(OUT/'all_coefficients.csv',index=False)
    pd.DataFrame(diags).to_csv(OUT/'diagnostics.csv',index=False)
    pd.DataFrame(effects).to_csv(OUT/'conditional_scenarios.csv',index=False)
    forecast=latest_forecast(full);forecast.to_csv(OUT/'quarter_end_forecast.csv',index=False)
    # Predeclared sensitivity: exclude the extreme pandemic target quarters.
    sensitivity=[]
    for m in MATURITIES:
        d=make_design(full,m,SPECS['macro'])
        for name,subset in [('all',d),('exclude_2020_targets',d[~d.target_date.dt.year.eq(2020)]),
                            ('latest_60',d.tail(60))]:
            r=fit(subset,SPECS['macro'])
            for term in ['growth_revision_pp','inflation_revision_pp']:
                sensitivity.append(dict(maturity=m,sample=name,term=term,n=len(subset),coefficient=float(r.params[term])))
    pd.DataFrame(sensitivity).to_csv(OUT/'coefficient_stability.csv',index=False)
    # SQL stores all real estimates for query practice.
    with sqlite3.connect(ROOT/'data/macro_yield.sqlite') as con:
        metrics.to_sql('forecast_comparison',con,if_exists='replace',index=False)
        pd.DataFrame(effects).to_sql('conditional_scenarios',con,if_exists='replace',index=False)
        pd.concat(allpred).to_sql('forecast_predictions',con,if_exists='replace',index=False)
    fig,axes=plt.subplots(1,2,figsize=(12,4.8),layout='constrained')
    for ax,period,title in zip(axes,['all_evaluation','last_12_quarters'],
        ['All expanding-window forecasts','Last 12 target quarters']):
        sub=metrics[(metrics['sample']=='long_sample')&(metrics.spec=='macro')&(metrics.period==period)]
        for j,(name,label,color) in enumerate([('random_walk_bp','No change','#94a3b8'),('ar_bp','AR only','#64748b'),('model_bp','GDP + inflation','#0f766e')]):
            v=sub[sub.benchmark.eq(name)].sort_values('maturity')
            ax.bar(np.arange(3)+(j-1)*.24,v.rmse_bp,width=.24,label=label,color=color)
        ax.set(xticks=range(3),xticklabels=['2Y','5Y','10Y'],ylabel='Forecast RMSE (bp)',title=title)
        ax.spines[['top','right']].set_visible(False)
    axes[0].legend(frameon=False,fontsize=9)
    fig.suptitle('Does the macro model beat simple forecasts? Lower is better',fontweight='bold')
    fig.savefig(OUT/'forecast_comparison.png',dpi=180);plt.close(fig)
    # Conditional associations only, not forecast performance or causal multipliers.
    e=pd.DataFrame(effects);e=e[e['mode'].eq('same_quarter_association')&e.maturity.eq('10')].copy()
    fig,ax=plt.subplots(figsize=(10,5.6),layout='constrained')
    ax.errorbar(e.effect_bp,np.arange(len(e)),xerr=np.vstack([np.maximum(e.effect_bp-e.lower90_bp,0),np.maximum(e.upper90_bp-e.effect_bp,0)]),fmt='o',color='#0f766e',capsize=4)
    ax.set(yticks=np.arange(len(e)),yticklabels=e.scenario,xlabel='Conditional association with 10Y yield change (bp)')
    ax.axvline(0,color='#94a3b8',lw=1);ax.invert_yaxis();ax.spines[['top','right']].set_visible(False)
    ax.set_title('Estimated associations are uncertain',loc='left',fontweight='bold')
    fig.supxlabel('90% conditional-mean bootstrap intervals. Different specifications/samples. Not causal effects; do not add rows.',fontsize=8)
    fig.savefig(OUT/'conditional_associations.png',dpi=180);plt.close(fig)
    print(metrics[(metrics['sample']=='long_sample')&(metrics.spec=='macro')].to_string(index=False))
    print('LATEST QUARTER-ORIGIN FORECAST\n',forecast.to_string(index=False))

if __name__=='__main__':main()
