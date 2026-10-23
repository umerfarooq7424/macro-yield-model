"""Generate the Stage 2 PDF from completed analysis outputs."""
from pathlib import Path
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
ROOT=Path(__file__).resolve().parent
O=ROOT/'outputs/stage2'
styles=getSampleStyleSheet()
styles['BodyText'].fontSize=10;styles['BodyText'].leading=14
styles['Title'].textColor=colors.HexColor('#123047')
styles['Heading1'].textColor=colors.HexColor('#0f766e')
story=[]
def p(t,style='BodyText'):story.append(Paragraph(t,styles[style]));story.append(Spacer(1,8))
def table(rows,widths):
 t=Table([[Paragraph(str(v),styles['BodyText']) for v in row] for row in rows],colWidths=widths,repeatRows=1)
 t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e5f0ef')),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,0),(-1,0),.8,colors.HexColor('#0f766e')),('LINEBELOW',(0,1),(-1,-1),.3,colors.HexColor('#dddddd'))]))
 story.append(t);story.append(Spacer(1,12))
def page():story.append(PageBreak())
def chart(name,w=480,h=200):story.append(Image(str(O/name),width=w,height=h));story.append(Spacer(1,10))
p('US yield curves and the macro outlook','Title')
p('Stage 2 | Real-data estimation and validation | Prepared 15 October 2026','Heading2')
p('Decision: retain simple forecasts as the benchmark','Heading1')
p('The quarterly GDP-and-inflation model does not improve forecast RMSE over a no-change forecast for 2-, 5- or 10-year Treasury yields in the full expanding-window evaluation. The analysis is useful for studying conditional relationships and uncertainty; it does not establish a reliable trading signal.')
m=pd.read_csv(O/'forecast_comparison.csv');a=m[(m['sample']=='long_sample')&(m.spec=='macro')&(m.period=='all_evaluation')]
rows=[['Maturity','Macro RMSE (bp)','AR RMSE (bp)','No-change RMSE (bp)']]
for tenor in [2,5,10]:
 q=a[a.maturity==tenor].set_index('benchmark');rows.append([f'{tenor}Y']+[f'{q.loc[b,"rmse_bp"]:.2f}' for b in ['model_bp','ar_bp','random_walk_bp']])
