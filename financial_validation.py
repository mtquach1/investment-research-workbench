"""Independent arithmetic reconciliation of installed research, not a source audit."""
from datetime import date
from decimal import Decimal,localcontext
from fractions import Fraction
from itertools import accumulate
import json
from pathlib import Path
from hashlib import sha256
from typing import Literal
from pydantic import Field
from data_pipeline import Contract,load_release,read_table
from stock_screen import stock_screen
from market_history import load_history


class ReconciliationCheck(Contract):
    issuer_key: str
    metric: str
    status: Literal['pass','mismatch','unavailable']
    expected: Decimal | None = None
    actual: Decimal | None = None
    formula: str
    inputs: dict[str,str] = Field(default_factory=dict)


class FinancialValidation(Contract):
    version: Literal['independent-arithmetic-v1']='independent-arithmetic-v1'
    status: str
    public_release_id: str | None = None
    market_snapshot_sha256: str | None = None
    checked_on: date | None = None
    reference_cases_sha256: str | None = None
    checks: list[ReconciliationCheck] = Field(default_factory=list)
    company_names: dict[str,str] = Field(default_factory=dict)
    source_accuracy_verified: Literal[False]=False
    historical_strategy_evaluation_available: Literal[False]=False
    limitations: list[str] = Field(default_factory=lambda:[
        'Independent arithmetic over the same installed normalized facts; this does not independently verify SEC tag selection or economic accuracy.',
        'Historical membership, delisted securities and contemporaneous filing/valuation vintages are not installed. A historical strategy backtest is withheld.',
        'Valuations remain estimates; IEX all-adjusted history is a provider proxy, not verified consolidated reinvested total return.'])


def reconcile_company(row,raw,series=None):
    """Use rational ratios and a Decimal two-pass variance, not production helpers."""
    facts=raw.get('facts',{});checks=[]
    def value(name):
        fact=facts.get(name)
        return Fraction(str(fact['value'])) if fact else None
    def add(name,numerator,denominator,formula,inputs,actual=None):
        expected=None
        if numerator is not None and denominator is not None and denominator>0:
            exact=numerator/denominator
            expected=Decimal(exact.numerator)/Decimal(exact.denominator)
        if actual is None:
            metric=row.metrics.get(name)
            actual=metric.value if metric and metric.status=='available' else None
        status='unavailable' if expected is None or actual is None else 'pass' if abs(expected-actual)<=Decimal('1e-10')*max(1,abs(expected)) else 'mismatch'
        checks.append(ReconciliationCheck(issuer_key=row.issuer_key,metric=name,status=status,expected=expected,actual=actual,formula=formula,inputs=inputs))
    def evidence(*names):return {name:str(value(name)) for name in names if value(name) is not None}
    start,end=value('assets_start'),value('assets_end')
    average=(start+end)/2 if start is not None and end is not None and start>0 and end>0 else None
    add('return_on_assets',value('net_income'),average,'Net income / mean(beginning assets, ending assets)',evidence('net_income','assets_start','assets_end'))
    add('operating_margin',value('operating_income'),value('revenue'),'Operating income / revenue',evidence('operating_income','revenue'))
    ocf,capex=value('operating_cashflow'),value('capital_expenditures')
    fcf=ocf-capex if ocf is not None and capex is not None and capex>=0 else None
    add('free_cashflow_margin',fcf,value('revenue'),'(Operating cash flow − cash capex) / revenue',evidence('operating_cashflow','capital_expenditures','revenue'))
    debt=value('liabilities_end')
    add('liabilities_to_assets',debt if debt is not None and debt>=0 else None,end,'Liabilities / ending assets',evidence('liabilities_end','assets_end'))
    if facts.get('liabilities_end',{}).get('tag')=='derived:current_plus_noncurrent_liabilities':
        current,noncurrent=value('current_liabilities_end'),value('noncurrent_liabilities_end')
        total=current+noncurrent if current is not None and noncurrent is not None and min(current,noncurrent)>=0 else None
        add('liabilities_component_sum',total,Fraction(1),'Reported current liabilities + reported noncurrent liabilities',
            evidence('current_liabilities_end','noncurrent_liabilities_end'),actual=Decimal(str(facts['liabilities_end']['value'])))
    v=row.valuation;ref=raw.get('share_reference',{}).get('evidence')
    cap=None;inputs={}
    if v.status=='estimated' and series is not None and ref:
        anchor=next((bar for bar in reversed(series.bars) if bar.day<=date.fromisoformat(ref['measured_on'])),None)
        latest=series.bars[-1]
        if anchor and anchor.split_adjusted_close and latest.split_adjusted_close:
            # Combine rational terms directly instead of calling estimate_valuation.
            shares=Fraction(ref['shares'])*Fraction(anchor.raw_close)*Fraction(latest.split_adjusted_close)/(Fraction(anchor.split_adjusted_close)*Fraction(latest.raw_close))
            cap=shares*Fraction(latest.raw_close)
            inputs={'reported_shares':ref['shares'],'share_date':ref['measured_on'],'price_date':str(latest.day),'raw_price':str(latest.raw_close),'anchor_raw':str(anchor.raw_close),'anchor_split_close':str(anchor.split_adjusted_close),'latest_split_close':str(latest.split_adjusted_close)}
    add('market_cap_estimate',cap,Fraction(1),'Reported shares × split factor × raw close',inputs,actual=v.market_cap_estimate if v.status=='estimated' else None)
    add('earnings_yield_estimate',value('net_income'),cap,'Annual net income / independently recomputed estimated capitalization',inputs,actual=v.annual_earnings_yield_estimate if v.status=='estimated' else None)
    add('fcf_yield_estimate',fcf,cap,'(Operating cash flow − cash capex) / independently recomputed estimated capitalization',inputs,actual=v.annual_fcf_yield_estimate if v.status=='estimated' else None)
    if series is not None and len(series.bars)>2:
        values=[bar.adjusted_close for bar in series.bars]
        with localcontext() as context:
            context.prec=40
            changes=[b/a-1 for a,b in zip(values,values[1:])]
            mean=sum(changes)/len(changes)
            volatility=(sum((item-mean)**2 for item in changes)/(len(changes)-1)*252).sqrt()
            drawdown=min(value/peak-1 for value,peak in zip(values,accumulate(values,max)))
        for name,expected,formula in [('annualized_volatility',volatility,'Sample standard deviation(daily simple returns) × sqrt(252)'),('maximum_drawdown',drawdown,'Minimum(value / preceding running peak − 1)')]:
            add(name,Fraction(expected),Fraction(1),formula,{'observations':str(len(values)),'basis':'provider all-adjusted closes'})
    return checks


