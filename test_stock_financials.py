"""Independent annual metrics and filing-coherence reference cases."""

from copy import deepcopy
from datetime import date
from decimal import Decimal

import pytest

from stock_financials import normalize_annual_financials


AS_OF = date(2026, 10, 28)


def company():
    data = {"cik": 123, "entityName": "Synthetic issuer", "facts": {"us-gaap": {}}}
    annual = {"RevenueFromContractWithCustomerExcludingAssessedTax": 1000, "OperatingIncomeLoss": 200,
              "NetIncomeLoss": 100, "NetCashProvidedByUsedInOperatingActivities": 180,
              "PaymentsToAcquirePropertyPlantAndEquipment": 60}
    for tag, amount in annual.items():
        data["facts"]["us-gaap"][tag] = {"units": {"USD": [
            {"start": "2025-01-01", "end": "2025-12-31", "filed": "2026-02-01", "accn": "one",
             "form": "10-K", "val": amount}]}}
    for tag, observations in {"Assets": [("2024-12-31", 900), ("2025-12-31", 1100)],
                              "Liabilities": [("2025-12-31", 550)]}.items():
        data["facts"]["us-gaap"][tag] = {"units": {"USD": [
            {"end": end, "filed": "2026-02-01", "accn": "one", "form": "10-K", "val": value}
            for end, value in observations]}}
    return data


def test_metrics_match_independent_arithmetic_and_retain_provenance():
    result = normalize_annual_financials(company(), as_of=AS_OF, source_sha256="a"*64)
    assert result.financials_complete
    assert result.metrics["return_on_assets"] == Decimal(".1")
    assert result.metrics["operating_margin"] == Decimal(".2")
    assert result.metrics["free_cashflow_margin"] == Decimal(".12")
    assert result.metrics["liabilities_to_assets"] == Decimal(".5")
    assert result.facts["free_cashflow"].value == 120
    assert result.facts["free_cashflow"].inputs == ("operating_cashflow", "capital_expenditures")
    assert all(fact.accession == "one" for fact in result.facts.values())
    assert result.source_sha256 == "a"*64
    assert result.metrics["earnings_yield"] is None and not result.recommendation_ready


def test_liabilities_fallback_requires_total_equity_including_noncontrolling_interests():
    data = company()
    data["facts"]["us-gaap"].pop("Liabilities")
    total_equity = {"units": {"USD": [{"end": "2025-12-31", "filed": "2026-02-01",
                                      "accn": "one", "form": "10-K", "val": 550}]}}
    data["facts"]["us-gaap"]["StockholdersEquity"] = total_equity
    missing = normalize_annual_financials(data, as_of=AS_OF)
    assert missing.metrics["liabilities_to_assets"] is None
    data["facts"]["us-gaap"]["StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"] = total_equity
    derived = normalize_annual_financials(data, as_of=AS_OF)
    assert derived.financials_complete
    assert derived.facts["liabilities_end"].value == 550
    assert derived.facts["liabilities_end"].inputs == ("assets_end", "total_equity_end")


def test_liabilities_can_sum_reported_current_and_noncurrent_totals_without_equity_assumptions():
    data=company();facts=data['facts']['us-gaap'];template=facts.pop('Liabilities')['units']['USD'][0]
    facts['LiabilitiesCurrent']={'units':{'USD':[dict(template,val=300)]}}
    facts['LiabilitiesNoncurrent']={'units':{'USD':[dict(template,val=250)]}}
    result=normalize_annual_financials(data,as_of=AS_OF)
    assert result.facts['liabilities_end'].value==550 and result.metrics['liabilities_to_assets']==Decimal('.5')
    assert result.facts['liabilities_end'].tag=='derived:current_plus_noncurrent_liabilities'
    assert result.facts['liabilities_end'].inputs==('current_liabilities_end','noncurrent_liabilities_end')


