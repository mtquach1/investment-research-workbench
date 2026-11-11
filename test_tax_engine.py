"""Regression tests for representative 2026 single-filer strategy pivots."""

import pytest
from schemas import UserFinancialProfile
from tax_engine import TAX_YEAR, calculate_tax, federal_income_tax, roth_direct_contribution_cap
from scenario_engine import (compare_retirement_accounts, project_goal, project_portfolio, time_budget_metrics,
                             underwrite_flip, underwrite_rental)


def test_ira_capacity_cannot_exceed_modeled_w2_compensation():
    result = calculate_tax(UserFinancialProfile(gross_income=1_000))
    assert result.roth_ira_direct_contribution_cap == 1_000
    deferred = calculate_tax(UserFinancialProfile(gross_income=1_000, traditional_401k_contribution=900))
    assert deferred.roth_ira_direct_contribution_cap == 100


def test_roth_phaseout_uses_required_rounding_and_minimum_but_respects_compensation():
    assert roth_direct_contribution_cap(153_001, 35)[0] == 7_500
    assert roth_direct_contribution_cap(160_501, 35)[0] == 3_750
    assert roth_direct_contribution_cap(167_999, 35)[0] == 200
    assert roth_direct_contribution_cap(167_999, 35, compensation=50)[0] == 50
    assert roth_direct_contribution_cap(168_000, 35)[0] == 0


def test_prior_traditional_and_roth_contributions_have_distinct_capacity_effects():
    assert roth_direct_contribution_cap(160_500, 35, 4_000, prior_traditional=4_000)[0] == 3_500
    assert roth_direct_contribution_cap(160_500, 35, 2_000)[0] == 1_750
    assert roth_direct_contribution_cap(160_500, 35, 3_000, prior_traditional=1_000)[0] == 1_750
    result = calculate_tax(UserFinancialProfile(
        gross_income=160_500, annual_ira_contributions_already_made=4_000,
        annual_traditional_ira_contributions_already_made=4_000))
    assert result.roth_ira_direct_contribution_cap == 3_500
    with pytest.raises(ValueError):
        UserFinancialProfile(gross_income=100_000, annual_traditional_ira_contributions_already_made=100)


def test_irs_2025_worksheet_reference_with_explicit_tax_year_parameters():
    from dataclasses import replace
    config = replace(TAX_YEAR, tax_year=2025, ira_limit=7_000,
                     roth_phaseout_start_single=150_000, roth_phaseout_end_single=165_000)
    # Publication 590-A worksheet example, with the unrounded ratio permitted by
    # "at least three places": 7,000*(1-1,000/15,000), rounded upward to $10.
    assert roth_direct_contribution_cap(151_000, 45, config=config, compensation=150_000)[0] == 6_540


@pytest.mark.parametrize(("income", "federal_tax", "state_tax", "roth_cap", "pivot_key"), [
    (100_000, 13_170.00, 6_712.00, 7_500.00, "eligible IRA"),
    (250_000, 51_304.00, 18_712.00, 0.00, "Direct Roth IRA contributions are phased out"),
    (500_000, 138_134.25, 38_712.00, 0.00, "Direct Roth IRA contributions are phased out"),
])
def test_core_income_tiers(income: float, federal_tax: float, state_tax: float, roth_cap: float, pivot_key: str) -> None:
    result = calculate_tax(UserFinancialProfile(gross_income=income, age=35))
    assert result.federal_income_tax == federal_tax
    assert result.state_tax_estimate == state_tax
    assert result.roth_ira_direct_contribution_cap == roth_cap
    assert pivot_key in result.strategic_pivot


