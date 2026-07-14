from __future__ import annotations

import numpy as np

from .cache import Cache
from .io import expand_metadata


class NowcastingDataset:
    """Torch-compatible dataset without importing torch during preprocessing/tests."""

    def __init__(self, cache: Cache, indices: np.ndarray, mean: np.ndarray, std: np.ndarray, *, with_targets: bool, augment: bool = False, with_future_frame: bool = False):
        self.cache = cache
        self.indices = np.asarray(indices, dtype=np.int64)
        self.mean = np.asarray(mean, dtype=np.float32)
        self.std = np.asarray(std, dtype=np.float32)
        self.with_targets = with_targets
        self.augment = augment
        self.with_future_frame = with_future_frame
        if with_targets and cache.targets is None:
            raise ValueError("This cache has no targets")

    def __len__(self) -> int:
        return self.indices.size

    def __getitem__(self, item: int) -> dict:
        index = int(self.indices[item])
        sensor = int(self.cache.sensors[index])
        image = np.asarray(self.cache.images[index], dtype=np.float32)
        image = (image - self.mean[sensor][None, :, None, None]) / self.std[sensor][None, :, None, None]
        image *= np.asarray(self.cache.band_mask[index], dtype=np.float32)[:, :, None, None]
        target = np.asarray(self.cache.targets[index], dtype=np.float32).copy() if self.with_targets else None
        future_image = future_band_mask = None
        if self.with_future_frame:
            future_index = int(self.cache.future_frame_index[index])
            if future_index >= 0:
                future_image = np.asarray(self.cache.images[future_index, 0], dtype=np.float32)
                future_image = (future_image - self.mean[sensor][:, None, None]) / self.std[sensor][:, None, None]
                future_band_mask = np.asarray(self.cache.band_mask[future_index, 0], dtype=np.float32).copy()
                future_image = future_image * future_band_mask[:, None, None]
            else:
                future_image = np.zeros_like(image[0])
                future_band_mask = np.zeros(16, dtype=np.float32)
        if self.augment:
            # Both transforms preserve the physical input/target registration;
            # they are intentionally limited to flips, not arbitrary warps.
            if np.random.random() < 0.5:
                image = image[..., ::-1].copy()
                if target is not None:
                    target = target[..., ::-1].copy()
                if future_image is not None:
                    future_image = future_image[..., ::-1].copy()
            if np.random.random() < 0.5:
                image = image[..., ::-1, :].copy()
                if target is not None:
                    target = target[..., ::-1, :].copy()
                if future_image is not None:
                    future_image = future_image[..., ::-1, :].copy()
        result = {
            "image": image,
            "metadata": expand_metadata(np.asarray(self.cache.metadata[index], dtype=np.float32)).copy(),
            "sensor": np.int64(sensor),
            "frame_mask": np.asarray(self.cache.frame_mask[index], dtype=np.float32).copy(),
            "band_mask": np.asarray(self.cache.band_mask[index], dtype=np.float32).copy(),
            "index": np.int64(index),
        }
        if self.with_targets:
            result["target"] = target
        if self.with_future_frame:
            result["future_image"] = future_image
            result["future_band_mask"] = future_band_mask
        return result
