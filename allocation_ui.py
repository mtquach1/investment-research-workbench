"""Session-only editor and result view for the shared allocation engine."""

from decimal import Decimal

import pandas as pd
from pydantic import ValidationError
import streamlit as st

from allocation_engine import allocate_contributions
from allocation_models import AllocationRequest


def example_allocation():
    return {
        "assets": [
            {"asset_id": "STOCKS", "target_weight": "0.60", "max_weight": "0.80"},
            {"asset_id": "BONDS", "target_weight": "0.40", "max_weight": "0.80"},
        ],
        "accounts": [
            {"account_id": "taxable", "account_type": "taxable", "available_cash": "2000.00",
             "holdings": {"STOCKS": "8000.00"}, "allowed_assets": ["STOCKS", "BONDS"]},
            {"account_id": "roth", "account_type": "roth", "available_cash": "2000.00",
             "holdings": {"BONDS": "2000.00"}, "allowed_assets": ["BONDS"]},
        ],
    }


def render_allocation():
    st.subheader("Contribution allocator")
    st.write("Turn existing holdings and available account cash into purchases that get as close as possible to your target weights.")
    st.caption("Choose your own targets. This version minimizes allocation drift; it does not choose investments, optimize taxes, or place trades. All cash must already be available in its account.")
    example = example_allocation()
    with st.form("allocation_editor"):
        st.markdown("**1. Assets and portfolio targets**")
        st.caption("Weights are percentages and targets must total 100. Identifiers use letters, numbers, dots, underscores, or hyphens.")
        assets = st.data_editor(pd.DataFrame([
            {"asset_id": asset["asset_id"], "target_pct": float(asset["target_weight"])*100,
             "maximum_pct": float(asset["max_weight"])*100} for asset in example["assets"]
        ]), num_rows="dynamic", hide_index=True, key="allocation_assets", width="stretch")
        st.markdown("**2. Account cash and purchase permissions**")
        st.caption("Use generic account labels. Separate permitted asset identifiers with commas. Cash is the amount you want fully invested; keep reserves outside this amount.")
        accounts = st.data_editor(pd.DataFrame([
            {"account_id": account["account_id"], "account_type": account["account_type"],
             "cash": float(account["available_cash"]), "allowed_assets": ",".join(account["allowed_assets"])}
            for account in example["accounts"]
        ]), num_rows="dynamic", hide_index=True, key="allocation_accounts", width="stretch",
            column_config={"account_type": st.column_config.SelectboxColumn(options=["taxable", "traditional", "roth"], required=True)})
        st.markdown("**3. Existing holdings at current dollar values**")
        holdings = st.data_editor(pd.DataFrame([
            {"account_id": account["account_id"], "asset_id": asset, "value": float(value)}
            for account in example["accounts"] for asset, value in account["holdings"].items()
        ]), num_rows="dynamic", hide_index=True, key="allocation_holdings", width="stretch")
        submitted = st.form_submit_button("Optimize purchases", type="primary")
    if submitted:
        st.session_state.pop("_allocation_result", None)
        st.session_state.pop("_allocation_inputs", None)
        try:
            payload = {"assets": [
                {"asset_id": row["asset_id"], "target_weight": Decimal(str(row["target_pct"]))/100,
                 "max_weight": Decimal(str(row["maximum_pct"]))/100} for row in assets.to_dict("records")
            ], "accounts": []}
            by_account = {}
            for row in accounts.to_dict("records"):
                account = {"account_id": row["account_id"], "account_type": row["account_type"],
                           "available_cash": str(row["cash"]), "holdings": {},
                           "allowed_assets": [item.strip() for item in row["allowed_assets"].split(",") if item.strip()]}
                if account["account_id"] in by_account:
                    raise ValueError("Duplicate account")
                by_account[account["account_id"]] = account
                payload["accounts"].append(account)
            for row in holdings.to_dict("records"):
                account = by_account[row["account_id"]]
                if row["asset_id"] in account["holdings"]:
                    raise ValueError("Duplicate holding")
                account["holdings"][row["asset_id"]] = str(row["value"])
            request = AllocationRequest.model_validate(payload)
        except (ValidationError, ValueError, KeyError, TypeError, ArithmeticError, AttributeError):
            st.error("Review the tables: use unique identifiers, declared assets and accounts, nonnegative amounts with at most two decimals, valid account types, and targets totaling 100%.")
        else:
            with st.spinner("Solving the constrained purchase plan…"):
                st.session_state["_allocation_result"] = allocate_contributions(request)
            st.session_state["_allocation_inputs"] = request.model_dump(mode="json")
    result = st.session_state.get("_allocation_result")
    if result is None:
        st.info(r"The illustrative starting example has \$10,000 invested and \$4,000 to add. Submit it, then try restricting purchases or tightening maximum weights.")
        return
    st.markdown("**Last submitted plan**")
    st.caption("Results correspond to the submitted input snapshot below. Submit again after editing the tables.")
    if result.status != "optimal":
        st.warning(result.explanation)
    else:
        st.success("Purchase plan found within your account budgets and concentration limits.")
        left, right = st.columns(2)
        left.metric("Cash allocated", f"${result.cash_to_invest_cents/100:,.2f}")
        right.metric("Absolute allocation drift", f"{result.absolute_weight_drift*100:.4f} pp",
                     help="Sum of absolute differences between final and target weights. Lower is better for this objective; zero exactly matches targets.")
        st.dataframe(pd.DataFrame([
            {"Account": trade.account_id, "Asset": trade.asset_id, "Purchase ($)": trade.amount_cents/100}
            for trade in result.trades
        ], columns=["Account", "Asset", "Purchase ($)"]), hide_index=True, width="stretch")
        exposures = pd.DataFrame([
            {"Asset": row.asset_id, "Target (%)": row.target_weight*100, "After (%)": row.after_weight*100}
            for row in result.exposures
        ]).set_index("Asset")
        st.bar_chart(exposures, stack=False)
        st.caption("Drift is measured in percentage points (pp). Lower means closer to your targets; it does not mean higher expected returns.")
        st.markdown("**Same-budget baseline comparison**")
        st.dataframe(pd.DataFrame([
            {"Method": baseline.name, "Satisfies constraints": baseline.feasible,
             "Absolute drift (percentage points)": baseline.absolute_weight_drift*100}
            for baseline in result.baselines
        ]), hide_index=True, width="stretch")
        st.caption("Baselines split cash by permitted target weights, split equally, or fill the largest deficits account by account. A baseline marked false violates a constraint and is not a valid alternative.")
    with st.expander("Submitted inputs, solver evidence, and limitations"):
        st.json(st.session_state["_allocation_inputs"])
        st.json(result.model_dump(mode="json"))
    st.caption("Calculated in this Streamlit process. No AI, saved history, or brokerage connection is used.")
