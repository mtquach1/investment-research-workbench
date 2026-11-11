"""FastAPI app for deterministic tax estimates and optional AI-assisted reports."""

from contextlib import asynccontextmanager
from dataclasses import asdict
import logging
from uuid import UUID
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse,Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from ai_service import AIServiceError, format_strategy_report, parse_financial_profile
from config import TAX_YEAR, get_settings
from schemas import (CalculateRequest, DeductionBreakdown, FlipUnderwritingRequest, FlipUnderwritingResponse,
                     GoalPlanRequest, GoalPlanResponse, GoalScenarioResponse, HealthResponse,
                     GoalRiskAnalysisRequest, GoalRiskAnalysisResponse,
                     GoalSensitivityRequest, GoalSensitivityResponse,
                     SaveGoalRiskRunRequest, SavedGoalRiskRun, SavedGoalRiskRunsResponse,
                     CompareGoalRiskRunsRequest, CompareGoalRiskRunsResponse, GoalRiskRunComparisonSide,
                     DebtPayoffRequest, DebtPayoffComparisonResponse, FinancialReadinessRequest, FinancialReadinessResponse,
                     OptimizeRequest, OptimizeResponse, PortfolioProjectionRequest,
                     PortfolioProjectionResponse, RentalUnderwritingRequest, RentalUnderwritingResponse,
                     RetirementAccountComparisonRequest, RetirementAccountComparisonResponse,
                     TaxMetrics, UserFinancialProfile)
from tax_engine import calculate_tax
from scenario_engine import (analyze_goal_sensitivity, compare_retirement_accounts, project_goal, project_portfolio, time_budget_metrics,
                             underwrite_flip, underwrite_rental)
from readiness_engine import review_financial_readiness
from debt_engine import DebtAccount, compare_debt_payoff
from simulation_engine import analyze_goal_risk
from scenario_store import get_goal_risk_run, list_goal_risk_runs, save_goal_risk_run
from goal_explorer import explore_goal
from schemas import GoalExplorerRequest, GoalExplorerResponse
from privacy import require_ai, require_saved_runs
from allocation_engine import allocate_contributions
from allocation_models import AllocationRequest, AllocationResponse
from stock_strategy import StrategyDemoRequest, StrategyDemoResponse, strategy_demo
from rental_feasibility import RentalFeasibilityRequest, RentalFeasibilityResponse, solve_rental_feasibility
from rental_projection import RentalProjectionRequest,RentalProjection,project_rental
from market_catalog import DataReadiness, load_catalog
from company_research import (CompanyDirectory, CompanyResearch, company_directory, company_research)
from company_events import CompanyEvents, company_events
from company_market import CompanyMarket, company_market
from stock_screen import StockScreen,stock_screen
from stock_metrics import ScreenFilters,FilteredScreen,filter_screen
from stock_replay import ReplayRequest,StockReplay,replay_stock
from stock_portfolio import ProposalRequest,StockProposal,stock_proposal
from experimental_basket import ExperimentalRequest,ExperimentalBasket,experimental_basket
from financial_validation import FinancialValidation,validate_installed_financials
from stock_evidence import EvidenceInventory,evidence_inventory
from stock_decisions import DecisionContext,DecisionAssessment,assess_decisions
from stock_monthly import MonthlyContributionPlan,plan_monthly_contribution
from decision_snapshots import SnapshotReviewRequest,SnapshotReview,restore_decision,review_decision
from holding_research import HoldingReviewRequest,HoldingReview,review_owned_holding
import sqlite3


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(
    title="Tax & Investment Strategy Optimizer",
    version="0.2.0",
    description="A deterministic 2026 single-filer W-2 tax estimate with an optional LLM interface.",
    lifespan=lifespan,
)
settings = get_settings()


@app.get('/research/stock-evidence',response_model=EvidenceInventory)
def stock_evidence_endpoint() -> EvidenceInventory:
    return evidence_inventory(stock_screen(settings.market_data_store,settings.market_history_store,mode=settings.market_data_mode))


@app.post('/research/stock-decisions',response_model=DecisionAssessment)
def stock_decisions_endpoint(request: DecisionContext) -> DecisionAssessment:
    return assess_decisions(stock_screen(settings.market_data_store,settings.market_history_store,mode=settings.market_data_mode),request)


