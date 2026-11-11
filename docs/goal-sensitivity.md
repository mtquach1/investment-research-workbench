# Goal sensitivity analysis

`POST /scenarios/goal-sensitivity` evaluates how four user-selected ranges affect the deterministic goal projection: annual return, monthly contribution, annual fee, and annual inflation.

For each factor, the service projects the ending account value using its low and high inputs while keeping every other assumption at its base value. It also reports the base projection, the span between the two endpoint balances in today's dollars, and a rank ordered by that span. A higher impact rank means the selected range changes this model's output more; it does not mean the assumption is more likely or that the factor is universally more important.

Ranges must be ordered, within the supported model bounds, and contain the corresponding base assumption. Return, fee, and inflation use decimal fractions in the API. The Streamlit interface displays these as percentages. Monthly contributions and balances use the account currency units supplied by the user.

## Method and limitations

This is one-variable-at-a-time analysis. It does not model interactions between assumptions, assign probability to any low/base/high value, or identify causal effects in real markets. Its output is the inflation-adjusted projected balance from `project_goal`; the result inherits that calculator's monthly compounding, end-of-month contribution, fixed contribution, fee, and inflation assumptions. It uses no market data and is not a forecast or recommendation.
