from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd


def location_statistics(manifest: pd.DataFrame, targets: np.ndarray) -> pd.DataFrame:
    rows = []
    for location, group in manifest.groupby("name_location", sort=True):
        indices = group.index.to_numpy()
        values = np.asarray(targets[indices], dtype=np.float32)
        rows.append({"name_location": location, "satellite_target": group["satellite_target"].iat[0], "samples": len(indices), "rain_energy": float(np.mean(values ** 2)), "wet_fraction": float(np.mean(values > 0))})
    return pd.DataFrame(rows).sort_values(["satellite_target", "name_location"], kind="stable").reset_index(drop=True)


def stratified_location_folds(manifest: pd.DataFrame, targets: np.ndarray, *, folds: int = 5, seed: int = 20260709) -> pd.DataFrame:
    """Assign each location once, balancing sensor, rain energy, and samples.

    Each sensor has at least five training locations, so every validation fold
    contains all sensors. Only location-level target summaries are used.
    """
    stats = location_statistics(manifest, targets)
    stats["fold"] = -1
    generator = np.random.default_rng(seed)
    for sensor, group in stats.groupby("satellite_target", sort=True):
        order = group.assign(tie=generator.random(len(group))).sort_values(["rain_energy", "samples", "tie"], ascending=[False, False, True]).index.tolist()
        loads = np.zeros((folds, 2), dtype=np.float64)
        for rank, index in enumerate(order):
            row = stats.loc[index]
            if rank < folds:
                selected = rank
            else:
                normalized = loads / np.maximum(loads.sum(axis=0, keepdims=True), 1.0)
                selected = int(np.argmin(normalized.sum(axis=1)))
            stats.loc[index, "fold"] = selected
            loads[selected] += (float(row["samples"]), float(row["rain_energy"]) * float(row["samples"]))
    if (stats["fold"] < 0).any():
        raise RuntimeError("Incomplete fold assignment")
    return stats


def materialize_folds(manifest: pd.DataFrame, targets: np.ndarray, destination: str | Path, *, folds: int = 5, seed: int = 20260709) -> pd.DataFrame:
    summary = stratified_location_folds(manifest, targets, folds=folds, seed=seed)
    mapping = summary.set_index("name_location")["fold"]
    assigned = manifest[["unique_id", "name_location", "satellite_target"]].copy()
    assigned["fold"] = assigned["name_location"].map(mapping).astype(int)
    if assigned.groupby("name_location")["fold"].nunique().max() != 1:
        raise AssertionError("A location appears in more than one fold")
    Path(destination).parent.mkdir(parents=True, exist_ok=True)
    assigned.to_csv(destination, index=False)
    summary.to_csv(Path(destination).with_name("fold_summary.csv"), index=False)
    return assigned
