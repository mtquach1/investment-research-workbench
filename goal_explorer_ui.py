"""Interactive planning workspace built on shared, validated calculation models."""

from dataclasses import asdict
from datetime import datetime, timezone
from uuid import uuid4

import altair as alt
from pydantic import ValidationError
import streamlit as st

from goal_explorer import changed_assumptions, comparison_checkpoints, explore_goal, export_goal_plan, import_goal_plan
from goal_report import REPORT_VERSION, build_goal_report
from schemas import GoalExplorerRequest, GoalExplorerSnapshot
from simulation_engine import analyze_goal_risk


DEFAULTS = {
    "goal_name": "Home down payment", "current_balance": 10_000.0,
    "monthly_contribution": 1000.0, "years": 10, "target_amount_today": 150_000.0,
    "annual_inflation_assumption": 0.03, "annual_fee_assumption": 0.002,
    "return_assumptions": {"low": 0.02, "base": 0.06, "high": 0.09},
}


def _money(value):
    return f"-\u0024{abs(value):,.2f}" if value < 0 else f"${value:,.2f}"


def _adjust_contribution():
    st.session_state["explorer_monthly"] = st.session_state["explorer_monthly_adjust"]


def _use_contribution(value):
    st.session_state["explorer_monthly"] = value


def _input_values(inputs):
    return {
        "name": inputs["goal_name"], "balance": inputs["current_balance"],
        "monthly": inputs["monthly_contribution"], "years": inputs["years"],
        "target": inputs["target_amount_today"],
        "fee": inputs["annual_fee_assumption"] * 100,
        "inflation": inputs["annual_inflation_assumption"] * 100,
        **{name: value * 100 for name, value in inputs["return_assumptions"].items()},
    }


def _chart(result, basis, inspection_year):
    rows = []
    for scenario in result.scenarios:
        for point in scenario.timeline:
            rows.append({"Year": point.year, "Amount": getattr(point, f"balance_{basis}"),
                         "Series": f"{scenario.summary.scenario.title()} return"})
    for point in result.scenarios[1].timeline:
        rows.extend([
            {"Year": point.year, "Amount": getattr(point, f"contributions_{basis}"),
             "Series": "Starting balance + deposits"},
            {"Year": point.year, "Amount": getattr(point, f"target_{basis}"), "Series": "Goal"},
        ])
    colors = alt.Scale(
        domain=["Low return", "Base return", "High return", "Starting balance + deposits", "Goal"],
        range=["#a85f20", "#157f83", "#7061b5", "#73808d", "#c34d69"],
    )
    lines = alt.Chart(alt.Data(values=rows)).mark_line(strokeWidth=2.5).encode(
        x=alt.X("Year:Q", axis=alt.Axis(tickMinStep=1), title="Years from now"),
        y=alt.Y("Amount:Q", title="Today's dollars" if basis == "today" else "Future dollars",
                axis=alt.Axis(format="~s")),
        color=alt.Color("Series:N", scale=colors, legend=alt.Legend(orient="bottom", columns=2)),
        strokeDash=alt.StrokeDash("Series:N", legend=None),
        tooltip=[alt.Tooltip("Year:Q", format=".0f"), "Series:N", alt.Tooltip("Amount:Q", format="$,.2f")],
    )
    marker = alt.Chart(alt.Data(values=[{"Year": inspection_year}])).mark_rule(
        color="#64748b", strokeDash=[4, 4], opacity=0.6,
    ).encode(x="Year:Q")
    st.altair_chart((lines + marker).properties(height=350), width="stretch")


