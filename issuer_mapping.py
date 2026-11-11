"""Exact current ticker associations; no guessed punctuation or share-class joins."""

from collections import defaultdict


def ticker_issuer_index(records):
    grouped = defaultdict(set)
    for row in records:
        grouped[row["ticker"]].add(row["cik"])
    return dict(grouped)


def exact_issuer_matches(securities, mapping):
    index = ticker_issuer_index(mapping)
    output = []
    for row in securities:
        candidates = index.get(row["ticker"], set())
        cik = next(iter(candidates)) if len(candidates) == 1 else None
        output.append({"security_id":row["security_id"], "ticker":row["ticker"],
            "issuer_id":f"sec:{cik:010d}" if cik is not None else None,
            "cik":cik, "status":"matched_exact_sec_ticker" if cik is not None else "ambiguous" if candidates else "unmatched",
            "index_membership_verified":False, "historical_mapping_verified":False})
    return output
