"""In-memory private PDF, always recomputed from server-owned stock evidence."""
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate,PageBreak,Spacer
from goal_report import _styles,_p,_table,INK,MUTED,RULE,MARGIN,WIDTH,PAGE_HEIGHT
from decision_snapshots import review_decision

REPORT_VERSION='stock-decision-report-v1'
LABELS={'buy_candidate':'Candidate (experimental)','hold':'Hold (limited rules)',
    'review_for_trim_or_sell':'Investigate trim/sell','pass':'Pass','insufficient_evidence':'Needs evidence'}


def _usd(cents):
    return f'${cents/100:,.2f}'


def _clip(value,limit=420):
    value=str(value)
    return value if len(value)<=limit else value[:limit]+'... [full text in JSON]'


def build_stock_decision_report(record,screen,*,acknowledge_experimental=False,context_override=None):
    review=review_decision(record,screen,acknowledge_experimental=acknowledge_experimental,context_override=context_override)
    if review.status!='reviewed':raise ValueError('Current acknowledged experimental assessment required')
    current=review.current;old=record.assessment;context=current.context
    styles=_styles();story=[]
    def text(value,kind='body'):story.append(_p(value,styles,kind))
    def table(rows,widths):story.append(_table(rows,widths,styles))
    text('Stock decision review','title')
    text('PRIVATE / LOCAL EXPERIMENTAL RESEARCH','heading')
    text(record.name)
    text(f'Recorded assessment: {old.checked_on} | Saved record: {record.saved_on} | Current evidence check: {current.checked_on}','small')
    table([['How to read this report'],['Current results were recomputed from installed server evidence. Saved results and dates are unverified records. This is not a verified recommendation, complete suitability review or instruction to trade.']],[WIDTH])
    text('Research settings and funding','heading')
    table([['Input','Current setting'],['New cash (USD)',_usd(context.new_cash_cents)],
        ['Paper additions (USD)',_usd(sum(card.paper_addition_cents for card in current.cards))],
        ['Cash left unassigned (USD)',_usd(current.cash_unassigned_cents)],
        ['Horizon',f'{context.horizon_years} '+('year' if context.horizon_years==1 else 'years')],['Maximum direct position',f'{context.maximum_direct_weight:.2%}'],
        ['Historical volatility ceiling',f'{context.maximum_volatility:.2%}' if context.maximum_volatility is not None else 'Not applied'],
        ['Monthly contribution intention (not allocated)',_usd(context.monthly_contribution_cents)],
        ['Exact-symbol exclusions',_clip(', '.join(context.excluded_symbols) or 'None')]], [WIDTH*.58,WIDTH*.42])
    if context.holdings:
        text('Entered holdings - unresolved fund look-through','heading')
        table([['Symbol','Entered value (USD)']]+[[item.symbol,_usd(item.value_cents)] for item in context.holdings],[WIDTH*.6,WIDTH*.4])
    text('Assessment counts - not confidence or probabilities','heading')
    table([['Assessment','Recorded (unverified)','Current']]+[[label,str(old.outcome_counts.get(code,0)),str(current.outcome_counts.get(code,0))]
        for code,label in LABELS.items()],[WIDTH*.5,WIDTH*.25,WIDTH*.25])
    text('Source membership is a dated fund-holdings proxy. Valuations use filing-based annual estimates, not verified current company values or TTM. Price history is not a forecast or proof of outperformance. Paper sizing retains the fixed baseline; blocked amounts stay cash. Taxes, trading costs, acquisition lots, news and underlying fund exposure need further review.','small')
    story.append(PageBreak())
    text('Current company assessments','title')
    text(f'All {len(current.cards)} current company/holding cards are included below. The primary reason is summarized; complete checks and supporting/contrary evidence remain in the companion JSON snapshot and application.','small')
    table([['Company / exact symbols','Assessment','Paper USD','Primary reason']]+[
        [_clip(card.company,160)+' / '+_clip(', '.join(card.symbols),160),LABELS[card.outcome],_usd(card.paper_addition_cents),
         _clip(card.reasons[0].detail) if card.reasons else 'No primary reason provided'] for card in current.cards],
        [WIDTH*.25,WIDTH*.19,WIDTH*.13,WIDTH*.43])
    text('Evidence dates for candidates and entered holdings','heading')
    rows={row.issuer_key:row for row in screen.rows}
    dated=[]
    for card in current.cards:
        if not card.paper_addition_cents and not card.held_value_cents:continue
        row=rows.get(card.issuer_key)
        dated.append([', '.join(card.symbols),str(row.financial_period or 'Unavailable') if row else 'Unavailable',
            str(row.valuation.measured_on or 'Unavailable') if row else 'Unavailable',
            str(row.valuation.price_date or 'Unavailable') if row else 'Unavailable'])
    if dated:table([['Symbols','Annual period end','Shares measured','Price observed']]+dated,[WIDTH*.25]*4)
    else:text('No current paper additions or entered holdings require this date table.','small')
    story.append(PageBreak())
    text('What changed since the record?','title')
    text('Settings: '+('current override applied' if review.context_changed else 'saved settings reused exactly'))
    text('Changed references: '+(', '.join(review.changed_inputs) or 'None detected'))
    if review.changes:
        table([['Company','Recorded / current','Findings changed']]+[[_clip(item.company,160),
            LABELS.get(item.previous_outcome,'Not covered')+' / '+LABELS.get(item.current_outcome,'Not covered'),
            '; '.join(item.triggers)+f'. Paper USD: {_usd(item.previous_addition_cents)} -> {_usd(item.current_addition_cents)}']
            for item in review.changes],[WIDTH*.26,WIDTH*.28,WIDTH*.46])
    else:text('No assessment, sizing, score, symbol or evidence-finding changes detected. A changed input reference may still appear above.')
    text('Recorded outcomes are an unverified comparison baseline. A changed rank is not a sell signal. No causal claim about price moves is made.','small')
    text('Reproducibility and privacy','heading')
    table([['Reference','Current identifier'],['Report format',REPORT_VERSION],['Decision model',current.model_version],
        ['Decision policy SHA-256',current.policy_sha256],['Strategy SHA-256',current.strategy_sha256],
        ['Public/reference release SHA-256',current.public_release_id],['Price snapshot SHA-256',current.market_snapshot_sha256],
        ['Universe reference SHA-256',current.universe_sha256],['Saved record checksum (not a signature)',record.fingerprint]]+
        [['Listing reference: '+key,value] for key,value in sorted(current.listing_reference_hashes.items())], [WIDTH*.38,WIDTH*.62])
    text('This PDF contains personal settings/holdings and is not encrypted. Generation uses memory only; saving a download creates your own local copy. Do not publish it as a cleared-data demo asset. Keep the JSON snapshot for validated restore; this PDF cannot be imported. No return guarantee or proven S&P 500 outperformance is claimed.','small')
    def decorate(canvas,doc):
        canvas.saveState();canvas.setStrokeColor(RULE)
        canvas.line(MARGIN,32,MARGIN+WIDTH,32)
        canvas.setFont('GoalRegular',7);canvas.setFillColor(MUTED)
        canvas.drawString(MARGIN,21,'PRIVATE - experimental stock research | '+REPORT_VERSION)
        canvas.drawRightString(MARGIN+WIDTH,21,f'Page {doc.page}')
        canvas.restoreState()
    buffer=BytesIO()
    document=SimpleDocTemplate(buffer,pagesize=letter,leftMargin=MARGIN,rightMargin=MARGIN,
        topMargin=42,bottomMargin=44,title='Private stock decision review',author='Investment Research Workspace',
        subject='Experimental research report',pageCompression=1)
    document.build(story,onFirstPage=decorate,onLaterPages=decorate)
    return buffer.getvalue()
