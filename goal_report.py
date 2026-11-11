"""Private, in-memory PDF reports recomputed from validated goal-plan inputs.

No network, database, temporary report file, or caller-supplied result is used.
Only non-financial font resources are registered globally.
"""

from datetime import datetime, timezone
from io import BytesIO
from math import ceil, floor, log10
from pathlib import Path
from typing import Literal
from xml.sax.saxutils import escape

import reportlab
from reportlab.graphics.shapes import Drawing, Line, PolyLine, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from goal_explorer import changed_assumptions, comparison_checkpoints, explore_goal
from schemas import GoalExplorerSnapshot


REPORT_VERSION = "goal-report-pdf-v1"
INK = colors.HexColor("#182d36")
TEAL = colors.HexColor("#086b70")
MUTED = colors.HexColor("#52656d")
PALE = colors.HexColor("#f0f5f6")
RULE = colors.HexColor("#dbe4e7")
PAGE_WIDTH, PAGE_HEIGHT = letter
MARGIN = 44
WIDTH = PAGE_WIDTH - 2 * MARGIN

_font_directory = Path(reportlab.__file__).parent / "fonts"
pdfmetrics.registerFont(TTFont("GoalRegular", str(_font_directory / "Vera.ttf")))
pdfmetrics.registerFont(TTFont("GoalBold", str(_font_directory / "VeraBd.ttf")))
_glyphs = pdfmetrics.getFont("GoalRegular").face.charToGlyph


def _text(value: object) -> str:
    """Escape paragraph markup and visibly represent unavailable glyphs."""
    raw = str(value).replace("\t", " ").replace("\r", " ")
    normalized = []
    for char in raw:
        if char in "\u2010\u2011\u2012\u2013\u2014\u2212":
            char = "-"
        if char == "\n":
            normalized.append(" ")
        elif ord(char) in _glyphs and char.isprintable():
            normalized.append(char)
        else:
            normalized.append(f"[U+{ord(char):04X}]")
    return escape("".join(normalized))


def money(value: float) -> str:
    sign = "-" if value < 0 else ""
    amount = abs(value)
    return f"{sign}${amount:.4e}" if amount >= 1e12 else f"{sign}${amount:,.2f}"


def _styles():
    return {
        "title": ParagraphStyle("GoalTitle", fontName="GoalBold", fontSize=23, leading=28, textColor=INK, spaceAfter=10),
        "heading": ParagraphStyle("GoalHeading", fontName="GoalBold", fontSize=12, leading=16, textColor=TEAL, spaceBefore=12, spaceAfter=8),
        "body": ParagraphStyle("GoalBody", fontName="GoalRegular", fontSize=9, leading=13, textColor=INK, spaceAfter=7, splitLongWords=True),
        "small": ParagraphStyle("GoalSmall", fontName="GoalRegular", fontSize=7.5, leading=10.5, textColor=MUTED, spaceAfter=6, splitLongWords=True),
        "cell": ParagraphStyle("GoalCell", fontName="GoalRegular", fontSize=8, leading=11, textColor=INK, splitLongWords=True),
        "header": ParagraphStyle("GoalHeader", fontName="GoalBold", fontSize=8, leading=11, textColor=colors.white),
    }


def _p(value, styles, kind="body"):
    return Paragraph(_text(value), styles[kind])


def _table(rows, widths, styles):
    data = [[_p(value, styles, "header" if index == 0 else "cell") for value in row]
            for index, row in enumerate(rows)]
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TEAL),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, TEAL),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, RULE),
    ]))
    return table