@app.post('/research/stock-decisions/snapshot-review',response_model=SnapshotReview)
def stock_snapshot_review_endpoint(request: SnapshotReviewRequest) -> SnapshotReview:
    if not request.acknowledge_experimental:return SnapshotReview(status='acknowledgement_required')
    screen=stock_screen(settings.market_data_store,settings.market_history_store,mode=settings.market_data_mode)
    try:
        record=restore_decision(request.snapshot_json,today=screen.checked_on)
        return review_decision(record,screen,acknowledge_experimental=True,context_override=request.context_override)
    except ValueError:
        raise HTTPException(status_code=422,detail='The decision snapshot could not be validated.') from None


@app.post('/research/stock-monthly-contribution',response_model=MonthlyContributionPlan)
def stock_monthly_contribution_endpoint(request: DecisionContext) -> MonthlyContributionPlan:
    screen=stock_screen(settings.market_data_store,settings.market_history_store,mode=settings.market_data_mode)
    return plan_monthly_contribution(screen,request)


@app.post('/research/stock-decisions/report',response_class=Response,
    responses={200:{'content':{'application/pdf':{'schema':{'type':'string','format':'binary'}}}}})
def stock_decision_report_endpoint(request: SnapshotReviewRequest):
    if not request.acknowledge_experimental:raise HTTPException(status_code=422,detail='Experimental acknowledgement is required.')
    screen=stock_screen(settings.market_data_store,settings.market_history_store,mode=settings.market_data_mode)
    try:
        from stock_decision_report import build_stock_decision_report
        record=restore_decision(request.snapshot_json,today=screen.checked_on)
        data=build_stock_decision_report(record,screen,acknowledge_experimental=True,context_override=request.context_override)
    except ValueError:
        raise HTTPException(status_code=422,detail='A valid snapshot and available current research evidence are required.') from None
    return Response(data,media_type='application/pdf',headers={'Content-Disposition':'attachment; filename="stock-decision-review.pdf"'})


@app.post('/research/stock-holding-review',response_model=HoldingReview)
def stock_holding_review_endpoint(request: HoldingReviewRequest) -> HoldingReview:
    screen=stock_screen(settings.market_data_store,settings.market_history_store,mode=settings.market_data_mode)
    try:return review_owned_holding(screen,request)
    except ValueError:
        raise HTTPException(status_code=422,detail='Review the exact entered holding and assumed amounts.') from None


@app.get('/research/stock-validation',response_model=FinancialValidation)
def stock_validation_endpoint() -> FinancialValidation:
    return validate_installed_financials(settings.market_data_store,settings.market_history_store,mode=settings.market_data_mode)


@app.get("/research/data-readiness", response_model=DataReadiness)
def public_data_readiness() -> DataReadiness:
    """Read verified public coverage only; never downloads or accepts financial inputs."""
    return load_catalog(settings.market_data_store)


@app.get("/research/companies", response_model=CompanyDirectory)
def supported_companies() -> CompanyDirectory:
    return company_directory(settings.market_data_store)


@app.get("/research/companies/{issuer_key}", response_model=CompanyResearch)
def issuer_research(issuer_key: str) -> CompanyResearch:
    return company_research(settings.market_data_store, issuer_key)


@app.get("/research/companies/{issuer_key}/events", response_model=CompanyEvents)
def issuer_events(issuer_key: str) -> CompanyEvents:
    return company_events(settings.market_data_store,issuer_key)


@app.get("/research/companies/{issuer_key}/market",response_model=CompanyMarket)
def issuer_market(issuer_key: str, symbol: str | None = Query(default=None,pattern=r"^[A-Z][A-Z0-9.-]{0,14}$")) -> CompanyMarket:
    return company_market(settings.market_data_store,settings.market_history_store,issuer_key,
                          mode=settings.market_data_mode,symbol=symbol)


@app.get("/research/stock-screen",response_model=StockScreen)
def research_stock_screen() -> StockScreen:
    return stock_screen(settings.market_data_store,settings.market_history_store,mode=settings.market_data_mode)

app.add_middleware(CORSMiddleware, allow_origins=settings.parsed_cors_origins, allow_credentials=True,
                   allow_methods=["GET", "POST"], allow_headers=["*"])


