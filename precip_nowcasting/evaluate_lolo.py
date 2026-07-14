"""Aggregate one held-out-location run per location as a finalist stress report."""
import argparse
import json
from pathlib import Path

import numpy as np

from evaluate_oof import report


parser = argparse.ArgumentParser(description="Score complete leave-one-location-out predictions.")
parser.add_argument("--runs", nargs="+", required=True, help="One run directory per held-out location")
parser.add_argument("--output", required=True)
args = parser.parse_args()
records = [np.load(Path(run) / "oof.npz") for run in args.runs]
locations = [set(record["locations"].tolist()) for record in records]
if any(len(value) != 1 for value in locations):
    raise ValueError("Each LOLO run must contain exactly one held-out location")
if len({next(iter(value)) for value in locations}) != len(records):
    raise ValueError("LOLO run locations must be unique")
values = {key: np.concatenate([record[key] for record in records]) for key in ("unique_ids", "locations", "sensors", "predictions", "targets")}
result = report(values)
result["locations"] = sorted(next(iter(value)) for value in locations)
Path(args.output).parent.mkdir(parents=True, exist_ok=True)
Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
