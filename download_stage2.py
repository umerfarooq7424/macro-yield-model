"""Download immutable source snapshots for the 2026-10-14 research run."""
from pathlib import Path
from urllib.request import urlopen
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json

ROOT=Path(__file__).resolve().parent
RAW=ROOT/'data'/'raw'
SPF='https://www.philadelphiafed.org/-/media/FRBP/Assets/Surveys-And-Data/survey-of-professional-forecasters/'
URLS={
 'spf_medianLevel.xlsx': SPF+'historical-data/medianLevel.xlsx',
 'spf_release_dates.txt': SPF+'spf-release-dates.txt',
}
for series in ['FYGFDPUN','TREAST','GDP','UNRATE','DCOILBRENTEU']:
    URLS[f'{series}_2026-10-14.csv']=(
        f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}&cosd=2000-01-01&coed=2026-10-14')

def download(item):
    name,url=item
    target=RAW/name
    if not target.exists():
        with urlopen(url,timeout=60) as response:
            payload=response.read()
        target.write_bytes(payload)
    return {'filename':name,'url':url,'bytes':target.stat().st_size,
            'saved_utc':datetime.fromtimestamp(target.stat().st_mtime,timezone.utc).isoformat(),
            'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}

if __name__=='__main__':
    RAW.mkdir(parents=True,exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows=list(pool.map(download,URLS.items()))
    (RAW/'stage2_sources.json').write_text(json.dumps(rows,indent=2))
    for row in rows: print(row['filename'],row['bytes'])
