# Blocker audit and release decisions

Latest progress: [installed fundamental refresh](fundamental-refresh.md) updated
all 88 installed SEC sources, advancing eight share references and increasing
usable estimates to 64. Ten remain stale despite successful retrieval. Full
class/share evidence, membership and public rights remain separate open gates.

Latest evidence progress: [class and financial evidence](class-and-financial-evidence.md)
adds two dated registered-class corroborations and conservative liability
recovery. Financial states are now 39 pass / 22 fail / 27 unavailable;
465 software tests pass. Full canonical identity, current class/share valuation,
membership and public permissions remain open.

Progress after audit: [daily price refresh](daily-stock-refresh.md) now stages
and atomically publishes all 89 installed IEX series, with resume/rollback,
freshness UI and 445 passing tests. The installed cutoff is October 30; the
original audit counts below describe the pre-refresh October 28 snapshot.
This closes the operator-run refresh slice, not scheduling, source refresh,
SIP adoption, evidence verification or public-data permissions.

Audited October 31, 2026 (America/Los_Angeles). This is the current feasibility
and scope reference; the ten-stage stock → rental → comparison order remains.
It supersedes earlier suggestions that source downloads alone will activate
verified recommendations, or that all free Alpaca history is necessarily IEX-only.

## Executive decision

The software can become a useful local investment decision workspace at zero
data-subscription cost. A public app serving current provider-backed stock
recommendations is **not yet a cleared release commitment**. Access, data quality,
public-display rights, and implementation are four different gates.

Keep the existing strict gates. Do not flip verification booleans, relabel ETF
holdings as official membership, or call filing estimates exact market caps.
Keep the S&P 500 recommendation objective; do not silently replace it with another
universe. A different release scope needs the user's explicit choice.

Approved first-release packaging, explicitly chosen by the user November 6, 2026:

- Local research edition: actual installed data under the user's permitted
  access, disclosed estimates, supported coverage, session-only finances and
  user-controlled reports. Research decisions can be useful without claiming
  certified inputs, complete suitability or demonstrated outperformance.
- Public demonstration edition: original synthetic fixtures and/or individually
  cleared sources only, with no bundled restricted snapshots, real-data screenshots
  or downloaded reports. Source-linked provider pages are not permission to copy.
  Independently of synthetic stock examples, visitors can use real user-entered
  goal, allocation and specific-property calculations without a provider feed,
  once privacy/deployment acceptance passes. The whole public application need
  not be a fictional exercise; automatic real-data stock discovery is the
  restricted capability.
- Public real-data edition: remains a separate gate until applicable display,
  derived-output and redistribution permissions are established. A user's own
  API key or an educational disclaimer does not itself establish those rights.

The user explicitly approved the local research/public demo sequence on November
6. Public full-index real-data recommendations remain conditional later work.
Earlier clarification questions were not consent; the November 6 selection is.
This changes first-release packaging/acceptance, not source rights, strict
verification gates, the two-domain requirement or the free-data budget.

## What was actually checked

Installed source/strategy audit:

- 505 proxy reference securities, 88 financial issuers, 89 price series including
  SPY; 89,266 observed security-date rows through October 28.
- Financial statuses: 36 pass, 21 fail, 31 unavailable. Missing financial checks
  occur in 43 issuers: 31 unavailable plus 12 with mixed missing/failed checks.
  Five issuers have financial-vintage/age concerns. These categories overlap.
- Valuation: 63 estimates, seven stale, 12 multiple-security cases, six unavailable.
- Listing cross-check: 501 corroborations, four unresolved proxy symbols.
  This does not prove legal class identity or official index membership.

Artifacts (ignored local outputs, no user finances):

- `output/audits/blocker-audit-2026-10-31.json`
- `output/audits/blocker-details-2026-10-31.json`
- `output/audits/alpaca-feed-feasibility-2026-10-31.json`
- `output/audits/alpaca-split-window-feasibility-2026-10-31.json`

The two bounded feed probes requested AAPL, NVDA and SPY, raw/split/all, for
October 27–29, 2026 and June 6–11, 2024. All 12 requests returned usable small
samples, for both IEX and SIP. June includes four observed trading days around
NVIDIA's split. Response hashes/dates/counts are recorded; quote values and
credentials are not included in reports. No plan/account/billing changes,
trades or production snapshot publication occurred. The app still uses its
existing IEX snapshot. Sample access does not establish every free account's
entitlements, full-history accuracy, exact dividend reinvestment or public rights.

## Stock blockers: disposition and acceptance

