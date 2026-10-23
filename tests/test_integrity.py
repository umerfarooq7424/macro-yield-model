import sys
import sqlite3
import unittest
from pathlib import Path
import pandas as pd
import numpy as np
from zipfile import ZipFile
from io import BytesIO
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from model import validate_panel, make_design, synthetic_panel, SPECS
from features import growth_revision_pp, balance_flow_pct_gdp
from download_vintages import validate as validate_vintage

class IntegrityTests(unittest.TestCase):
    def test_wrong_vintage_rejected(self):
        data=BytesIO()
        with ZipFile(data,'w') as z:
            z.writestr('monthly.csv','observation_date,UNRATE_20261014\n2019-11-01,3.5\n')
        with self.assertRaisesRegex(ValueError,'Wrong vintage'):
            validate_vintage(data.getvalue(),'2019-12-31')

    def test_missing_feature_does_not_compress_lag(self):
        d=synthetic_panel()
        d.loc[5,'growth_revision_pp']=np.nan
        d=validate_panel(d,SPECS['macro'],allow_missing_features=True)
        x=make_design(d,2,SPECS['macro'])
        row=x.loc[x.quarter_end.eq(d.loc[6,'quarter_end'])].iloc[0]
        self.assertAlmostEqual(row.lag_change_bp,100*(d.loc[6,'y2']-d.loc[5,'y2']))
        self.assertFalse(x.quarter_end.eq(d.loc[5,'quarter_end']).any())

    def test_reject_future_feature(self):
        d = synthetic_panel()
        d.loc[5,'growth_revision_pp_available_date'] = d.loc[5,'quarter_end'] + pd.Timedelta(days=1)
        with self.assertRaisesRegex(ValueError, 'Look-ahead'):
            validate_panel(d,SPECS['macro'])

    def test_reject_calendar_gap(self):
        with self.assertRaisesRegex(ValueError, 'consecutive'):
            validate_panel(synthetic_panel().drop(index=5),SPECS['macro'])

    def test_lag_target_alignment(self):
        d=synthetic_panel()
        x=make_design(d,2,SPECS['macro'])
        self.assertEqual(x.iloc[0].quarter_end,d.iloc[1].quarter_end)
        self.assertEqual(x.iloc[0].target_date,d.iloc[2].quarter_end)
        self.assertAlmostEqual(x.iloc[0].target_change_bp,100*(d.y2.iloc[2]-d.y2.iloc[1]))

    def test_within_vintage_rebasing(self):
        # Each vintage can have a different GDP base; within-vintage ratios survive.
        self.assertAlmostEqual(growth_revision_pp(100,101,200,202),0)
        self.assertAlmostEqual(balance_flow_pct_gdp(1100,1000,20000),0.5)

    def test_sql_vintage_exclusion(self):
        root=Path(__file__).resolve().parents[1]
        con=sqlite3.connect(':memory:')
        con.executescript((root/'sql/schema.sql').read_text())
        con.execute("INSERT INTO forecast_origins VALUES ('2020-03-31')")
        rows=[('GDP','2019-12-31','2020-01-30','2020-01-30',100,'billions','test'),
              ('GDP','2019-12-31','2020-04-30','2020-04-30',110,'billions','test')]
        con.executemany('INSERT INTO observations VALUES (?,?,?,?,?,?,?)',rows)
        self.assertEqual(con.execute('SELECT value FROM observations_asof').fetchall(),[(100.0,)])
        con.close()

if __name__=='__main__': unittest.main()
