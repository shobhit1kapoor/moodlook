from __future__ import annotations

from collections.abc import Mapping
import numpy as np


def paired_location_bootstrap(candidate_mse: Mapping[str, float], baseline_mse: Mapping[str, float], *, draws: int = 10_000, seed: int = 20260709) -> tuple[float, float, float]:
    """Return mean MSE improvement and a paired 95% location-bootstrap interval."""
    locations = sorted(set(candidate_mse) & set(baseline_mse))
    if len(locations) < 2:
        raise ValueError("At least two shared locations are required")
    delta = np.array([baseline_mse[item] - candidate_mse[item] for item in locations], dtype=np.float64)
    generator = np.random.default_rng(seed)
    sampled = generator.choice(delta, size=(draws, len(delta)), replace=True).mean(axis=1)
    return float(delta.mean()), float(np.quantile(sampled, 0.025)), float(np.quantile(sampled, 0.975))


def accepts_candidate(candidate_rmse: float, baseline_rmse: float, ci_low_mse_improvement: float, *, min_rmse_gain: float = 0.002) -> bool:
    return (baseline_rmse - candidate_rmse) >= min_rmse_gain and ci_low_mse_improvement > 0.0


def nonnegative_convex_weights_from_statistics(gram: np.ndarray, cross: np.ndarray) -> np.ndarray:
    """Solve simplex regression from normalized P'P and P'y statistics."""
    gram = np.asarray(gram, dtype=np.float64)
    cross = np.asarray(cross, dtype=np.float64)
    models = len(cross)
    if gram.shape != (models, models):
        raise ValueError("Invalid ensemble Gram matrix")
    if models > 12:
        raise ValueError("Ensemble active-set solver supports at most 12 candidates")
    best_objective, best = float("inf"), None
    for active_mask in range(1, 1 << models):
        active = [index for index in range(models) if active_mask & (1 << index)]
        sub_gram = gram[np.ix_(active, active)]
        system = np.block([[sub_gram, np.ones((len(active), 1))], [np.ones((1, len(active))), np.zeros((1, 1))]])
        rhs = np.concatenate([cross[active], [1.0]])
        try:
            solution = np.linalg.solve(system, rhs)[:-1]
        except np.linalg.LinAlgError:
            solution = np.linalg.lstsq(system, rhs, rcond=None)[0][:-1]
        if np.any(solution < -1e-8):
            continue
        candidate = np.zeros(models, dtype=np.float64)
        candidate[active] = np.maximum(solution, 0.0)
        candidate /= candidate.sum()
        objective = -2 * candidate @ cross + candidate @ gram @ candidate
        if objective < best_objective:
            best_objective, best = float(objective), candidate
    return (best if best is not None else np.full(models, 1.0 / models)).astype(np.float32)


def nonnegative_convex_weights(predictions: np.ndarray, target: np.ndarray, *, steps: int | None = None, lr: float | None = None) -> np.ndarray:
    """Exact active-set simplex regression for a small OOF ensemble.

    Candidate counts are deliberately small (normally two or three), so
    enumerating active sets is both deterministic and vastly cheaper than
    thousands of full-image gradient iterations.

    ``steps`` and ``lr`` remain accepted as ignored compatibility arguments
    for earlier experiment scripts.
    """
    predictions = np.asarray(predictions, dtype=np.float64)
    target = np.asarray(target, dtype=np.float64).reshape(-1)
    if predictions.ndim != 2 or predictions.shape[0] != target.size:
        raise ValueError("predictions must be [n_values, n_models] aligned to target")
    gram = predictions.T @ predictions / target.size
    cross = predictions.T @ target / target.size
    return nonnegative_convex_weights_from_statistics(gram, cross)