def render_goal_explorer():
    # Permanent copies survive Streamlit's cleanup of widgets when navigating pages.
    pending = st.session_state.pop("_explorer_pending", None)
    pending_label = st.session_state.pop("_explorer_pending_label", None)
    if pending_label:
        st.session_state["explorer_label"] = pending_label
    if pending:
        st.session_state["explorer_inspect"] = pending["years"]
    inputs = pending or st.session_state.get("_explorer_inputs", DEFAULTS)
    for key, value in _input_values(inputs).items():
        widget_key = f"explorer_{key}"
        if pending or widget_key not in st.session_state:
            st.session_state[widget_key] = value

    st.markdown("**Set a goal. Explore the tradeoffs. Keep a plan.**")
    st.caption("Adjust any assumption to update the plan. These are hypothetical outcomes, not forecasts.")
    layout = st.radio("Workspace layout", ["Chart first", "Side by side"], horizontal=True,
                      help="Chart first keeps the results full width on smaller screens.", key="explorer_layout")
    if layout == "Side by side":
        controls, canvas = st.columns([1, 2.3], gap="large")
    else:
        controls = st.expander("1 · Set your goal and monthly budget", expanded=False)
        canvas = st.container()
    with controls:
        st.markdown("**Your goal**")
        name = st.text_input("Goal name", max_chars=80, key="explorer_name",
                             help="Use a generic label. No name, address, account number, or login is needed.")
        target = st.number_input("Goal cost today ($)", min_value=0.0, max_value=100_000_000.0,
                                 step=5000.0, key="explorer_target")
        balance = st.number_input("Starting balance ($)", min_value=0.0, max_value=100_000_000.0,
                                  step=1000.0, key="explorer_balance")
        # Precision entry supports large budgets without an unwieldy million-dollar slider.
        monthly = st.number_input("Monthly contribution ($)", min_value=0.0, max_value=1_000_000.0,
                                  step=50.0, key="explorer_monthly")
        if monthly <= 10_000:
            st.session_state["explorer_monthly_adjust"] = monthly
            st.slider("Adjust monthly contribution ($)", 0.0, 10_000.0, step=50.0,
                      key="explorer_monthly_adjust", on_change=_adjust_contribution)
        years = st.slider("Goal deadline (years)", 1, 60, key="explorer_years")
        with st.expander("Return, fee & inflation assumptions"):
            st.caption("Illustrative defaults. Set your own rates; low ≤ base ≤ high.")
            low = st.number_input("Low annual return (%)", min_value=-95.0, max_value=100.0,
                                  step=0.5, key="explorer_low")
            base = st.number_input("Base annual return (%)", min_value=-95.0, max_value=100.0,
                                   step=0.5, key="explorer_base")
            high = st.number_input("High annual return (%)", min_value=-95.0, max_value=100.0,
                                   step=0.5, key="explorer_high")
            fee = st.number_input("Annual fee (%)", min_value=0.0, max_value=10.0,
                                  step=0.1, key="explorer_fee")
            inflation = st.number_input("Annual inflation (%)", min_value=0.0, max_value=20.0,
                                        step=0.25, key="explorer_inflation")
        st.caption("The server processes these inputs. Explorer does not send them to AI or save them in the database. Session plans and downloads are not encrypted by this app.")

    try:
        request = GoalExplorerRequest(
            goal_name=name, target_amount_today=target, current_balance=balance,
            monthly_contribution=monthly, years=years,
            annual_fee_assumption=fee / 100, annual_inflation_assumption=inflation / 100,
            return_assumptions={"low": low / 100, "base": base / 100, "high": high / 100},
        )
    except ValidationError as error:
        st.session_state.pop("_explorer_pdf", None)
        with canvas:
            st.warning("Review your inputs: " + "; ".join(item["msg"] for item in error.errors()))
        return
    st.session_state["_explorer_inputs"] = request.model_dump(mode="json")
    result = explore_goal(request)
    summary = result.scenarios[1].summary

    with canvas:
        st.markdown("**2 · Explore your plan**")
        first, second, third = st.columns(3)
        first.metric("Deadline balance · today's $", _money(summary.projected_balance_in_today_dollars))
        second.metric("Goal in today's dollars", _money(target))
        third.metric("Monthly amount needed · base", _money(summary.required_monthly_contribution))
        st.caption("Deadline balance uses today's purchasing power. Required monthly deposits are fixed future-dollar amounts under the base assumption.")
        real_gap = summary.projected_balance_in_today_dollars - target
        if target == 0:
            st.info("A zero-dollar goal requires no additional deposits in this model.")
        elif abs(real_gap) <= 2.5:
            st.info("The base outcome is within $2.50 of the goal in today's dollars. Rounded deposits and actual returns can leave a shortfall.")
        elif real_gap < 0 and summary.required_monthly_contribution <= monthly:
            st.info(f"The rounded deposit estimate still leaves a modeled shortfall of {_money(-real_gap)} in today's dollars. Adjust the deposit manually or change the assumptions.")
        elif real_gap < 0:
            st.info(f"Under the base assumption, the plan needs {_money(summary.required_monthly_contribution - monthly)} more per month to reach this goal in {years} years.")
        else:
            st.success("The base scenario meets your goal at the deadline. Lower returns can change that outcome.")
        st.button("Use base monthly estimate", on_click=_use_contribution,
                  args=(summary.required_monthly_contribution,),
                  disabled=(summary.required_monthly_contribution > 1_000_000 or
                            (summary.required_monthly_contribution == 0 and real_gap < 0)),
                  help="Updates your deposit to the rounded mathematical estimate. This is not an affordability recommendation.")
        view = st.radio("Show amounts in", ["Today's dollars", "Future dollars"], horizontal=True,
                        key="explorer_display")
        basis = "today" if view == "Today's dollars" else "nominal"
        if st.session_state.get("explorer_inspect", years) > years:
            st.session_state["explorer_inspect"] = years
        inspect = st.slider("Inspect year", 0, years, value=years, key="explorer_inspect",
                            help="Inspect a checkpoint without changing your goal deadline or required monthly deposit. Use arrow keys for one-year steps.")
        _chart(result, basis, inspect)
        st.caption("Low/base/high lines use constant user-selected returns. They are not probability bounds. The dashed vertical line marks the inspected year.")
        point = result.scenarios[1].timeline[inspect]
        st.markdown(f"**At year {inspect} · base scenario · {view.lower()}**")
        cards = st.columns(4)
        cards[0].metric("Starting balance + deposits", _money(getattr(point, f"contributions_{basis}")))
        cards[1].metric("Modeled growth / loss", _money(getattr(point, f"growth_{basis}")))
        cards[2].metric("Modeled balance", _money(getattr(point, f"balance_{basis}")))
        cards[3].metric("Goal gap / surplus", _money(getattr(point, f"balance_{basis}") - getattr(point, f"target_{basis}")))
        st.caption("These four figures describe the inspected year. The headline figures above always describe your deadline.")
        if basis == "today":
            st.caption("Deposits and growth are deflated together at the inspected year. Their displayed sum may differ by a cent due to rounding.")

    st.divider()
    st.markdown("**What would it take to reach the goal?**")
    for column, scenario in zip(st.columns(3), result.scenarios):
        with column:
            with st.container(border=True):
                label = scenario.summary.scenario.title()
                st.markdown(f"**{label} return · {scenario.summary.annual_return_assumption:.1%} / year**")
                st.metric(f"{label} monthly deposit needed", _money(scenario.summary.required_monthly_contribution))
                st.write("Balance at deadline (today's dollars):", _money(scenario.summary.projected_balance_in_today_dollars))
    st.caption("Required contributions are mathematical estimates, rounded to cents; they do not establish affordability, account eligibility, or a guaranteed result.")
    with st.expander("Year-by-year figures · base scenario"):
        st.table([
            {"Year": point.year, "Balance": _money(getattr(point, f"balance_{basis}")),
             "Starting balance + deposits": _money(getattr(point, f"contributions_{basis}")),
             "Growth / loss": _money(getattr(point, f"growth_{basis}")),
             "Goal": _money(getattr(point, f"target_{basis}"))}
            for point in result.scenarios[1].timeline
        ])
        st.caption(f"All figures use {view.lower()}. This table provides a text alternative to the chart.")
    _render_risk(request)
    _render_plans(request)
    with st.expander("How the model works"):
        st.markdown(
            "Deposits arrive at each month end. Annual net return is simplified as return minus fee, "
            "then converted to an effective monthly rate. Deposits stay constant; the goal increases with inflation. "
            "The starting balance is included in the deposits line; historical gains are unknown. "
            "The model excludes taxes, withdrawals, changing contributions, and account limits. "
            "Actual progress tracking and property comparisons are not part of this explorer."
        )
        st.markdown("[Investor.gov compound interest calculator](https://www.investor.gov/financial-tools-calculators/calculators/compound-interest-calculator) · Model: goal-explorer-v1")


