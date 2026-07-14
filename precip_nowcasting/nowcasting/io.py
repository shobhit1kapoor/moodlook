from __future__ import annotations

import ast
import io
import json
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd

SENSORS = ("goes", "himawari", "meteosat")
SENSOR_TO_ID = {name: index for index, name in enumerate(SENSORS)}

# Physical channel groups, ordered to make the three supplied instruments
# comparable without pretending that their radiometry is identical.  The first
# two instruments follow ABI/AHI's closely aligned 16-band order.  FCI uses
# the names documented by the competition: five VIS, three NIR/SWIR, two WV,
# then six thermal IR channels.
SPECTRAL_GROUP_NAMES = ("visible", "near_ir", "shortwave_ir", "water_vapor", "thermal_ir")
SPECTRAL_GROUPS = {
    "goes": (0, 0, 0, 1, 1, 2, 2, 3, 3, 3, 4, 4, 4, 4, 4, 4),
    "himawari": (0, 0, 0, 1, 1, 2, 2, 3, 3, 3, 4, 4, 4, 4, 4, 4),
    "meteosat": (0, 0, 0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 4, 4, 4),
}


def csv_name_for_split(split: str) -> str:
    return "train_dataset.csv" if split == "train" else "evaluation_target.csv"


def target_dir_for_split(split: str) -> str:
    return "gpm_imerg" if split == "train" else "test_files"


def load_manifest(archive: str | Path, split: str) -> pd.DataFrame:
    with zipfile.ZipFile(archive) as handle:
        frame = pd.read_csv(handle.open(csv_name_for_split(split)))
    required = {"unique_id", "name_location", "satellite_target", "datetime", "last_30_minutes_observation_filename", "gpm_imerg_filename"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Manifest is missing columns: {sorted(missing)}")
    frame["satellite_target"] = frame["satellite_target"].astype(str).str.lower()
    if not set(frame["satellite_target"]).issubset(SENSOR_TO_ID):
        raise ValueError("Unknown satellite target found")
    frame["datetime"] = pd.to_datetime(frame["datetime"], utc=False)
    return frame


def observation_names(value: str) -> list[str]:
    names = ast.literal_eval(value)
    if not isinstance(names, list) or not 0 <= len(names) <= 3 or not all(isinstance(name, str) for name in names):
        raise ValueError(f"Expected zero to three observation filenames, got {value!r}")
    return names


def archive_path_for_observation(sensor: str, filename: str) -> str:
    return f"{sensor}/{filename}"


def validate_archive(archive: str | Path, split: str, *, check_tiffs: bool = False) -> pd.DataFrame:
    """Validate manifest-to-archive references without extracting competition data."""
    manifest = load_manifest(archive, split)
    with zipfile.ZipFile(archive) as handle:
        names = set(handle.namelist())
        missing: list[str] = []
        for row in manifest.itertuples(index=False):
            for observation in observation_names(row.last_30_minutes_observation_filename):
                path = archive_path_for_observation(row.satellite_target, observation)
                if path not in names:
                    missing.append(path)
            if split == "train":
                target = f"gpm_imerg/{row.gpm_imerg_filename}"
                if target not in names:
                    missing.append(target)
        if missing:
            raise FileNotFoundError(f"Archive has {len(missing)} missing manifest references; first: {missing[:5]}")
        if check_tiffs:
            import rasterio
            from rasterio.io import MemoryFile
            row = manifest.iloc[0]
            input_path = archive_path_for_observation(row.satellite_target, observation_names(row.last_30_minutes_observation_filename)[0])
            with MemoryFile(handle.read(input_path)) as memory:
                with memory.open() as dataset:
                    if not 1 <= dataset.count <= 16:
                        raise ValueError(f"Expected 1-16 bands, found {dataset.count}")
            if split == "train":
                with MemoryFile(handle.read(f"gpm_imerg/{row.gpm_imerg_filename}")) as memory:
                    with memory.open() as dataset:
                        if (dataset.count, dataset.height, dataset.width) != (1, 41, 41):
                            raise ValueError("Unexpected target TIFF shape")
    return manifest


def encode_metadata(manifest: pd.DataFrame) -> np.ndarray:
    timestamps = pd.to_datetime(manifest["datetime"])
    hour = timestamps.dt.hour.to_numpy() + timestamps.dt.minute.to_numpy() / 60.0
    day = timestamps.dt.dayofyear.to_numpy()
    hour_phase = 2 * np.pi * hour / 24
    day_phase = 2 * np.pi * day / 366
    return np.stack(
        [
            np.sin(hour_phase), np.cos(hour_phase), np.sin(day_phase), np.cos(day_phase),
            np.sin(2 * hour_phase), np.cos(2 * hour_phase), np.sin(2 * day_phase), np.cos(2 * day_phase),
        ], axis=1,
    ).astype(np.float32)


def expand_metadata(values: np.ndarray) -> np.ndarray:
    """Upgrade legacy four-feature caches without needing to recache imagery."""
    values = np.asarray(values, dtype=np.float32)
    if values.shape[-1] == 8:
        return values
    if values.shape[-1] != 4:
        raise ValueError(f"Expected 4 or 8 time features, got {values.shape}")
    hour_sin, hour_cos, day_sin, day_cos = np.moveaxis(values, -1, 0)
    return np.stack(
        [hour_sin, hour_cos, day_sin, day_cos,
         2 * hour_sin * hour_cos, np.square(hour_cos) - np.square(hour_sin),
         2 * day_sin * day_cos, np.square(day_cos) - np.square(day_sin)], axis=-1,
    ).astype(np.float32)


def write_json(path: str | Path, data: dict) -> None:
    Path(path).write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
