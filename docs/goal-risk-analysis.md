# Goal risk analysis model

`POST /scenarios/goal-risk-analysis` simulates an educational distribution of ending balances from assumptions supplied by the user. It complements the deterministic low/base/high goal planner; it does not forecast returns or recommend an investment.

## Model

For annual expected return assumption `r`, annual fee `f`, and annualized volatility `sigma`, the model sets monthly volatility to `sigma / sqrt(12)` and monthly log-return drift to:

```text
monthly_log_mean = ln(1 + r - f) / 12 - monthly_volatility^2 / 2
monthly_gross_return = exp(monthly_log_mean + monthly_volatility * Z)
```

`Z` is an independent standard normal draw for each month and path. This calibrates the annual arithmetic expected return after the fee to `r - f`, subject to floating-point precision. Each month the existing balance earns the simulated return, then the fixed contribution is added at month end. The model starts with the current balance, and keeps contributions fixed in nominal dollars. It does not model contribution growth.

The goal amount is entered in today's dollars and inflated deterministically to the target year. The response reports the empirical share of paths ending at or above that future-dollar target. The p10, median, and p90 ending balances are deflated back to today's dollars. Quantiles use linear interpolation between sorted samples.

## Repeatability and bounds

The API accepts 100–5,000 paths, a 1–60 year horizon, and a non-negative integer seed. The default is 2,000 paths and seed 42. Repeating the same request with the same implementation and Python runtime produces the same paths and results. Changing seed or assumptions changes the simulation. Since the service uses bounded input counts, maximum work is 3.6 million monthly path steps per request.

The reported goal probability is a Monte Carlo estimate, so finite samples introduce sampling error; it is not a probability established by market data. Increasing path count can reduce sampling noise, at additional compute cost.

## Limitations

Returns are independent and identically distributed lognormal monthly draws. The model excludes fat tails, volatility clustering, correlations across assets, changing market regimes, taxes, contribution changes, withdrawals, and liquidity constraints. It uses a constant user-entered inflation assumption. The resulting percentiles describe only the chosen mathematical model; they are not confidence intervals for real-world wealth. No external market data is used.
