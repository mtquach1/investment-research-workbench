"""Validated API and AI data contracts."""

from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class OptimizeRequest(StrictModel):
    text: str = Field(min_length=3, max_length=4000, description="Natural-language description of finances")


class UserFinancialProfile(StrictModel):
    gross_income: float = Field(gt=0, le=10_000_000)
    filing_status: Literal["single"] = "single"
    income_type: Literal["w2"] = "w2"
    age: int = Field(default=35, ge=18, le=100)
    traditional_401k_contribution: float = Field(default=0, ge=0, le=100_000)
    other_pretax_adjustments: float = Field(default=0, ge=0, le=1_000_000)
    roth_magi_adjustments: float = Field(default=0, ge=0, le=1_000_000, description="User-entered additions needed to estimate Roth IRA MAGI")
    itemized_deductions: float | None = Field(default=None, ge=0, le=10_000_000)
    other_ira_assets: float = Field(default=0, ge=0, le=100_000_000, description="Pre-tax IRA balances relevant to Roth conversion pro-rata rule")
    annual_ira_contributions_already_made: float = Field(default=0, ge=0, le=100_000)
    annual_traditional_ira_contributions_already_made: float = Field(
        default=0, ge=0, le=100_000,
        description="Traditional IRA portion of annual_ira_contributions_already_made; remainder is Roth",
    )
    state_tax_rate: float = Field(default=0.08, ge=0, le=0.25)

    @model_validator(mode="after")
    def check_prior_ira_split(self):
        if self.annual_traditional_ira_contributions_already_made > self.annual_ira_contributions_already_made:
            raise ValueError("Traditional IRA contributions cannot exceed total prior IRA contributions")
        return self

    @field_validator("gross_income", "traditional_401k_contribution", "other_pretax_adjustments", "roth_magi_adjustments", "itemized_deductions", "other_ira_assets", "annual_ira_contributions_already_made", "annual_traditional_ira_contributions_already_made")
    @classmethod
    def finite_nonnegative(cls, value: float | None) -> float | None:
        if value is not None and (value != value or value in (float("inf"), float("-inf"))):
            raise ValueError("Amount must be a finite number")
        return value


class DeductionBreakdown(StrictModel):
    standard_deduction: float
    itemized_deduction: float
    deduction_used: float


class TaxMetrics(StrictModel):
    tax_year: int
    gross_income: float
    traditional_401k_contribution: float
    agi_estimate: float
    roth_ira_magi_estimate: float
    deduction: DeductionBreakdown
    federal_taxable_income: float
    federal_income_tax: float
    federal_marginal_rate: float
    federal_effective_rate_on_gross: float
    state_tax_estimate: float
    social_security_tax: float
    medicare_tax: float
    additional_medicare_tax: float
    total_estimated_tax: float
    estimated_take_home: float
    tax_savings_from_401k: float
    roth_ira_direct_contribution_cap: float
    roth_ira_phaseout_status: str
    recommended_401k_contribution: float
    recommended_ira_contribution: float
    backdoor_roth_pro_rata_note: str
    strategic_pivot: str
    assumptions: list[str]


class OptimizeResponse(StrictModel):
    profile: UserFinancialProfile
    metrics: TaxMetrics
    strategy_report_markdown: str


class CalculateRequest(UserFinancialProfile):
    """Structured deterministic calculator request."""


class HealthResponse(StrictModel):
    status: Literal["ok"]
    tax_year: int
    ai_enabled: bool


class PortfolioProjectionRequest(StrictModel):
    monthly_contribution: float = Field(ge=0, le=1_000_000)
    years: int = Field(ge=1, le=60)
    annual_return_assumption: float = Field(ge=-0.95, le=1.0, description="Decimal fraction; e.g. 0.07 means 7%")
    annual_fee_assumption: float = Field(default=0, ge=0, le=0.1)
    estimated_monthly_hours: float | None = Field(default=None, ge=0, le=1000,
        description="Your estimate of monthly time spent managing this portfolio")
    available_monthly_hours: float | None = Field(default=None, ge=0, le=1000,
        description="Hours per month you can realistically devote to investing")