def _chart(result, basis):
    drawing = Drawing(WIDTH, 263)
    left, bottom, plot_width, plot_height = 64, 68, WIDTH - 76, 176
    timeline = result.scenarios[1].timeline
    series = [
        ("Low return", [getattr(p, f"balance_{basis}") for p in result.scenarios[0].timeline], "#a85f20", [4, 3]),
        ("Base return", [getattr(p, f"balance_{basis}") for p in timeline], "#086b70", []),
        ("High return", [getattr(p, f"balance_{basis}") for p in result.scenarios[2].timeline], "#7061b5", [7, 3]),
        ("Starting balance + deposits", [getattr(p, f"contributions_{basis}") for p in timeline], "#64748b", [2, 3]),
        ("Goal", [getattr(p, f"target_{basis}") for p in timeline], "#b94d68", [5, 3]),
    ]
    maximum = max(1, max(max(values) for _, values, _, _ in series))
    magnitude = 10 ** floor(log10(maximum / 4))
    tick = ceil(maximum / 4 / magnitude) * magnitude
    ceiling = tick * 4
    for index in range(5):
        value = index * tick
        y = bottom + index * plot_height / 4
        drawing.add(Line(left, y, left + plot_width, y, strokeColor=RULE, strokeWidth=0.5))
        axis_label = f"${value / 1e6:g}m" if 1e6 <= value < 1e12 else (f"${value / 1000:g}k" if 1000 <= value < 1e6 else money(value))
        drawing.add(String(left - 8, y - 3, axis_label, fontName="GoalRegular", fontSize=7, textAnchor="end", fillColor=MUTED))
    years = result.inputs.years
    ticks = sorted({0, years, *range(0, years + 1, max(1, ceil(years / 6)))})
    for year in ticks:
        x = left + year / years * plot_width
        drawing.add(String(x, bottom - 15, str(year), fontName="GoalRegular", fontSize=8, textAnchor="middle", fillColor=MUTED))
    drawing.add(String(left, bottom + plot_height + 10, "Today's dollars" if basis == "today" else "Future dollars", fontName="GoalBold", fontSize=8, fillColor=INK))
    drawing.add(String(left + plot_width / 2, bottom - 31, "Years from plan start", fontName="GoalRegular", fontSize=8, textAnchor="middle", fillColor=MUTED))
    for index, (label, values, color, dash) in enumerate(series):
        points = [coordinate for year, value in enumerate(values)
                  for coordinate in (left + year / years * plot_width, bottom + value / ceiling * plot_height)]
        drawing.add(PolyLine(points, strokeColor=colors.HexColor(color), strokeWidth=1.8 if index == 1 else 1.1, strokeDashArray=dash))
        x, y = ((index * 172, 17) if index < 3 else ((index - 3) * 300, 2))
        drawing.add(Line(x, y + 3, x + 18, y + 3, strokeColor=colors.HexColor(color), strokeWidth=1.5, strokeDashArray=dash))
        drawing.add(String(x + 24, y, label, fontName="GoalRegular", fontSize=7.5, fillColor=INK))
    return drawing


