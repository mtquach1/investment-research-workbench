# Rental holding-period ledger and deterministic stress

Model `rental-hold-v1`, October 28, 2026. This completes a holding-period slice of
roadmap phase 7; it does not complete rental discovery or the full product.

Real estate has Purchase & cash flow and Holding period & stress tabs. The latter
uses the actual entered property, debt, first-year expense and reserve inputs.
It supports 1–30 years, annual rent/expense/value changes, selling costs, a one-time
repair and an explicit additional-cash commitment. Inputs and results remain in
the session and survive domain navigation; Clear session workspace resets them.
Nothing downloads, persists assumptions to a database, or calls a provider.

`POST /real-estate/rental-projection` exposes the same typed deterministic engine;
responses are no-store under the existing privacy middleware. Original purchase
criteria are not lender approval. An entered down payment may still fail the
first-year feasibility criteria; the projection does not override that result.

## Accounting and timing

- All monetary ledger operations round half-up to cents with Decimal arithmetic.
- Rent and fixed operating costs grow at the start of each subsequent year.
  Collected rent first loses the vacancy fraction; management is a fraction of
  collected rent. This is a monthly expected-vacancy allowance, not a simulated
  randomly vacant month. Taxes use purchase price for the initial entered tax
  assumption and then the expense growth assumption, not market appreciation.
- One fixed-rate amortizing loan: monthly rounded interest and payment; the last
  contractual payment clears its rounding residual. Payments stop at payoff.
  No refinance, rate reset, PMI, lender qualification or future borrowing.
- Replacement-reserve contributions accumulate separately rather than disappearing
  as a presumed expense. An actual repair draws that account first; the remaining
  bill reduces monthly cash flow. Maintenance and the one-time shock are separate
  assumptions; a user must not enter the same bill in both.
- Positive after-reserve cash flow is distributed at month-end and retained outside
  the property at zero return. It is not automatically reinvested or used to pay
  a later deficit. Negative flow uses operating reserves and then additional cash,
  bounded by the entered limit. Uncommitted purchase capital is not automatically
  pledged. No interest is earned on reserves or distributions.
- If closing cannot be funded, there is no operating timeline. If a later month
  cannot be fully funded, the model stops before that transaction: its unpaid rent,
  costs and debt are not partially booked. Only completed months are reported,
  with the first failed month and the cash needed beyond the limit. No sale return
  is reported after failure; foreclosure/default mechanics are outside this model.
- Property value compounds monthly at the annual effective appreciation assumption.
  Equity equals property value minus debt. It is not spendable income.
- At the planned sale: value minus selling costs and debt payoff, plus the remaining
  two reserve accounts. Net profit equals this cash plus distributions minus initial
  and subsequent invested cash. Principal reduction is never separately added.
  An underwater sale requires additional cash within the same remaining funding limit. If it cannot be funded, exit profit is withheld. If funded, that contribution is counted in invested capital and exit cash is zero, avoiding double-counting the loss.

All outputs are nominal, pre-income-tax and undiscounted. There is no depreciation,
capital-gains tax, inflation adjustment or IRR claim. First-year annual calculator
values may differ by a few cents because the timeline rounds actual monthly debt
and expense entries. Area data is not used to claim achievable property rent.

## Stress and interface

The joint adverse case adds 10 percentage points of vacancy (capped at 100%),
reduces annual rent growth and property appreciation by two percentage points,
raises expense growth by two points, and adds a $15,000 repair in the selected
repair month. It retains the same fixed loan, purchase and capital commitment.
This is an illustrative deterministic scenario, not a percentile or probability.

Equity, mortgage balance and combined reserve charts compare both paths and stop
when funding fails. A month inspector shows distributions, outside cash and held
reserves. An accessible monthly table exposes the full ledger and inputs.
No opaque score or automatic stock/property winner is produced.

## Verification

Independent references cover an all-cash rent ledger, reserve release and repair
accounting, a zero-rate payoff, the standard $100,000 / 6% / 360-month payment,
debt/principal/cash identities, reserve exhaustion, bounded external funding,
initial shortfall, growth timing, and price-independent tax escalation. API tests
check repeatability, no-store and invalid financing. UI tests check funding failure,
navigation persistence, horizon/repair bounds and reset. Full-suite and browser
verification: 347 tests passed, zero skipped, 30 dependency warnings in 40.59s.
The actual local API returned the independent all-cash reference result with
no-store headers. Browser QA verified both tabs, readable metric labels, the
base/adverse timelines, and the default adverse case stopping before month 12
with no reported sale profit. The earlier Windows native allocation/API issue
did not appear in this run, but its underlying cause remains unresolved.
