# Sources checked on 14 October 2026

The summaries below identify relevance; no published coefficient is imported as
our own estimate. Stage 1 does not establish empirical forecasting performance.

1. New York Fed, Treasury Term Premia. Expectations/term-premium decomposition;
   term premia are estimated, not observed.
   https://www.newyorkfed.org/research/data_indicators/term-premia-tabs
2. Diebold, Rudebusch and Aruoba (2006), The Macroeconomy and the Yield Curve:
   A Dynamic Latent Factor Approach, Journal of Econometrics 131, 309–338.
   Earlier FRBSF working paper: The Macroeconomy and the Yield Curve:
   A Nonstructural Analysis (2003-18). Macro variables and yield factors interact;
   our maturity regressions do not replicate their latent-factor model.
   https://www.frbsf.org/research-and-insights/publications/working-papers/2003/10/the-macroeconomy-and-the-yield-curve-a-nonstructural-analysis/
   https://econ.umd.edu/publication/macroeconomy-and-yield-curve-dynamic-latent-factor-approach
3. Ang and Piazzesi (2003), A No-Arbitrage Vector Autoregression of Term Structure
   Dynamics with Macroeconomic and Latent Variables, Journal of Monetary Economics.
   Working paper 8363 (2001): https://www.nber.org/papers/w8363
4. Li and Wei (2013), Term Structure Modeling with Supply Factors and the Federal
   Reserve's Large-Scale Asset Purchase Programs. FEDS working paper 2012-37:
   https://www.federalreserve.gov/pubs/feds/2012/201237/
5. Philadelphia Fed SPF data catalog:
   https://www.philadelphiafed.org/surveys-and-data/data-files
6. SPF real GDP median level forecasts and documentation:
   https://www.philadelphiafed.org/surveys-and-data/rgdp
7. SPF CPI forecasts and linked documentation (forecast horizons and units):
   https://www.philadelphiafed.org/surveys-and-data/cpi-spf
   https://www.philadelphiafed.org/surveys-and-data/tbill
8. Treasury Bulletin, Federal Debt Held by the Public (FYGFDPUN):
   https://fred.stlouisfed.org/series/FYGFDPUN
9. Fed H.4.1 Treasury securities held outright (TREAST), weekly Wednesday levels:
   https://fred.stlouisfed.org/series/TREAST
10. EIA Brent spot prices (DCOILBRENTEU):
    https://fred.stlouisfed.org/series/DCOILBRENTEU
11. BLS unemployment rate and BEA nominal GDP (Stage 2 acquisition targets):
    https://fred.stlouisfed.org/series/UNRATE
    https://fred.stlouisfed.org/series/GDP
12. SF Fed, The Changing Sensitivity of Interest Rates to Oil Supply News (2025).
    Oil-to-yield relationships depend on the monetary-policy/inflation regime.
    https://www.frbsf.org/research-and-insights/publications/economic-letter/2025/12/changing-sensitivity-of-interest-rates-to-oil-supply-news/
    Fed IFDP Note (2016), demand/supply distinctions in oil and inflation compensation:
    https://www.federalreserve.gov/econresdata/notes/ifdp-notes/2016/relationship-between-oil-prices-and-inflation-compensation-20160406.html
13. Orphanides and Wei, Evolving Macroeconomic Perceptions and the Term Structure
    of Interest Rates, FEDS 2010-01. Survey forecasts and real-time vintages:
    https://www.federalreserve.gov/pubs/feds/2010/201001/index.html
14. Laubach (2009), New Evidence on the Interest Rate Effects of Budget Deficits
    and Debt. Long-horizon fiscal projections help distinguish fiscal expectations
    from cyclical movements. Published estimates are not current universal rules.
    https://www.federalreserve.gov/econres/feds/new-evidence-on-the-interest-rate-effects-of-budget-deficits-and-debt.htm
15. Federal Reserve H.15 via FRED, constant-maturity yields:
    https://fred.stlouisfed.org/series/DGS2
    https://fred.stlouisfed.org/series/DGS5
    https://fred.stlouisfed.org/series/DGS10
16. statsmodels OLS implementation:
    https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.OLS.html

Methodological judgment: quarterly ARX, exact feature specifications, staged model
comparison and the testing workflow are our project design choices. The cited
literature motivates the channels, not an assertion that these exact choices are optimal.