@pytest.mark.parametrize('fault',['missing','different_accession','different_period','duration','negative','conflicting'])
def test_liability_components_cannot_be_guessed_or_mixed(fault):
    data=company();facts=data['facts']['us-gaap'];template=facts.pop('Liabilities')['units']['USD'][0]
    facts['LiabilitiesCurrent']={'units':{'USD':[dict(template,val=300)]}}
    value=dict(template,val=250)
    facts['LiabilitiesNoncurrent']={'units':{'USD':[value]}}
    if fault=='missing':facts.pop('LiabilitiesNoncurrent')
    elif fault=='different_accession':value['accn']='different'
    elif fault=='different_period':value['end']='2024-12-31'
    elif fault=='duration':value['start']='2025-01-01'
    elif fault=='negative':value['val']=-1
    elif fault=='conflicting':facts['LiabilitiesNoncurrent']['units']['USD'].append(dict(value,val=251))
    assert normalize_annual_financials(data,as_of=AS_OF).metrics['liabilities_to_assets'] is None


def test_ambiguous_direct_liabilities_do_not_use_a_fallback_to_hide_the_conflict():
    data=company();facts=data['facts']['us-gaap'];template=facts['Liabilities']['units']['USD'][0]
    facts['Liabilities']['units']['USD'].append(dict(template,val=999))
    for tag,value in [('LiabilitiesCurrent',300),('LiabilitiesNoncurrent',250)]:facts[tag]={'units':{'USD':[dict(template,val=value)]}}
    assert normalize_annual_financials(data,as_of=AS_OF).metrics['liabilities_to_assets'] is None


def test_future_amendment_is_excluded_and_partial_known_amendment_never_mixes_filings():
    data = company()
    original = data["facts"]["us-gaap"]["RevenueFromContractWithCustomerExcludingAssessedTax"]["units"]["USD"][0]
    amendment = dict(original, filed="2026-11-01", accn="two", form="10-K/A", val=1100)
    data["facts"]["us-gaap"]["RevenueFromContractWithCustomerExcludingAssessedTax"]["units"]["USD"].append(amendment)
    assert normalize_annual_financials(data, as_of=AS_OF).accession == "one"
    amendment["filed"] = "2026-10-01"
    result = normalize_annual_financials(data, as_of=AS_OF)
    assert result.accession == "two" and not result.financials_complete
    assert result.metrics["operating_margin"] is None


def test_inconsistent_same_accession_values_are_rejected():
    data = company()
    values = data["facts"]["us-gaap"]["NetIncomeLoss"]["units"]["USD"]
    values.append(dict(values[0], val=999))
    result = normalize_annual_financials(data, as_of=AS_OF)
    assert "ambiguous_fact:net_income" in result.issues
    assert result.metrics["return_on_assets"] is None


def test_quarterly_or_wrong_currency_facts_cannot_fill_missing_annual_inputs():
    data = company()
    income = data["facts"]["us-gaap"]["OperatingIncomeLoss"]["units"]["USD"][0]
    income["start"] = "2025-10-01"
    cf = data["facts"]["us-gaap"]["NetCashProvidedByUsedInOperatingActivities"]["units"]
    cf["EUR"] = cf.pop("USD")
    result = normalize_annual_financials(data, as_of=AS_OF)
    assert not result.financials_complete
    assert result.metrics["operating_margin"] is None and result.metrics["free_cashflow_margin"] is None


def test_cash_capex_sign_and_nonpositive_assets_fail_closed():
    data = company()
    data["facts"]["us-gaap"]["PaymentsToAcquirePropertyPlantAndEquipment"]["units"]["USD"][0]["val"] = -60
    data["facts"]["us-gaap"]["Assets"]["units"]["USD"][0]["val"] = -10
    result = normalize_annual_financials(data, as_of=AS_OF)
    assert result.metrics["free_cashflow_margin"] is None
    assert result.metrics["return_on_assets"] is None
    assert "invalid_negative_cash_capex" in result.issues
    assert not result.financials_complete


def test_stale_period_is_not_strategy_ready_and_separate_calls_do_not_share_data():
    original = company()
    stale = normalize_annual_financials(original, as_of=date(2028, 1, 1))
    assert not stale.financials_complete
    assert "financial_period_older_than_strategy_gate" in stale.issues
    other = deepcopy(original)
    other["entityName"] = "Another issuer"
    first = normalize_annual_financials(original, as_of=AS_OF)
    second = normalize_annual_financials(other, as_of=AS_OF)
    assert first.issuer != second.issuer and first.facts is not second.facts
