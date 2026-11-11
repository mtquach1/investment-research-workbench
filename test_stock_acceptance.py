from stock_acceptance import evaluate_stock_workflow
from test_experimental_basket import research_universe


def test_fresh_evidence_exercises_connected_workflow_without_changing_sources(tmp_path):
    screen=research_universe(tmp_path);before=screen.model_dump_json()
    report=evaluate_stock_workflow(screen)
    assert report.status=='passed'
    assert len(report.checks)>=8 and all(item.status=='passed' for item in report.checks)
    assert report.public_release_id==screen.public_release_id
    assert report.market_snapshot_sha256==screen.market_snapshot_sha256
    assert not report.production_ready and not report.investment_performance_verified
    assert report.input_summary.references_fresh
    assert report.input_summary.company_count==20
    assert report.input_summary.candidate_count==10
    assert report.input_summary.oldest_price_date<=report.input_summary.newest_price_date
    assert screen.model_dump_json()==before
    assert report==evaluate_stock_workflow(screen)


def test_stale_evidence_never_turns_guard_checks_into_workflow_acceptance(tmp_path):
    screen=research_universe(tmp_path);screen.universe.fresh=False
    report=evaluate_stock_workflow(screen)
    assert report.status=='incomplete'
    states={item.check_id:item.status for item in report.checks}
    assert states['stale_withholding']=='passed'
    assert states['decision_portability']=='blocked'
    assert states['monthly_accounting']=='blocked'
    assert states['holding_note_portability']=='passed'  # personal opinions need no market data
    assert not report.input_summary.references_fresh
    assert report.input_summary.candidate_count is None


def test_incomplete_candidate_pool_explains_the_actual_blocker(tmp_path):
    screen=research_universe(tmp_path)
    for row in screen.rows:
        row.price_status='unavailable'
    report=evaluate_stock_workflow(screen)
    assert report.status=='incomplete' and report.input_summary.references_fresh
    assert report.input_summary.candidate_count==0
    assert report.input_summary.blocking_reason_counts
    detail=next(item.detail for item in report.checks if item.check_id=='monthly_accounting')
    assert '0 of 10' in detail


def test_invalid_monthly_accounting_is_a_failure_not_an_investment_result(tmp_path,monkeypatch):
    import stock_acceptance
    from stock_monthly import plan_monthly_contribution
    def broken(screen,ctx):
        result=plan_monthly_contribution(screen,ctx)
        result.cash_unassigned_cents+=1
        return result
    monkeypatch.setattr(stock_acceptance,'plan_monthly_contribution',broken)
    report=evaluate_stock_workflow(research_universe(tmp_path))
    assert report.status=='failed'
    assert next(item for item in report.checks if item.check_id=='monthly_accounting').status=='failed'


def test_check_errors_are_sanitized_and_fail_closed(tmp_path,monkeypatch):
    import stock_acceptance
    def broken(*args,**kwargs):raise ValueError('PRIVATE INPUT MARKER')
    monkeypatch.setattr(stock_acceptance,'freeze_decision',broken)
    report=evaluate_stock_workflow(research_universe(tmp_path))
    assert report.status=='failed' and 'PRIVATE INPUT MARKER' not in report.model_dump_json()
