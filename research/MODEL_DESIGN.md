# Macro drivers of the US Treasury curve
Stage 1: research design and tested starter code | 14 October 2026

## Recommendation

Start with a quarterly macro-augmented autoregression in yield changes (ARX),
estimated separately for 2-, 5- and 10-year Treasury yields. This is a deliberately
small reduced-form benchmark informed by macro-finance research, not a replication
of an arbitrage-free term-structure model and not a model proven best before testing.
Use ordinary least squares with Newey–West/HAC coefficient standard errors.

The first baseline has two macro variables: revisions to expected real GDP growth
and expected CPI inflation. Add borrowing and Fed Treasury holdings as a separate
supply specification. Test oil separately; substitute unemployment for GDP in a
labor-market specification. Do not put every candidate in one initial regression.

The main question is whether information known at quarter-end improves a forecast
of next quarter's yield change beyond a random walk or an autoregressive benchmark.
An explanatory companion regression can describe same-quarter associations. Neither
version alone identifies the causal effect of a policy or macroeconomic shock.

## Economic framework

A nominal long-term yield can be approximated as expected average future short
rates plus a maturity-specific term premium [1]. GDP and inflation outlooks can
change the expected policy path. Debt issuance, duration supply and central-bank
holdings can change the premium required to absorb interest-rate risk. The two
channels interact, and this small regression will not separately identify them.

An observed level is not the same as news. High inflation already expected by
investors need not cause a new selloff. A positive inflation surprise may do so.
Survey forecast revisions are imperfect proxies for changing expectations, not
identified announcement surprises. At a quarter-end origin they may already be
priced in, so their incremental predictive power can be weak or zero.

## Selected variables

| Topic | Preferred measurement | Initial role | Main qualification |
|---|---|---|---|
| Growth outlook | Same-target revision to SPF next-quarter real GDP growth, percentage points | Baseline | Construct within each survey vintage; do not compare nominal GDP levels or rebase across vintages |
| Inflation outlook | Same-target revision to SPF next-quarter headline CPI inflation, annualized percentage points | Baseline | CPI chosen for long history; core PCE is a shorter-sample robustness check |
| Government borrowing | Change in Treasury debt held by the public, scaled by nominal GDP; preferably marketable coupon issuance or duration-adjusted supply | Supply extension | Stock change is a borrowing proxy, not exact net issuance; fiscal news is preferable for causal work |
| Central-bank balance sheet | Change in Fed Treasury securities held outright / nominal GDP | Supply extension | Use Treasury holdings, not total Fed assets; stock changes need not equal purchases |
| Global oil | 100 × log change in quarterly-average Brent spot price | Oil extension | Demand-driven and supply-driven oil moves have different effects |
| Unemployment | Change in latest available three-month average US unemployment rate, percentage points | Substitute for growth | Growth and unemployment share cyclical information; a joint model is only a sensitivity check |
| Expected policy path | Same-target revision to SPF three-month Treasury bill forecast | Separate policy check | This is a market-rate proxy, not an exact Fed funds forecast; conditioning on it can absorb the macro transmission channel |

Sources: Philadelphia Fed SPF [5–7], Treasury debt via FRED [8], Fed H.4.1
Treasury holdings [9], Brent via EIA/FRED [10], BLS/FRED unemployment [11].
Do not sum Fed, ECB and BoJ total assets after converting currencies: exchange-rate
valuation and different asset mixes would confound interpretation. Cross-border
monetary spillovers are deferred to an extension using separate, consistently
scaled measures. The first model is US-focused and covers the Fed explicitly.

### Precise forecast-revision construction

At survey quarter q, let G(q,h) denote the median RGDP level for target q+h.
Construct annualized expected growth for target q+1 as
100 × [(G(q,1)/G(q,0))^4 − 1]. Compare with the preceding survey's forecast of
growth for that SAME target: 100 × [(G(q−1,2)/G(q−1,1))^4 − 1].
Subtract the second from the first. In SPF median-level columns this is growth
from RGDP3/RGDP2 today minus growth from RGDP4/RGDP3 in the previous survey.
This is growth derived from median levels, not necessarily the median of individual
growth forecasts. Ratios are taken within vintages to avoid base-year inconsistencies.