| Blocker | What the audit establishes | Required implementation or release decision | Acceptance evidence |
| --- | --- | --- | --- |
| Strict selection is unfinished | `stock_portfolio.py` is a readiness checker: selected list has maximum length zero; evidence flags are literal false. Synthetic/experimental selection exists separately. | Implement a server-owned verified-evidence contract and selection adapter after source criteria are satisfied. Preserve experimental separation. | Source fixtures can produce a verified proposal only when every gate passes; altered/missing/future/stale evidence cannot. No client certification. |
| Official dated S&P membership | Sponsor holdings are a proxy. The official S&P page's accessible full-list link did not provide a usable constituent dataset in this review. This does not prove free access impossible. | Obtain a permitted dated complete source; otherwise retain proxy labels and withhold official-index claims. User approval required to change universe promise. | Complete source rows, dates, identity joins, additions/removals, permissions; independent membership reconciliation. |
| Exact security identity | SEC directory + listing corroboration are helpful but not legal class mapping. | Use issuer filing cover-page class/symbol/exchange evidence plus current directory/listing references. Start with supported single-common-class cases; quarantine aliases, rights, preferreds, ADRs and ambiguous classes. | Dated/hash-bound issuer/security evidence, reviewed examples, class-change and ticker-reuse adversarial tests. |
| Missing annual inputs | 43 issuers have missing checks. Main missing rule inputs include cash capex (23), operating income (15), liabilities (16), and derived FCF (25); these overlap and are not negative business facts. | Review exact filing/tag/context gaps. Add only justified same-vintage semantic mappings/reconciliations with independent fixtures. Preserve unsupported custom-tag cases; do not assume missing capex is zero. | Source statement ties, fiscal/accession alignment, absent/ambiguous input tests, before/after coverage. |
| Current valuation | No installed market cap is verified. Twelve issuers have multiple directory securities; not all necessarily represent equivalent common economic classes. | Build a class-aware ledger and source-supported share-count estimates with measurement/file dates, split treatment and uncertainty. Exclude unsupported classes. Do not require or promise perfectly known real-time shares. Any replacement for the legacy exact-verification requirement needs a new clearly named research contract and user-approved scope. | Class quantities/prices reconcile; issuance/repurchase/staleness scenarios are disclosed; no weighted-average-share substitution or one-class price for all classes. |
| Consolidated daily prices | Historical SIP samples are accessible with configured credentials; prior blanket IEX-only conclusion was too strong. | Add a separately versioned, explicitly configured delayed/EOD SIP importer after broad-window testing. Never mix IEX and SIP bars inside one series or silently switch feeds. No subscription fallback. | Full intended periods, splits/dividends/spin-offs, benchmark, missing sessions, independent sampled closes and feed provenance. |
| Return basis | Provider all-adjusted prices are not proof of exact reinvested distributions. | Keep price-only and provider-adjusted proxy labels. Exact total-return claims require corporate-action/distribution ledger evidence; optional for a clearly labeled research v1, not silently optional for the existing strict strategy. | Separately checked splits, distributions, reinvestment timing, fees and aligned SPY basis. |
| Reliable daily refresh | Existing merges require the same completed interval/directory; they cannot safely roll all 89 series forward as a daily job. | Stage all required series at one completed cutoff, validate the full candidate, atomically publish once, record failures, retain last-known-good and support rollback. Add resumable bounded batches and source/reference refresh. | Failed batch, interruption, concurrent writer, stale source, holiday/early-close and rollback tests. No partial snapshot advertised as current. Scheduling is a later explicit action. |
| Full-universe scale | Current importer/store cap is 100 securities, batches at most 24 issuers plus SPY; 88 issuers are not full coverage. | Use bounded per-series artifacts/manifests and selective reads; measure memory/request budgets before expanding. Audit every reference row, including excluded and unanalysed companies. | Full declared universe accounted for, cache/quota behavior measured, bounded startup/lookup/refresh memory and latency. No assertion every constituent must be eligible. |
| Strategy effectiveness | Five-factor quality/value is a testable hypothesis, not demonstrated alpha. | Freeze policy, retain baselines, start prospective evaluation. Historical walk-forward requires historical membership, contemporaneous filings/valuation and removed-security coverage. | Matched SPY/equal-weight/quality-only/value-only evaluation, costs, drawdown, turnover, losses and out-of-sample observations. No release date promises statistical proof. |
| News and calendars | SEC filing metadata and two manual announcements are not broad news coverage. | Source-linked filing/issuer-event context first; expand only permitted feeds. Distinguish confirmed dates from estimates and disclose missing coverage. | Publication timestamps, source links, duplicate/correction handling and visible gaps. News does not become a guessed causal price explanation or sentiment buy trigger. |
| Holdings decisions | Experimental triage exists, not a complete thesis/sell policy. | Dated thesis and changes; issuer/fund overlap where supported; explicit cost/tax input support before computing liquidation outcomes. No automatic rank-drop sell. | Refresh-to-reason diffs, unchanged-evidence stability, uncertainty precedence, cost/tax limitations and user override history. |
| Portability and goals | Goal PDFs exist; stock/rental decision PDFs and full restore/change review do not. Monthly contribution intentions are recorded only. | Bounded versioned JSON restore, named snapshots/shortlists, stock PDF with evidence/limitations, and constrained recurring-cash allocation. | Round-trip and hostile-file checks, exact cents, scenario/source/version retention, visually checked reports, no private global state. |

