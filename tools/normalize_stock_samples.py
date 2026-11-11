"""Offline normalization of cached public issuer samples. No recommendations."""

import argparse
from datetime import date
from decimal import Decimal
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from market_data import load_snapshot
from market_sources import SOURCES
from stock_financials import normalize_annual_financials


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", type=date.fromisoformat, required=True)
    parser.add_argument("--cache", type=Path, default=Path("data_cache"))
    parser.add_argument("--output", type=Path, default=Path("output/audits/annual-financials.json"))
    args = parser.parse_args()
    results = {}
    for source_id in SOURCES:
        if not source_id.startswith("sec_companyfacts_"):
            continue
        snapshot = load_snapshot(source_id, args.cache)
        company = json.loads(snapshot.path.read_text(encoding="utf-8-sig"))
        result = normalize_annual_financials(company, as_of=args.as_of, source_sha256=snapshot.metadata["sha256"])
        ticker = source_id.removeprefix("sec_companyfacts_").upper()
        results[ticker] = result.to_dict()
        print(ticker, result.period_end, "financials_complete:", result.financials_complete,
              "issues:", ", ".join(result.issues) or "none")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2, default=lambda value: str(value) if isinstance(value, Decimal) else value,
                                     allow_nan=False), encoding="utf-8")
    print(args.output.resolve())


if __name__ == "__main__":
    main()
