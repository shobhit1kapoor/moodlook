from __future__ import annotations

from collections.abc import Mapping
import numpy as np


def rmse(prediction: np.ndarray, target: np.ndarray) -> float:
    prediction = np.asarray(prediction, dtype=np.float64)
    target = np.asarray(target, dtype=np.float64)
    if prediction.shape != target.shape:
        raise ValueError(f"Shape mismatch: {prediction.shape} != {target.shape}")
    if not (np.isfinite(prediction).all() and np.isfinite(target).all()):
        raise ValueError("RMSE inputs must be finite")
    return float(np.sqrt(np.mean((prediction - target) ** 2)))


def sensor_weighted_rmse(sensor_mse: Mapping[str, float], weights: Mapping[str, float]) -> float:
    missing = set(weights) - set(sensor_mse)
    if missing:
        raise ValueError(f"Missing sensor MSE values: {sorted(missing)}")
    total = sum(float(weights[sensor]) for sensor in weights)
    if total <= 0:
        raise ValueError("Sensor weights must sum to a positive value")
    weighted_mse = sum(float(weights[sensor]) * float(sensor_mse[sensor]) for sensor in weights) / total
    return float(np.sqrt(weighted_mse))


def sensor_mse_from_arrays(prediction: np.ndarray, target: np.ndarray, sensors: np.ndarray) -> dict[str, float]:
    values: dict[str, float] = {}
    for sensor in sorted(set(sensors.tolist())):
        mask = sensors == sensor
        values[str(sensor)] = float(np.mean((prediction[mask] - target[mask]) ** 2))
    return values