An estimation problem is not cured by paying for an API. Even a provider market
cap needs class/quantity/date definitions. The attainable claim is traceable,
checked inputs with explicit assumptions, not 100% certainty about current value.

## Public/data permissions

Alpaca's [published redistribution answer](https://alpaca.markets/support/redistribute-alpaca-api)
says API data cannot be redistributed through a platform. Its
[terms](https://files.alpaca.markets/disclosures/library/TermsAndConditions.pdf)
also distinguish personal use from an application serving others. Standard
credential access is not evidence that this project has a public display grant.
Do not publish quote charts, derived outputs or cached data on that assumption.
Written/provider-specific authorization or another explicitly permitted source
is needed for the intended public scope; none was obtained in this audit.

S&P's [disclaimers](https://www.spglobal.com/spdji/en/disclaimers/) restrict
reproduction/redistribution of its content without permission. A visible table
or official membership download would not by itself clear our deployed use.
The ETF sponsor holdings, Nasdaq directory and Zillow Research roles each need
their own rights determination; attribution alone has not been established as
sufficient. No missing permission is marked approved in `source_policy.py`.

Free accounts remain allowed; paid data/trials/billing remain excluded. No provider
was contacted or agreement accepted on the user's behalf. If necessary, prepare
a concrete request describing audience, data fields, cache, charts, exports and
derived recommendations for the user to send. Do not assume a provider will agree.

## Rental blockers remain part of the final product

| Blocker | Supported finding / final product implication | Required next work after stocks |
| --- | --- | --- |
| Geographic scope | Existing 92-area Census 2020 land-overlap set is not a complete current residential USPS ZIP universe; eight cross county boundaries. | Dated ZCTA map with border labels or a supported current residential crosswalk. Use exact county/address checks for specific properties. |
| Property-compatible ZIP rent | Audited single-family values cover 89 candidate areas; mixed-property rent covers 81. Audited single-family rent is metro-level. Those cannot establish SFR ZIP yields. | Keep map/discovery for dated market context, user-entered rent scenarios and explicit source/provenance. Automated SFR ZIP cash-flow ranking requires compatible licensed rent coverage; do not replace it silently with mixed rent. |
| HUD context | HUD SAFMR is a ZIP/bedroom program benchmark, not an individual SFR rent quote. Previously attempted workbook access returned no usable body. | Validate actual downloaded rows before enabling HUD context. Label gross rent/utilities and program purpose; never call it verified achievable rent. |
| Listings | No cleared automated listing inventory. | Manual exact-property scenarios remain a valid initial workflow. Listing scraping is not an assumed solution. |
| Decision integration | Underwriting and monthly stress engines exist; map-to-property, named comparisons and reports are incomplete. | Carry context into a specific property, validate required rent/funding, compare and export with all due-diligence unknowns. |
| Shared comparison | Tax and cashflow bases are not yet aligned end to end. | Same starting/recurring funding and horizon; stock fees/cash vs rental reserves/debt/repair/sale costs/liquidity/workload. Pre-tax first; no unsupported after-tax superiority. |

The market-context map → property underwriting → stress → comparison path is
feasible without pretending we have a free complete property scanner. Automatic
ZIP rent/yield matches and public Zillow display stay conditional on evidence
and rights. This is an explicit fallback proposal, not removal of the user's
rental-scanner goal.

## Privacy, production and interview acceptance

- Preserve session-only private inputs and optional private downloads; do not
  require financial accounts, names, or server-side financial profiles.
- Verify session isolation, clear-session behavior, private logs/errors, bounded
  report uploads/downloads and retention. Localhost correctness is not hosting
  security certification.
- CI configuration exists; no remote run/cloud deployment was verified here.
  Add reproducible packaging/container build, HTTPS/reverse-proxy limits and
  rollback deployment only for a scope whose sources are cleared.
- Measure concurrent sessions, repeated company navigation, heavy report/math
  jobs and peak refresh memory. Introduce a worker if measured blocking justifies
  it. A Redis/Celery/microservice checklist is not proof of engineering quality.
- A real novice should complete investigate → compare → save → revisit tasks.
  Record observed problems and timings; large feature/test counts are not a
  usability study or investment-performance evidence.

## Finite next implementation sequence

1. Release-scope choice completed November 6; keep all strict evidence gates intact.
2. Build versioned daily staging/atomic refresh with recovery, and an isolated SIP
   candidate dataset. Validate broad intended history before adoption. Do not
   schedule a recurring job until requested.
3. Build exact security evidence and class/share ledger for a declared supported
   cohort; resolve financial gaps with reference fixtures. Obtain membership/
   display permissions or take the explicitly approved alternative scope.
4. Implement the actual strict selection adapter only against satisfied evidence
   contracts; otherwise keep it withheld. Complete thesis/restore/PDF/recurring
   allocation and prospective evaluation acceptance for the chosen research mode.
5. Complete rentals under the approved source scope, then fair shared comparisons,
   usability, measured performance and the permitted public package.

No open-ended data-provider hunting: treat an explicit applicable grant as pass,
an explicit restriction as blocked for that use, and unconfirmed coverage as
unavailable. Do not design required launch features around hoped-for permission.
If full public real-data scope is mandatory, securing a no-cost applicable data
arrangement is a release prerequisite, with no promised completion date.

## Approved release sequence, November 6

**Approved:** finish local actual-data research and a public synthetic/cleared
demo first, preserving official full-index/public real-data recommendations as
conditional gates. This guarantees a concrete buildable package, not alpha.

**Unselected alternative:** keep publicly hosted real-data recommendations as mandatory v1.
Then first secure a no-cost applicable data arrangement; do not declare public
launch feasible until that passes. Continue unaffected engine/test work while
that requirement is unresolved. Neither choice permits spending money.

## Additional academic validation route

[UCI Libraries lists S&P Capital IQ](https://guides.lib.uci.edu/business/global/companies)
for active faculty, staff and enrolled students. Harvard's
[constituent guide](https://www.library.hbs.edu/services/help-center/index-constituents)
documents an S&P 500 constituent export in Capital IQ. This makes institutionally
permitted academic cross-checks a concrete lead, **not verified access for this
user or an export/public-display grant for this project**. The UCI page's direct
fetch returned 429; its official indexed guide supplied the availability details.
No account was accessed or registered.

[UCI WRDS guidance](https://guides.lib.uci.edu/merage-resources/wrds) restricts WRDS
to scholarly, non-commercial research and describes supervised undergraduate
research-assistant registration with a faculty advisor. Dataset subscriptions
are not confirmed until an authorized user checks them. Do not invent an advisor,
enroll, scrape, or assume CRSP/Compustat availability. Academic data cannot be
reused for personal investing or public serving without the applicable permission.
Keep any approved academic validation dataset separate from deployable artifacts.

This route may help evaluate membership or historical selection academically;
it is optional, not a new required paid account or guaranteed public-data solution.

## Primary sources reviewed

- [Alpaca historical feed FAQ](https://docs.alpaca.markets/us/docs/market-data-faq):
  describes older SIP access without a subscription. A separate
  [historical guide](https://docs.alpaca.markets/us/docs/historical-stock-data-1)
  gives narrower free-feed wording; bounded successful requests, not speculation,
  establish the configured credential's sampled access.
- [Historical bars reference](https://docs.alpaca.markets/us/reference/stockbars):
  feed/adjustment parameters and as-of symbol mapping; mapping is not membership.
- [SEC API definitions](https://www.sec.gov/search-filings/edgar-application-programming-interfaces):
  entity-wide non-custom facts explain why Companyfacts cannot supply every input.
- [Apple FY2025 cover page](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm):
  demonstrates available class/symbol/exchange evidence; not a completed master.
- [S&P index page](https://www.spglobal.com/spdji/en/indices/equity/sp-500/):
  inspected current public interface; no full dataset was verified from that view.
- [Zillow categories/methodology](https://www.zillow.com/research/data/) and
  [terms](https://www.zillow.com/corporate/terms-of-use/): regional indices are not
  parcel rent quotes; no blanket public license inferred, no listing scraping.
- [HUD SAFMR](https://www.huduser.gov/portal/datasets/fmr/smallarea/index.html):
  program-level ZIP benchmarks. Not a type-matched SFR rent source.

## Verification

Six new diagnostic tests pass: fixed host/bounded requests, no secret/error-body
output, refused oversized-date/future/empty requests, missing symbols/pagination,
and no subscription/publication flags. Latest application full suite remains
419 passed from the previous milestone; it was not rerun for this isolated
diagnostic and documentation audit. No live recommendation flags were changed.
