"""Offline experimental ranking and entry-cost diagnostics; no return forecasts."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from config import get_settings
from stock_screen import stock_screen
from experimental_basket import ExperimentalRequest
from ranking_cost_evaluation import evaluate_ranking_costs
from public_data_store import atomic_json


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--acknowledge-experimental',action='store_true')
    args=parser.parse_args()
    try:
        settings=get_settings()
        screen=stock_screen(settings.market_data_store,settings.market_history_store,mode=settings.market_data_mode)
        result=evaluate_ranking_costs(screen,ExperimentalRequest(
            acknowledge_proxy_and_estimates=args.acknowledge_experimental,budget_cents=100003))
        atomic_json(args.output,result.model_dump(mode='json'))
        print(f'Ranking/cost diagnostics: {result.status}; scenarios={len(result.sensitivity)}; changes={result.scenarios_with_changes}; minimum_retained={result.minimum_retained}')
        return 0 if result.status=='evaluated' and result.row_order_invariant and result.uniform_yield_scale_invariant else 2
    except (ValueError,OSError,ArithmeticError):
        print('Evaluation failed. Check installed evidence, configuration and local tests; no provider response is logged.')
        return 1


if __name__=='__main__':raise SystemExit(main())