class RetirementAccountComparisonRequest(StrictModel):
    annual_gross_contribution: float = Field(gt=0, le=100_000)
    current_marginal_tax_rate: float = Field(ge=0, le=0.6)
    retirement_tax_rate_assumption: float = Field(ge=0, le=0.6)
    years: int = Field(ge=1, le=60)
    annual_return_assumption: float = Field(ge=-0.95, le=1.0)
    annual_fee_assumption: float = Field(default=0, ge=0, le=0.1)


class RentalUnderwritingRequest(StrictModel):
    model_config = ConfigDict(allow_inf_nan=False)
    purchase_price: float = Field(gt=0, le=100_000_000)
    down_payment: float = Field(ge=0, le=100_000_000)
    closing_costs: float = Field(default=0, ge=0)
    monthly_rent_per_unit: float = Field(ge=0, le=1_000_000)
    rented_units: int = Field(ge=0, le=100)
    owner_occupied_units: int = Field(default=0, ge=0, le=100)
    total_units: int = Field(default=1, ge=1, le=100)
    vacancy_rate: float = Field(ge=0, le=1)
    annual_property_tax: float = Field(ge=0)
    annual_insurance: float = Field(ge=0)
    annual_maintenance: float = Field(ge=0)
    annual_capex_reserve: float = Field(ge=0)
    annual_management_rate: float = Field(ge=0, le=1)
    annual_interest_rate: float = Field(ge=0, le=0.5)
    loan_term_years: int = Field(ge=1, le=50)
    monthly_owner_costs: float = Field(default=0, ge=0)
    initial_repairs: float = Field(default=0, ge=0, le=100_000_000)
    initial_operating_reserves: float = Field(default=0, ge=0, le=100_000_000)
    annual_hoa: float = Field(default=0, ge=0, le=100_000_000)
    annual_owner_paid_utilities: float = Field(default=0, ge=0, le=100_000_000)
    estimated_monthly_hours: float | None = Field(default=None, ge=0, le=1000,
        description="Your estimated monthly time for this property at its expected operating stage")
    available_monthly_hours: float | None = Field(default=None, ge=0, le=1000,
        description="Hours per month you can realistically devote to investing")


class FlipUnderwritingRequest(StrictModel):
    purchase_price: float = Field(gt=0)
    rehab_budget: float = Field(ge=0)
    contingency_rate: float = Field(ge=0, le=1)
    holding_months: int = Field(ge=0, le=60)
    monthly_holding_cost: float = Field(ge=0)
    selling_cost_rate: float = Field(ge=0, le=0.25)
    financing_costs: float = Field(ge=0)
    estimated_resale_value: float = Field(ge=0)
    closing_costs: float = Field(default=0, ge=0)
    estimated_monthly_hours: float | None = Field(default=None, ge=0, le=1000,
        description="Your estimated active hours per month during the project")
    available_monthly_hours: float | None = Field(default=None, ge=0, le=1000,
        description="Hours per month you can realistically devote to investing")


class FinancialReadinessRequest(StrictModel):
    strategy_category: Literal["portfolio", "rental_property", "property_flip", "other"]
    emergency_savings: float = Field(ge=0, le=100_000_000)
    monthly_essential_expenses: float = Field(gt=0, le=10_000_000)
    emergency_fund_target_months: float = Field(gt=0, le=120,
        description="Your own emergency-reserve target; no universal target is assumed")
    debt_balance_at_highest_apr: float = Field(default=0, ge=0, le=100_000_000)
    highest_debt_apr: float | None = Field(default=None, ge=0, le=1,
        description="APR as a decimal fraction, e.g. 0.24 means 24%")
    user_debt_apr_comparison: float | None = Field(default=None, ge=0, le=1,
        description="Optional user-selected APR threshold; the app does not set a universal cutoff")
    liquidity_horizon_months: int | None = Field(default=None, ge=0, le=600,
        description="When you may need the invested funds; omit if not yet known")
    available_monthly_hours: float | None = Field(default=None, ge=0, le=1000)
    estimated_strategy_monthly_hours: float | None = Field(default=None, ge=0, le=1000)
    risk_tolerance_rating: int = Field(ge=1, le=5,
        description="Self-rating of willingness to accept volatility or loss; 1 is low, 5 is high")
    risk_capacity_rating: int = Field(ge=1, le=5,
        description="Self-rating of ability to absorb financial loss; 1 is low, 5 is high")


