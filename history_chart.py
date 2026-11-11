"""Truthful chart styling: linear observed paths, paired hover and range presets."""

import calendar
from datetime import date,timedelta
import altair as alt
import pandas as pd


def range_start(label,end):
    if label=="All":return None
    if label=="1W":return end-timedelta(days=7)
    if label=="YTD":return date(end.year,1,1)
    months={"1M":1,"3M":3,"1Y":12}[label]
    ordinal=end.year*12+end.month-1-months
    year,month=divmod(ordinal,12);month+=1
    return date(year,month,min(end.day,calendar.monthrange(year,month)[1]))


def comparison_chart(points,*,drawdown=False,company_label="Company",markers=None,share_price=False,raw_price=False):
    rows=[{"Date":p.day.isoformat(),"Exact date":p.day.isoformat(),"Primary":
        float(p.company_raw_close if raw_price else p.company_split_adjusted_close) if share_price else (100*p.company_drawdown if drawdown else p.company_index),"Benchmark":
        100*p.benchmark_drawdown if drawdown else p.benchmark_index} for p in points]
    wide=pd.DataFrame(rows);labels=[company_label] if share_price else [company_label,"SPY ETF proxy"]
    colors=["#289dff","#9aa9bd"]
    x=alt.X("Date:T",scale=alt.Scale(type="utc"),title=None,
        axis=alt.Axis(format="%b %Y",tickCount=6,grid=False,labelPadding=12,domain=False))
    title=("Share price ($ · original daily close)" if raw_price else "Share price ($ · split-adjusted)") if share_price else ("Decline from earlier peak (%)" if drawdown else "Value of a starting $100 ($)")
    y=alt.Y("Value:Q",title=title,scale=alt.Scale(zero=drawdown),
        axis=alt.Axis(gridOpacity=.10,domain=False,tickCount=5,labelPadding=8))
    folded=alt.Chart(wide).transform_fold(["Primary"] if share_price else ["Primary","Benchmark"],as_=["Series","Value"]).transform_calculate(
        Series=alt.expr.if_(alt.datum.Series=="Primary",company_label,"SPY ETF proxy"))
    encoding=dict(x=x,y=y,color=alt.Color("Series:N",scale=alt.Scale(domain=labels,range=colors),
        legend=alt.Legend(title=None,orient="bottom",symbolStrokeWidth=3,labelFontSize=12)))
    area=alt.Chart(wide).mark_area(color=alt.Gradient(gradient="linear",x1=0,y1=0,x2=0,y2=1,
        stops=[alt.GradientStop(color="rgba(40,157,255,0.24)",offset=0),
               alt.GradientStop(color="rgba(40,157,255,0)",offset=1)])).encode(x=x,
        y=alt.Y("Primary:Q",title=title),y2=alt.Y2(datum=min(row["Primary"] for row in rows) if share_price else (0 if drawdown else 100)),tooltip=alt.value(None))
    lines=folded.mark_line(strokeWidth=2.8,interpolate="linear").encode(**encoding,
        strokeDash=alt.StrokeDash("Series:N",scale=alt.Scale(domain=labels,range=[[],[6,5]]),legend=None),tooltip=alt.value(None))
    hover=alt.selection_point(fields=["Date"],nearest=True,on="pointermove",clear="pointerout",empty=False)
    paired_tooltip=[alt.Tooltip("Exact date:N",title="Date"),alt.Tooltip("Primary:Q",title=company_label,format=".2f"),
                    alt.Tooltip("Benchmark:Q",title="SPY ETF proxy",format=".2f")]
    if share_price:paired_tooltip=paired_tooltip[:2]
    selectors=alt.Chart(wide).mark_point(opacity=0).encode(x=x,tooltip=paired_tooltip).add_params(hover)
    rule=alt.Chart(wide).mark_rule(color="#c4d1df",opacity=.55).encode(x=x,
        tooltip=paired_tooltip).transform_filter(hover)
    dots=folded.mark_point(filled=True,size=65,stroke="#121c27",strokeWidth=2).encode(**encoding,tooltip=alt.value(None)).transform_filter(hover)
    last=folded.transform_filter(alt.datum["Exact date"]==rows[-1]["Exact date"]).mark_point(filled=True,size=55).encode(**encoding,tooltip=alt.value(None))
    layers=[area,lines,selectors,rule,dots,last]
    if markers:
        layers.append(alt.Chart(pd.DataFrame(markers)).mark_rule(color="#b8b1f1",strokeDash=[3,5],opacity=.7).encode(
            x=alt.X("Date:T",scale=alt.Scale(type="utc")),tooltip=["Publication","Announcement"]))
    return alt.layer(*layers).properties(height=300).configure_view(stroke=None)