@app.middleware("http")
async def privacy_boundary(request: Request, call_next):
    # Gate before parsing request bodies, including malformed payloads and IDs.
    try:
        path = request.url.path
        if path == "/scenario-runs" or path.startswith("/scenario-runs/"):
            require_saved_runs(settings)
        if path.rstrip("/") == "/optimize":
            require_ai(settings)
    except HTTPException as error:
        response = JSONResponse(status_code=error.status_code, content={"detail": error.detail})
    else:
        try:
            response = await call_next(request)
        except Exception:
            # Do not attach exception text, request paths, bodies, or tracebacks.
            logging.getLogger("privacy").error("API request failed; financial payload omitted")
            response = JSONResponse(status_code=500, content={"detail": "The calculation could not be completed."})
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.exception_handler(RequestValidationError)
async def private_validation_error(_: Request, __: RequestValidationError):
    # FastAPI's default payload can repeat financial inputs and free-text prose.
    return JSONResponse(status_code=422, content={
        "detail": "Invalid request. Review the input fields and allowed ranges.",
    })


def _tax_metrics(profile: UserFinancialProfile) -> TaxMetrics:
    result = calculate_tax(profile)
    values = asdict(result)
    values["assumptions"] = list(result.assumptions)
    values["deduction"] = DeductionBreakdown(standard_deduction=result.standard_deduction,
        itemized_deduction=result.itemized_deduction, deduction_used=result.deduction_used)
    values.pop("standard_deduction")
    values.pop("itemized_deduction")
    values.pop("deduction_used")
    values["federal_effective_rate_on_gross"] = result.federal_effective_rate_on_gross
    return TaxMetrics.model_validate(values)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", tax_year=TAX_YEAR.tax_year, ai_enabled=settings.ai_enabled)


@app.post("/calculate", response_model=TaxMetrics)
async def calculate(request: CalculateRequest) -> TaxMetrics:
    """Calculate deterministic estimates from structured inputs; no LLM is called."""
    try:
        return _tax_metrics(request)
    except (ValueError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail="Invalid financial inputs. Review supported values.") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Tax calculation failed due to an internal error.") from exc


@app.post("/optimize", response_model=OptimizeResponse)
async def optimize(request: OptimizeRequest) -> OptimizeResponse:
    """Parse natural language, calculate in Python, and add a narrative report."""
    require_ai(settings)
    try:
        profile = await parse_financial_profile(request.text)
        result = calculate_tax(profile)
        metrics = _tax_metrics(profile)
        report = await format_strategy_report(result)
        return OptimizeResponse(profile=profile, metrics=metrics, strategy_report_markdown=report)
    except AIServiceError as exc:
        raise HTTPException(status_code=503, detail="AI processing failed. Use structured inputs or try again later.") from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail="Could not validate the financial profile. Review supported inputs.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid financial inputs. Review supported values.") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Optimization failed due to an internal error.") from exc


@app.post("/portfolio/contribution-allocation", response_model=AllocationResponse)
def contribution_allocation(request: AllocationRequest) -> AllocationResponse:
    """Optimize contribution-only allocation; never persist or execute trades."""
    return allocate_contributions(request)


@app.post("/research/stock-strategy-demo", response_model=StrategyDemoResponse)
def stock_strategy_demo(request: StrategyDemoRequest) -> StrategyDemoResponse:
    """Server-generated synthetic cases only. Cannot enable live recommendations."""
    return StrategyDemoResponse.model_validate(strategy_demo(request))


@app.post("/research/experimental-basket",response_model=ExperimentalBasket)
def experimental_basket_endpoint(request: ExperimentalRequest) -> ExperimentalBasket:
    return experimental_basket(stock_screen(settings.market_data_store,settings.market_history_store,mode=settings.market_data_mode),request)


@app.post("/research/stock-proposal",response_model=StockProposal)
def stock_proposal_endpoint(request: ProposalRequest) -> StockProposal:
    return stock_proposal(stock_screen(settings.market_data_store,settings.market_history_store,mode=settings.market_data_mode),request)


@app.post("/research/stock-replay",response_model=StockReplay)
def stock_replay_endpoint(request: ReplayRequest) -> StockReplay:
    return replay_stock(settings.market_data_store,settings.market_history_store,request,mode=settings.market_data_mode)


@app.post("/research/stock-screen/filter",response_model=FilteredScreen)
def stock_screen_filter(request: ScreenFilters) -> FilteredScreen:
    return filter_screen(stock_screen(settings.market_data_store,settings.market_history_store,mode=settings.market_data_mode),request)