def _render_risk(request):
    with st.expander("Explore uncertainty with a seeded simulation"):
        st.caption("Optional and separate from the constant-return lines above. Returns vary monthly in this mathematical model.")
        volatility = st.number_input("Annual volatility (%)", 0.0, 150.0, 15.0, step=1.0,
                                     key="explorer_volatility")
        seed = st.number_input("Simulation seed", 0, 2_147_483_647, 42, key="explorer_seed")
        signature = (request.model_dump_json(), volatility, seed)
        if st.button("Run uncertainty simulation", key="explorer_simulate"):
            risk = analyze_goal_risk(
                current_balance=request.current_balance, monthly_contribution=request.monthly_contribution,
                years=request.years, annual_return=request.return_assumptions.base,
                annual_volatility=volatility / 100, annual_fee=request.annual_fee_assumption,
                annual_inflation=request.annual_inflation_assumption,
                target_amount_today=request.target_amount_today, simulation_count=1000, random_seed=seed,
            )
            st.session_state["_explorer_risk"] = (signature, asdict(risk))
        saved = st.session_state.get("_explorer_risk")
        if saved and saved[0] != signature:
            st.info("Inputs changed. Run the simulation again to update these results.")
        elif saved:
            risk = saved[1]
            st.metric("Simulated paths reaching goal", f"{risk['probability_of_reaching_goal']:.1%}")
            rows = [{"Percentile": label, "Balance": risk[field]} for label, field in (
                ("10th", "ending_balance_p10_in_today_dollars"),
                ("Median", "ending_balance_median_in_today_dollars"),
                ("90th", "ending_balance_p90_in_today_dollars"),
            )]
            chart = alt.Chart(alt.Data(values=rows)).mark_bar(color="#157f83").encode(
                x=alt.X("Percentile:N", sort=["10th", "Median", "90th"]),
                y=alt.Y("Balance:Q", title="Balance at deadline · today's dollars"),
                tooltip=["Percentile:N", alt.Tooltip("Balance:Q", format="$,.2f")],
            ).properties(height=200)
            st.altair_chart(chart, width="stretch")
            st.table([{ "Percentile": row["Percentile"], "Balance · today's $": _money(row["Balance"])} for row in rows])
            st.caption(f"1,000 paths · seed {seed}. These percentiles do not show the worst and best possible outcomes.")
            st.warning(risk["disclaimer"])


