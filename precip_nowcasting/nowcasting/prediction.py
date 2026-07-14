from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

from .cache import Cache
from .config import load_config
from .dataset import NowcastingDataset
from .models import build_model
from .submission import audit_submission, write_submission


def load_checkpoint(path: str | Path, device: torch.device) -> tuple[torch.nn.Module, dict]:
    checkpoint = torch.load(path, map_location=device, weights_only=False)
    model = build_model(checkpoint["config"]).to(device)
    model.load_state_dict(checkpoint["model"])
    model.eval()
    return model, checkpoint


@torch.no_grad()
def predict(cache: Cache, checkpoints: list[str | Path], *, weights: np.ndarray | None = None, batch_size: int = 8, workers: int = 2) -> tuple[np.ndarray, np.ndarray]:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    models, normalizers = [], []
    for checkpoint_path in checkpoints:
        model, _ = load_checkpoint(checkpoint_path, device)
        values = np.load(Path(checkpoint_path).with_name("normalizer.npz"))
        models.append(model); normalizers.append((values["mean"], values["std"]))
    if not models:
        raise ValueError("At least one checkpoint is required")
    # Each checkpoint can have fold-specific normalization; build one loader per model.
    all_predictions = []
    indices = np.arange(cache.count)
    for model, (mean, std) in zip(models, normalizers):
        dataset = NowcastingDataset(cache, indices, mean, std, with_targets=False)
        loader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=workers, pin_memory=device.type == "cuda")
        batches = []
        for batch in loader:
            batches.append(model(
                batch["image"].to(device), batch["metadata"].to(device), batch["sensor"].to(device),
                batch["frame_mask"].to(device), batch["band_mask"].to(device),
            ).cpu().numpy())
        all_predictions.append(np.concatenate(batches, axis=0))
    if weights is None:
        weights = np.full(len(all_predictions), 1.0 / len(all_predictions), dtype=np.float32)
    weights = np.asarray(weights, dtype=np.float32)
    if weights.shape != (len(all_predictions),) or np.any(weights < 0) or not np.isclose(weights.sum(), 1.0, atol=1e-5):
        raise ValueError("Ensemble weights must be nonnegative, sum to 1, and match checkpoints")
    return np.tensordot(weights, np.stack(all_predictions), axes=(0, 0)).astype(np.float32), cache.manifest["unique_id"].astype(str).to_numpy()


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict cached evaluation data and produce an audited submission ZIP.")
    parser.add_argument("--config", default="configs/base.yaml")
    parser.add_argument("--checkpoints", nargs="+", required=True)
    parser.add_argument("--output", required=True, help="Prediction .npz path")
    parser.add_argument("--submission", help="Optional final submission ZIP path")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--weights", help="Optional .npz produced by fit_ensemble.py")
    args = parser.parse_args()
    config = load_config(args.config)
    cache = Cache(config["paths"]["cache_dir"], "test")
    weights = np.load(args.weights)["weights"] if args.weights else None
    prediction_values, unique_ids = predict(cache, args.checkpoints, weights=weights, batch_size=args.batch_size, workers=args.workers)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.output, predictions=prediction_values, unique_ids=unique_ids)
    if args.submission:
        output = write_submission(prediction_values, unique_ids, evaluation_zip=config["paths"]["evaluation_zip"], sample_submission_zip=config["paths"]["sample_submission_zip"], output_zip=args.submission)
        print(audit_submission(output, config["paths"]["evaluation_zip"]))


if __name__ == "__main__":
    main()