@app.post("/real-estate/rental-projection", response_model=RentalProjection)
def rental_projection(request: RentalProjectionRequest) -> RentalProjection:
    return project_rental(request)


@app.post("/real-estate/rental-feasibility", response_model=RentalFeasibilityResponse)
def rental_feasibility(request: RentalFeasibilityRequest) -> RentalFeasibilityResponse:
    return solve_rental_feasibility(request)


@app.post("/scenarios/portfolio", response_model=PortfolioProjectionResponse)
async def portfolio_projection(request: PortfolioProjectionRequest) -> PortfolioProjectionResponse:
    """Project contributions under an explicit assumed return and fee."""
    try:
        result = project_portfolio(request.monthly_contribution, request.years,
                                   request.annual_return_assumption, request.annual_fee_assumption)
        return PortfolioProjectionResponse.model_validate({
            **asdict(result),
            **time_budget_metrics(request.estimated_monthly_hours, request.available_monthly_hours),
        })
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/scenarios/goal-plan", response_model=GoalPlanResponse)
async def goal_plan(request: GoalPlanRequest) -> GoalPlanResponse:
    """Show nominal and inflation-adjusted savings outcomes across three assumptions."""
    try:
        scenarios: list[GoalScenarioResponse] = []
        for label in ("low", "base", "high"):
            projection = project_goal(
                current_balance=request.current_balance,
                monthly_contribution=request.monthly_contribution,
                years=request.years,
                annual_return=getattr(request.return_assumptions, label),
                annual_fee=request.annual_fee_assumption,
                annual_inflation=request.annual_inflation_assumption,
                target_amount_today=request.target_amount_today,
            )
            scenarios.append(GoalScenarioResponse(scenario=label, **asdict(projection)))
        return GoalPlanResponse(
            goal_name=request.goal_name,
            years=request.years,
            current_balance=request.current_balance,
            monthly_contribution=request.monthly_contribution,
            target_amount_today=request.target_amount_today,
            annual_inflation_assumption=request.annual_inflation_assumption,
            annual_fee_assumption=request.annual_fee_assumption,
            scenarios=scenarios,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/scenarios/goal-sensitivity", response_model=GoalSensitivityResponse)
def goal_sensitivity(request: GoalSensitivityRequest) -> GoalSensitivityResponse:
    """Rank how selected assumption ranges affect deterministic goal value."""
    try:
        result = analyze_goal_sensitivity(
            goal_name=request.goal_name,
            current_balance=request.current_balance,
            monthly_contribution=request.monthly_contribution,
            years=request.years,
            annual_return=request.annual_return_assumption,
            annual_fee=request.annual_fee_assumption,
            annual_inflation=request.annual_inflation_assumption,
            target_amount_today=request.target_amount_today,
            ranges={
                name: (getattr(getattr(request.sensitivity_ranges, name), "low"),
                       getattr(getattr(request.sensitivity_ranges, name), "high"))
                for name in ("annual_return", "monthly_contribution", "annual_fee", "annual_inflation")
            },
        )
        return GoalSensitivityResponse.model_validate(asdict(result))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/scenarios/goal-explorer", response_model=GoalExplorerResponse)
def goal_explorer(request: GoalExplorerRequest) -> GoalExplorerResponse:
    """Return deterministic annual trajectories and goal funding requirements."""
    return explore_goal(request)


@app.post("/scenarios/goal-risk-analysis", response_model=GoalRiskAnalysisResponse)
def goal_risk_analysis(request: GoalRiskAnalysisRequest) -> GoalRiskAnalysisResponse:
    """Estimate goal outcomes across seeded, assumption-driven return paths."""
    try:
        return _calculate_goal_risk(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _calculate_goal_risk(request: GoalRiskAnalysisRequest) -> GoalRiskAnalysisResponse:
    result = analyze_goal_risk(
        current_balance=request.current_balance,
        monthly_contribution=request.monthly_contribution,
        years=request.years,
        annual_return=request.annual_return_assumption,
        annual_volatility=request.annual_volatility_assumption,
        annual_fee=request.annual_fee_assumption,
        annual_inflation=request.annual_inflation_assumption,
        target_amount_today=request.target_amount_today,
        simulation_count=request.simulation_count,
        random_seed=request.random_seed,
    )
    return GoalRiskAnalysisResponse.model_validate(asdict(result))


@app.post("/scenario-runs/goal-risk", response_model=SavedGoalRiskRun)
def create_goal_risk_run(request: SaveGoalRiskRunRequest) -> SavedGoalRiskRun:
    """Calculate and explicitly save a local, reproducible goal-risk run."""
    require_saved_runs(settings)
    try:
        result = _calculate_goal_risk(request.analysis)
        saved = save_goal_risk_run(
            label=request.label,
            inputs=request.analysis.model_dump(mode="json"),
            result=result.model_dump(mode="json"),
            database_path=settings.scenario_db_path,
        )
        return SavedGoalRiskRun.model_validate(saved)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except sqlite3.Error as exc:
        raise HTTPException(status_code=500, detail="Could not save scenario run to the local database.") from exc


@app.get("/scenario-runs/goal-risk", response_model=SavedGoalRiskRunsResponse)
def saved_goal_risk_runs(limit: int = Query(default=50, ge=1, le=100)) -> SavedGoalRiskRunsResponse:
    """List recent explicitly saved goal-risk runs."""
    require_saved_runs(settings)
    try:
        runs = list_goal_risk_runs(database_path=settings.scenario_db_path, limit=limit)
        return SavedGoalRiskRunsResponse(runs=[SavedGoalRiskRun.model_validate(run) for run in runs])
    except sqlite3.Error as exc:
        raise HTTPException(status_code=500, detail="Could not read saved scenarios from the local database.") from exc


@app.get("/scenario-runs/goal-risk/{run_id}", response_model=SavedGoalRiskRun)
def saved_goal_risk_run(run_id: UUID) -> SavedGoalRiskRun:
    """Retrieve a saved goal-risk run, including exact input and output snapshots."""
    require_saved_runs(settings)
    try:
        run = get_goal_risk_run(run_id, database_path=settings.scenario_db_path)
    except sqlite3.Error as exc:
        raise HTTPException(status_code=500, detail="Could not read the saved scenario from the local database.") from exc
    if run is None:
        raise HTTPException(status_code=404, detail="Saved scenario run not found.")
    return SavedGoalRiskRun.model_validate(run)


@app.post("/scenario-runs/goal-risk/compare", response_model=CompareGoalRiskRunsResponse)
def compare_saved_goal_risk_runs(request: CompareGoalRiskRunsRequest) -> CompareGoalRiskRunsResponse:
    """Compare saved runs with aligned goal horizon and contribution assumptions."""
    require_saved_runs(settings)
    if request.baseline_run_id == request.comparison_run_id:
        raise HTTPException(status_code=422, detail="Choose two different saved runs to compare.")
    try:
        baseline = get_goal_risk_run(request.baseline_run_id, database_path=settings.scenario_db_path)
        comparison = get_goal_risk_run(request.comparison_run_id, database_path=settings.scenario_db_path)
    except sqlite3.Error as exc:
        raise HTTPException(status_code=500, detail="Could not read saved scenarios from the local database.") from exc
    if baseline is None or comparison is None:
        raise HTTPException(status_code=404, detail="One or both saved scenario runs were not found.")
    if baseline["model_version"] != comparison["model_version"]:
        raise HTTPException(status_code=409, detail="Saved runs use different model versions and cannot be compared directly.")
    base_inputs = GoalRiskAnalysisRequest.model_validate(baseline["inputs"])
    compare_inputs = GoalRiskAnalysisRequest.model_validate(comparison["inputs"])
    comparable_fields = (
        "current_balance", "monthly_contribution", "years", "annual_inflation_assumption",
        "target_amount_today", "simulation_count", "random_seed",
    )
    if any(getattr(base_inputs, name) != getattr(compare_inputs, name) for name in comparable_fields):
        raise HTTPException(status_code=422, detail="Align starting balance, monthly contribution, horizon, inflation, goal, path count, and seed before comparing runs.")
    base_result = GoalRiskAnalysisResponse.model_validate(baseline["result"])
    compare_result = GoalRiskAnalysisResponse.model_validate(comparison["result"])

    def side(run: dict[str, object], inputs: GoalRiskAnalysisRequest, result: GoalRiskAnalysisResponse) -> GoalRiskRunComparisonSide:
        return GoalRiskRunComparisonSide(
            run_id=run["run_id"], label=run["label"],
            annual_return_assumption=inputs.annual_return_assumption,
            annual_volatility_assumption=inputs.annual_volatility_assumption,
            annual_fee_assumption=inputs.annual_fee_assumption,
            p10_balance_today_dollars=result.ending_balance_p10_in_today_dollars,
            median_balance_today_dollars=result.ending_balance_median_in_today_dollars,
            p90_balance_today_dollars=result.ending_balance_p90_in_today_dollars,
            probability_of_reaching_goal=result.probability_of_reaching_goal,
        )

    probability_delta = None
    if base_result.probability_of_reaching_goal is not None and compare_result.probability_of_reaching_goal is not None:
        probability_delta = round(compare_result.probability_of_reaching_goal - base_result.probability_of_reaching_goal, 4)
    return CompareGoalRiskRunsResponse(
        baseline=side(baseline, base_inputs, base_result),
        comparison=side(comparison, compare_inputs, compare_result),
        p10_balance_delta_today_dollars=round(compare_result.ending_balance_p10_in_today_dollars - base_result.ending_balance_p10_in_today_dollars, 2),
        median_balance_delta_today_dollars=round(compare_result.ending_balance_median_in_today_dollars - base_result.ending_balance_median_in_today_dollars, 2),
        p90_balance_delta_today_dollars=round(compare_result.ending_balance_p90_in_today_dollars - base_result.ending_balance_p90_in_today_dollars, 2),
        goal_probability_delta=probability_delta,
        disclaimer="Deltas describe the two saved model runs under their stored assumptions; they are not expected returns or guarantees.",
    )


@app.post("/scenarios/retirement-accounts", response_model=RetirementAccountComparisonResponse)
async def retirement_account_comparison(request: RetirementAccountComparisonRequest) -> RetirementAccountComparisonResponse:
    """Compare Roth and traditional retirement account outcomes at equal cash cost."""
    try:
        result = compare_retirement_accounts(request.annual_gross_contribution,
            request.current_marginal_tax_rate, request.retirement_tax_rate_assumption,
            request.years, request.annual_return_assumption, request.annual_fee_assumption)
        return RetirementAccountComparisonResponse.model_validate(asdict(result))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/real-estate/rental-underwriting", response_model=RentalUnderwritingResponse)
async def rental_underwriting(request: RentalUnderwritingRequest) -> RentalUnderwritingResponse:
    """Underwrite an assumed rental or owner-occupied multifamily scenario."""
    try:
        result = underwrite_rental(**request.model_dump(exclude={"estimated_monthly_hours", "available_monthly_hours"}))
        return RentalUnderwritingResponse.model_validate({
            **asdict(result),
            **time_budget_metrics(request.estimated_monthly_hours, request.available_monthly_hours),
        })
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/real-estate/flip-underwriting", response_model=FlipUnderwritingResponse)
async def flip_underwriting(request: FlipUnderwritingRequest) -> FlipUnderwritingResponse:
    """Estimate flip project costs and profit from user-entered assumptions."""
    try:
        result = underwrite_flip(**request.model_dump(exclude={"estimated_monthly_hours", "available_monthly_hours"}))
        return FlipUnderwritingResponse.model_validate({
            **asdict(result),
            **time_budget_metrics(request.estimated_monthly_hours, request.available_monthly_hours),
        })
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/scenarios/readiness-check", response_model=FinancialReadinessResponse)
async def financial_readiness(request: FinancialReadinessRequest) -> FinancialReadinessResponse:
    """Return user-specific education prompts without ranking or recommending a strategy."""
    try:
        result = review_financial_readiness(**request.model_dump())
        values = asdict(result)
        values["review_prompts"] = list(result.review_prompts)
        return FinancialReadinessResponse.model_validate(values)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/scenarios/debt-payoff", response_model=DebtPayoffComparisonResponse)
async def debt_payoff(request: DebtPayoffRequest) -> DebtPayoffComparisonResponse:
    """Compare two payoff orders using fixed user-entered debt assumptions."""
    try:
        accounts = [DebtAccount(**debt.model_dump()) for debt in request.debts]
        result = compare_debt_payoff(accounts, request.extra_monthly_payment, request.max_months)
        return DebtPayoffComparisonResponse.model_validate(asdict(result))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