class DebtAccountRequest(StrictModel):
    name: str = Field(min_length=1, max_length=60)
    balance: float = Field(gt=0, le=100_000_000)
    annual_apr: float = Field(ge=0, le=5, description="Decimal fraction; e.g. 0.24 means 24% APR")
    minimum_monthly_payment: float = Field(gt=0, le=1_000_000)


class DebtPayoffRequest(StrictModel):
    debts: list[DebtAccountRequest] = Field(min_length=1, max_length=10)
    extra_monthly_payment: float = Field(ge=0, le=1_000_000)
    max_months: int = Field(default=600, ge=1, le=1200)


class PortfolioProjectionResponse(StrictModel):
    years: int
    monthly_contribution: float
    annual_return_assumption: float
    annual_fee_assumption: float
    total_contributions: float
    projected_balance: float
    projected_growth: float
    estimated_monthly_hours: float | None
    available_monthly_hours: float | None
    time_budget_utilization: float | None
    fits_time_budget: bool | None
    disclaimer: str


class RetirementAccountComparisonResponse(StrictModel):
    annual_gross_contribution: float
    current_marginal_tax_rate: float
    retirement_tax_rate_assumption: float
    years: int
    annual_return_assumption: float
    traditional_current_tax_reduction_estimate: float
    traditional_future_balance_before_tax: float
    traditional_future_spendable_balance: float
    roth_contribution_at_equal_current_cash_cost: float
    roth_future_spendable_balance: float
    traditional_advantage_at_assumptions: float
    note: str


class RentalUnderwritingResponse(StrictModel):
    purchase_price: float
    monthly_gross_rent: float
    monthly_effective_rent: float
    monthly_operating_expenses: float
    monthly_debt_service: float
    annual_noi: float
    cap_rate: float
    annual_pre_tax_cash_flow: float
    cash_invested_estimate: float
    cash_on_cash_return: float | None
    dscr: float | None
    monthly_owner_occupied_rent_comparable: float
    initial_repairs: float
    initial_operating_reserves: float
    initial_cash_required: float
    annual_capex_reserve: float
    annual_cash_flow_before_capex_reserve: float
    break_even_monthly_rent_per_unit: float | None
    break_even_status: str
    first_year_interest: float
    first_year_principal: float
    loan_balance_after_one_year: float
    model_version: Literal["rental-underwriting-v2"]
    estimated_monthly_hours: float | None
    available_monthly_hours: float | None
    time_budget_utilization: float | None
    fits_time_budget: bool | None
    disclaimer: str


class FlipUnderwritingResponse(StrictModel):
    purchase_price: float
    rehab_budget: float
    contingency: float
    holding_costs: float
    selling_costs: float
    financing_costs: float
    all_in_cost: float
    estimated_resale_value: float
    estimated_profit_before_tax: float
    estimated_return_on_cost: float
    break_even_resale_price: float
    estimated_monthly_hours: float | None
    available_monthly_hours: float | None
    time_budget_utilization: float | None
    fits_time_budget: bool | None
    disclaimer: str


class FinancialReadinessResponse(StrictModel):
    strategy_category: Literal["portfolio", "rental_property", "property_flip", "other"]
    emergency_savings_months: float
    emergency_target_amount: float
    emergency_target_gap: float
    debt_balance_at_highest_apr: float
    highest_debt_apr: float | None
    user_debt_apr_comparison: float | None
    debt_apr_above_user_threshold: bool | None
    liquidity_horizon_months: int | None
    available_monthly_hours: float | None
    estimated_strategy_monthly_hours: float | None
    fits_time_budget: bool | None
    risk_tolerance_rating: int
    risk_capacity_rating: int
    risk_rating_difference: int
    review_prompts: list[str]
    disclaimer: str


class DebtLineResponse(StrictModel):
    name: str
    payoff_month: int | None
    interest_paid: float
    remaining_balance: float


class DebtPayoffMethodResponse(StrictModel):
    method: Literal["avalanche", "snowball"]
    payoff_months: int | None
    total_interest: float
    total_paid: float
    remaining_balance_after_horizon: float
    debt_results: list[DebtLineResponse]


class DebtPayoffComparisonResponse(StrictModel):
    monthly_payment_budget: float
    simulation_horizon_months: int
    avalanche: DebtPayoffMethodResponse
    snowball: DebtPayoffMethodResponse
    avalanche_interest_minus_snowball: float | None
    avalanche_months_minus_snowball: int | None
    disclaimer: str