def test_2026_rule_table_matches_published_single_filer_parameters() -> None:
    assert TAX_YEAR.tax_year == 2026
    assert TAX_YEAR.standard_deduction_single == 16_100
    assert TAX_YEAR.traditional_401k_limit == 24_500
    assert TAX_YEAR.ira_limit == 7_500
    assert TAX_YEAR.ira_catch_up_limit == 1_100
    assert (TAX_YEAR.roth_phaseout_start_single, TAX_YEAR.roth_phaseout_end_single) == (153_000, 168_000)
    assert TAX_YEAR.social_security_wage_base == 184_500
    assert TAX_YEAR.additional_medicare_threshold_single == 200_000
    assert TAX_YEAR.federal_brackets_single == (
        (12_400, .10), (50_400, .12), (105_700, .22), (201_775, .24),
        (256_225, .32), (640_600, .35), (None, .37),
    )


def test_tax_output_discloses_401k_catchup_scope() -> None:
    result = calculate_tax(UserFinancialProfile(gross_income=250_000, age=55))
    assert any("excludes age-based catch-up contributions" in note for note in result.assumptions)


def test_401k_max_reduces_agi_and_federal_tax() -> None:
    baseline = calculate_tax(UserFinancialProfile(gross_income=250_000))
    maxed = calculate_tax(UserFinancialProfile(gross_income=250_000, traditional_401k_contribution=24_500))
    assert maxed.traditional_401k_contribution == 24_500
    assert maxed.agi_estimate == 225_500
    assert maxed.federal_income_tax == 43_464
    assert maxed.federal_income_tax < baseline.federal_income_tax


def test_401k_is_capped_at_annual_limit() -> None:
    result = calculate_tax(UserFinancialProfile(gross_income=100_000, traditional_401k_contribution=99_000))
    assert result.traditional_401k_contribution == 24_500


def test_roth_ira_phaseout_boundaries_and_partial_phaseout() -> None:
    assert roth_direct_contribution_cap(153_000, 35)[0] == 7_500
    assert roth_direct_contribution_cap(160_500, 35)[0] == 3_750
    assert roth_direct_contribution_cap(168_000, 35)[0] == 0
    assert roth_direct_contribution_cap(160_500, 35)[1].startswith("Direct Roth IRA contribution partially")


def test_roth_catchup_cap_for_50_plus() -> None:
    assert roth_direct_contribution_cap(100_000, 50)[0] == 8_600


def test_roth_phaseout_uses_explicit_magi_adjustments() -> None:
    result = calculate_tax(UserFinancialProfile(gross_income=150_000, roth_magi_adjustments=4_000))
    assert result.agi_estimate == 150_000
    assert result.roth_ira_magi_estimate == 154_000
    assert result.roth_ira_direct_contribution_cap < 7_500


def test_existing_ira_assets_surface_pro_rata_caution() -> None:
    result = calculate_tax(UserFinancialProfile(gross_income=250_000, other_ira_assets=20_000))
    assert "pro-rata rule" in result.backdoor_roth_pro_rata_note
    assert "reported" in result.backdoor_roth_pro_rata_note


def test_federal_bracket_progression() -> None:
    assert federal_income_tax(12_400) == 1_240
    assert federal_income_tax(50_400) == 5_800
    assert federal_income_tax(105_700) == 17_966


def test_negative_income_is_rejected() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        federal_income_tax(-1)


def test_portfolio_projection_separates_deposits_from_growth() -> None:
    result = project_portfolio(500, 10, 0.07, 0.002)
    assert result.total_contributions == 60_000
    assert result.projected_balance > result.total_contributions
    assert result.projected_growth == pytest.approx(result.projected_balance - result.total_contributions)


def test_goal_projection_adjusts_target_for_inflation_and_reports_gap() -> None:
    result = project_goal(current_balance=20_000, monthly_contribution=1_200, years=8,
        annual_return=.05, annual_fee=.002, annual_inflation=.03, target_amount_today=150_000)
    assert result.total_contributions == 135_200
    assert result.target_amount_future_dollars == pytest.approx(150_000 * 1.03**8, abs=.01)
    assert result.projected_balance_nominal > result.total_contributions
    assert result.projected_balance_in_today_dollars == pytest.approx(result.projected_balance_nominal / 1.03**8, abs=.01)
    assert result.goal_surplus_or_shortfall == pytest.approx(
        result.projected_balance_nominal - result.target_amount_future_dollars, abs=.01)
    assert result.required_monthly_contribution >= 0
    assert result.goal_status in {"on track under this scenario", "below target under this scenario"}


