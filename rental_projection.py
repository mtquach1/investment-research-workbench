"""Monthly, cent-rounded rental cash ledger. No forecasts or unlimited deficit funding."""

from decimal import Decimal, ROUND_HALF_UP, localcontext
from typing import Annotated, Literal
from pydantic import Field, model_validator
from schemas import StrictModel
from rental_feasibility import RentalFeasibilityRequest, Money

Growth = Annotated[Decimal, Field(ge=Decimal('-.5'),le=Decimal('.5'),decimal_places=6,allow_inf_nan=False)]
ZERO=Decimal(0)


def money(value):return value.quantize(Decimal('.01'),rounding=ROUND_HALF_UP)


class RentalProjectionRequest(StrictModel):
    property: RentalFeasibilityRequest
    down_payment: Money
    years: int = Field(default=10,ge=1,le=30,strict=True)
    annual_rent_growth: Growth = Decimal('.02')
    annual_expense_growth: Growth = Decimal('.03')
    annual_appreciation: Growth = ZERO
    selling_cost_rate: Annotated[Decimal, Field(ge=0,le=Decimal('.3'),decimal_places=6,allow_inf_nan=False)] = Decimal('.06')
    additional_capital_limit: Money = ZERO
    repair_shock_amount: Money = ZERO
    repair_shock_month: int = Field(default=12,ge=1,le=360,strict=True)

    @model_validator(mode='after')
    def coherent(self):
        if self.property.candidate_purchase_price is None:raise ValueError('A specific purchase price is required')
        if self.down_payment>self.property.candidate_purchase_price:raise ValueError('Down payment exceeds price')
        if self.repair_shock_amount and self.repair_shock_month>self.years*12:raise ValueError('Repair must be inside the holding period')
        return self


class RentalMonth(StrictModel):
    month: int
    property_value: Decimal
    loan_balance: Decimal
    collected_rent: Decimal
    operating_costs: Decimal
    debt_payment: Decimal
    interest: Decimal
    principal: Decimal
    capex_transfer: Decimal
    repair_spend: Decimal
    operating_cash_flow: Decimal
    distribution: Decimal
    reserve_draw: Decimal
    external_cash: Decimal
    operating_reserves: Decimal
    capex_reserves: Decimal
    cumulative_distributions: Decimal
    cumulative_external_cash: Decimal
    equity: Decimal


class RentalProjection(StrictModel):
    model_version: Literal['rental-hold-v1'] = 'rental-hold-v1'
    status: Literal['funded','initial_capital_shortfall','funding_shortfall','exit_funding_shortfall']
    initial_cash_required: Decimal
    initial_capital_shortfall: Decimal = ZERO
    scheduled_monthly_payment: Decimal
    completed_months: int
    first_unfunded_month: int | None = None
    unfunded_amount: Decimal = ZERO
    months: list[RentalMonth]
    gross_sale_value: Decimal | None = None
    selling_costs: Decimal | None = None
    exit_net_cash: Decimal | None = None
    exit_cash_before_funding: Decimal | None = None
    exit_external_cash: Decimal = ZERO
    total_cash_invested: Decimal
    total_distributions: Decimal
    net_profit: Decimal | None = None
    disclaimer: str = 'Hypothetical nominal pre-income-tax scenario, not a rent forecast, appraisal or lender quote. No depreciation, capital-gains tax, refinance, PMI or return on retained cash is modeled. A funding failure stops the ledger; no exit profit is reported.'


def project_rental(request: RentalProjectionRequest) -> RentalProjection:
    with localcontext() as context:
        context.prec=40
        return _project(request)