class GoalReturnAssumptions(StrictModel):
    low: float = Field(ge=-0.95, le=1.0, description="Annual return scenario as a decimal fraction")
    base: float = Field(ge=-0.95, le=1.0, description="Annual return scenario as a decimal fraction")
    high: float = Field(ge=-0.95, le=1.0, description="Annual return scenario as a decimal fraction")


class GoalPlanRequest(StrictModel):
    goal_name: str = Field(min_length=2, max_length=80)
    current_balance: float = Field(default=0, ge=0, le=100_000_000)
    monthly_contribution: float = Field(ge=0, le=1_000_000)
    years: int = Field(ge=1, le=60)
    target_amount_today: float | None = Field(default=None, ge=0, le=100_000_000,
        description="Goal cost in today's dollars; the calculator inflates it to the target year")
    annual_inflation_assumption: float = Field(default=0.03, ge=0, le=0.2)
    annual_fee_assumption: float = Field(default=0, ge=0, le=0.1)
    return_assumptions: GoalReturnAssumptions


class GoalScenarioResponse(StrictModel):
    scenario: Literal["low", "base", "high"]
    annual_return_assumption: float
    total_contributions: float
    projected_balance_nominal: float
    projected_balance_in_today_dollars: float
    projected_growth: float
    target_amount_future_dollars: float | None
    goal_surplus_or_shortfall: float | None
    required_monthly_contribution: float | None
    goal_status: str
    disclaimer: str


class GoalPlanResponse(StrictModel):
    goal_name: str
    years: int
    current_balance: float
    monthly_contribution: float
    target_amount_today: float | None
    annual_inflation_assumption: float
    annual_fee_assumption: float
    scenarios: list[GoalScenarioResponse]


class GoalExplorerRequest(GoalPlanRequest):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)
    target_amount_today: float = Field(ge=0, le=100_000_000)

    @model_validator(mode="after")
    def validate_explorer_returns(self):
        rates = self.return_assumptions
        if not rates.low <= rates.base <= rates.high:
            raise ValueError("Return scenarios must be ordered low <= base <= high")
        if rates.low - self.annual_fee_assumption <= -1:
            raise ValueError("Each annual return less fees must be greater than -100%")
        return self


class GoalTimelinePoint(StrictModel):
    year: int
    balance_nominal: float
    balance_today: float
    contributions_nominal: float
    contributions_today: float
    growth_nominal: float
    growth_today: float
    target_nominal: float
    target_today: float


class GoalExplorerScenario(StrictModel):
    summary: GoalScenarioResponse
    timeline: list[GoalTimelinePoint]


class GoalExplorerResponse(StrictModel):
    model_version: Literal["goal-explorer-v1"] = "goal-explorer-v1"
    inputs: GoalExplorerRequest
    scenarios: list[GoalExplorerScenario]


class GoalExplorerSnapshot(StrictModel):
    model_version: Literal["goal-explorer-v1"]
    label: str = Field(min_length=2, max_length=80)
    created_at: str = Field(min_length=1, max_length=80)
    inputs: GoalExplorerRequest


class GoalRiskAnalysisRequest(StrictModel):
    current_balance: float = Field(default=0, ge=0, le=100_000_000)
    monthly_contribution: float = Field(ge=0, le=1_000_000)
    years: int = Field(ge=1, le=60)
    annual_return_assumption: float = Field(ge=-0.95, le=1.0, description="Expected annual return assumption before fees")
    annual_volatility_assumption: float = Field(ge=0, le=1.5, description="Annualized standard deviation as a decimal fraction")
    annual_fee_assumption: float = Field(default=0, ge=0, le=0.1)
    annual_inflation_assumption: float = Field(default=0.03, ge=0, le=0.2)
    target_amount_today: float | None = Field(default=None, ge=0, le=100_000_000)
    simulation_count: int = Field(default=2000, ge=100, le=5000)
    random_seed: int = Field(default=42, ge=0, le=2_147_483_647)


class GoalRiskAnalysisResponse(StrictModel):
    simulation_count: int
    random_seed: int
    annual_return_assumption: float
    annual_volatility_assumption: float
    annual_fee_assumption: float
    target_amount_future_dollars: float | None
    probability_of_reaching_goal: float | None
    ending_balance_p10_in_today_dollars: float
    ending_balance_median_in_today_dollars: float
    ending_balance_p90_in_today_dollars: float
    total_contributions: float
    disclaimer: str