def _render_plans(request):
    st.markdown("**3 · Keep a baseline. Explore an alternative.**")
    st.caption("Session plans disappear when the session ends. Export a file to keep one. Files contain your financial assumptions; store them privately.")
    label = st.text_input("Plan label", value="My baseline", max_chars=80, key="explorer_label")
    snapshot = None
    if len(label.strip()) >= 2:
        snapshot = GoalExplorerSnapshot(model_version="goal-explorer-v1", label=label,
                                        created_at=datetime.now(timezone.utc).isoformat(), inputs=request)
    left, right = st.columns(2)
    if left.button("Keep plan in this session", key="explorer_keep"):
        if snapshot is None:
            st.warning("Enter a plan label with at least two characters.")
        else:
            plans = st.session_state.setdefault("_explorer_plans", [])
            if len(plans) >= 10:
                st.warning("Keep up to 10 session plans. Delete one before adding another.")
            else:
                plans.append(snapshot.model_dump(mode="json"))
                st.success(f"Kept {snapshot.label} in this session.")
    right.download_button("Export current plan", data=export_goal_plan(snapshot) if snapshot else "",
                          file_name="goal-plan.json", mime="application/json", disabled=snapshot is None)
    plans = st.session_state.get("_explorer_plans", [])
    baseline = None
    comparison_view = "Same elapsed year"
    if plans:
        selected = st.selectbox("Baseline plan", list(range(len(plans))),
                                format_func=lambda i: f"{i + 1}. {plans[i]['label']}", key="explorer_baseline")
        baseline = GoalExplorerSnapshot.model_validate(plans[selected])
        try:
            changes = changed_assumptions(baseline.inputs, request)
        except ValueError as error:
            st.info(str(error))
        else:
            if changes:
                st.dataframe(changes, hide_index=True, width="stretch")
                comparison_view = st.radio("Compare at", ["Same elapsed year", "Each plan's deadline"],
                                           horizontal=True, key="explorer_compare_view")
                if comparison_view == "Same elapsed year":
                    evaluated = [min(baseline.inputs.years, request.years)] * 2
                    st.caption(f"Both plans are evaluated at year {evaluated[0]}, the earlier deadline. The same starting balance, goal and inflation are required.")
                else:
                    evaluated = [baseline.inputs.years, request.years]
                    st.warning("Different deadlines include different amounts of time and deposits. This is a goal-planning comparison, not a performance ranking.")
                points = comparison_checkpoints(baseline.inputs, request,
                                                "aligned" if comparison_view == "Same elapsed year" else "deadlines")
                comparison_rows = [
                    {"Plan": label, "Goal deadline (years)": value.years, "Evaluated year": point.year,
                     "Monthly deposit": _money(value.monthly_contribution),
                     "Starting balance + deposits · future $": _money(point.contributions_nominal),
                     "Base balance · today's $": _money(point.balance_today),
                     "Goal surplus / gap · today's $": _money(point.balance_today - request.target_amount_today)}
                    for label, value, point in zip((baseline.label, "Current"), (baseline.inputs, request), points)
                ]
                for column, name, row in zip(st.columns(2), ("Baseline", "Current"), comparison_rows):
                    with column:
                        with st.container(border=True):
                            st.metric(f"{name} balance · today's $", row["Base balance · today's $"])
                            st.write(f"Evaluated at year {row['Evaluated year']}; goal deadline {row['Goal deadline (years)']} years.")
                            st.write("Monthly deposit:", row["Monthly deposit"])
                            st.write("Starting balance + deposits (future dollars):", row["Starting balance + deposits · future $"])
                            st.write("Goal gap / surplus (today's dollars):", row["Goal surplus / gap · today's $"])
                with st.expander("Comparison details table"):
                    st.table(comparison_rows)
                st.metric("Base balance change · today's $", _money(points[1].balance_today - points[0].balance_today))
                st.caption("Different deposits still change the balance. A higher balance alone does not establish a better strategy.")
            else:
                st.info("Change a contribution, deadline, or return assumption to compare with this baseline.")
        if st.button("Restore baseline inputs", key="explorer_restore"):
            st.session_state["_explorer_pending"] = baseline.inputs.model_dump(mode="json")
            st.session_state["_explorer_pending_label"] = baseline.label
            st.rerun()
        if st.button("Delete selected session plan", key="explorer_delete"):
            plans.pop(selected)
            st.session_state.pop("explorer_baseline", None)
            st.rerun()
    _render_pdf_export(snapshot, baseline, comparison_view)
    with st.expander("Import a previously exported plan"):
        st.caption("Import uploads the file to this server. Only validated inputs are loaded; outputs are recalculated. Maximum plan size: 32,000 bytes.")
        token = st.session_state.setdefault("_explorer_upload_token", uuid4().hex)
        upload = st.file_uploader("Goal plan JSON", type=["json"], key=f"explorer_import_{token}")
        if st.button("Load imported inputs", disabled=upload is None, key="explorer_load"):
            try:
                if upload.size > 32_000:
                    raise ValueError("File too large")
                imported = import_goal_plan(upload.getvalue())
            except (ValueError, ValidationError):
                st.error("This file is not a supported goal-explorer-v1 plan. Check its format, version, size, and input ranges.")
            else:
                st.session_state["_explorer_pending"] = imported.inputs.model_dump(mode="json")
                st.session_state["_explorer_pending_label"] = imported.label
                st.session_state["_explorer_upload_token"] = uuid4().hex
                st.rerun()


