"""Session-only holding-period exploration, with explicit funding failures."""
from decimal import Decimal
import altair as alt
import pandas as pd
import streamlit as st
from rental_projection import RentalProjectionRequest,project_rental


def _control(widget,label,low,high,default,step=None,*,key,**kwargs):
    saved=st.session_state.setdefault('_rental_hold_inputs',{})
    if key not in st.session_state:st.session_state[key]=saved.get(key,default)
    st.session_state[key]=max(low,min(high,st.session_state[key]))
    args=dict(min_value=low,max_value=high,key=key,**kwargs)
    if step is not None:args['step']=step
    value=widget(label,**args)
    saved[key]=value
    return value


def render_rental_hold(property_inputs,down):
    st.subheader('Can this property sustain a longer hold?')
    st.caption('Hypothetical future assumptions, not Orange County price or rent forecasts. Edit the purchase and first-year expenses in the Purchase & cash flow tab.')
    controls,display=st.columns([1,2],gap='large')
    with controls:
        years=_control(st.slider,'Hold for (years)',1,30,10,key='rh_years')
        rent_growth=_control(st.slider,'Yearly rent growth (%)',-10.0,10.0,2.0,.5,key='rh_rent_growth',help='Applied at the beginning of each new operating year. No growth is applied to the first year.')
        expense_growth=_control(st.slider,'Yearly expense growth (%)',-10.0,15.0,3.0,.5,key='rh_expense_growth',help='Operating expenses and replacement-reserve contributions grow together. Property tax follows this expense assumption, not market appreciation.')
        appreciation=_control(st.slider,'Yearly property value change (%)',-15.0,15.0,0.0,.5,key='rh_appreciation',help='Changes hypothetical sale value and equity. It does not create spendable monthly income.')
        with st.expander('Sale, repairs and extra funding'):
            selling=_control(st.number_input,'Selling costs (%)',0.0,30.0,6.0,.5,key='rh_selling')
            additional=_control(st.number_input,'Maximum extra cash you would add ($)',0,10000000,0,1000,key='rh_extra',help='A separate funding commitment beyond cash required at purchase. Unused purchase capital is not automatically pledged. Positive monthly cash flow is distributed, not reinvested.')
            repair=_control(st.number_input,'One-time repair bill ($)',0,1000000,0,1000,key='rh_repair')
            shock_month=_control(st.number_input,'Repair month',1,years*12,min(12,years*12),1,key='rh_repair_month')
        st.caption('The mortgage rate stays fixed. Payments stop when the loan is paid off. Positive cash flow is paid out; reserves earn no return.')
    percent=lambda x:Decimal(str(x))/100
    base=RentalProjectionRequest(property=property_inputs,down_payment=down,years=years,
        annual_rent_growth=percent(rent_growth),annual_expense_growth=percent(expense_growth),
        annual_appreciation=percent(appreciation),selling_cost_rate=percent(selling),
        additional_capital_limit=additional,repair_shock_amount=repair,repair_shock_month=shock_month)
    stress_inputs=base.model_copy(update={
        'property':property_inputs.model_copy(update={'vacancy_rate':min(Decimal(1),property_inputs.vacancy_rate+Decimal('.10'))}),
        'annual_rent_growth':base.annual_rent_growth-Decimal('.02'),
        'annual_expense_growth':base.annual_expense_growth+Decimal('.02'),
        'annual_appreciation':base.annual_appreciation-Decimal('.02'),
        'repair_shock_amount':base.repair_shock_amount+Decimal(15000)})
    # Revalidate derived stress assumptions; never bypass the request contract.
    stress_inputs=RentalProjectionRequest.model_validate(stress_inputs.model_dump())
    results={'Base':project_rental(base),'Adverse stress':project_rental(stress_inputs)}
    st.session_state['_rental_hold_result']={key:value.model_dump(mode='json') for key,value in results.items()}
    with display:
        scenario=st.segmented_control('Inspect scenario',['Base','Adverse stress'],default='Base',key='rh_scenario') or 'Base'
        result=results[scenario]
        if scenario=='Adverse stress':
            st.info('Illustrative joint stress: vacancy +10 percentage points (capped at 100%); rent growth −2 points; expense growth +2 points; property value growth −2 points; an extra $15,000 repair in your selected repair month. No probability is assigned.')
        a,b,c=st.columns(3)
        a.metric('Purchase cash',f'${result.initial_cash_required:,.0f}',help='Down payment, closing costs, initial repairs and held operating reserves. Reserves are still your cash, not an acquisition expense.')
        b.metric('Funded months',f'{result.completed_months} / {years*12}')
        c.metric('Net profit at sale',f'${result.net_profit:,.0f}' if result.net_profit is not None else '—',help='Sale cash after debt and selling costs, plus cash distributed and released reserves, minus initial and additional cash invested. Pre-income-tax; no time-value adjustment.')
        if result.status=='initial_capital_shortfall':
            st.error(f'Purchase cannot be funded: ${result.initial_capital_shortfall:,.2f} more is needed before closing. No timeline or exit return is invented.')
        elif result.status=='funding_shortfall':
            st.warning(f'Funding stops before month {result.first_unfunded_month}. That month needs ${result.unfunded_amount:,.2f} beyond the operating reserves and extra-cash limit. Later months and sale profit are not reported.')
        elif result.status=='exit_funding_shortfall':
            st.warning(f'The operating period is funded, but selling requires ${result.unfunded_amount:,.2f} beyond your remaining extra-cash limit. No realizable sale profit is reported.')
        else:st.success('The entered reserves and extra-cash limit cover every modeled month. This does not guarantee the property will perform this way.')
        if result.exit_external_cash:
            st.caption(f'The modeled sale uses an additional ${result.exit_external_cash:,.2f} of your extra-cash commitment to pay off debt and selling costs. That cash is included in total invested capital.')
        metric=st.radio('Timeline shows',['Property equity','Mortgage balance','Cash reserves'],horizontal=True,key='rh_metric')
        field={'Property equity':'equity','Mortgage balance':'loan_balance','Cash reserves':'cash_reserves'}[metric]
        chart_rows=[]
        for label,projection in results.items():
            for row in projection.months:
                value=row.operating_reserves+row.capex_reserves if field=='cash_reserves' else getattr(row,field)
                chart_rows.append({'Month':row.month,'Dollars':float(value),'Scenario':label})
        if chart_rows:
            chart=alt.Chart(pd.DataFrame(chart_rows)).mark_line(strokeWidth=3,interpolate='linear').encode(
                x=alt.X('Month:Q',title='Months after purchase',axis=alt.Axis(grid=False,domain=False)),y=alt.Y('Dollars:Q',title=metric+' ($)',scale=alt.Scale(zero=False),axis=alt.Axis(gridOpacity=.10,domain=False,format='~s')),
                color=alt.Color('Scenario:N',scale=alt.Scale(domain=['Base','Adverse stress'],range=['#289dff','#f398a4'])),
                strokeDash=alt.StrokeDash('Scenario:N',scale=alt.Scale(domain=['Base','Adverse stress'],range=[[],[5,4]]),legend=None),
                tooltip=['Scenario',alt.Tooltip('Month:Q',format='d'),alt.Tooltip('Dollars:Q',format='$,.2f')]).properties(height=300).configure_view(stroke=None)
            st.altair_chart(chart,width='stretch',alt='Base and adverse rental timelines. Lines stop at the last funded month; no future values are filled.')
        st.caption('Equity = modeled property value minus mortgage balance. It is not cash you can withdraw without a sale or new financing. Lines stop when funding fails.')
        if result.months:
            month=_control(st.slider,'Inspect funded month',1,result.completed_months,result.completed_months,key='rh_inspect_'+scenario,help='These values describe completed months. A failed month is excluded because its bills could not all be paid.') if result.completed_months>1 else 1
            row=result.months[month-1]
            a,b,c=st.columns(3)
            a.metric('Cash paid out',f'${row.cumulative_distributions:,.0f}')
            b.metric('Extra cash added',f'${row.cumulative_external_cash:,.0f}')
            c.metric('Reserves held',f'${row.operating_reserves+row.capex_reserves:,.0f}')
        with st.expander('Cash ledger and definitions'):
            st.write('Operating reserves cover shortfalls first; only then is extra cash drawn, up to your limit. Replacement contributions accumulate in a separate account; the repair bill uses that account first. Remaining reserves are released at sale, so they are not deducted twice. Distributions are kept outside the property at zero return and are not available to rescue later deficits.')
            st.write('At sale: property value − selling costs − mortgage payoff + remaining operating and replacement reserves = net sale cash. Principal repayment builds equity; it is never added again as profit.')
            st.dataframe(pd.DataFrame([row.model_dump() for row in result.months]),hide_index=True,width='stretch')
            st.json({'scenario':scenario,'inputs':(base if scenario=='Base' else stress_inputs).model_dump(mode='json'),
                'model_version':result.model_version,'exit_net_cash':str(result.exit_net_cash) if result.exit_net_cash is not None else None})
        st.caption(result.disclaimer)