class OrderedSensitivityRange(StrictModel):
    low: float = Field(allow_inf_nan=False)
    high: float = Field(allow_inf_nan=False)

    @model_validator(mode="after")
    def ordered(self):
        if self.low > self.high:
            raise ValueError("Sensitivity range low must be less than or equal to high")
        return self


class GoalSensitivityRanges(StrictModel):
    annual_return: OrderedSensitivityRange
    monthly_contribution: OrderedSensitivityRange
    annual_fee: OrderedSensitivityRange
    annual_inflation: OrderedSensitivityRange


class GoalSensitivityRequest(StrictModel):
    goal_name: str = Field(min_length=2, max_length=80)
    current_balance: float = Field(default=0, ge=0, le=100_000_000)
    monthly_contribution: float = Field(ge=0, le=1_000_000)
    years: int = Field(ge=1, le=60)
    annual_return_assumption: float = Field(ge=-0.95, le=1.0)
    annual_fee_assumption: float = Field(default=0, ge=0, le=0.1)
    annual_inflation_assumption: float = Field(default=0.03, ge=0, le=0.2)
    target_amount_today: float | None = Field(default=None, ge=0, le=100_000_000)
    sensitivity_ranges: GoalSensitivityRanges

    @model_validator(mode="after")
    def base_is_within_sensitivity_ranges(self):
        bases = {
            "annual_return": self.annual_return_assumption,
            "monthly_contribution": self.monthly_contribution,
            "annual_fee": self.annual_fee_assumption,
            "annual_inflation": self.annual_inflation_assumption,
        }
        for name, base in bases.items():
            band = getattr(self.sensitivity_ranges, name)
            if not band.low <= base <= band.high:
                raise ValueError(f"{name} sensitivity range must contain the base assumption")
            limits = {
                "annual_return": (-0.95, 1.0),
                "monthly_contribution": (0.0, 1_000_000.0),
                "annual_fee": (0.0, 0.1),
                "annual_inflation": (0.0, 0.2),
            }[name]
            if band.low < limits[0] or band.high > limits[1]:
                raise ValueError(f"{name} sensitivity range must be between {limits[0]} and {limits[1]}")
        return self


class GoalSensitivityFactorResponse(StrictModel):
    assumption: Literal["annual_return", "monthly_contribution", "annual_fee", "annual_inflation"]
    low_input: float
    base_input: float
    high_input: float
    balance_at_low_input_today_dollars: float
    balance_at_base_today_dollars: float
    balance_at_high_input_today_dollars: float
    balance_span_today_dollars: float
    impact_rank: int


class GoalSensitivityResponse(StrictModel):
    goal_name: str
    factors: list[GoalSensitivityFactorResponse]
    method: str
    disclaimer: str


class SaveGoalRiskRunRequest(StrictModel):
    label: str = Field(min_length=2, max_length=80)
    analysis: GoalRiskAnalysisRequest


class SavedGoalRiskRun(StrictModel):
    run_id: UUID
    scenario_type: Literal["goal-risk-analysis"]
    label: str
    created_at: str
    model_version: str
    inputs: GoalRiskAnalysisRequest
    result: GoalRiskAnalysisResponse


class SavedGoalRiskRunsResponse(StrictModel):
    runs: list[SavedGoalRiskRun]


class CompareGoalRiskRunsRequest(StrictModel):
    baseline_run_id: UUID
    comparison_run_id: UUID


class GoalRiskRunComparisonSide(StrictModel):
    run_id: UUID
    label: str
    annual_return_assumption: float
    annual_volatility_assumption: float
    annual_fee_assumption: float
    p10_balance_today_dollars: float
    median_balance_today_dollars: float
    p90_balance_today_dollars: float
    probability_of_reaching_goal: float | None


class CompareGoalRiskRunsResponse(StrictModel):
    baseline: GoalRiskRunComparisonSide
    comparison: GoalRiskRunComparisonSide
    p10_balance_delta_today_dollars: float
    median_balance_delta_today_dollars: float
    p90_balance_delta_today_dollars: float
    goal_probability_delta: float | None
    disclaimer: str