table(rows,[70,138,138,138])
p('Evaluation covers 33 target quarters, September 2018 through September 2026. A basis point (bp) is 0.01 percentage point. Lower RMSE is better. The autoregressive (AR) model uses the preceding yield change; the no-change forecast predicts zero change.')
chart('forecast_comparison.png',480,192)
p('Scope: US nominal constant-maturity Treasury yields. The latest model origin is 30 September 2026. This is a quarter-end research snapshot, not a live assessment of today\'s curve. Stage 2 completes estimation and documentation; presentation design follows separately.')
page();p('1. Variables and economic channels','Heading1')
table([['Driver','Implemented variable and interpretation'],['GDP outlook','SPF revision to next-quarter annualized real GDP growth, comparing the same target quarter across consecutive surveys. Growth is derived from median GDP levels. Stronger activity may lift expected policy rates.'],['Inflation outlook','SPF revision to next-quarter CPI inflation (annualized percentage points), aligned to the same target. Higher inflation expectations may lift policy expectations and inflation compensation.'],['Government borrowing','Change in debt held by the public / lagged annual nominal GDP, in percent. This is a realized stock-change proxy; it is not expected net issuance, deficit news or duration-weighted supply.'],['Central-bank holdings','Change in Federal Reserve Treasury holdings / lagged annual nominal GDP. Purchases may reduce privately held duration. Covers Fed Treasuries only, not all assets or other central banks.'],['Global oil','100 times log change in average Brent price, previous full quarter versus the quarter before. Oil demand and supply shocks can have different effects; this model does not identify them.'],['Unemployment','Latest three-month mean unemployment rate minus the prior three-month mean, in percentage points. Used in an alternative activity specification.'],['Policy expectations','SPF same-target revision to next-quarter Treasury-bill rate; a robustness extension, not the baseline.']],[100,384])
p('These are parsimonious, economically motivated choices rather than a claim that one variable set is universally best. Debt and holdings ratios use annual GDP as a scale denominator; they are not annualized quarterly flows.')
page();p('2. Econometric design and data timing','Heading1')
p('For each maturity m, the baseline is a quarterly autoregressive regression with macro predictors (ARX):')
p('Change in yield(m, t+1) = intercept + persistence x change in yield(m, t) + GDP-revision coefficient x GDP revision(t) + inflation-revision coefficient x inflation revision(t) + error.')
p('Yield changes are in basis points. Ordinary least squares estimates the coefficients; HAC covariance with four lags provides inference robust to some serial correlation and heteroskedasticity. This accessible benchmark is motivated by macro-finance literature [1-4]; it is not a replication of a no-arbitrage or latent-factor term-structure model.')
p('The long panel has 95 consecutive quarter ends, 2003 Q1 to 2026 Q3. Supply and oil comparisons begin in 2011 Q2, leaving 62 quarters because of usable historical-vintage coverage. Models are estimated separately for 2Y, 5Y and 10Y; the 10Y-minus-2Y spread measures slope. No full-curve interpolation, term-premium decomposition or no-arbitrage restrictions are imposed.')
p('Forecasts use expanding windows, with at least 60 usable training rows in the long sample and 40 in the shorter common sample. The shorter minimum is a documented deviation from Stage 1 and makes extension results exploratory. Actual target outcomes must be observable by each forecast origin. Random train/test splits are not used.')
p('The macro inputs use 95 ALFRED quarter-end vintage bundles. Vintage headers are checked for every series. SPF survey release dates are aligned to origins, but the current historical workbook includes errata and is not a frozen original-file archive. Yield history also uses a current snapshot. Therefore the experiment is timing-aware, but not a completely vintage-pure real-time backtest.')
p('Unemployment gaps at December 2025 and March 2026 are retained. Calendar lags are constructed before dropping unusable regression rows. Comparisons across different specifications should use matched_date_comparison.csv. Borrowing and Fed holdings use the latest common observable reference quarter; oil deliberately has an extra quarter lag.')
p('Model variants: AR only; GDP + inflation baseline; baseline + borrowing and Fed holdings; baseline + oil; unemployment + inflation; baseline + bill-rate expectations. Extensions are compared separately to limit dimensionality and overlapping activity signals.')
page();p('3. Conditional macro associations','Heading1')
e=pd.read_csv(O/'conditional_scenarios.csv');z=e[(e['mode']=='same_quarter_association')&(e.maturity.astype(str)=='10')]
table([['Scenario','10Y association (bp)','90% interval (bp)']]+[[r.scenario,f'{r.effect_bp:.1f}',f'[{r.lower90_bp:.1f}, {r.upper90_bp:.1f}]'] for r in z.itertuples()],[260,112,112])
p('These are same-quarter regression contrasts, controlling for the preceding yield change and the other variables in each specification. They measure conditional associations, not identified causal responses. Different rows use different samples/specifications and must not be added into a combined macro scenario.')
chart('conditional_associations.png',480,269)
p('Intervals use 1,000 fixed-design residual block-bootstrap replications with blocks of four observations and shared draws across maturities. They describe uncertainty in conditional mean contrasts, not the range of future realized yields. Missing labor rows make observation blocks only approximately calendar-quarter blocks. The CSV also reports next-quarter predictive contrasts and 2s10s slope contrasts.')
page();p('4. Forecast limits and checks','Heading1')
f=pd.read_csv(O/'quarter_end_forecast.csv')
table([['Maturity','30 Sep yield (%)','31 Dec model (%)','Approx. 90% range (%)']]+[[f'{r.maturity}Y',f'{r.origin_yield_pct:.2f}',f'{r.predicted_yield_pct:.2f}',f'{r.approximate_lower90_pct:.2f} - {r.approximate_upper90_pct:.2f}'] for r in f.itertuples()],[70,130,130,154])
p('The quarter-end forecast is included for reproducibility, not as a preferred investment forecast: the baseline failed its benchmark comparison. The range uses a normal approximation combining residual variance and coefficient uncertainty. It is not coverage-calibrated and does not include future predictor uncertainty, model selection or regime uncertainty.')
d=pd.read_csv(O/'diagnostics.csv');tests=d[d.ljung_box_lag4_p.notna()]
p(f'Diagnostics are supplied for {len(tests)} fitted maturity/specification combinations. Ljung-Box p &lt; 0.05 occurs in {int((tests.ljung_box_lag4_p<.05).sum())}; Breusch-Pagan p &lt; 0.05 in {int((tests.breusch_pagan_p<.05).sum())}. These are unadjusted screening tests, not independent confirmations of validity. Predictor ADF and VIF results are in diagnostics.csv.')
p('The package includes coefficient stability checks for the full sample, exclusion of 2020 target quarters and the latest 60 observations. Forecast errors are split into earlier evaluation and the latest 12 calendar target quarters. No significance or superior performance should be inferred simply from selecting the best extension after observing results.')
p('Completed integrity checks: all three maturity lags and targets reconcile between Python and SQLite; vintage dates and feature availability are checked; missing-feature handling preserves calendar lags; unit transformations and target alignment are tested. See VALIDATION.md and stage2_run.log for the executed checks.')
p('Main limitations: small quarterly samples, omitted fiscal expectations and global central-bank holdings, no causal shock identification, mutable historical survey/yield inputs, possible structural breaks and coarse quarterly timing. The current model addresses conditional relationships and forecast benchmarking; it does not explain every movement in the current curve.')
page();p('5. Reproduction, Codex workflow and references','Heading1')
p('Extract the ZIP, follow README.md to create a Python environment, install requirements, then run <b>python run_stage2.py</b>. Bundled snapshots permit offline analysis after dependencies are installed. The SQLite database and example queries support SQL inspection. To rebuild this PDF, install reportlab and run <b>python make_report.py</b>.')
p('Codex assisted implementation, debugging, tests, SQL alignment and documentation. The model itself is conventional econometrics: no language-model output is used as a market predictor. The development log records the corrected multi-series vintage-date issue and information-timing safeguards. Review of economic assumptions remains essential.')
p('The next presentation should lead with the research question, channels and variable choices; show the honest benchmark comparison; then explain conditional associations and limitations. It should avoid presenting fitted coefficients as causal market forecasts.')
p('Selected primary references','Heading2')
for text in [
'[1] Ang and Piazzesi (2003), A No-Arbitrage Vector Autoregression of Term Structure Dynamics with Macroeconomic and Latent Variables. NBER working paper: https://www.nber.org/papers/w8363',
'[2] Diebold, Rudebusch and Aruoba (2006), The Macroeconomy and the Yield Curve: A Dynamic Latent Factor Approach. Journal of Econometrics 131, 309-338. https://econ.umd.edu/publication/macroeconomy-and-yield-curve-dynamic-latent-factor-approach',
'[3] Li and Wei, Term Structure Modeling with Supply Factors, FEDS 2012-37. https://www.federalreserve.gov/pubs/feds/2012/201237/',
'[4] Orphanides and Wei, Evolving Macroeconomic Perceptions and the Term Structure, FEDS 2010-01. https://www.federalreserve.gov/pubs/feds/2010/201001/index.html',
'[5] Philadelphia Fed Survey of Professional Forecasters. https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/survey-of-professional-forecasters',
'[6] FRED / ALFRED series: DGS2, DGS5, DGS10, GDP, UNRATE, FYGFDPUN, TREAST and DCOILBRENTEU. https://alfred.stlouisfed.org/ ; https://fred.stlouisfed.org/ . Source URLs and input audit records are bundled.']:
 p(text)
p('A broader bibliography and the original Stage 1 rationale appear in research/SOURCES.md and research/MODEL_DESIGN.md. Exact ARX specifications and scenario sizes are project choices, not claims of optimality from the cited papers.')
def footer(c,doc):
 c.setFont('Helvetica',8);c.setFillColor(colors.HexColor('#64748b'));c.drawString(42,25,'MACRO YIELD MODEL | Stage 2 research package');c.drawRightString(553,25,str(doc.page))
SimpleDocTemplate(str(ROOT/'Stage2_Report.pdf'),pagesize=(595,842),rightMargin=42,leftMargin=42,topMargin=40,bottomMargin=43).build(story,onFirstPage=footer,onLaterPages=footer)
print(ROOT/'Stage2_Report.pdf')
