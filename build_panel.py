"""Build quarterly features from survey vintages and ALFRED as-of bundles.
No macro series is forward-filled. All joins and source periods are auditable.
"""
from pathlib import Path
from zipfile import ZipFile
import re, json, sqlite3, warnings
import numpy as np
import pandas as pd
from features import growth_revision_pp
from download_vintages import SERIES, validate

ROOT=Path(__file__).resolve().parent
RAW=ROOT/'data'/'raw'

def release_dates():
    rows={}; year=None
    for line in (RAW/'spf_release_dates.txt').read_text().splitlines():
        match=re.match(r'^\s*(?:(\d{4})\s+)?Q([1-4])\s+',line)
        if not match: continue
        if match[1]: year=int(match[1])
        ds=re.findall(r'\d{1,2}/\d{1,2}/\d{2,4}',line)
        if year and len(ds)>=2:
            rows[pd.Period(f'{year}Q{match[2]}',freq='Q')]=pd.to_datetime(ds[-1],format='%m/%d/%y')
    return rows

def survey_frames():
    result={}
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore',message='Cannot parse header or footer')
        for name in ['RGDP','CPI','TBILL']:
            d=pd.read_excel(RAW/'spf_medianLevel.xlsx',sheet_name=name)
            d.index=pd.PeriodIndex([f'{int(y)}Q{int(q)}' for y,q in zip(d.YEAR,d.QUARTER)],freq='Q')
            d=d.replace('#N/A',np.nan)
            for c in d.columns: d[c]=pd.to_numeric(d[c],errors='coerce')
            if d.index.has_duplicates: raise ValueError('Duplicate survey quarter')
            result[name]=d
    return result

def vintage(date):
    path=RAW/'alfred'/f'vintage_{date}.zip'
    validate(path.read_bytes(),date)
    series={}
    with ZipFile(path) as z:
        for name in z.namelist():
            if not name.endswith('.csv'):continue
            d=pd.read_csv(z.open(name),na_values=['.'])
            d['date']=pd.to_datetime(d.iloc[:,0])
            for s in SERIES:
                col=s+'_'+date.replace('-','')
                if col in d:
                    v=pd.to_numeric(d[col],errors='raise')
                    series[s]=pd.Series(v.to_numpy(),index=d.date).dropna().sort_index()
    for s in SERIES:
        if s not in series:series[s]=pd.Series(dtype=float,index=pd.DatetimeIndex([]))
        if (series[s].index>pd.Timestamp(date)).any():
            raise ValueError(f'Observation dated after vintage origin: {s} {date}')
    return series