For inflation, use CPI3 in survey q minus CPI4 in survey q−1. Both refer to
inflation during q+1. The rates are already annualized; do not annualize again.
For TBILL use the analogous target mapping after checking source documentation.
Unlike changes in a rolling year-ahead forecast, these revisions keep the target
quarter fixed between the two surveys. Changes still reflect survey composition
and revised information, not just an exogenous shock [6,7].

For a slower-moving outlook robustness check, next-four-quarter real growth can
be constructed as 100 × (RGDP6/RGDP2 − 1), and CPI from the geometric combination
of CPI3–CPI6. Differences across surveys of these rolling horizons must be labeled
outlook changes, not pure same-target revisions. This check is not implemented.

### Borrowing and Fed measurement

Normalize each balance to billions of dollars first. FYGFDPUN is in millions,
TREAST is in millions, and nominal GDP is in billions at a seasonally adjusted
annual rate. For a quarter p observed at origin q, define borrowing flow as
100 × (D_p − D_(p−1)) / GDP_(p−1), and Fed flow analogously with F_p.
Units are percent of annualized GDP; these quarterly stock changes are NOT
annualized. A positive Fed flow means increased holdings.

Only use a period p for which both endpoints and the GDP denominator were
published by q. Match dates as closely as possible and record the weekly Fed
observation used. Do not assume a universal one-quarter release lag. Debt figures
may arrive later. The available-date of a derived feature is the latest release
date among its inputs. Keep reference periods and ages, so stale supply information
is visible and not described as new issuance news.

A rough outside-Fed supply measure is D − F. It includes foreign official holders
and is not private-investor duration supply. If using changes in this net measure,
do NOT also include D and F in the same regression: that is exact redundancy.
The proposed supply extension includes D and F separately, with no net column.
Ideally replace par amounts with coupon/duration-weighted supply: bills and
30-year bonds do not impose the same duration risk [4].

## Model and interpretation

For maturity m in {2,5,10}, define dY_m,q = 100 × (y_m,q − y_m,q−1), in bp,
where y is the last common valid daily constant-maturity yield in the quarter.
The predictive baseline is:

    dY_m,q+1 = a_m + phi_m*dY_m,q
               + beta_g,m*growth_revision_q
               + beta_pi,m*inflation_revision_q + error_m,q+1

The supply extension adds beta_D,m*borrowing_flow_q and
beta_F,m*fed_treasury_flow_q. Every q subscript means available by the forecast
origin, not necessarily a reference period equal to q.

ARX means autoregressive model with external regressors; these are externally
supplied inputs, NOT a claim of economic exogeneity. This is a restricted dynamic
regression rather than a fully estimated general ARDL or VAR.

Estimate the same maturity set on a common calendar. Compute predicted 2s10s change
as predicted 10Y change minus predicted 2Y change. A positive result means
steepening. The 5Y response helps show whether the belly moves differently.
These three points do not constitute a fitted continuous zero-coupon curve.
Do not use par/constant-maturity yields as zero-coupon yields in a pricing model.

The same-quarter companion replaces the target with dY_m,q and the autoregressive
term with dY_m,q−1. It is useful for retrospective attribution, with endogenous
regressors and unexplained residuals. Its coefficients must not be presented as
forecast coefficients or causal multipliers. It is specified here, not implemented
in this first code release.

## Expected directions: hypotheses, not constraints

| New information / change | Plausible yield response | Curve qualification |
|---|---|---|
| Stronger growth outlook | Often higher yields via real-rate and policy expectations | Flattening if 2Y rises more; steepening if long-run real rates/term premium dominate |
| Higher inflation outlook | Often higher nominal yields | Short-lived inflation with forceful policy can flatten; de-anchoring can lift the long end |
| More coupon borrowing / greater duration supply | Often more upward pressure on long yields | Often steepening, conditional on demand and what was already priced |
| Fed Treasury purchases | Often lower long yields through duration removal/signaling | Often flattening if the long end falls more; not a universal response |
| Fed runoff | Often reverses some purchase-related pressure | Expectations, replacement demand and asset mix matter |
| Higher oil price | Inflation pressure up; growth can weaken | Ambiguous without demand/supply identification and policy regime |
| Higher unemployment | Often lowers expected future policy rates | Can steepen if 2Y falls faster; not guaranteed in stagflation |

These are mechanism-based expectations for news. They do NOT impose signs on
lagged predictive coefficients. Anticipation and mean reversion can reverse those
coefficients. No universal “+1% oil = +X bp” number is justified here [2–4,12].

