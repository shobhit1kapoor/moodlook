import argparse
import json
from pathlib import Path

import numpy as np

from nowcasting.experiments import nonnegative_convex_weights, nonnegative_convex_weights_from_statistics
from nowcasting.metrics import rmse


parser = argparse.ArgumentParser(description="Fit nonnegative ensemble weights from complete aligned OOF runs.")
parser.add_argument("--candidate", action="append", nargs="+", required=True, help="Repeat once per model: five run directories")
parser.add_argument("--output", required=True)
args = parser.parse_args()
arrays = []
reference_ids = reference_target = reference_locations = None
for runs in args.candidate:
    parts = [np.load(Path(run) / "oof.npz") for run in runs]
    ids = np.concatenate([part["unique_ids"] for part in parts]); predictions = np.concatenate([part["predictions"] for part in parts]); targets = np.concatenate([part["targets"] for part in parts]); locations = np.concatenate([part["locations"] for part in parts])
    order = np.argsort(ids); ids, predictions, targets, locations = ids[order], predictions[order], targets[order], locations[order]
    if reference_ids is None: reference_ids, reference_target, reference_locations = ids, targets, locations
    elif not (np.array_equal(ids, reference_ids) and np.array_equal(targets, reference_target) and np.array_equal(locations, reference_locations)):
        raise ValueError("Candidates must have aligned complete OOF coverage")
    arrays.append(predictions.reshape(-1))
matrix = np.stack(arrays, axis=1)
target = reference_target.reshape(-1)
weights = nonnegative_convex_weights(matrix, target)
ensemble = np.tensordot(weights, np.stack([array.reshape(reference_target.shape) for array in arrays]), axes=(0, 0))
# Cross-fitted location weights provide an unbiased check on whether the blend
# is real before full-OOF weights are used for the final checkpoint ensemble.
total_count = target.size
total_gram = matrix.T @ matrix
total_cross = matrix.T @ target
crossfit = np.empty_like(ensemble)
for location in sorted(set(reference_locations.tolist())):
    validation = reference_locations == location
    selected = np.repeat(validation, reference_target.shape[1] * reference_target.shape[2])
    held_matrix, held_target = matrix[selected], target[selected]
    train_count = total_count - held_target.size
    location_weights = nonnegative_convex_weights_from_statistics((total_gram - held_matrix.T @ held_matrix) / train_count, (total_cross - held_matrix.T @ held_target) / train_count)
    crossfit[validation] = np.tensordot(location_weights, np.stack([array.reshape(reference_target.shape)[validation] for array in arrays]), axes=(0, 0))
Path(args.output).parent.mkdir(parents=True, exist_ok=True)
np.savez(args.output, weights=weights, crossfit_predictions=crossfit)
print(json.dumps({"weights": weights.tolist(), "oof_rmse": rmse(ensemble, reference_target), "crossfit_location_rmse": rmse(crossfit, reference_target), "best_single_rmse": min(rmse(array.reshape(reference_target.shape), reference_target) for array in arrays)}, indent=2))
