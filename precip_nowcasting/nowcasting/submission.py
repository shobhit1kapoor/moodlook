from __future__ import annotations

from pathlib import Path
import tempfile
import zipfile

import numpy as np

from .io import load_manifest


def write_submission(predictions: np.ndarray, unique_ids: np.ndarray, *, evaluation_zip: str | Path, sample_submission_zip: str | Path, output_zip: str | Path) -> Path:
    """Write exact competition layout using every provided sample TIFF as template."""
    import rasterio
    from rasterio.io import MemoryFile

    manifest = load_manifest(evaluation_zip, "test")
    lookup = {str(identifier): np.asarray(predictions[index], dtype=np.float32) for index, identifier in enumerate(unique_ids)}
    expected = manifest["unique_id"].astype(str).tolist()
    if set(lookup) != set(expected) or len(lookup) != len(expected):
        raise ValueError("Predictions must contain each evaluation unique_id exactly once")
    output_zip = Path(output_zip); output_zip.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="solafune_submission_") as temp:
        root = Path(temp)
        (root / "test_files").mkdir()
        with zipfile.ZipFile(evaluation_zip) as evaluation, zipfile.ZipFile(sample_submission_zip) as sample:
            (root / "evaluation_target.csv").write_bytes(evaluation.read("evaluation_target.csv"))
            for row in manifest.itertuples(index=False):
                array = lookup[str(row.unique_id)]
                if array.shape != (41, 41) or not np.isfinite(array).all():
                    raise ValueError(f"Invalid prediction for {row.unique_id}")
                template = sample.read(f"test_files/{row.gpm_imerg_filename}")
                with MemoryFile(template) as source_memory:
                    with source_memory.open() as source:
                        profile = source.profile.copy()
                profile.update(driver="GTiff", count=1, dtype="float32", height=41, width=41)
                with rasterio.open(root / "test_files" / row.gpm_imerg_filename, "w", **profile) as destination:
                    destination.write(np.maximum(array, 0.0)[None].astype(np.float32))
        with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=4) as destination:
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    destination.write(path, path.relative_to(root).as_posix())
    return output_zip


def audit_submission(submission_zip: str | Path, evaluation_zip: str | Path) -> dict:
    """Check the upload layout and raster contract before leaderboard submission."""
    import rasterio
    from rasterio.io import MemoryFile

    manifest = load_manifest(evaluation_zip, "test")
    expected_files = {"evaluation_target.csv"} | {f"test_files/{name}" for name in manifest["gpm_imerg_filename"]}
    with zipfile.ZipFile(submission_zip) as submitted:
        actual = {item for item in submitted.namelist() if not item.endswith("/")}
        if actual != expected_files:
            raise ValueError(f"Submission file set differs; missing={len(expected_files - actual)}, extra={len(actual - expected_files)}")
        for filename in manifest["gpm_imerg_filename"]:
            with MemoryFile(submitted.read(f"test_files/{filename}")) as memory:
                with memory.open() as dataset:
                    array = dataset.read(1)
                    if array.shape != (41, 41) or dataset.count != 1 or array.dtype != np.float32 or not np.isfinite(array).all() or np.any(array < 0):
                        raise ValueError(f"Invalid TIFF: {filename}")
    return {"files": len(expected_files), "rows": len(manifest), "valid": True}
