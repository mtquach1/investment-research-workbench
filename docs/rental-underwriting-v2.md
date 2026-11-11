# Rental underwriting v2

Implemented October 28, 2026. Shared function `underwrite_rental()` backs the
existing `POST /real-estate/rental-underwriting` route and Streamlit rental form.
`model_version` now returns `rental-underwriting-v2`. Default UI is one rented
unit, with manual assumptions; there is no automated ZIP rent estimate.

## Defined accounting

```text
Effective annual rent = gross rent * (1 - vacancy)
Operating expenses = property tax + insurance + maintenance + HOA
                   + owner-paid utilities + other monthly property costs * 12
                   + effective annual rent * management rate
NOI = effective annual rent - operating expenses
Cash flow before capex reserve = NOI - annual debt service
Distributable pre-tax cash flow = NOI - debt service - annual capex reserve
Spent initial cash = down payment + closing costs + initial repairs
Initial cash required = spent initial cash + held operating reserves
Cash-on-cash = distributable pre-tax cash flow / initial cash required
```

Initial operating reserves are held cash, not a spent operating expense. They
are included in committed initial capital for this model's cash-on-cash ratio.
Annual capex reserve is an ongoing set-aside, separate from initial repairs and
the operating buffer. Changing either reserve must not change NOI or count the
same money twice. Existing `cash_invested_estimate` reports spent initial cash;
new `initial_cash_required` includes the held buffer.

Cap rate uses operating NOI / purchase price. `dscr` explicitly uses NOI / annual
debt service in this educational model. Actual lender reserve and coverage
conventions may differ; this is not qualification underwriting. For a cash
purchase, DSCR is null, not zero or infinity. Zero initial capital also makes
cash-on-cash null. The UI explains these states instead of failing to format them.

This is a deliberate correction to v1, where capex reserves reduced reported
NOI/cap rate/DSCR. Existing v1 comparisons must not silently treat those model
definitions as equivalent. Cash flow still deducts capex reserves.

## Break-even and amortization

The rent per rented unit required to cover operating expenses, debt service and
capex reserve is:

```text
(fixed monthly operating costs + monthly loan payment + annual capex reserve/12)
----------------------------------------------------------------------------
                rented units * (1 - vacancy) * (1 - management rate)
```

No rented units or no retained rental income with positive costs returns null
and `no_rent_capacity`. Fully vacant and 100% management-cost stress cases are
valid scenarios. With rented units, no retained income and zero costs, zero rent
is cash-flow neutral. Full vacancy does not eliminate fixed property costs.

Fixed-rate amortization handles zero interest and uses a numerically stable
payment expression near zero rates. First-year interest, principal and ending
loan balance are separate outputs; principal reduction is not added again to
cash flow. Loan payments are calculated unrounded, so multiplying a displayed
cent-rounded payment can differ slightly from annual totals. This is not a
loan-servicing ledger.

Owner-occupied comparable rent is context only, not collected income. The
provided expenses are for the whole property; this is not a tax allocation of
owner-occupied costs.

## API/UI additions and limits

Inputs added: `initial_repairs`, `initial_operating_reserves`, `annual_hoa`, and
`annual_owner_paid_utilities`, all defaulting to zero for old clients.
Outputs added: initial capital, reserve details, cash flow before reserve,
break-even rent/status, first-year loan accounting, and model version.
Null ratio responses are an intentional contract correction.

No mortgage insurance, variable-rate loans, refinancing, lender qualification,
depreciation, sale tax, appreciation/exit model, price optimization, or automatic
rent sourcing is implied. They require later explicit inputs/models. Current
property amounts are bounded; unit counts and loan terms are validated.

Independent tests reconcile known cash flows and reserve changes, Decimal
amortization, break-even inversion, no-debt/zero-capital cases, and extreme
vacancy/management cases. API and real HTTP UI tests verify new fields and nulls.

Context: [Fannie Mae operations definitions](https://multifamily.fanniemae.com/media/35991/display)
distinguish NOI and cash flow after replacement reserves. Our NOI-based coverage
ratio is explicitly a model convention, not a claim to reproduce lender rules.
