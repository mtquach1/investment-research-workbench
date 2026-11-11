"""Check installed stock workflow behavior offline with fixed example inputs."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from config import get_settings
from stock_screen import stock_screen
from stock_acceptance import evaluate_stock_workflow
from public_data_store import atomic_json


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    settings=get_settings()
    screen=stock_screen(settings.market_data_store,settings.market_history_store,mode=settings.market_data_mode)
    report=evaluate_stock_workflow(screen)
    atomic_json(args.output,report.model_dump(mode='json'))
    print(f'Workflow checks: {report.status}; '+', '.join(
        f'{status}={sum(item.status==status for item in report.checks)}' for status in ('passed','blocked','failed')))
    return 1 if report.status=='failed' else 2 if report.status=='incomplete' else 0


if __name__=='__main__':raise SystemExit(main())
