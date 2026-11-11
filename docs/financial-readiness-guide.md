# Financial readiness guide scope

The `POST /scenarios/readiness-check` endpoint provides a small educational self-check before a user compares investing strategies. It does not produce a readiness score, name a best strategy, or determine whether an investment is suitable.

## Inputs and interpretation

- **Emergency reserve:** The user enters savings set aside for emergencies, monthly essential expenses, and their own target months. The engine returns months covered, target amount, and the gap to that target. It does not hard-code a universal emergency-fund amount. The CFPB says the amount needed depends on a person's circumstances and describes emergency savings as a way to manage unplanned expenses.
- **Debt cost:** The user may enter a balance at the highest APR and the APR that applies to it. To flag an APR comparison, the user must also set their own comparison threshold. There is no application-defined high-interest cutoff, and a result below the threshold does not say that investing is preferable. Investor.gov includes paying off high-interest debt in its investor-preparedness checklist; this tool only prompts users to compare debt cost with uncertain investment outcomes.
- **Liquidity horizon:** The user may state when they expect to need the funds. For horizons of five years or less, the guide repeats Investor.gov's caution that risky investments may need to be sold at a loss when the money is needed. It also asks users to check access restrictions and exit costs. This prompt does not characterize a particular strategy or asset as liquid.
- **Time:** The user may enter available monthly hours and estimated strategy hours. Fit is `None` unless both are provided. The guide names different workload drivers for portfolios, rentals, and flips, but does not claim that a strategy has a universal time requirement.
- **Risk willingness and capacity:** The user separately rates willingness to accept volatility/loss and ability to absorb a financial loss on a 1-to-5 scale. The engine reports the difference and a reflection prompt; the ratings are self-reported and do not produce a risk score or allocation.

## Deterministic method

The engine calculates emergency months as `emergency_savings / monthly_essential_expenses`; target reserve as `monthly_essential_expenses * emergency_fund_target_months`; and target gap as `max(target_reserve - emergency_savings, 0)`. It compares the entered APR and user-selected threshold, and compares estimated workload with available hours. Risk ratings are surfaced as entered with a signed difference (`tolerance - capacity`). A fixed set of validations, comparisons, formulas, and prompt construction makes the calculation O(1) in time and space.

## Source ledger

- Consumer Financial Protection Bureau, [An essential guide to building an emergency fund](https://www.consumerfinance.gov/an-essential-guide-to-building-an-emergency-fund/). The CFPB describes emergency savings for unexpected expenses and says the amount needed depends on personal circumstances.
- U.S. Securities and Exchange Commission, Investor.gov, [Gauge Your Risk Tolerance](https://www.investor.gov/introduction-investing/investing-basics/save-and-invest/gauge-your-risk-tolerance). Investor.gov discusses goals, time horizons, and the risk of having to sell at a loss for goals five years or less.
- U.S. Securities and Exchange Commission, Investor.gov, [Investor Preparedness Checklist](https://www.investor.gov/introduction-investing/general-resources/investor-preparedness-checklist). The checklist includes paying off high-interest debt and understanding risk tolerance.
- FINRA, [Know Your Risk Tolerance](https://www.finra.org/investors/insights/know-your-risk-tolerance). The article distinguishes ability from willingness to accept investment risk and discusses goals, time horizon, liquidity, and reliance on invested funds.

These sources provide general education, not individualized recommendations. The review output should be revisited when goals, debts, expenses, time availability, or other circumstances change.
