"""Shared presentation vocabulary. Never changes scores, gates or financial values."""

TERMS = {
    'return_on_assets': ('Profit relative to business assets (ROA)',
        'Annual profit divided by the average assets the business owned during that year.',
        '$10 of profit from $100 of average assets means 10% ROA.',
        'This measures the business, not the return you earned on its stock.'),
    'operating_margin': ('Operating profit margin',
        'The share of sales left as operating profit, before interest and income taxes.',
        '$20 of operating profit from $100 of sales means a 20% margin.',
        'Compare similar businesses; a high margin alone does not make a stock cheap.'),
    'free_cashflow_margin': ('Cash left after equipment spending (FCF margin)',
        'Operating cash flow minus cash spending on property, plant and equipment, divided by sales.',
        '$20 of operating cash minus $5 of equipment spending on $100 of sales means a 15% FCF margin.',
        'This cash is not automatically paid to shareholders as a dividend.'),
    'earnings_yield': ('Profit relative to the estimated share value',
        'Reported annual profit divided by the estimated total value of the company’s common shares.',
        '$5 of annual profit for every $100 of estimated share value means a 5% earnings yield.',
        'This is not a promised investment return or a dividend payment.'),
    'free_cashflow_yield': ('Cash relative to the estimated share value',
        'Operating cash minus cash spending on property, plant and equipment, divided by the estimated total common-share value.',
        '$4 of annual free cash flow for every $100 of estimated share value means a 4% FCF yield.',
        'The company may reinvest this cash. You are not promised a 4% payment.'),
    'liabilities_to_assets': ('What the business owes relative to its assets',
        'Total reported liabilities divided by assets. Liabilities include more than bank loans.',
        '$70 of liabilities and $100 of assets means a 70% ratio.',
        'This is an accounting measure, not a probability of bankruptcy.'),
    'revenue_growth': ('Annual sales growth',
        'The change in sales between two comparable reported financial years.',
        'Sales rising from $100 to $110 means 10% growth.',
        'Growing sales do not necessarily mean growing profit or a rising stock price.'),
    'annualized_volatility': ('How much prices fluctuated',
        'Historical daily price-return fluctuations expressed on an annual scale.',
        '30% volatility describes the scale of past variation; it does not mean a 30% gain or a 30% maximum loss.',
        'It is not a forecast. A price can fall more than this number.'),
    'maximum_drawdown': ('Largest historical peak-to-trough drop',
        'The biggest fall from an earlier high within the installed history window.',
        'An investment falling from $100 to $75 has a 25% drawdown.',
        'This is not the most you could lose in the future.'),
    'sector': ('Business sector',
        'A group of businesses with similar activities, such as technology or health care.',
        'Comparing two software businesses can be more useful than comparing one with a utility.',
        'A sector label does not establish that a stock belongs to the S&P 500.'),
    'share_class': ('Share classes and stock splits',
        'A company can issue different securities with different rights. A stock split changes the number and price of shares.',
        'In a 10-for-1 split, one $1,000 share becomes ten $100 shares: the total is still $1,000.',
        'Different tickers may represent common shares, preferred shares, rights or debt; we do not assume they are interchangeable.'),
    'annual_basis': ('Annual figures versus the latest 12 months',
        'This strategy uses one reported financial year. That is different from combining the latest four quarters (TTM).',
        'A year ending December 2025 does not include results from the first nine months of 2026.',
        'Always check the report period. A new download does not update an old reporting period.'),
}

FINANCIAL_STATES={'pass':'Meets financial rules','fail':'Does not meet financial rules','unavailable':'Needs more data'}
PRICE_STATES={'pass':'Recent enough','fail':'Out of date','unavailable':'Needs price data'}
HISTORY_STATES={'pass':'Meets history rule','fail':'Too short or incomplete','unavailable':'Needs price history'}
VALUATION_STATES={
    'estimated':('Estimate available','Based on reported shares and a dated price. Share counts and class coverage are not fully verified.'),
    'stale':('Data is too old','The price or reported share count is older than this research policy allows.'),
    'multiple_securities':('Share coverage needs checking','Several securities are associated with this company. We have not established how their prices and share counts fit together.'),
    'ambiguous':('Reports conflict','The available evidence does not identify one usable reported share count.'),
    'unavailable':('Needs more data','We do not have enough usable evidence for this estimate. This is not a negative judgment about the business.'),
    'split_evidence_missing':('Split data needs checking','We cannot safely put the reported share count and price on the same stock-split basis.'),
}


def render_term_guide(key):
    import streamlit as st
    with st.popover('Explain a term'):
        chosen=st.selectbox('What would you like explained?',list(TERMS),format_func=lambda item:TERMS[item][0],key=key)
        title,meaning,example,limit=TERMS[chosen]
        st.markdown('**'+title+'**')
        st.write(meaning)
        st.info('Example: '+example.replace('$',r'\$'))
        st.caption(limit)
