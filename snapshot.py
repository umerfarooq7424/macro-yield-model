"""Build a dated yield reference from the bundled snapshot; optional --download.
This is not a macro regression. Downloaded FRED histories are not vintage archives.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from urllib.request import urlopen
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parent
AS_OF = '2026-10-14'
URL = ('https://fred.stlouisfed.org/graph/fredgraph.csv'
       '?id=DGS2,DGS5,DGS10&cosd=2000-01-01&coed=' + AS_OF)

def main(download=False):
    raw = BASE/'data'/'raw'/f'fred_yields_{AS_OF}.csv'
    if download:
        if raw.exists():
            raise FileExistsError('Preserve the bundled snapshot. Move it before a new download.')
        raw.parent.mkdir(parents=True, exist_ok=True)
        with urlopen(URL, timeout=45) as response:
            data = response.read()
        raw.write_bytes(data)
    df = pd.read_csv(raw, na_values=['.'])
    date_col = 'observation_date' if 'observation_date' in df else 'DATE'
    df = df.rename(columns={date_col: 'date'})
    df['date'] = pd.to_datetime(df.date, errors='raise')
    df = df.loc[df.date.between('2000-01-01', AS_OF), ['date','DGS2','DGS5','DGS10']]
    if df.date.duplicated().any():
        raise ValueError('Duplicate dates in snapshot')
    for c in ['DGS2','DGS5','DGS10']:
        df[c] = pd.to_numeric(df[c], errors='raise')
    clean = df.dropna().sort_values('date').copy()
    if clean.empty:
        raise ValueError('No complete yield observations')
    output = BASE/'outputs'; output.mkdir(exist_ok=True)
    with sqlite3.connect(BASE/'data'/'macro_yield.sqlite') as con:
        con.executescript((BASE/'sql'/'schema.sql').read_text())
        # These are snapshot observations, not claimed historical release vintages.
        clean.assign(date=clean.date.dt.strftime('%Y-%m-%d')).to_sql(
            'yield_snapshot', con, if_exists='replace', index=False)
        latest = pd.read_sql_query(
            'SELECT * FROM yield_snapshot WHERE date=(SELECT MAX(date) FROM yield_snapshot)', con)
    last = latest.iloc[0]
    metadata = {'snapshot_date': AS_OF, 'source_url': URL,
        'file_sha256': hashlib.sha256(raw.read_bytes()).hexdigest(),
        'raw_file_saved_utc': datetime.fromtimestamp(raw.stat().st_mtime, timezone.utc).isoformat(),
        'processed_utc': datetime.now(timezone.utc).isoformat(),
        'last_common_date': last.date, 'complete_observations_since_2000':len(clean),
        'yields_percent':{k:float(last[k]) for k in ['DGS2','DGS5','DGS10']},
        'spread_2s10s_bp':round(float(last.DGS10-last.DGS2)*100,8),
        'note':'Dated reference curve; not live data or a macro model forecast.'}
    (output/'yield_snapshot.json').write_text(json.dumps(metadata,indent=2))
    fig, ax = plt.subplots(figsize=(8,4.8),layout='constrained')
    values = [last.DGS2,last.DGS5,last.DGS10]
    ax.plot([2,5,10], values, marker='o',color='#146c80',lw=2)
    for m,v in zip([2,5,10],values):
        ax.annotate(f'{v:.2f}%',(m,v),xytext=(0,12),textcoords='offset points',ha='center')
    ax.set(xlabel='Maturity (years)',ylabel='Constant-maturity yield (%)',xticks=[2,5,10])
    ax.set_ylim(min(values)-0.15,max(values)+0.2)
    ax.set_title(f'US Treasury reference curve | {last.date}',loc='left',fontweight='bold')
    ax.spines[['top','right']].set_visible(False)
    ax.grid(alpha=0.2)
    fig.supxlabel('Source: Federal Reserve H.15 via FRED. Three maturity points; not a fitted zero-coupon curve.',fontsize=8)
    fig.savefig(output/'reference_curve.png',dpi=180)
    plt.close(fig)
    print(json.dumps(metadata,indent=2))

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--download',action='store_true')
    main(p.parse_args().download)
