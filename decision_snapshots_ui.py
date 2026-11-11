"""Named session-only decision records; private JSON import and current-evidence review."""
import hashlib
import json
import pandas as pd
import streamlit as st
from decision_snapshots import freeze_decision,restore_decision,review_decision,SnapshotReview
from public_data_store import canonical_bytes

OUTCOMES={'buy_candidate':'Candidate · experimental','hold':'Hold · limited rules',
    'review_for_trim_or_sell':'Investigate trim/sell','pass':'Pass','insufficient_evidence':'Needs evidence'}


def _store(record):
    records=st.session_state.setdefault('_decision_snapshots',[])
    if len(records)>=10 or any(item['fingerprint']==record.fingerprint for item in records):
        raise ValueError('Session limit or duplicate record')
    records.append(record.model_dump(mode='json'))


def render_decision_snapshots(screen,context,result):
    panel=st.expander('4 · Save, reopen and compare decisions',key='decision_snapshot_panel',on_change='rerun')
    if not panel.open:return
    with panel:
        records=st.session_state.setdefault('_decision_snapshots',[])
        st.caption(f'{len(records)} / 10 records in this session. Download to keep a record after clearing or closing the session. Files contain your holdings and settings; save them privately.')
        name=st.text_input('Snapshot name',value=f'Research {screen.checked_on}',max_chars=80,key='decision_snapshot_name')
        if st.button('Save current assessment',disabled=result.status!='experimental' or len(records)>=10,key='decision_snapshot_save'):
            try:
                _store(freeze_decision(result,name=name,saved_on=screen.checked_on))
                st.success('Saved in this session. Download the selected snapshot below to keep it.')
            except ValueError:st.warning('Could not save: use a name, a complete experimental assessment, and a new record within the session limit.')
        with st.expander('Restore a downloaded record'):
            upload=st.file_uploader('Decision snapshot JSON',type=['json'],max_upload_size=1,key='decision_snapshot_upload')
            if st.button('Restore decision snapshot',disabled=upload is None or len(records)>=10,key='decision_snapshot_restore'):
                try:
                    record=restore_decision(upload.getvalue(),today=screen.checked_on,
                        known_fingerprints=[item['fingerprint'] for item in records])
                    _store(record)
                    st.success('Restored as an unverified saved record. Recompute it below using current installed evidence.')
                except ValueError:st.warning('Could not restore: check the snapshot format, size, checksum, dates or duplicate/session limit. Older raw assessment downloads are not restorable snapshots.')
        if not records:
            st.info('Save an assessment or restore a snapshot to review it after evidence changes.')
            return
        by_id={item['fingerprint']:item for item in records}
        selected=st.selectbox('Saved research record',list(by_id),format_func=lambda key:by_id[key]['name']+' · '+by_id[key]['saved_on'],key='decision_snapshot_selected')
        record=restore_decision(json.dumps(by_id[selected]),today=screen.checked_on)
        st.caption(f'Recorded assessment: {record.assessment.checked_on} · Saved record date: {record.saved_on} · Current evidence check: {screen.checked_on}')
        st.warning('Recorded results and dates are unverified. A checksum detects accidental changes; it does not authenticate a saved assessment.')
        st.download_button('Download selected decision snapshot (private JSON)',record.model_dump_json(indent=2),file_name='stock-decision-snapshot.json',mime='application/json')
        if st.button('Remove selected snapshot from session',key='decision_snapshot_remove'):
            st.session_state['_decision_snapshots']=[item for item in records if item['fingerprint']!=selected]
            st.session_state.pop('_decision_snapshot_review',None)
            st.rerun()
        mode=st.radio('Settings for recomputation',['Saved settings','Current editor settings'],horizontal=True,key='decision_snapshot_mode')
        override=context if mode=='Current editor settings' else None
        with st.expander('Inspect the saved settings'):
            st.json(record.assessment.context.model_dump(mode='json'))
        signature=hashlib.sha256(canonical_bytes({'record':selected,'mode':mode,
            'context':(override or record.assessment.context).model_dump(mode='json'),
            'screen':screen.model_dump(mode='json')})).hexdigest()
        if st.button('Recompute and compare with current evidence',key='decision_snapshot_compare'):
            review=review_decision(record,screen,acknowledge_experimental=True,context_override=override)
            st.session_state['_decision_snapshot_review']={'signature':signature,'review':review.model_dump(mode='json')}
        saved=st.session_state.get('_decision_snapshot_review')
        if not saved or saved['signature']!=signature:
            st.session_state.pop('_decision_snapshot_review',None)
            st.session_state.pop('_decision_snapshot_pdf',None)
            st.caption('Recompute after choosing a record or changing settings/evidence. Previous comparisons are cleared when their inputs change.')
            return
        review=SnapshotReview.model_validate(saved['review'])
        if review.status!='reviewed':
            st.session_state.pop('_decision_snapshot_pdf',None)
            st.warning('Current evidence cannot support an assessment. Recorded outcomes are not carried forward as current recommendations.')
            return
        a,b=st.columns(2)
        a.metric('Companies or holdings with changes',len(review.changes))
        b.metric('Current unassigned cash ($)',f'{review.current.cash_unassigned_cents/100:,.2f}')
        st.caption('Compared with the unverified saved result using '+mode.lower()+'. Changes are findings to investigate, not instructions to trade.')
        st.write('Changed input references: '+(', '.join(review.changed_inputs) or 'None detected.'))
        if review.changes:
            st.dataframe(pd.DataFrame([{'Company':item.company,
                'Recorded assessment':OUTCOMES.get(item.previous_outcome,'Not covered'),
                'Current assessment':OUTCOMES.get(item.current_outcome,'Not covered'),
                'Recorded paper amount ($)':f'{item.previous_addition_cents/100:,.2f}',
                'Current paper amount ($)':f'{item.current_addition_cents/100:,.2f}',
                'What changed':'; '.join(item.triggers)} for item in review.changes]),hide_index=True,width='stretch')
        else:st.success('No assessment, sizing, score, symbol or evidence-finding changes detected for these inputs.')
        st.download_button('Download this comparison (private JSON)',review.model_dump_json(indent=2),file_name='stock-decision-change-review.json',mime='application/json')
        with st.expander('Export a readable private report'):
            st.caption('PDF summary of current settings, every assessment, primary reasons, changes and source dates. Full evidence remains in JSON. Recomputed before export; not encrypted.')
            if st.button('Prepare private PDF report',key='decision_snapshot_pdf_prepare'):
                from stock_decision_report import build_stock_decision_report
                data=build_stock_decision_report(record,screen,acknowledge_experimental=True,context_override=override)
                st.session_state['_decision_snapshot_pdf']={'signature':signature,'data':data}
            pdf=st.session_state.get('_decision_snapshot_pdf')
            if pdf and pdf['signature']==signature:
                st.download_button('Download private PDF report',pdf['data'],file_name='stock-decision-review.pdf',mime='application/pdf')
        st.caption(review.notice)
