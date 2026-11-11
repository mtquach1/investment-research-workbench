# Connecting company research to the strategy

Implemented October 28, 2026. Company research now opens a Strategy fit tab that
explains what supported financials establish and what they cannot establish.
It is a bridge to the recommendation workflow, not completion of live screening.

The five feature definitions, weights, financial age and liability thresholds
come from `quality_value_annual_v1.json`. Research displays raw reported ROA,
operating margin and free cash flow margin, plus explicit unavailable valuation
yields. It does not reweight available features, compute a partial selection
score or interpret profitability as evidence of an attractive purchase price.

`strategy_financial_rules.py` is shared by research explanations and the synthetic
strategy engine. It checks positive operating inputs, nonnegative cash capex and
liabilities, positive derived free cash flow and the configured liability cap.
The liability comparison uses exact Fraction cross products so a value just over
85% cannot round down to a pass. Missing inputs and observed rule failures are
different states. Research additionally checks financial age and aligned filing
evidence available by the assessment date.

The selected fiscal-year slider updates the raw-ratio chart, financial checks
and assessment date disclosure. Older years are assessed against today's
requirements; this does not reconstruct what an investor knew in that year.
All historical points retain the existing warning that source history may
reflect later restatements. The latest-year typed assessment is also returned in
`GET /research/companies/{issuer_key}` as `strategy_evidence`, including the
strategy content hash. Unavailable/withheld responses contain no assessment.

Unresolved requirements remain explicit: verified membership and tradable security,
sector classification, issuer market cap, recent price, 756 daily total-return
observations, sufficient eligible sector peers, portfolio constraints, and matched
benchmark/evaluation evidence. Even passing every supported financial check does
not establish investment eligibility. There is no live selection score, purchase
proposal, claimed outperformance, new provider account or paid data dependency.

## Verification and next work

Full suite: 285 passed, zero skipped, two dependency warnings, 24.75 seconds.
Log: ignored `output/tests/strategy-evidence-full-suite.log`. Reference cases cover
raw ratio arithmetic, unchanged feature weights, missing valuation, losses,
negative cash capex, unavailable evidence, stale periods, mixed/future filings
and exact liability boundaries. Existing strategy selection, offline HTTP and
Streamlit period/search flows also passed. The earlier Windows allocation/API
native diagnostic remains unresolved; this passing run does not establish a fix.

Browser verification confirmed Apple ticker search and fiscal-year inspection:
selecting 2024-09-28 updated revenue to $391.04B, displayed the stale financial
period failure and missing beginning-assets evidence, and left the score absent.
The running HTTP API returned all five feature definitions and disabled
recommendations. Screenshot saved with the milestone artifacts.

Next: establish usable free end-of-day price/total-return and benchmark coverage,
source permissions, security identity and sector data. Then implement supported
valuation and risk metrics, sector scoring, and portfolio selection. Orange County
single-family rental discovery remains an equal release requirement.