def build_goal_report(snapshot: GoalExplorerSnapshot, *, basis: Literal["today", "nominal"] = "today",
                      baseline: GoalExplorerSnapshot | None = None,
                      comparison_mode: Literal["aligned", "deadlines"] = "aligned",
                      generated_at: datetime | None = None) -> bytes:
    """Return PDF bytes only. Revalidate and recompute all financial outputs."""
    if basis not in ("today", "nominal") or comparison_mode not in ("aligned", "deadlines"):
        raise ValueError("Unsupported report display or comparison mode")
    snapshot = GoalExplorerSnapshot.model_validate(snapshot.model_dump(mode="json"))
    if baseline is not None:
        baseline = GoalExplorerSnapshot.model_validate(baseline.model_dump(mode="json"))
        changed_assumptions(baseline.inputs, snapshot.inputs)
    created = generated_at or datetime.now(timezone.utc)
    if created.utcoffset() is None:
        raise ValueError("Report time must include a timezone")
    created = created.astimezone(timezone.utc)
    styles = _styles()
    result = explore_goal(snapshot.inputs)
    request = snapshot.inputs
    opening_only = explore_goal(request.model_copy(update={"monthly_contribution": 0}))
    estimates = {
        scenario.summary.scenario: (
            "< $0.01 (model)" if scenario.summary.required_monthly_contribution == 0
            and opening.summary.goal_surplus_or_shortfall < 0
            else money(scenario.summary.required_monthly_contribution)
        )
        for scenario, opening in zip(result.scenarios, opening_only.scenarios)
    }
    base = result.scenarios[1]
    final = base.timeline[-1]
    display = "today's dollars" if basis == "today" else "future dollars"
    paragraph = lambda value, kind="body": _p(value, styles, kind)
    story = [
        paragraph("Your goal, on paper", "title"),
        paragraph(f"Plan: {snapshot.label}"),
        paragraph(f"Goal: {request.goal_name}"),
        paragraph(f"Created {created:%Y-%m-%d %H:%M UTC} | Model {result.model_version} | Report {REPORT_VERSION}", "small"),
        paragraph("Private financial assumptions. This PDF is not encrypted. Store it privately; use the JSON export to reopen and edit the plan.", "small"),
        _table([
            ["Starting point", "Contribution plan", "Goal"],
            [f"{money(request.current_balance)} starting balance", f"{money(request.monthly_contribution)} / month", f"{money(request.target_amount_today)} in today's dollars"],
            [f"{request.years} years to deadline", f"{estimates['base']} / month needed under base assumptions", f"{money(final.target_nominal)} at deadline in future dollars"],
        ], [WIDTH / 3] * 3, styles),
        paragraph(f"Base scenario at the deadline ({display})", "heading"),
        _table([
            ["Balance", "Starting balance + deposits", "Modeled growth / loss", "Goal surplus / shortfall"],
            [money(getattr(final, f"balance_{basis}")), money(getattr(final, f"contributions_{basis}")),
             money(getattr(final, f"growth_{basis}")), money(getattr(final, f"balance_{basis}") - getattr(final, f"target_{basis}"))],
        ], [WIDTH / 4] * 4, styles),
        Spacer(1, 13), _chart(result, basis), Spacer(1, 10),
        paragraph("Low/base/high lines use constant return assumptions, not probability bounds. Actual outcomes may fall outside these lines. This report covers the full goal horizon, not the UI's inspected year.", "small"),
        PageBreak(), paragraph("Assumptions and funding pace", "title"),
        _table([
            ["Assumption", "Value"],
            ["Annual return before fees (low / base / high)", " / ".join(f"{getattr(request.return_assumptions, label):.2%}" for label in ("low", "base", "high"))],
            ["Annual fee / inflation", f"{request.annual_fee_assumption:.2%} / {request.annual_inflation_assumption:.2%}"],
            ["Deposit timing", "Fixed nominal deposits at each month end"],
        ], [WIDTH * .48, WIDTH * .52], styles),
        Spacer(1, 12),
        _table([
            ["Scenario / return", "Balance (today's $)", "Goal gap (today's $)", "Monthly deposit needed (future $)"],
            *[[f"{s.summary.scenario.title()} / {s.summary.annual_return_assumption:.2%}",
               money(s.summary.projected_balance_in_today_dollars),
               money(s.summary.projected_balance_in_today_dollars - request.target_amount_today),
               estimates[s.summary.scenario]] for s in result.scenarios],
        ], [105, 139, 139, WIDTH - 383], styles),
        paragraph("Selected yearly checkpoints", "heading"),
    ]
    checkpoints = sorted({0, request.years, *range(0, request.years + 1, max(1, ceil(request.years / 6)))})
    story.append(_table([
        [f"Year / {display}", "Balance", "Starting + deposits", "Growth / loss"],
        *[[str(year), money(getattr(base.timeline[year], f"balance_{basis}")),
           money(getattr(base.timeline[year], f"contributions_{basis}")),
           money(getattr(base.timeline[year], f"growth_{basis}"))] for year in checkpoints],
    ], [112, 137, 137, WIDTH - 386], styles))
    story.extend([
        Spacer(1, 12),
        paragraph("Reading this report", "heading"),
        paragraph("Annual net return is simplified as return minus fee, converted to an effective monthly rate. The goal rises with inflation. Today's-dollar balances, cumulative deposits and growth are deflated together at each checkpoint; historical cost basis is unknown. Values are rounded independently to cents, so sums may differ by a cent. Required deposits are rounded estimates and can still leave a shortfall; sub-cent results must not be interpreted as a usable zero-deposit solution.", "small"),
        paragraph("The model excludes taxes, account limits, withdrawals and changing deposits. It does not establish affordability or investment suitability. No stochastic simulation or actual holdings are included. Educational planning only; not a forecast or guarantee. Very large amounts use approximate scientific notation. Unsupported font characters are shown as [U+XXXX] rather than silently omitted.", "small"),
    ])
    if baseline is not None:
        points = comparison_checkpoints(baseline.inputs, request, comparison_mode)
        story.extend([
            PageBreak(), paragraph("Baseline and alternative", "title"),
            paragraph(f"Baseline: {baseline.label}"),
            paragraph(f"Current plan: {snapshot.label}"),
            paragraph("Both plans use the earlier deadline as a common elapsed year." if comparison_mode == "aligned" else
                      "Separate deadlines: these balances include different amounts of time and deposits. This is not a performance ranking."),
            paragraph(f"All balances and gaps below use today's dollars. Deposit amounts use nominal future dollars.", "small"),
            _table([
                ["Measure", "Baseline", "Current plan"],
                ["Goal deadline / evaluated year", f"{baseline.inputs.years} / {points[0].year}", f"{request.years} / {points[1].year}"],
                ["Monthly deposit", money(baseline.inputs.monthly_contribution), money(request.monthly_contribution)],
                ["Starting balance + deposits (future dollars)", money(points[0].contributions_nominal), money(points[1].contributions_nominal)],
                ["Base balance (today's dollars)", money(points[0].balance_today), money(points[1].balance_today)],
                ["Goal surplus / shortfall (today's dollars)", money(points[0].balance_today - request.target_amount_today), money(points[1].balance_today - request.target_amount_today)],
            ], [WIDTH * .42, WIDTH * .29, WIDTH * .29], styles),
            paragraph("Change in base balance", "heading"),
            paragraph(f"{money(points[1].balance_today - points[0].balance_today)} in today's dollars (current minus baseline)."),
            paragraph("Different contributions can explain a larger balance. Neither the balance difference nor a higher assumed return establishes a better strategy.", "small"),
        ])
        changes = changed_assumptions(baseline.inputs, request)
        if changes:
            story.append(_table([["Changed assumption", "Baseline", "Current plan"],
                                 *[[row["Assumption"], row["Baseline"], row["Current"]] for row in changes]],
                                [WIDTH * .42, WIDTH * .29, WIDTH * .29], styles))
        else:
            story.append(paragraph("No financial assumptions changed."))
        story.extend([
            paragraph("Baseline assumptions", "heading"),
            paragraph(f"Opening balance {money(baseline.inputs.current_balance)}; today's target {money(baseline.inputs.target_amount_today)}; inflation {baseline.inputs.annual_inflation_assumption:.2%}; fee {baseline.inputs.annual_fee_assumption:.2%}. Low/base/high returns: " +
                      " / ".join(f"{getattr(baseline.inputs.return_assumptions, label):.2%}" for label in ("low", "base", "high")) + "."),
        ])

    def decorate(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(RULE)
        canvas.line(MARGIN, PAGE_HEIGHT - 35, PAGE_WIDTH - MARGIN, PAGE_HEIGHT - 35)
        canvas.setFont("GoalBold", 8)
        canvas.setFillColor(TEAL)
        canvas.drawString(MARGIN, PAGE_HEIGHT - 26, "GOAL EXPLORER / PRIVATE PLAN")
        canvas.setFont("GoalRegular", 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(MARGIN, 25, "User-entered assumptions. Results are not guaranteed. Not encrypted.")
        canvas.drawRightString(PAGE_WIDTH - MARGIN, 25, f"Page {document.page}")
        canvas.restoreState()

    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=MARGIN, rightMargin=MARGIN,
                                 topMargin=54, bottomMargin=45, title="Goal planning report",
                                 author="Goal Explorer", subject="Educational scenario report", pageCompression=1)
    document.build(story, onFirstPage=decorate, onLaterPages=decorate)
    return buffer.getvalue()