def test_goal_projection_calculates_required_contribution_for_unfunded_target() -> None:
    result = project_goal(current_balance=0, monthly_contribution=0, years=10,
        annual_return=.04, annual_fee=0, annual_inflation=.02, target_amount_today=100_000)
    assert result.projected_balance_nominal == 0
    assert result.goal_surplus_or_shortfall < 0
    assert result.required_monthly_contribution > 0
    assert result.goal_status == "below target under this scenario"


def test_goal_projection_handles_no_target() -> None:
    result = project_goal(current_balance=5_000, monthly_contribution=300, years=5,
        annual_return=0, annual_fee=0, annual_inflation=.03)
    assert result.projected_balance_nominal == 23_000
    assert result.projected_balance_in_today_dollars < result.projected_balance_nominal
    assert result.target_amount_future_dollars is None
    assert result.goal_surplus_or_shortfall is None
    assert result.required_monthly_contribution is None
    assert result.goal_status == "target not provided"


def test_retirement_accounts_compares_equal_current_cash_cost() -> None:
    result = compare_retirement_accounts(10_000, 0.30, 0.20, 20, 0.07)
    assert result.traditional_current_tax_reduction_estimate == 3_000
    assert result.roth_contribution_at_equal_current_cash_cost == 7_000
    assert result.traditional_future_spendable_balance > 0
    assert "assumption" in result.note


def test_rental_underwriting_includes_owner_occupied_house_hack() -> None:
    result = underwrite_rental(purchase_price=500_000, down_payment=100_000, closing_costs=10_000,
        monthly_rent_per_unit=2_000, rented_units=3, owner_occupied_units=1, total_units=4,
        vacancy_rate=.05, annual_property_tax=6_000, annual_insurance=2_000, annual_maintenance=5_000,
        annual_capex_reserve=3_000, annual_management_rate=.08, annual_interest_rate=.065,
        loan_term_years=30)
    assert result.monthly_gross_rent == 6_000
    assert result.monthly_owner_occupied_rent_comparable == 2_000
    assert result.cash_invested_estimate == 110_000
    assert result.dscr > 0


def test_flip_underwriting_includes_contingency_and_sale_costs() -> None:
    result = underwrite_flip(purchase_price=200_000, rehab_budget=50_000, contingency_rate=.15,
        holding_months=6, monthly_holding_cost=2_000, selling_cost_rate=.07,
        financing_costs=10_000, estimated_resale_value=350_000, closing_costs=4_000)
    assert result.contingency == 7_500
    assert result.selling_costs == 24_500
    assert result.estimated_profit_before_tax == 42_000


def test_time_budget_fit_requires_both_inputs_and_reports_utilization() -> None:
    assert time_budget_metrics(estimated_monthly_hours=8, available_monthly_hours=None) == {
        "estimated_monthly_hours": 8,
        "available_monthly_hours": None,
        "time_budget_utilization": None,
        "fits_time_budget": None,
    }
    assert time_budget_metrics(estimated_monthly_hours=6, available_monthly_hours=10)["fits_time_budget"] is True
    assert time_budget_metrics(estimated_monthly_hours=12, available_monthly_hours=10)["fits_time_budget"] is False
    assert time_budget_metrics(estimated_monthly_hours=6, available_monthly_hours=10)["time_budget_utilization"] == .6
    assert time_budget_metrics(estimated_monthly_hours=1, available_monthly_hours=0)["time_budget_utilization"] is None


def test_time_budget_rejects_invalid_hour_estimates() -> None:
    with pytest.raises(ValueError, match="estimated_monthly_hours"):
        time_budget_metrics(estimated_monthly_hours=-1, available_monthly_hours=10)
    with pytest.raises(ValueError, match="available_monthly_hours"):
        time_budget_metrics(estimated_monthly_hours=1, available_monthly_hours=1001)
