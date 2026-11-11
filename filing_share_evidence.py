"""Narrow inline-XBRL point-share reader for the two registered cover filings.

No text/label inference of class assignment. Weighted averages, duration facts,
typed dimensions, continuations and unknown transforms never become quantities.
"""
from datetime import date
from decimal import Decimal
from html.parser import HTMLParser
import re

TAGS = {'dei:EntityCommonStockSharesOutstanding', 'us-gaap:CommonStockSharesOutstanding'}


class _Node:
    def __init__(self, tag, attrs):
        self.tag, self.attrs, self.children = tag, dict(attrs), []

    def text(self):
        return ''.join(child if isinstance(child, str) else child.text() for child in self.children).strip()

    def find(self, tag):
        result = [self] if self.tag == tag else []
        for child in self.children:
            if isinstance(child, _Node):
                result.extend(child.find(tag))
        return result


class _Fragments(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.roots, self.stack = [], []
        self.nodes = 0

    def handle_starttag(self, tag, attrs):
        selected = tag in ('xbrli:context', 'xbrli:unit') or (
            tag == 'ix:nonfraction' and dict(attrs).get('name') in TAGS)
        if not self.stack and not selected:
            return
        self.nodes += 1
        if self.nodes > 50000 or len(self.stack) > 32:
            raise ValueError('Share evidence structure exceeds budget')
        node = _Node(tag, attrs)
        if self.stack:
            self.stack[-1].children.append(node)
        else:
            self.roots.append(node)
        self.stack.append(node)

    def handle_endtag(self, tag):
        if self.stack:
            if self.stack[-1].tag != tag:
                raise ValueError('Unsupported nested share evidence')
            self.stack.pop()

    def handle_data(self, text):
        if self.stack:
            self.stack[-1].children.append(text)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)


def filing_point_shares(body, reference):
    parser = _Fragments()
    parser.feed(body)
    parser.close()
    if parser.stack:
        raise ValueError('Truncated share evidence')
    contexts, units = {}, {}
    for node in parser.roots:
        target = contexts if node.tag == 'xbrli:context' else units if node.tag == 'xbrli:unit' else None
        if target is not None:
            key = node.attrs.get('id')
            if not key or key in target:
                raise ValueError('Missing or duplicate share context/unit')
            target[key] = node
    rows = []
    for fact in parser.roots:
        if fact.tag != 'ix:nonfraction':
            continue
        attrs = fact.attrs
        if (attrs.get('continuedat') or attrs.get('xsi:nil') in ('true', '1') or attrs.get('sign')
                or attrs.get('format', '') not in ('', 'ixt:num-dot-decimal')
                or fact.find('ix:exclude')):
            raise ValueError('Unsupported point-share fact semantics')
        nested = fact.find('ix:nonfraction')[1:]
        if nested and not (len(nested) == 1 and attrs['name'] == 'us-gaap:CommonStockSharesOutstanding'
                and nested[0].attrs.get('name') == 'us-gaap:CommonStockSharesIssued'
                and nested[0].text() == fact.text() and all(
                    nested[0].attrs.get(key) == attrs.get(key) for key in
                    ('contextref', 'unitref', 'scale', 'decimals', 'format', 'sign', 'xsi:nil', 'continuedat'))):
            raise ValueError('Unsupported nested point-share semantics')
        context = contexts[attrs['contextref']]
        identifiers, instants = context.find('xbrli:identifier'), context.find('xbrli:instant')
        if (len(identifiers) != 1 or identifiers[0].text() != f"{reference['cik']:010d}"
                or identifiers[0].attrs.get('scheme') != 'http://www.sec.gov/CIK'
                or len(instants) != 1 or context.find('xbrli:startdate') or context.find('xbrli:enddate')
                or context.find('xbrldi:typedmember') or context.find('xbrli:forever')):
            raise ValueError('Point-share context must identify this issuer at one instant')
        instant = date.fromisoformat(instants[0].text())
        if instant > date.fromisoformat(reference['filed_on']):
            raise ValueError('Future share measurement')
        unit = units[attrs['unitref']]
        measures = unit.find('xbrli:measure')
        if len(measures) != 1 or measures[0].text() != 'xbrli:shares' or unit.find('xbrli:divide'):
            raise ValueError('Point-share unit must be pure shares')
        text = fact.text()
        if not re.fullmatch(r'(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?', text):
            raise ValueError('Unsupported point-share numeric text')
        scale, decimals = attrs.get('scale', '0'), attrs.get('decimals', '')
        if not re.fullmatch(r'-?[0-9]{1,2}', scale) or not -12 <= int(scale) <= 12:
            raise ValueError('Unsupported point-share scale')
        if decimals != 'INF' and (not re.fullmatch(r'-?[0-9]{1,2}', decimals) or not -15 <= int(decimals) <= 15):
            raise ValueError('Missing or unsupported point-share rounding')
        quantity = Decimal(text.replace(',', '')) * Decimal(10) ** int(scale)
        if not 0 <= quantity <= Decimal('1e15') or quantity != quantity.to_integral_value():
            raise ValueError('Point-share quantity must be an integer within budget')
        dimensions = {}
        for member in context.find('xbrldi:explicitmember'):
            axis = member.attrs.get('dimension')
            if not axis or axis in dimensions or not member.text():
                raise ValueError('Ambiguous share dimension')
            dimensions[axis] = member.text()
        rows.append(dict(tag=attrs['name'], context_ref=attrs['contextref'], measured_on=instant.isoformat(),
            filed_on=reference['filed_on'], accession=reference['accession'], cik=reference['cik'],
            shares=str(quantity), scale=int(scale), decimals=decimals, dimensions=dimensions,
            scope='dimensional_unassigned' if dimensions else 'issuer_unallocated'))
    # Duplicate facts remain observations. Conflicting values are never silently
    # collapsed or selected as the newest, and these values do not price a class.
    return sorted(rows, key=lambda row: (row['measured_on'], row['tag'], row['context_ref'], row['shares']))
