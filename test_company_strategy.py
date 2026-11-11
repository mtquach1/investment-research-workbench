"""Independent rule boundaries and explanations without fabricated live scores."""

from datetime import date
from decimal import Decimal

from company_research import company_research
from company_strategy import explain_company_strategy
from stock_strategy import SPEC
from strategy_financial_rules import financial_checks
from test_company_research import research_store, DAY


def test_report_keeps_raw_features_weights_and_market_gaps(tmp_path):
    detail=company_research(research_store(tmp_path),"aapl",today=DAY)
    result=detail.strategy_evidence
    features={row.key:row for row in result.features}
    assert features["return_on_assets"].value==Decimal(".1")
    assert features["operating_margin"].value==Decimal(".2")
    assert features["free_cashflow_margin"].value==Decimal(".12")
    assert features["earnings_yield"].value is None
    assert features["free_cashflow_yield"].status=="unavailable"
    assert sum(row.weight for row in result.features)==1
    assert all(row.weight==Decimal(".2") for row in result.features)
    assert all(row.status=="pass" for row in result.financial_checks)
    assert result.score is None and not result.recommendation_enabled
    assert len(result.unresolved_requirements)==8


def test_losses_missing_inputs_and_stale_periods_are_distinct(tmp_path):
    year=company_research(research_store(tmp_path),"aapl",today=DAY).latest.model_copy(deep=True)
    year.facts["net_income"].value=Decimal("-1")
    del year.facts["capital_expenditures"]
    del year.facts["free_cashflow"]
    result=explain_company_strategy(year,as_of=date(2028,1,1))
    checks={row.key:row.status for row in result.financial_checks}
    assert checks["net_income"]=="fail"
    assert checks["cash_capex"]==checks["free_cashflow"]=="unavailable"
    assert checks["financial_period_age"]=="fail"
    assert not result.recommendation_enabled and result.score is None


def test_liability_boundary_is_inclusive_and_does_not_round():
    values={key:Decimal("100") for key in SPEC["required_positive_fields"]}
    values.update(assets_end=Decimal("100"),liabilities=Decimal("85"),cash_capex=Decimal("0"))
    def result():return {row["key"]:row["status"] for row in financial_checks(values,SPEC)}
    assert result()["leverage_limit"]=="pass"
    values["liabilities"]=Decimal("85.00000000000000000000000000001")
    assert result()["leverage_limit"]=="fail"
    values["liabilities"]=None
    assert result()["leverage_limit"]=="unavailable"
    values["liabilities"]=Decimal("-1")
    assert result()["liabilities"]=="fail" and result()["leverage_limit"]=="unavailable"


def test_no_capex_sign_guess_and_no_future_or_mixed_filing_pass(tmp_path):
    year=company_research(research_store(tmp_path),"aapl",today=DAY).latest.model_copy(deep=True)
    year.facts["capital_expenditures"].value=Decimal("-60")
    year.facts["net_income"].accession="different-filing"
    year.facts["revenue"].filed="2027-01-01"
    result=explain_company_strategy(year,as_of=DAY)
    checks={row.key:row.status for row in result.financial_checks}
    assert checks["cash_capex"]=="fail" and checks["free_cashflow"]=="unavailable"
    assert checks["filing_evidence"]=="fail"
