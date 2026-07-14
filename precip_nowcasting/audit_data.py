"""Read-only audit of source TIFF contracts and cached training inputs."""
import argparse
import json
import zipfile

import numpy as np

from nowcasting.cache import Cache
from nowcasting.io import archive_path_for_observation, observation_names, validate_archive


def raw_summary(archive: str, split: str, cache: Cache) -> dict:
    import rasterio
    from rasterio.io import MemoryFile

    manifest = validate_archive(archive, split, check_tiffs=True)
    result = {"rows": len(manifest), "cache": cache.info, "sensors": {}, "missing_frames": {}}
    with zipfile.ZipFile(archive) as handle:
        for sensor, group in manifest.groupby("satellite_target"):
            sample = group.iloc[0]
            name = observation_names(sample.last_30_minutes_observation_filename)[-1]
            with MemoryFile(handle.read(archive_path_for_observation(sensor, name))) as memory:
                with memory.open() as dataset:
                    values = dataset.read()
                    result["sensors"][sensor] = {
                        "rows": int(len(group)), "bands": int(dataset.count), "shape": [int(dataset.height), int(dataset.width)],
                        "dtype": dataset.dtypes[0], "crs": str(dataset.crs), "transform": tuple(dataset.transform),
                        "range": [float(np.nanmin(values)), float(np.nanmax(values))],
                    }
        available = np.asarray(cache.frame_mask).sum(axis=1)
        result["missing_frames"] = {str(count): int((available == count).sum()) for count in range(4)}
        result["cache_band_mask_missing"] = int((np.asarray(cache.band_mask) == 0).sum())
    return result


parser = argparse.ArgumentParser(description="Audit a Solafune archive/cache without extracting data.")
parser.add_argument("--archive", required=True)
parser.add_argument("--cache-dir", required=True)
parser.add_argument("--split", choices=("train", "test"), required=True)
parser.add_argument("--output")
args = parser.parse_args()
report = raw_summary(args.archive, args.split, Cache(args.cache_dir, args.split))
encoded = json.dumps(report, indent=2)
if args.output:
    open(args.output, "w", encoding="utf-8").write(encoded)
print(encoded)
