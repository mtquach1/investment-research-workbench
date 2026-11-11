# 2026 Tax Rule Source Ledger

This project is an educational estimate for a single W-2 filer. These sources support the published rule values used in the engine; they do not make the model a tax-return calculation. Confirm the source material again when updating a tax year.

## Values used by the current model

| Rule | Model value | Primary source |
| --- | ---: | --- |
| Single standard deduction | $16,100 | [IRS, Working Families Tax Cuts – Individuals and Workers](https://www.irs.gov/newsroom/working-families-tax-cuts-individuals-and-workers) |
| Federal ordinary income bracket ceilings | $12,400; $50,400; $105,700; $201,775; $256,225; $640,600 | [IRS, Working Families Tax Cuts – Individuals and Workers](https://www.irs.gov/newsroom/working-families-tax-cuts-individuals-and-workers) |
| Base employee 401(k) elective deferral limit | $24,500 | [IRS, 401(k) limit increases to $24,500 for 2026](https://www.irs.gov/newsroom/401k-limit-increases-to-24500-for-2026-ira-limit-increases-to-7500) |
| IRA annual limit | $7,500 | [IRS, 401(k) limit increases to $24,500 for 2026](https://www.irs.gov/newsroom/401k-limit-increases-to-24500-for-2026-ira-limit-increases-to-7500) |
| IRA age-50 catch-up | $1,100 | [IRS, 401(k) limit increases to $24,500 for 2026](https://www.irs.gov/newsroom/401k-limit-increases-to-24500-for-2026-ira-limit-increases-to-7500) |
| Single direct Roth IRA phase-out | $153,000–$168,000 MAGI | [IRS, 401(k) limit increases to $24,500 for 2026](https://www.irs.gov/newsroom/401k-limit-increases-to-24500-for-2026-ira-limit-increases-to-7500) |
| Social Security wage base | $184,500 | [Social Security Administration, Contribution and Benefit Base](https://www.ssa.gov/OACT/cola/cbb.html) |
| Employee Social Security and Medicare rates | 6.2% and 1.45% | [Social Security Administration, Contribution and Benefit Base](https://www.ssa.gov/OACT/cola/cbb.html) |
| Single Additional Medicare Tax threshold and rate | $200,000 and 0.9% | [IRS, Questions and Answers about Additional Medicare Tax](https://www.irs.gov/businesses/small-businesses-self-employed/questions-and-answers-about-the-additional-medicare-tax) |

## Model boundaries

October 28 eligibility correction: the direct Roth calculation now limits IRA
capacity by modeled taxable W-2 compensation (gross less traditional employee
401(k) deferrals), applies upward $10 rounding and the $200 phaseout minimum
subject to compensation/aggregate capacity, and distinguishes prior traditional
contributions from prior Roth contributions. The new
`annual_traditional_ira_contributions_already_made` field is a subset of the
existing total prior IRA contributions. Unspecified prior contributions retain
the conservative legacy interpretation as Roth contributions. This is not an
affordability check or an excess-contribution correction workflow.

The method is based on [IRS Publication 590-A, Worksheet 2-2](https://www.irs.gov/publications/p590a),
using the separately sourced 2026 limits above. The currently published worksheet
is for 2025; its 2025 numerical example is independently tested with explicit
2025 parameters. Recheck when the 2026 edition is published.

- The 401(k) calculation applies the $24,500 base limit uniformly. It does not calculate age-based 401(k) catch-up limits, the higher limit for ages 60–63, or the Roth catch-up requirement for certain higher-paid employees.
- The model estimates Roth IRA MAGI from modeled AGI plus user-entered adjustments. It does not reproduce every IRS MAGI worksheet adjustment.
- State income tax is an illustrative flat-rate estimate, not a state-specific tax calculation.
- The estimate omits credits, capital gains, qualified dividends, AMT, NIIT, local taxes, detailed deduction limitations, and special deductions introduced for 2026.
- Payroll calculations assume one employer and W-2 wages; they do not coordinate multiple employers or account for self-employment income.

The tested values are regression anchors, not a substitute for reviewing current IRS and SSA materials when changing the tax-year table.