def _render_pdf_export(snapshot, baseline, comparison_view):
    """Prepare explicitly; discard stale report bytes after any relevant change."""
    with st.expander("Download a PDF goal report", expanded=True):
        st.caption("A readable copy of the full plan, not just the inspected year. It is generated on this server in memory, without AI or an application-created report file. The download is not encrypted. JSON remains the format for reopening a plan.")
        compatible = baseline is not None and snapshot is not None
        if compatible:
            try:
                changed_assumptions(baseline.inputs, snapshot.inputs)
            except ValueError:
                compatible = False
        include = st.checkbox("Include selected baseline in PDF", disabled=not compatible,
                              key="explorer_pdf_comparison") and compatible
        if baseline is not None and not compatible:
            st.caption("That baseline uses a different goal setup. The report can still include the current plan alone.")
        basis = "today" if st.session_state.get("explorer_display", "Today's dollars") == "Today's dollars" else "nominal"
        mode = "aligned" if comparison_view == "Same elapsed year" else "deadlines"
        # Exclude the per-rerun snapshot timestamp: the prepared report has its own creation time.
        signature = None if snapshot is None else (
            REPORT_VERSION, snapshot.model_version, snapshot.label, snapshot.inputs.model_dump_json(), basis,
            baseline.model_dump_json() if include else None, mode if include else None,
        )
        prepared = st.session_state.get("_explorer_pdf")
        if prepared is not None and prepared[0] != signature:
            st.session_state.pop("_explorer_pdf", None)
            prepared = None
            st.info("Report inputs changed. Prepare a new PDF to include your current choices.")
        display_text = "today's dollars" if basis == "today" else "future dollars"
        st.caption(f"Report amounts follow the chart's {display_text} display. Scenario funding and comparison tables explicitly show their own units.")
        if st.button("Prepare PDF report", disabled=snapshot is None, key="explorer_prepare_pdf"):
            try:
                with st.spinner("Preparing your report..."):
                    pdf = build_goal_report(snapshot, basis=basis, baseline=baseline if include else None,
                                            comparison_mode=mode)
            except Exception:
                # Do not log financial labels, assumptions, exception text, or document bytes.
                st.session_state.pop("_explorer_pdf", None)
                st.error("Could not prepare the PDF. Your plan is unchanged; try again or export JSON.")
                prepared = None
            else:
                prepared = (signature, pdf)
                st.session_state["_explorer_pdf"] = prepared
                st.success("PDF prepared for your current plan. Download it below and store it privately.")
        if prepared is not None:
            st.download_button("Download PDF report", data=prepared[1], file_name="goal-plan.pdf",
                               mime="application/pdf", key="explorer_download_pdf")
            st.caption("Prepared reports remain in this session until replaced, cleared, or cleaned up by the framework. Downloads and framework delivery URLs need the same privacy care as your financial inputs.")
