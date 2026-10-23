"""Retrieve and validate five ALFRED series for each quarter-end origin.
Each series requires its own vintage_date parameter entry.
"""
from pathlib import Path
from urllib.request import urlopen
from concurrent.futures import ThreadPoolExecutor, as_completed
from zipfile import ZipFile
from io import BytesIO
from datetime import datetime, timezone
import hashlib, json, time

ROOT=Path(__file__).resolve().parent
RAW=ROOT/'data'/'raw'/'alfred'
SERIES=['GDP','UNRATE','FYGFDPUN','TREAST','DCOILBRENTEU']

def download(date):
    path=RAW/f'vintage_{date}.zip'
    url=('https://alfred.stlouisfed.org/graph/alfredgraph.csv?id='+','.join(SERIES)
         +'&vintage_date='+','.join([date]*len(SERIES)))
    if not path.exists():
        for attempt in range(3):
            try:
                with urlopen(url,timeout=55) as r: payload=r.read()
                break
            except Exception:
                if attempt==2: raise
                time.sleep(1+attempt)
        # Validate before committing the file.
        validate(payload,date)
        path.write_bytes(payload)
    payload=path.read_bytes()
    missing=validate(payload,date)
    return dict(origin_date=date,url=url,filename=path.name,bytes=len(payload),
        missing_series=missing,
        sha256=hashlib.sha256(payload).hexdigest(),
        retrieved_utc=datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat())

def validate(payload,date):
    headers=[]
    with ZipFile(BytesIO(payload)) as z:
        for name in z.namelist():
            if name.endswith('.csv'):
                headers.extend(z.read(name).decode('utf-8-sig').splitlines()[0].split(',')[1:])
    expected={s+'_'+date.replace('-','') for s in SERIES}
    if not headers or not set(headers).issubset(expected):
        raise ValueError(f'Wrong vintage columns for {date}: {headers}')
    return sorted(s for s in SERIES if s+'_'+date.replace('-','') not in headers)

if __name__=='__main__':
    RAW.mkdir(parents=True,exist_ok=True)
    dates=[f'{y}-{md}' for y in range(2003,2027) for md in ['03-31','06-30','09-30','12-31']
           if f'{y}-{md}'<='2026-09-30']
    rows=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(download,d):d for d in dates}
        for f in as_completed(futures):
            rows.append(f.result())
            if len(rows)%10==0: print(f'Validated {len(rows)}/{len(dates)} vintage bundles',flush=True)
    rows.sort(key=lambda x:x['origin_date'])
    (RAW/'manifest.json').write_text(json.dumps(rows,indent=2))
    print('Complete:',len(rows),'validated vintage bundles')