def validate_installed_financials(public_root,history_root,*,mode='withheld',today=None):
    screen=stock_screen(public_root,history_root,mode=mode,today=today)
    report=FinancialValidation(status=screen.status,checked_on=screen.checked_on,public_release_id=screen.public_release_id,market_snapshot_sha256=screen.market_snapshot_sha256)
    if screen.status!='available':return report
    report.company_names={row.issuer_key:row.company for row in screen.rows}
    try:
        release,manifest=load_release(public_root)
        market,bundle=load_history(history_root)
        if release!=screen.public_release_id or market!=screen.market_snapshot_sha256:
            report.status='snapshot_changed';return report
        installed={}
        for row in screen.rows:
            raw=read_table(public_root,manifest.tables['sec_companyfacts_'+row.issuer_key])['records'][0]
            installed[row.issuer_key]=raw
            candidates=[series for series in bundle.series.values() if series.cik==row.cik]
            report.checks.extend(reconcile_company(row,raw,candidates[0] if len(candidates)==1 else None))
        reference_bytes=(Path(__file__).parent/'data/financial_reference_cases.json').read_bytes()
        report.reference_cases_sha256=sha256(reference_bytes).hexdigest()
        references=json.loads(reference_bytes)
        report.checks.extend(reconcile_reference_cases(installed,references))
        report.status='mismatch' if any(check.status=='mismatch' for check in report.checks) else 'reconciled_available_inputs'
    except (OSError,ValueError,KeyError,ArithmeticError):
        report.status='unavailable';report.checks=[]
    return report


def reconcile_reference_cases(installed,references):
    checks=[]
    for case in references['cases']:
        raw=installed.get(case['issuer_key'],{})
        periods=[raw]+raw.get('annual_history',[])
        year=next((row for row in periods if row.get('period_end')==case['period_end'] and row.get('cik')==case['cik']),{})
        for name,millions in case['values_millions'].items():
            fact=year.get('facts',{}).get(name)
            actual=Decimal(str(fact['value'])) if fact else None
            expected=Decimal(millions)*1000000
            checks.append(ReconciliationCheck(issuer_key=case['issuer_key'],metric='official_reference:'+name,
                status='unavailable' if actual is None else 'pass' if actual==expected else 'mismatch',expected=expected,actual=actual,
                formula='Published statement USD millions × 1,000,000; exact fiscal period and issuer match',
                inputs={'source_url':case['source_url'],'period_end':case['period_end'],'reviewed_on':references['reviewed_on'],'location':case['location']}))
    return checks
