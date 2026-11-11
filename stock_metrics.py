"""Inspectable research metrics and fail-closed filters; never selection scores."""
from datetime import date
from decimal import Decimal
from typing import Annotated,Literal
from pydantic import Field,model_validator
from data_pipeline import Contract
from stock_strategy import SPEC

CANONICAL_SECTORS=('Information Technology','Consumer Staples','Health Care','Consumer Discretionary',
    'Communication Services','Financials','Industrials','Energy','Materials','Utilities','Real Estate')


class Metric(Contract):
    value: Decimal | None = None
    status: Literal['available','missing_inputs','nonpositive_baseline','unaligned_periods','stale']
    basis: str


def screen_metrics(year,history,risk,*,today):
    metrics={}
    stale=year.period_end is None or not 0<=(today-date.fromisoformat(year.period_end)).days<=SPEC['maximum_financial_period_age_days']
    for name in ('return_on_assets','operating_margin','free_cashflow_margin','liabilities_to_assets'):
        value=year.metrics.get(name)
        metrics[name]=Metric(value=value,status='stale' if stale else 'available' if value is not None else 'missing_inputs',
            basis='Aligned reported annual SEC financials; ratios are not TTM or historical point-in-time screening data.')
    def growth(name):
        basis='Latest annual value / prior annual value − 1; positive prior value required. Current-snapshot revised history.'
        prior=[row for row in history if row.get('period_end') and year.period_end and row['period_end']<year.period_end]
        if not prior or name not in year.facts:return Metric(status='missing_inputs',basis=basis)
        previous=max(prior,key=lambda row:row['period_end'])
        if not 330<=(date.fromisoformat(year.period_end)-date.fromisoformat(previous['period_end'])).days<=400:
            return Metric(status='unaligned_periods',basis=basis)
        fact=previous.get('facts',{}).get(name)
        if fact is None:return Metric(status='missing_inputs',basis=basis)
        baseline=Decimal(str(fact['value']))
        if baseline<=0:return Metric(status='nonpositive_baseline',basis=basis)
        return Metric(value=year.facts[name].value/baseline-1,status='stale' if stale else 'available',basis=basis)
    metrics['revenue_growth']=growth('revenue');metrics['net_income_growth']=growth('net_income')
    fresh=risk is not None and 0<=(today-risk.last).days<=SPEC['maximum_price_age_calendar_days']
    for name,field in [('annualized_volatility','annualized_volatility'),('maximum_drawdown','maximum_drawdown')]:
        value=getattr(risk,field) if risk is not None else None
        metrics[name]=Metric(value=Decimal(str(value)) if value is not None else None,
            status='missing_inputs' if value is None or not risk.minimum_history_gate_passed else 'stale' if not fresh else 'available',
            basis='Full installed IEX all-adjusted daily history, not exact consolidated reinvested total return. Active risk filters require 756 complete return observations. Drawdown peaks start inside this window.'+
                  (f' Window: {risk.first} through {risk.last}; {risk.return_observations} returns; {len(risk.missing_sessions)} missing sessions.' if risk else ' No installed history.'))
    return metrics


Threshold=Annotated[Decimal,Field(ge=-10,le=10,allow_inf_nan=False)]
class ScreenFilters(Contract):
    sectors: list[str] = Field(default_factory=list,max_length=11)
    financial_pass_only: bool = False
    minimum_roa: Threshold | None = None
    minimum_operating_margin: Threshold | None = None
    minimum_fcf_margin: Threshold | None = None
    maximum_liabilities_to_assets: Threshold | None = None
    minimum_revenue_growth: Threshold | None = None
    maximum_volatility: Annotated[Decimal,Field(ge=0,le=10,allow_inf_nan=False)] | None = None
    maximum_drawdown_loss: Annotated[Decimal,Field(ge=0,le=1,allow_inf_nan=False)] | None = None
    minimum_estimated_earnings_yield: Threshold | None = None
    allow_valuation_estimates: bool = False

    @model_validator(mode='after')
    def coherent(self):
        if len(set(self.sectors))!=len(self.sectors) or any(item not in CANONICAL_SECTORS for item in self.sectors):
            raise ValueError('Use unique canonical sector labels')
        if self.minimum_estimated_earnings_yield is not None and not self.allow_valuation_estimates:
            raise ValueError('Explicit consent to research valuation estimates is required')
        return self


class ScreenExclusion(Contract):
    issuer_key: str
    reasons: list[str]


class FilteredScreen(Contract):
    filter_version: Literal['stock-research-filters-v1'] = 'stock-research-filters-v1'
    status: str
    filters: ScreenFilters
    public_release_id: str | None
    market_snapshot_sha256: str | None
    included_issuer_keys: list[str]
    exclusions: list[ScreenExclusion]
    live_recommendations_enabled: Literal[False] = False


def filter_screen(screen,filters):
    included=[];excluded=[]
    gates=[('minimum_roa','return_on_assets',True),('minimum_operating_margin','operating_margin',True),
        ('minimum_fcf_margin','free_cashflow_margin',True),('maximum_liabilities_to_assets','liabilities_to_assets',False),
        ('minimum_revenue_growth','revenue_growth',True),('maximum_volatility','annualized_volatility',False),
        ('maximum_drawdown_loss','maximum_drawdown',False)]
    for row in screen.rows:
        reasons=[]
        financial_thresholds=(filters.minimum_roa,filters.minimum_operating_margin,filters.minimum_fcf_margin,filters.maximum_liabilities_to_assets)
        if any(value is not None for value in financial_thresholds) and row.sector_status!='pass':
            reasons.append('Profitability/leverage thresholds require a fresh sector supported by the initial nonfinancial-company strategy.')
        if filters.sectors and (row.sector not in filters.sectors or row.sector_status=='unavailable'):
            reasons.append('Sector is outside the selection or lacks a fresh supported reference.')
        if filters.financial_pass_only and row.financial_status!='pass':reasons.append('Supported financial checks do not all pass.')
        for setting,key,minimum in gates:
            threshold=getattr(filters,setting)
            if threshold is None:continue
            metric=row.metrics.get(key)
            if metric is None or metric.status!='available' or metric.value is None:
                reasons.append(f'{key}: unavailable or stale; active threshold cannot pass.');continue
            value=-metric.value if key=='maximum_drawdown' else metric.value
            if (minimum and value<threshold) or (not minimum and value>threshold):
                reasons.append(f'{key}: {value} does not meet {setting}={threshold}.')
        if filters.minimum_estimated_earnings_yield is not None:
            valuation=row.valuation
            if valuation.status!='estimated' or valuation.annual_earnings_yield_estimate is None:
                reasons.append('Estimated earnings yield is unavailable or stale.')
            elif valuation.annual_earnings_yield_estimate<filters.minimum_estimated_earnings_yield:
                reasons.append('Estimated earnings yield is below the entered research threshold.')
        if reasons:excluded.append(ScreenExclusion(issuer_key=row.issuer_key,reasons=reasons))
        else:included.append(row.issuer_key)
    return FilteredScreen(status=screen.status,filters=filters,public_release_id=screen.public_release_id,
        market_snapshot_sha256=screen.market_snapshot_sha256,included_issuer_keys=included,exclusions=excluded)