def build():
    releases=release_dates(); surveys=survey_frames()
    yields=pd.read_csv(RAW/'fred_yields_2026-10-14.csv',na_values=['.'])
    yields['date']=pd.to_datetime(yields.iloc[:,0])
    yields=yields.loc[yields.date.between('2000-01-01','2026-09-30')].dropna(subset=['DGS2','DGS5','DGS10'])
    yields['quarter']=yields.date.dt.to_period('Q')
    yq=yields.sort_values('date').groupby('quarter').tail(1).set_index('quarter')
    rows=[]; audits=[]; raw_rows=[]
    for quarter in pd.period_range('2003Q1','2026Q3',freq='Q'):
        end=quarter.end_time.normalize(); date=end.strftime('%Y-%m-%d')
        row={'quarter_end':date,'yield_observation_date':yq.loc[quarter,'date'].strftime('%Y-%m-%d')}
        for m in [2,5,10]:row[f'y{m}']=float(yq.loc[quarter,f'DGS{m}'])
        if releases[quarter]>end:raise ValueError('Survey not available by origin')
        rg=surveys['RGDP']; cp=surveys['CPI']; tb=surveys['TBILL']
        row['growth_revision_pp']=growth_revision_pp(rg.loc[quarter,'RGDP2'],rg.loc[quarter,'RGDP3'],rg.loc[quarter-1,'RGDP3'],rg.loc[quarter-1,'RGDP4'])
        row['inflation_revision_pp']=float(cp.loc[quarter,'CPI3']-cp.loc[quarter-1,'CPI4'])
        row['policy_revision_pp']=float(tb.loc[quarter,'TBILL3']-tb.loc[quarter-1,'TBILL4'])
        for name in ['growth_revision_pp','inflation_revision_pp','policy_revision_pp']:
            row[name+'_available_date']=releases[quarter].strftime('%Y-%m-%d')
        row['spf_target_quarter']=str(quarter+1)
        row['spf_growth_next_quarter_pct']=100*((rg.loc[quarter,'RGDP3']/rg.loc[quarter,'RGDP2'])**4-1)
        row['spf_cpi_next_quarter_pct']=cp.loc[quarter,'CPI3']
        source=vintage(date)
        for s,values in source.items():
            # Store recent periods sufficient to reproduce selected features.
            relevant=values.loc[values.index>=end-pd.DateOffset(years=3)]
            for obs,val in relevant.items():
                raw_rows.append((s,obs.strftime('%Y-%m-%d'),date,date,float(val)))
        # Supply: latest quarter for which debt endpoints, prior GDP and Fed
        # holdings endpoints are available in this origin's vintage.
        debt=source['FYGFDPUN'].copy()/1000.0
        debt.index=debt.index.to_period('Q')
        gdp=source['GDP'].copy();gdp.index=gdp.index.to_period('Q')
        fed=source['TREAST']/1000.0
        candidates=[]
        for p in debt.index:
            pe=p.end_time.normalize();prev=(p-1).end_time.normalize()
            f=fed.loc[fed.index.to_period('Q')==p]
            fp=fed.loc[fed.index.to_period('Q')==p-1]
            if p-1 in debt.index and p-1 in gdp.index and pe<=end and len(f) and len(fp):
                # Keep a near-quarter-end weekly observation, not a distant value.
                if (pe-f.index[-1]).days<=7 and (prev-fp.index[-1]).days<=7:
                    candidates.append((p,f,fp))
        if candidates:
            p,f,fp=candidates[-1]
            denominator=float(gdp.loc[p-1])
            row['borrowing_flow_pct_gdp']=100*(float(debt.loc[p])-float(debt.loc[p-1]))/denominator
            row['fed_treasury_flow_pct_gdp']=100*(float(f.iloc[-1])-float(fp.iloc[-1]))/denominator
            row['supply_reference_quarter']=str(p)
            row['supply_age_days']=(end-p.end_time.normalize()).days
            audits.append(dict(origin_date=date,feature='supply',reference_period=str(p),
                debt_billions=float(debt.loc[p]),prior_debt_billions=float(debt.loc[p-1]),
                fed_billions=float(f.iloc[-1]),prior_fed_billions=float(fp.iloc[-1]),
                nominal_gdp_denominator_billions=denominator,
                fed_observation_date=str(f.index[-1].date()),
                availability_basis='ALFRED origin-date vintage; exact publication date not inferred'))
        # Labor: latest six fully elapsed monthly observations known at origin.
        u=source['UNRATE']
        u=u.loc[(u.index.to_period('M').to_timestamp(how='end').normalize()<=end)]
        tail=u.tail(6)
        if len(tail)==6 and np.all(np.diff(tail.index.to_period('M').asi8)==1):
            row['unemployment_change_pp']=float(tail.iloc[3:].mean()-tail.iloc[:3].mean())
            row['labor_reference_last_month']=str(tail.index[-1].to_period('M'))
            audits.append(dict(origin_date=date,feature='labor',reference_period=row['labor_reference_last_month'],
                current_three_month_average=float(tail.iloc[3:].mean()),prior_three_month_average=float(tail.iloc[:3].mean()),
                availability_basis='ALFRED origin-date vintage'))
        # Oil: full PREVIOUS quarter vs the quarter before that. This deliberately
        # avoids using an incomplete current-quarter spot series at the origin.
        oil=source['DCOILBRENTEU'];pq=quarter-1
        a=oil.loc[oil.index.to_period('Q')==pq];b=oil.loc[oil.index.to_period('Q')==pq-1]
        if len(a)>=50 and len(b)>=50 and a.mean()>0 and b.mean()>0:
            row['oil_log_change_pct']=100*np.log(a.mean()/b.mean())
            row['oil_reference_quarter']=str(pq)
            audits.append(dict(origin_date=date,feature='oil',reference_period=str(pq),
                brent_quarter_mean=float(a.mean()),prior_brent_quarter_mean=float(b.mean()),
                availability_basis='ALFRED origin-date vintage; previous full quarter'))
        for feature in ['borrowing_flow_pct_gdp','fed_treasury_flow_pct_gdp','unemployment_change_pp','oil_log_change_pct']:
            # A known-by date verified by the vintage, NOT an invented release date.
            row[feature+'_available_date']=date if feature in row else None
        rows.append(row)
    panel=pd.DataFrame(rows)
    panel.to_csv(ROOT/'data'/'quarterly_panel_all.csv',index=False)
    pd.DataFrame(audits).to_csv(ROOT/'data'/'feature_audit.csv',index=False)
    features=['growth_revision_pp','inflation_revision_pp','policy_revision_pp',
              'borrowing_flow_pct_gdp','fed_treasury_flow_pct_gdp','unemployment_change_pp','oil_log_change_pct']
    common_features=[f for f in features if f!='unemployment_change_pp']
    valid=panel[common_features].notna().all(axis=1)
    if not valid.any():raise ValueError('No common feature panel')
    first=valid[valid].index[0]
    common=panel.loc[first:]
    if not common[common_features].notna().all().all():raise ValueError('Interior data gap: investigate, do not drop')
    common.to_csv(ROOT/'data'/'quarterly_panel_common.csv',index=False)
    panel.to_csv(ROOT/'data'/'quarterly_panel.csv',index=False)
    with sqlite3.connect(ROOT/'data'/'macro_yield.sqlite') as con:
        con.executescript((ROOT/'sql/schema.sql').read_text())
        # Dedicated origin-vintage table: 'known_by_date' is not 'first_release_date'.
        con.execute('DROP TABLE IF EXISTS macro_vintages')
        con.execute('CREATE TABLE macro_vintages(series TEXT, observation_date TEXT, known_by_date TEXT, vintage_date TEXT, value REAL, PRIMARY KEY(series,observation_date,vintage_date))')
        con.executemany('INSERT INTO macro_vintages VALUES (?,?,?,?,?)',raw_rows)
        panel.to_sql('quarterly_features',con,if_exists='replace',index=False)
        # Actual SQL window implementation for lag/target reconciliation.
        con.executescript((ROOT/'sql'/'stage2_analysis.sql').read_text())
        sql=pd.read_sql_query('SELECT * FROM modeling_targets ORDER BY quarter_end',con)
        for m in (2,5,10):
            py=panel[f'y{m}'].diff()*100
            if not np.allclose(sql[f'change_y{m}_bp'],py,equal_nan=True):raise AssertionError('SQL lag differs from Python')
            if not np.allclose(sql[f'next_change_y{m}_bp'],py.shift(-1),equal_nan=True):raise AssertionError('SQL target differs from Python')
    status={'primary_quarters':len(panel),'primary_start':panel.quarter_end.iloc[0],
            'common_quarters':len(common),'common_start':common.quarter_end.iloc[0],'end':common.quarter_end.iloc[-1],
            'excluded_leading_quarters':int(first),'sql_python_target_reconciliation':True,
            'missing_labor_origins':panel.loc[panel.unemployment_change_pp.isna(),'quarter_end'].tolist(),
            'vintage_bundles_checked':len(rows),
            'spf_note':'Historical survey expectations and actual release dates; current workbook incorporates errata, not a frozen original-file archive.',
            'availability_note':'Macro feature dates are verified known-by origin dates, not claimed first publication dates.',
            'oil_note':'Uses preceding full quarter, one quarter more lagged than original design.',
            'yield_note':'Current daily snapshot; any subsequent historical corrections not vintage-reconstructed.'}
    (ROOT/'outputs'/'panel_quality.json').write_text(json.dumps(status,indent=2))
    print(json.dumps(status,indent=2))
    print(common.tail(2)[['quarter_end']+features].to_string(index=False))
    return panel

if __name__=='__main__':build()
