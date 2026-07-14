"""Sequential, fixed-fold screening runner; intentionally never overlaps GPU jobs."""
import argparse
import json
from pathlib import Path

from evaluate_oof import load_runs, report
from nowcasting.config import load_config
from nowcasting.experiments import accepts_candidate, paired_location_bootstrap
from nowcasting.training import train


parser = argparse.ArgumentParser(description="Run the fixed 0/2/4 location-held-out screening protocol sequentially.")
parser.add_argument("--config", required=True)
parser.add_argument("--run-prefix", required=True)
parser.add_argument("--output", required=True)
parser.add_argument("--folds", nargs="+", default=["0", "2", "4"])
parser.add_argument("--baseline-runs", nargs="+")
parser.add_argument("--max-samples", type=int)
args = parser.parse_args()
config = load_config(args.config)
runs = [str(train(config, fold, run_id=f"{args.run_prefix}-fold{fold}", max_samples=args.max_samples)) for fold in args.folds]
candidate = report(load_runs(runs))
candidate["runs"] = runs
if args.baseline_runs:
    baseline = report(load_runs(args.baseline_runs))
    mean, low, high = paired_location_bootstrap(candidate["location_mse"], baseline["location_mse"])
    candidate["comparison"] = {
        "baseline_weighted_rmse": baseline["weighted_rmse"], "paired_mse_improvement": mean, "ci95": [low, high],
        "screen_advance": (baseline["weighted_rmse"] - candidate["weighted_rmse"]) >= 0.02,
        "accepted_full_oof": accepts_candidate(candidate["weighted_rmse"], baseline["weighted_rmse"], low),
    }
Path(args.output).parent.mkdir(parents=True, exist_ok=True)
Path(args.output).write_text(json.dumps(candidate, indent=2), encoding="utf-8")
print(json.dumps(candidate, indent=2))
