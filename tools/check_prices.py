"""Check installed daily closes against Yahoo Finance for personal local research."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from price_checks import check_price

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols",nargs="+",required=True)
    parser.add_argument("--store",type=Path,default=Path("data_cache/local_market_history"))
    args=parser.parse_args()
    if not 1<=len(args.symbols)<=5:parser.error("Choose one through five installed symbols")
    for symbol in dict.fromkeys(args.symbols):
        try:
            result=check_price(args.store,symbol)
            print(f"{symbol}: {result.status}; date={result.price_date}; difference_percent={result.difference_percent}")
        except (OSError,ValueError,KeyError,TypeError):
            print("Check unavailable; primary data preserved.")
    return 0

if __name__=="__main__":raise SystemExit(main())
