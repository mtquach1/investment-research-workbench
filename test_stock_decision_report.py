from io import BytesIO
from pypdf import PdfReader
import pytest
from stock_decision_report import build_stock_decision_report
from test_decision_snapshots import saved


def test_pdf_recomputes_settings_funding_and_all_cards_with_private_metadata(tmp_path):
    screen,record=saved(tmp_path)
    context=record.assessment.context.model_copy(update={'horizon_years':1})
    data=build_stock_decision_report(record,screen,acknowledge_experimental=True,context_override=context)
    reader=PdfReader(BytesIO(data));text='\n'.join(page.extract_text() for page in reader.pages)
    assert data.startswith(b'%PDF-') and not reader.is_encrypted
    assert '$1,000.03' in text and 'Current evidence check' in text and '1 year' in text
    assert 'stock-decision-report-v1' in text and 'unverified' in text and 'not encrypted' in text
    assert 'Research settings' in text and 'Current company assessments' in text
    assert all(row.company in text for row in screen.rows)
    assert record.name not in str(reader.metadata)
    assert reader.trailer['/Root'].get('/OpenAction') is None and reader.trailer['/Root'].get('/Names') is None
    assert all(not page.get('/Annots') for page in reader.pages)
    assert record.assessment.context.horizon_years==5
    original_pdf=build_stock_decision_report(record,screen,acknowledge_experimental=True)
    original_text='\n'.join(page.extract_text() for page in PdfReader(BytesIO(original_pdf)).pages)
    assert '2025-12-31' in original_text and '2026-10-26' in original_text


def test_no_report_without_consent_or_current_available_evidence(tmp_path):
    screen,record=saved(tmp_path)
    with pytest.raises(ValueError):build_stock_decision_report(record,screen)
    screen.universe.fresh=False
    with pytest.raises(ValueError):build_stock_decision_report(record,screen,acknowledge_experimental=True)


def test_hostile_labels_and_long_rows_are_inert_and_layout_bounded(tmp_path):
    from decision_snapshots import freeze_decision
    from stock_decisions import assess_decisions
    screen,record=saved(tmp_path)
    screen.rows[0].company='<img src="https://invalid.local/private">'+'Long name '*100
    snapshot=freeze_decision(assess_decisions(screen,record.assessment.context),name='<b>Private</b> label',saved_on=screen.checked_on)
    data=build_stock_decision_report(snapshot,screen,acknowledge_experimental=True)
    reader=PdfReader(BytesIO(data));text='\n'.join(page.extract_text() for page in reader.pages)
    normalized=' '.join(text.split())
    assert '<b>Private</b> label' in normalized and '[full text in JSON]' in normalized
    assert '<b>Private' not in str(reader.metadata)
    assert all(not page.get('/Annots') for page in reader.pages)
