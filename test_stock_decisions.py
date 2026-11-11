"""Behavioral decision boundaries, not investment-performance tests."""
from decimal import Decimal as D
import pytest
from pydantic import ValidationError
from test_experimental_basket import research_universe
from stock_evidence import evidence_inventory
from stock_decisions import DecisionContext, DecisionHolding, assess_decisions, POLICY_HASH
from experimental_basket import ExperimentalRequest, experimental_basket
from security_listing import ListingEvidence


def context(**changes):
    return DecisionContext(acknowledge_experimental=True, **changes)


def indexed(result):
    return {card.symbols[0]: card for card in result.cards}


def test_consent_source_mode_and_stale_universe_withhold_decisions(tmp_path):
    screen = research_universe(tmp_path)
    assert assess_decisions(screen, DecisionContext()).status == 'acknowledgement_required'
    for status in ('withheld', 'unavailable', 'integrity_error'):
        screen.status = status
        result = assess_decisions(screen, context())
        assert result.status == 'unavailable' and not result.cards
        assert not evidence_inventory(screen).companies
        assert result.cash_unassigned_cents == 1000000
    screen.status = 'available'
    screen.universe.fresh = False
    assert assess_decisions(screen, context()).status == 'unavailable'


def test_baseline_selection_exact_cents_and_provenance_do_not_mutate_inputs(tmp_path):
    screen = research_universe(tmp_path)
    before = screen.model_dump_json()
    request = context(new_cash_cents=100003)
    result = assess_decisions(screen, request)
    baseline = experimental_basket(screen, ExperimentalRequest(acknowledge_proxy_and_estimates=True, budget_cents=100003))
    assert result.status == 'experimental' and result.outcome_counts == {'pass': 10, 'buy_candidate': 10}
    assert sum(card.paper_addition_cents for card in result.cards) == 100000
    assert result.cash_unassigned_cents == 3
    assert {card.symbols[0] for card in result.cards if card.outcome == 'buy_candidate'} == {row.symbol for row in baseline.selected}
    assert result.policy_sha256 == POLICY_HASH and len(POLICY_HASH) == 64
    assert result.public_release_id == screen.public_release_id
    assert not result.live_recommendations_enabled
    assert screen.model_dump_json() == before
    screen.rows.reverse()
    assert assess_decisions(screen, request).model_dump_json() == result.model_dump_json()


def test_rank_removal_alone_is_not_a_sell_and_held_amount_is_not_added_again(tmp_path):
    screen = research_universe(tmp_path)
    baseline = indexed(assess_decisions(screen, context()))
    low = next(symbol for symbol, card in baseline.items() if card.outcome == 'pass')
    high = next(symbol for symbol, card in baseline.items() if card.outcome == 'buy_candidate')
    result = indexed(assess_decisions(screen, context(maximum_direct_weight=1,
        holdings=[DecisionHolding(symbol=low, value_cents=10000), DecisionHolding(symbol=high, value_cents=10000)])))
    assert result[low].outcome == result[high].outcome == 'hold'
    assert result[low].reasons[0].code == 'holding_rules_pass'
    assert result[high].paper_addition_cents == 0


def test_missing_evidence_overrides_failure_but_preserves_known_review_flags(tmp_path):
    screen = research_universe(tmp_path)
    row = screen.rows[0]
    row.financial_status = 'fail'
    row.financial_reasons = ['Profitability fails', 'Beginning assets unavailable']
    row.financial_missing_reasons = ['Beginning assets unavailable']
    request = context(holdings=[DecisionHolding(symbol=row.tickers[0], value_cents=10000)])
    card = indexed(assess_decisions(screen, request))[row.tickers[0]]
    assert card.outcome == 'insufficient_evidence'
    assert any(item.code == 'financial_inputs' for item in card.reasons)
    assert any(item.code == 'concentration' for item in card.review_flags)
    assert not card.paper_addition_cents


def test_complete_failure_passes_for_unheld_and_triggers_review_for_held(tmp_path):
    screen = research_universe(tmp_path)
    row = screen.rows[0]
    row.financial_status = 'fail'
    row.financial_reasons = ['Annual financial checks fail']
    assert indexed(assess_decisions(screen, context()))[row.tickers[0]].outcome == 'pass'
    result = indexed(assess_decisions(screen, context(maximum_direct_weight=1,
        holdings=[DecisionHolding(symbol=row.tickers[0], value_cents=10000)])))
    assert result[row.tickers[0]].outcome == 'review_for_trim_or_sell'


