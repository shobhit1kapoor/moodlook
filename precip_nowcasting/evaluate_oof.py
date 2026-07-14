import argparse
import json
from pathlib import Path

import numpy as np

from nowcasting.experiments import accepts_candidate, paired_location_bootstrap
from nowcasting.metrics import sensor_mse_from_arrays, sensor_weighted_rmse


WEIGHTS = {"goes": 0.24916, "himawari": 0.40406, "meteosat": 0.34678}


def load_runs(runs: list[str]) -> dict:
    records = [np.load(Path(run) / "oof.npz") for run in runs]
    ids = np.concatenate([record["unique_ids"] for record in records])
    if len(set(ids.tolist())) != len(ids):
        raise ValueError("OOF runs overlap; provide exactly one run per fold")
    order = np.argsort(ids)
    return {key: np.concatenate([record[key] for record in records])[order] for key in ("unique_ids", "locations", "sensors", "predictions", "targets")}


def report(values: dict) -> dict:
    mse = sensor_mse_from_arrays(values["predictions"], values["targets"], values["sensors"])
    location_mse = {location: float(np.mean((values["predictions"][values["locations"] == location] - values["targets"][values["locations"] == location]) ** 2)) for location in sorted(set(values["locations"].tolist()))}
    return {"sensor_mse": mse, "sensor_rmse": {key: float(np.sqrt(value)) for key, value in mse.items()}, "weighted_rmse": sensor_weighted_rmse(mse, WEIGHTS), "location_mse": location_mse}


def main() -> None:
    parser = argparse.ArgumentParser(description="Score a complete five-fold OOF candidate and optionally compare it to baseline.")
    parser.add_argument("--runs", nargs="+", required=True)
    parser.add_argument("--baseline-runs", nargs="+")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    candidate = report(load_runs(args.runs))
    if args.baseline_runs:
        baseline = report(load_runs(args.baseline_runs))
        mean, low, high = paired_location_bootstrap(candidate["location_mse"], baseline["location_mse"])
        candidate["comparison"] = {"baseline_weighted_rmse": baseline["weighted_rmse"], "paired_mse_improvement": mean, "ci95": [low, high], "accepted": accepts_candidate(candidate["weighted_rmse"], baseline["weighted_rmse"], low)}
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(candidate, indent=2), encoding="utf-8")
    print(json.dumps(candidate, indent=2))


if __name__ == "__main__":
    main()