## Why this first, and what the literature actually says

| Approach | Benefit | Decision |
|---|---|---|
| Small ARX in yield changes | Easy to audit and explain; useful benchmark with limited observations | Start here; our simplification, not a claimed replication |
| Macro-augmented dynamic Nelson–Siegel / factor VAR | Models level, slope and curvature with macro feedback [2] | Preferred next structural description if simple results justify more complexity |
| No-arbitrage macro-finance model | Enforces cross-maturity pricing restrictions [3] | Later: requires more yields, estimation choices and identification work |
| Local projections with identified shocks | Horizon-specific causal responses if identification is credible | Later if the question is truly causal; raw macro changes are not identified shocks |
| Black-box ML | Can represent nonlinearities | Defer until a credible simple benchmark and enough data exist |

Diebold, Rudebusch and Aruoba motivate macro/yield-factor dynamics [2]; Ang and
Piazzesi motivate no-arbitrage macro-finance restrictions [3]. Li and Wei support
attention to duration supply and central-bank holdings [4]. Orphanides and Wei
motivate survey expectations and vintage-aware estimation [13]. Laubach's
long-horizon fiscal-forecast approach explains why contemporaneous deficits can
be misleading [14]. None establishes that this exact small ARX is universally best.

## Timing, sample and validation

Use quarterly frequency because the expectation survey is quarterly. Do not
interpolate quarterly survey forecasts into fake independent monthly observations.
Target an initial sample from 2003 onward, subject to verified source overlap.
Report the actual dates and number of usable quarters, not an assumed sample size.
Do not splice the partial fourth quarter of 2026 into a completed-quarter sample.

1. Store observation/reference dates, release dates, vintage dates, units and source.
2. Retain unrevised survey vintages; retrieve macro vintages for historical origins.
   Current downloads of revised macro history are not a real-time backtest.
3. Apply transforms on the complete quarter grid before dropping observations.
   Missing quarters must never silently turn one-row lags into multi-quarter lags.
4. Estimate AR, macro, supply, oil, labor and policy specifications separately.
5. Use at least 60 training quarters, expanding one quarter at a time; compare
   RMSE and MAE against zero yield change and AR-only on identical test dates.
   Reserve the last 12 quarters as untouched confirmation if tuning any choices.
6. Inspect coefficient intervals, residual correlation, predictor correlations,
   variance inflation and sensitivity to sample endpoints. The starter reports
   HAC intervals, Ljung–Box and a raw condition number; the full diagnostic and
   stability program remains a Stage 2 requirement.
7. Review pandemic and lower-bound periods explicitly. Compare post-2008 and
   rolling-window estimates only where sample size permits; do not delete outliers
   merely to improve fit. Test stationarity of transformed series and investigate
   persistence rather than assuming that all transformations solve it.
8. If using scenarios, report conditional mean differences and joint uncertainty.
   Resample the SAME time blocks across maturity equations to preserve residual
   covariance. Coefficient confidence intervals are not prediction intervals.

An in-sample R-squared is not proof of forecast value. If the macro model loses to
the random walk, report that result and retain it as an explanatory tool only if
its associations are stable and economically interpretable.

## Current starting point and limits

The downloaded daily yield snapshot has a last common complete observation of
9 October 2026: 2Y 4.80%, 5Y 5.02%, 10Y 5.24%; 2s10s +44 bp. It is a dated
reference curve, not live pricing. Market data cannot establish which macro factor
caused the move. No real macro regression has been estimated in Stage 1.

Do not translate the next-quarter model automatically into a forecast from today's
intraday curve: the origin, information set and horizon differ. A current scenario
exercise requires a dated baseline, a reconciled macro panel and explicit assumptions.

## Deliverable status

- Completed: literature review, variable selection, economic mechanisms, model
  equation, release-timing plan, real yield snapshot, Python estimator and SQL
  vintage schema, and software tests using clearly labeled synthetic inputs.
- Pending Stage 2: downloading and reconciling macro histories/vintages, fitting
  real coefficients, full diagnostics, holdout validation and current scenarios.
- The synthetic demo is only a software test. Its coefficients and forecast
  scores are not evidence about US Treasury markets.

See SOURCES.md for bibliography and URLs, README.md for commands, and
AI_DEVELOPMENT_LOG.md for the Codex workflow and interview language.
