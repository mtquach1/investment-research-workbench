"""Plain-language, session-only review of entered exact-symbol holdings."""
from decimal import Decimal
import streamlit as st
from holding_research import HoldingReviewInputs,HoldingReviewRequest,review_owned_holding
from holding_notes import save_holding_note,restore_holding_note

STATES={'not_reviewed':'I have not checked yet','still_supported':'My original reason still holds',
    'concerns':'I have concerns','no_longer_supported':'My original reason no longer holds'}


def _cents(value):
    amount=Decimal(str(value))
    if not amount.is_finite() or amount!=amount.quantize(Decimal('.01')):raise ValueError('Use cents')
    return int(amount*100)


def render_owned_holdings(screen,context):
    if not context.holdings:return
    panel=st.expander('Review a stock I already own',key='owned_holding_panel',on_change='rerun')
    if not panel.open:return
    with panel:
        st.caption('Your reason for owning a stock and the company evidence are checked separately. A lower ranking alone is not a reason to sell.')
        by_symbol={item.symbol:item for item in context.holdings}
        drafts=st.session_state.setdefault('_holding_note_drafts',{})
        for removed in set(drafts)-set(by_symbol):
            del drafts[removed]
        with st.expander('Reopen a personal note'):
            st.caption('Add the matching holding first. Restoring replaces that holding’s reason and notes only; sale illustrations reset. Saved dates and opinions are unverified. Company evidence is checked again.')
            upload=st.file_uploader('Personal holding note JSON (16 KB maximum)',type=['json'],max_upload_size=1,key='holding_note_upload')
            if st.button('Restore personal note',disabled=upload is None,key='holding_note_restore'):
                try:
                    note=restore_holding_note(upload.getvalue(),context,today=screen.checked_on)
                    restored_prefix='owned_'+note.symbol
                    drafts[note.symbol]={'reason':note.reason_state,'notes':note.notes}
                    st.session_state['owned_holding_symbol']=note.symbol
                    st.session_state[restored_prefix+'_reason']=note.reason_state
                    st.session_state[restored_prefix+'_notes']=note.notes
                    for suffix in ('simulate','fee','know_cost','cost'):
                        st.session_state.pop(restored_prefix+'_'+suffix,None)
                    st.success(f'Personal note restored for {note.symbol}. Saved date {note.saved_on} and opinions are unverified; company evidence is recomputed. Sale assumptions cleared.')
                except ValueError:
                    st.warning('Could not restore. Use a personal-note file under 16 KB with a valid date, opt in, and enter its exact holding. Review downloads and decision snapshots use different formats.')
        if st.session_state.get('owned_holding_symbol') not in by_symbol:
            st.session_state.pop('owned_holding_symbol',None)
        symbol=st.selectbox('Holding to review',list(by_symbol),key='owned_holding_symbol')
        holding=by_symbol[symbol];prefix='owned_'+symbol
        draft=drafts.get(symbol,{'reason':'not_reviewed','notes':''})
        for suffix in ('reason','notes'):
            if prefix+'_'+suffix not in st.session_state:
                st.session_state[prefix+'_'+suffix]=draft[suffix]
        st.metric('Your entered holding value ($)',f'{holding.value_cents/100:,.2f}')
        reason=st.selectbox('Does your original reason for owning it still hold?',list(STATES),format_func=STATES.get,key=prefix+'_reason')
        notes=st.text_area('My reason and what would change my mind (optional)',max_chars=500,key=prefix+'_notes',
            help='Your private notes are not verified company facts and do not change the strategy score.')
        drafts[symbol]={'reason':reason,'notes':notes}
        st.caption('Notes stay in this session. Download a personal note below to reopen it later; clearing private data removes session drafts.')
        if context.acknowledge_experimental:
            note=save_holding_note(context,symbol,HoldingReviewInputs(reason_state=reason,notes=notes),saved_on=screen.checked_on)
            st.download_button('Download personal note (restorable JSON)',note.model_dump_json(indent=2),
                file_name=f'personal-holding-note-{symbol}.json',mime='application/json')
        simulate=st.checkbox('Show a hypothetical full sale, before tax',key=prefix+'_simulate')
        fee=0;cost=None
        if simulate:
            st.caption(r'Example: an entered value of \$1,000 minus a \$5 sale fee leaves \$995 before tax. This is an illustration, not a sell instruction.')
            fee=st.number_input('Assumed total sale fee ($)',0.0,1000000.0,0.0,1.0,key=prefix+'_fee')
            if st.checkbox('I know the total amount I paid for this holding',key=prefix+'_know_cost'):
                cost=st.number_input('Total amount paid ($)',0.0,10000000.0,0.0,1.0,key=prefix+'_cost',
                    help='An entered acquisition cost for this illustration, not a tax-basis or tax-lot calculation.')
        try:
            inputs=HoldingReviewInputs(reason_state=reason,notes=notes,illustrate_full_sale=simulate,
                assumed_sale_fee_cents=_cents(fee),purchase_cost_cents=_cents(cost) if cost is not None else None)
            result=review_owned_holding(screen,HoldingReviewRequest(context=context,symbol=symbol,inputs=inputs))
        except ValueError:
            st.warning('Use valid amounts with at most two decimal places. The assumed fee cannot exceed the holding value.')
            return
        st.markdown('**'+{'needs_evidence':'Company evidence needed','review_needed':'Take a closer look',
            'limited_checks_pass':'Limited checks pass','acknowledgement_required':'Research opt-in needed'}[result.status]+'**')
        st.write(result.summary)
        for concern in result.concerns:st.write(concern)
        if result.illustration:
            illustration=result.illustration
            a,b=st.columns(2)
            a.metric('Cash after assumed fee, before tax ($)',f'{illustration.cash_before_tax_cents/100:,.2f}')
            b.metric('Change versus entered purchase cost ($)',
                f'{illustration.change_from_entered_cost_cents/100:,.2f}' if illustration.change_from_entered_cost_cents is not None else 'Cost not entered')
            st.caption(f'Assumed fee: {illustration.fee_percent_of_value:.2f}% of the entered holding value. Tax and execution-price effects are not calculated.')
            with st.expander('Why is this before tax?'):
                st.write('The amount you typed is not a verified tax basis. This tool has not checked acquisition lots, purchase dates, account treatment or applicable tax rules. The displayed difference is an arithmetic illustration, not a taxable-gain calculation.')
        with st.expander('Company evidence and next checks'):
            for detail in result.evidence_details:st.write(detail)
            for step in result.next_steps:st.write(step)
        st.caption('This explanation uses checked rules, not a language model. The review download retains the illustration for reading; use the personal-note download above for restore. Both are separate from decision snapshots/PDFs.')
        st.download_button('Download this holding review (private JSON)',result.model_dump_json(indent=2),file_name='private-holding-review.json',mime='application/json')