@pytest.mark.parametrize('change', ['stale_price', 'short_history', 'missing_yield', 'listing_conflict', 'duplicate_issuer', 'multiple_classes', 'missing_quality', 'invalid_filing_vintage'])
def test_evidence_defects_are_not_negative_investment_judgments(tmp_path, change):
    screen = research_universe(tmp_path)
    row = screen.rows[0]
    symbol = row.tickers[0]
    if change == 'stale_price': row.price_status = 'fail'
    elif change == 'short_history': row.history_count_status = 'fail'
    elif change == 'missing_yield': row.valuation.annual_earnings_yield_estimate = None
    elif change == 'listing_conflict': row.listing_evidence[symbol] = ListingEvidence(status='exchange_conflict')
    elif change == 'duplicate_issuer': screen.rows[1].cik = row.cik
    elif change == 'multiple_classes': row.tickers.append('OTHER')
    elif change == 'missing_quality': row.metrics['operating_margin'].status = 'missing_inputs'
    elif change == 'invalid_filing_vintage':
        row.financial_status = 'fail'
        row.financial_evidence_reasons = ['Inputs do not share a known filing vintage.']
    assert indexed(assess_decisions(screen, context()))[symbol].outcome == 'insufficient_evidence'


def test_personal_constraints_do_not_rewrite_quality_scores_and_cash_reconciles(tmp_path):
    screen = research_universe(tmp_path)
    baseline = assess_decisions(screen, context(new_cash_cents=100003))
    selected = next(card for card in baseline.cards if card.outcome == 'buy_candidate')
    restricted = assess_decisions(screen, context(new_cash_cents=100003, excluded_symbols=selected.symbols))
    assert [card.research_score for card in restricted.cards] == [card.research_score for card in baseline.cards]
    assert indexed(restricted)[selected.symbols[0]].outcome == 'pass'
    assert restricted.cash_unassigned_cents == 10003
    assert sum(card.paper_addition_cents for card in restricted.cards) + restricted.cash_unassigned_cents == 100003
    tight = assess_decisions(screen, context(new_cash_cents=100003, maximum_direct_weight=D('.09')))
    assert not any(card.outcome == 'buy_candidate' for card in tight.cards)
    assert tight.cash_unassigned_cents == 100003


def test_horizon_volatility_unknown_holdings_and_contribution_intentions(tmp_path):
    screen = research_universe(tmp_path)
    short = assess_decisions(screen, context(horizon_years=4))
    assert all(card.outcome == 'pass' for card in short.cards)
    limited = assess_decisions(screen, context(maximum_volatility=D('.20')))
    assert all(card.outcome == 'pass' for card in limited.cards)
    screen.rows[0].metrics['annualized_volatility'].status = 'missing_inputs'
    assert indexed(assess_decisions(screen, context(maximum_volatility=D('.20'))))['T00'].outcome == 'insufficient_evidence'
    unknown = indexed(assess_decisions(screen, context(holdings=[DecisionHolding(symbol='VOO', value_cents=100)])))['VOO']
    assert unknown.outcome == 'insufficient_evidence' and unknown.held_value_cents == 100
    assert unknown.review_flags[0].code == 'concentration'
    first = assess_decisions(screen, context())
    recurring = assess_decisions(screen, context(monthly_contribution_cents=50000))
    assert [card.model_dump() for card in first.cards] == [card.model_dump() for card in recurring.cards]


def test_zero_funding_withholds_new_candidates_but_allows_supported_hold_review(tmp_path):
    screen = research_universe(tmp_path)
    result = assess_decisions(screen, context(new_cash_cents=0, maximum_direct_weight=1,
        holdings=[DecisionHolding(symbol='T00', value_cents=100)]))
    assert result.baseline_status == 'infeasible' and indexed(result)['T00'].outcome == 'hold'
    assert not any(card.paper_addition_cents for card in result.cards)


def test_evidence_inventory_reconciles_per_requirement_and_retains_dates(tmp_path):
    screen = research_universe(tmp_path)
    screen.rows[0].valuation.status = 'stale'
    result = evidence_inventory(screen)
    assert len(result.companies) == 20
    assert all(sum(counts.values()) == 20 for counts in result.counts.values())
    assert result.counts['valuation']['missing'] == 1 and result.counts['valuation']['provisional'] == 19
    assert result.counts['security_identity']['missing'] == 20
    assert result.screen.checked_on == screen.checked_on
    assert not result.strict_recommendations_enabled and not result.automatic_refresh_enabled


@pytest.mark.parametrize('values', [
    {'live_recommendations_enabled': True}, {'horizon_years': True}, {'new_cash_cents': '100'},
    {'maximum_direct_weight': 'NaN'}, {'maximum_volatility': 'Infinity'},
    {'acknowledge_experimental': 'true'}, {'excluded_symbols': ['AAPL', 'AAPL']},
    {'holdings': [{'symbol': 'AAPL', 'value_cents': 100}] * 2},
    {'holdings': [{'symbol': 'AAPL', 'value_cents': 100000000}, {'symbol': 'MSFT', 'value_cents': 1}]},
])
def test_context_rejects_certification_injection_duplicates_and_unbounded_inputs(values):
    with pytest.raises(ValidationError): DecisionContext(**values)
