"""Reproduce Stage 2 offline from bundled snapshots. Add --download for missing inputs."""
from pathlib import Path
import argparse, subprocess, sys
ROOT=Path(__file__).resolve().parent

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--download',action='store_true')
    args=p.parse_args()
    scripts=(['download_stage2.py','download_vintages.py'] if args.download else [])
    scripts+=['build_panel.py','analyze_stage2.py']
    for script in scripts:
        subprocess.run([sys.executable,str(ROOT/script)],cwd=ROOT,check=True)
    subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=ROOT,check=True)
    print('Results:',ROOT/'outputs'/'stage2')
