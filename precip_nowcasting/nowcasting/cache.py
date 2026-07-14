from __future__ import annotations

import json
import ast
from pathlib import Path

import numpy as np
import pandas as pd

from .io import SENSORS
from .preprocess import cache_paths


class Cache:
    def __init__(self, cache_root: str | Path, split: str):
        self.cache_root = str(cache_root)
        self.split = split
        self.paths = cache_paths(cache_root, split)
        if not self.paths["meta"].exists():
            raise FileNotFoundError(f"Cache metadata not found: {self.paths['meta']}. Run preprocessing first.")
        self.info = json.loads(self.paths["meta"].read_text(encoding="utf-8"))
        self.manifest = pd.read_csv(self.paths["manifest"], parse_dates=["datetime"])
        count, image_size = self.info["count"], self.info["image_size"]
        image_dtype = np.dtype(self.info.get("cache_dtype", "uint8"))
        self.paths = cache_paths(cache_root, split, image_dtype.name)
        metadata_dim = int(self.info.get("metadata_dim", 4))
        self.images = np.memmap(self.paths["images"], mode="r", dtype=image_dtype, shape=(count, 3, 16, image_size, image_size))
        self.metadata = np.memmap(self.paths["metadata"], mode="r", dtype=np.float32, shape=(count, metadata_dim))
        self.sensors = np.memmap(self.paths["sensors"], mode="r", dtype=np.int8, shape=(count,))
        self.frame_mask = np.memmap(self.paths["frame_mask"], mode="r", dtype=np.uint8, shape=(count, 3))
        self.band_mask = np.memmap(self.paths["band_mask"], mode="r", dtype=np.uint8, shape=(count, 3, 16))
        self.targets = None
        if self.info["has_targets"]:
            size = self.info["target_size"]
            self.targets = np.memmap(self.paths["targets"], mode="r", dtype=np.float32, shape=(count, size, size))
        self.future_frame_index = self._future_frame_index()

    def __getstate__(self) -> dict:
        """Windows DataLoader workers must reopen memmaps instead of pickling them."""
        return {"cache_root": self.cache_root, "split": self.split}

    def __setstate__(self, state: dict) -> None:
        self.__init__(state["cache_root"], state["split"])

    @property
    def count(self) -> int:
        return int(self.info["count"])

    def _future_frame_index(self) -> np.ndarray:
        """Find the train-only observation at each row's target timestamp.

        A row at time t+30 contains the t observation as its first input frame.
        This is used only as an auxiliary training target; evaluation rows never
        consume their neighbouring observations.
        """
        links = np.full(self.count, -1, dtype=np.int64)
        if self.split != "train":
            return links
        lookup = {(row.name_location, pd.Timestamp(row.datetime)): index for index, row in self.manifest.iterrows()}
        for index, row in self.manifest.iterrows():
            timestamp = pd.Timestamp(row.datetime)
            next_index = lookup.get((row.name_location, timestamp + pd.Timedelta(minutes=30)))
            if next_index is None or not self.frame_mask[next_index, 0]:
                continue
            # Guard against exceptional non-standard windows rather than
            # assuming every following row has the target observation first.
            names = ast.literal_eval(self.manifest.at[next_index, "last_30_minutes_observation_filename"])
            if names and timestamp.strftime("%Y%m%d_%H%M") in names[0]:
                links[index] = int(next_index)
        return links


def fold_normalizer(cache: Cache, train_indices: np.ndarray, *, max_samples_per_sensor: int = 2_000, seed: int = 20260709) -> tuple[np.ndarray, np.ndarray]:
    """Per-sensor per-band statistics using only indices supplied by the fold."""
    generator = np.random.default_rng(seed)
    mean = np.zeros((len(SENSORS), 16), dtype=np.float64)
    std = np.ones((len(SENSORS), 16), dtype=np.float64)
    for sensor_id in range(len(SENSORS)):
        candidates = train_indices[np.asarray(cache.sensors[train_indices]) == sensor_id]
        if candidates.size == 0:
            # Useful for a deliberately tiny single-sensor smoke cache. Full
            # location folds are validated separately to contain every sensor.
            continue
        if candidates.size > max_samples_per_sensor:
            candidates = generator.choice(candidates, size=max_samples_per_sensor, replace=False)
        total = np.zeros(16, dtype=np.int64)
        running_sum = np.zeros(16, dtype=np.float64)
        running_sq = np.zeros(16, dtype=np.float64)
        for index in candidates:
            values = np.asarray(cache.images[int(index)], dtype=np.float64)  # [time, band, y, x]
            valid_frames = np.asarray(cache.frame_mask[int(index)], dtype=bool)
            available = np.asarray(cache.band_mask[int(index)], dtype=bool) & valid_frames[:, None]
            for band in range(16):
                valid = available[:, band]
                if valid.any():
                    band_values = values[valid, band]
                    running_sum[band] += band_values.sum()
                    running_sq[band] += np.square(band_values).sum()
                    total[band] += band_values.size
        if np.any(total == 0):
            raise ValueError(f"No valid frames available for sensor {SENSORS[sensor_id]}")
        mean[sensor_id] = running_sum / total
        variance = np.maximum(running_sq / total - np.square(mean[sensor_id]), 1e-6)
        std[sensor_id] = np.sqrt(variance)
    return mean.astype(np.float32), std.astype(np.float32)
