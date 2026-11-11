# Debt payoff comparison model

`POST /scenarios/debt-payoff` compares two payment orders using a fixed user-entered total monthly payment budget:

- **Avalanche:** Pay each account's minimum first, then apply remaining funds to the outstanding account with the highest APR. Ties go to the smaller current balance, then input order.
- **Snowball:** Pay each account's minimum first, then apply remaining funds to the outstanding account with the smallest balance. Ties go to the higher APR, then input order.

When an account is paid off, its minimum payment stays in the total monthly budget and is redirected to the next account in the priority order. The budget is the sum of entered minimums plus the user's extra monthly payment.

## Calculation and limits

For every month, the simulator adds interest using `balance × (annual_APR / 12)`, rounded to cents, pays fixed minimums, then distributes the remaining budget according to the selected order. It tracks account payoff months, total interest and payment, and remaining balance. It uses O(M × D + D log D) time and O(D) space, where M is the simulation months and D is the debt count. API bounds limit D to 10 and M to 1,200.

These are simplified estimates. Actual card issuers may calculate interest daily, update minimum payments, apply payments under contractual rules, change APRs, or charge fees. The model excludes new spending, late charges, promotional/deferred-interest terms, tax effects, and debt-specific payment allocation rules. CFPB explains that many card issuers calculate interest daily and that payment allocation depends on account terms. Compare the output with current statements and agreements.

The result is a comparison under assumptions, not a recommendation. Avalanche may reduce modeled interest when higher-rate balances are targeted first; snowball may clear smaller accounts earlier. The tool makes no claim about behavior or adherence and does not choose a method for the user.

## Source note

- Consumer Financial Protection Bureau, [How does my credit card company calculate the amount of interest I owe?](https://www.consumerfinance.gov/ask-cfpb/how-does-my-credit-card-company-calculate-the-amount-of-interest-i-owe-en-51/)
- Consumer Financial Protection Bureau, [A box on my credit card bill says that I will pay off the balance in three years if I pay a certain amount. What does that mean?](https://www.consumerfinance.gov/ask-cfpb/a-box-on-my-credit-card-bill-says-that-i-will-pay-off-the-balance-in-three-years-if-i-pay-a-certain-amount-what-does-that-mean-do-i-have-to-pay-that-much-if-i-pay-that-much-and-make-new-purchases-will-i-still-owe-nothing-after-three-years-en-36/)
