from __future__ import annotations

import argparse
from pathlib import Path
import zipfile

import numpy as np
from tqdm import tqdm

from .io import (
    SENSOR_TO_ID,
    archive_path_for_observation,
    encode_metadata,
    load_manifest,
    observation_names,
    target_dir_for_split,
    validate_archive,
    write_json,
)


def _read_input(handle: zipfile.ZipFile, path: str, image_size: int, cache_dtype: np.dtype) -> tuple[np.ndarray, np.ndarray]:
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.io import MemoryFile

    with MemoryFile(handle.read(path)) as memory:
        with memory.open() as dataset:
            if not 1 <= dataset.count <= 16:
                raise ValueError(f"{path} has {dataset.count} bands; expected 1-16")
            source = dataset.read(out_shape=(dataset.count, image_size, image_size), resampling=Resampling.bilinear)
    # The supplied data contains a small number of 15-band files despite the
    # nominal 16-band schema. Preserve known channels and mark the padded tail
    # unavailable; the dataset converts it to a neutral normalized value.
    if source.dtype.kind not in {"u", "i", "f"}:
        raise ValueError(f"{path} has unsupported raster dtype {source.dtype}")
    image = np.zeros((16, image_size, image_size), dtype=cache_dtype)
    image[: source.shape[0]] = source.astype(cache_dtype, copy=False)
    band_mask = np.zeros(16, dtype=np.uint8); band_mask[: source.shape[0]] = 1
    return image, band_mask


def _read_target(handle: zipfile.ZipFile, path: str, target_size: int) -> np.ndarray:
    import rasterio
    from rasterio.io import MemoryFile

    with MemoryFile(handle.read(path)) as memory:
        with memory.open() as dataset:
            target = dataset.read(1)
    if target.shape != (target_size, target_size):
        raise ValueError(f"{path} has target shape {target.shape}, expected {(target_size, target_size)}")
    if not np.isfinite(target).all() or np.any(target < 0):
        raise ValueError(f"{path} has invalid precipitation values")
    return target.astype(np.float32, copy=False)


def cache_paths(cache_root: str | Path, split: str, cache_dtype: str = "uint8") -> dict[str, Path]:
    root = Path(cache_root) / split
    return {
        "root": root,
        "images": root / f"images.{cache_dtype}.mmap",
        "targets": root / "targets.float32.mmap",
        "metadata": root / "metadata.float32.mmap",
        "frame_mask": root / "frame_mask.uint8.mmap",
        "band_mask": root / "band_mask.uint8.mmap",
        "sensors": root / "sensors.int8.mmap",
        "manifest": root / "manifest.csv",
        "meta": root / "cache_meta.json",
    }


def build_cache(archive: str | Path, cache_root: str | Path, split: str, *, image_size: int = 128, target_size: int = 41, cache_dtype: str = "uint8", verify: bool = True, max_samples: int | None = None) -> dict:
    """Decode an archive once into compact memory-mappable arrays.

    The default preserves supplied uint8 radiances exactly; a float cache can
    be requested only when a future source archive genuinely requires it.
    Fold-specific normalization is calculated later from training indices only.
    """
    if split not in {"train", "test"}:
        raise ValueError("split must be 'train' or 'test'")
    if verify:
        manifest = validate_archive(archive, split, check_tiffs=True)
    else:
        manifest = load_manifest(archive, split)
    if max_samples is not None:
        if max_samples <= 0:
            raise ValueError("max_samples must be positive")
        manifest = manifest.iloc[:max_samples].copy()
    cache_dtype_np = np.dtype(cache_dtype)
    if cache_dtype_np.kind not in {"u", "i", "f"}:
        raise ValueError("cache_dtype must be an integer or floating-point dtype")
    paths = cache_paths(cache_root, split, cache_dtype_np.name)
    paths["root"].mkdir(parents=True, exist_ok=True)
    count = len(manifest)
    images = np.memmap(paths["images"], mode="w+", dtype=cache_dtype_np, shape=(count, 3, 16, image_size, image_size))
    metadata_values = encode_metadata(manifest)
    metadata = np.memmap(paths["metadata"], mode="w+", dtype=np.float32, shape=(count, metadata_values.shape[1]))
    sensors = np.memmap(paths["sensors"], mode="w+", dtype=np.int8, shape=(count,))
    frame_mask = np.memmap(paths["frame_mask"], mode="w+", dtype=np.uint8, shape=(count, 3))
    band_mask = np.memmap(paths["band_mask"], mode="w+", dtype=np.uint8, shape=(count, 3, 16))
    targets = None
    if split == "train":
        targets = np.memmap(paths["targets"], mode="w+", dtype=np.float32, shape=(count, target_size, target_size))

    with zipfile.ZipFile(archive) as handle:
        for index, row in enumerate(tqdm(manifest.itertuples(index=False), total=count, desc=f"cache-{split}")):
            sensor = row.satellite_target
            observations = observation_names(row.last_30_minutes_observation_filename)
            images[index] = 0
            frame_mask[index] = 0
            band_mask[index] = 0
            for frame, filename in enumerate(observations):
                image, available_bands = _read_input(handle, archive_path_for_observation(sensor, filename), image_size, cache_dtype_np)
                images[index, frame] = image
                band_mask[index, frame] = available_bands
            # Missing late observations are represented by an explicit mask. Their
            # image slot repeats the latest valid image only to keep arrays dense;
            # the model zeros masked frames before temporal fusion.
            for frame in range(len(observations), 3):
                if observations:
                    images[index, frame] = images[index, len(observations) - 1]
                    band_mask[index, frame] = band_mask[index, len(observations) - 1]
            frame_mask[index, : len(observations)] = 1
            sensors[index] = SENSOR_TO_ID[sensor]
            if targets is not None:
                targets[index] = _read_target(handle, f"{target_dir_for_split(split)}/{row.gpm_imerg_filename}", target_size)

    metadata[:] = metadata_values
    images.flush(); metadata.flush(); sensors.flush(); frame_mask.flush(); band_mask.flush()
    if targets is not None:
        targets.flush()
    manifest.to_csv(paths["manifest"], index=False)
    info = {"split": split, "count": count, "image_size": image_size, "target_size": target_size, "frames": 3, "bands": 16, "has_targets": split == "train", "cache_dtype": cache_dtype_np.name, "metadata_dim": int(metadata_values.shape[1])}
    write_json(paths["meta"], info)
    return info


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a compact memmap cache from a Solafune archive.")
    parser.add_argument("--archive", required=True)
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--split", choices=("train", "test"), required=True)
    parser.add_argument("--image-size", type=int, default=128)
    parser.add_argument("--target-size", type=int, default=41)
    parser.add_argument("--cache-dtype", default="uint8", choices=("uint8", "float16", "float32"))
    parser.add_argument("--max-samples", type=int, help="Optional smoke-test cache size")
    parser.add_argument("--skip-verify", action="store_true")
    args = parser.parse_args()
    build_cache(args.archive, args.cache_dir, args.split, image_size=args.image_size, target_size=args.target_size, cache_dtype=args.cache_dtype, verify=not args.skip_verify, max_samples=args.max_samples)


if __name__ == "__main__":
    main()