def _project(r):
    p=r.property;price=p.candidate_purchase_price
    closing=money(price*p.closing_cost_rate)+p.fixed_closing_costs
    initial=money(r.down_payment+closing+p.initial_repairs+p.initial_operating_reserves)
    balance=price-r.down_payment;rate=p.annual_interest_rate/12;term=p.loan_term_years*12
    payment=money(balance/term if rate==0 else balance*rate/(1-(1+rate)**(-term)))
    base=dict(initial_cash_required=initial,scheduled_monthly_payment=payment)
    if initial>p.available_capital:
        return RentalProjection(**base,status='initial_capital_shortfall',initial_capital_shortfall=initial-p.available_capital,
            completed_months=0,months=[],total_cash_invested=ZERO,total_distributions=ZERO)
    operating=p.initial_operating_reserves;capex=ZERO;distributed=ZERO;external=ZERO;rows=[]
    failure=None;gap=ZERO
    # Purchase tax is an entered first-year parcel assumption. It grows with the
    # expense assumption, not with hypothetical market appreciation.
    annual_cost=money(price*p.annual_property_tax_rate)+p.annual_special_assessments+p.annual_insurance+p.annual_maintenance+p.annual_hoa+p.annual_owner_paid_utilities
    for month in range(1,r.years*12+1):
        year=(month-1)//12
        expense_factor=(1+r.annual_expense_growth)**year
        rent=money(p.monthly_rent*(1+r.annual_rent_growth)**year*(1-p.vacancy_rate))
        costs=money(annual_cost*expense_factor/12)+money(rent*p.management_rate)
        transfer=money(p.annual_capex_reserve*expense_factor/12)
        interest=money(balance*rate) if balance else ZERO
        # Final contractual month clears rounding residual; debt stops at payoff.
        debt=money(balance+interest) if balance and month==term else min(payment,money(balance+interest))
        principal=debt-interest
        repair=r.repair_shock_amount if month==r.repair_shock_month else ZERO
        capex_after=capex+transfer
        capex_used=min(capex_after,repair)
        capex_after-=capex_used
        cashflow=rent-costs-debt-transfer-(repair-capex_used)
        draw=min(operating,max(ZERO,-cashflow))
        needed=max(ZERO,-cashflow-draw)
        if needed>r.additional_capital_limit-external:
            failure=month;gap=needed-(r.additional_capital_limit-external)
            break  # Failing month is not partly paid or silently borrowed.
        operating-=draw;external+=needed;capex=capex_after
        distribution=max(ZERO,cashflow);distributed+=distribution;balance=money(balance-principal)
        value=money(price*(1+r.annual_appreciation)**(Decimal(month)/12))
        rows.append(RentalMonth(month=month,property_value=value,loan_balance=balance,collected_rent=rent,
            operating_costs=costs,debt_payment=debt,interest=interest,principal=principal,capex_transfer=transfer,
            repair_spend=repair,operating_cash_flow=cashflow,distribution=distribution,reserve_draw=draw,
            external_cash=needed,operating_reserves=operating,capex_reserves=capex,
            cumulative_distributions=distributed,cumulative_external_cash=external,equity=value-balance))
    result=dict(**base,status='funding_shortfall' if failure else 'funded',completed_months=len(rows),
        first_unfunded_month=failure,unfunded_amount=gap,months=rows,total_cash_invested=initial+external,total_distributions=distributed)
    if failure:return RentalProjection(**result)
    value=rows[-1].property_value;sale_cost=money(value*r.selling_cost_rate)
    exit_cash=value-sale_cost-balance+operating+capex
    exit_needed=max(ZERO,-exit_cash)
    if exit_needed>r.additional_capital_limit-external:
        result['status']='exit_funding_shortfall'
        result['unfunded_amount']=exit_needed-(r.additional_capital_limit-external)
        return RentalProjection(**result,gross_sale_value=value,selling_costs=sale_cost,exit_cash_before_funding=exit_cash)
    # Sale proceeds are net of an explicitly budgeted contribution if underwater.
    external+=exit_needed
    result['total_cash_invested']=initial+external
    return RentalProjection(**result,gross_sale_value=value,selling_costs=sale_cost,exit_cash_before_funding=exit_cash,exit_net_cash=max(ZERO,exit_cash),
        exit_external_cash=exit_needed,net_profit=max(ZERO,exit_cash)+distributed-initial-external)
