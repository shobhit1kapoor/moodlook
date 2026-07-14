from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import subprocess
import time

import numpy as np
import pandas as pd
import torch
from torch.nn import functional as F
from torch.utils.data import DataLoader, WeightedRandomSampler

from .cache import Cache, fold_normalizer
from .config import config_hash, ensure_dirs, load_config
from .dataset import NowcastingDataset
from .metrics import sensor_weighted_rmse
from .models import build_model
from .splits import materialize_folds


def set_seed(seed: int) -> None:
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = True


def git_revision() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "unknown"


def model_forward(model: torch.nn.Module, batch: dict, device: torch.device, *, return_aux: bool = False):
    return model(
        batch["image"].to(device, non_blocking=True),
        batch["metadata"].to(device, non_blocking=True),
        batch["sensor"].to(device, non_blocking=True),
        batch["frame_mask"].to(device, non_blocking=True),
        batch["band_mask"].to(device, non_blocking=True),
        return_aux=return_aux,
    )


def loss_function(prediction: torch.Tensor, target: torch.Tensor, config: dict, *, sensor: torch.Tensor | None = None, sensor_loss_weights: torch.Tensor | None = None, aux: dict | None = None, image: torch.Tensor | None = None, band_mask: torch.Tensor | None = None, future_image: torch.Tensor | None = None, future_band_mask: torch.Tensor | None = None) -> torch.Tensor:
    training = config["training"]
    sample_weights = sensor_loss_weights[sensor] if sensor is not None and sensor_loss_weights is not None else torch.ones(prediction.shape[0], device=prediction.device, dtype=prediction.dtype)
    def weighted_mean(value: torch.Tensor) -> torch.Tensor:
        return (value.reshape(value.shape[0], -1).mean(dim=1) * sample_weights).mean()
    loss = weighted_mean((prediction - target).square())
    if float(training.get("log_loss_weight", 0.0)):
        loss = loss + float(training["log_loss_weight"]) * weighted_mean((torch.log1p(prediction) - torch.log1p(target)).square())
    if float(training.get("occurrence_loss_weight", 0.0)):
        occurrence = (target > 0).float()
        if aux and "occurrence_logits" in aux:
            occurrence_loss = weighted_mean(F.binary_cross_entropy_with_logits(aux["occurrence_logits"], occurrence, reduction="none"))
        else:
            probability = 1.0 - torch.exp(-prediction.clamp(max=20))
            occurrence_loss = weighted_mean(F.binary_cross_entropy(probability.clamp(1e-5, 1 - 1e-5), occurrence, reduction="none"))
        loss = loss + float(training["occurrence_loss_weight"]) * occurrence_loss
    if float(training.get("self_supervised_weight", 0.0)):
        if not (aux and "reconstruction" in aux and image is not None and band_mask is not None):
            raise ValueError("self_supervised_weight requires a model with reconstruction output")
        valid = band_mask[:, 2, :, None, None]
        reconstruction_error = (aux["reconstruction"] - image[:, 2]).square() * valid
        loss = loss + float(training["self_supervised_weight"]) * weighted_mean(reconstruction_error)
    if float(training.get("future_satellite_weight", 0.0)):
        if not (aux and "future_satellite" in aux and image is not None and band_mask is not None):
            raise ValueError("future_satellite_weight requires future-satellite model output and dataset targets")
        if future_image is None or future_band_mask is None:
            raise ValueError("future satellite targets were not supplied to the loss")
        valid = future_band_mask[:, :, None, None]
        satellite_loss = F.smooth_l1_loss(aux["future_satellite"], future_image, reduction="none") * valid
        loss = loss + float(training["future_satellite_weight"]) * weighted_mean(satellite_loss)
    return loss


@torch.no_grad()
def evaluate(model: torch.nn.Module, loader: DataLoader, device: torch.device, weights: dict[str, float]) -> dict:
    model.eval()
    squared = {0: 0.0, 1: 0.0, 2: 0.0}
    counts = {0: 0, 1: 0, 2: 0}
    for batch in loader:
        sensor = batch["sensor"].to(device, non_blocking=True)
        target = batch["target"].to(device, non_blocking=True)
        prediction = model_forward(model, batch, device)
        errors = (prediction - target).square()
        for sensor_id in range(3):
            selection = sensor == sensor_id
            if selection.any():
                squared[sensor_id] += float(errors[selection].sum().item())
                counts[sensor_id] += int(errors[selection].numel())
    names = ("goes", "himawari", "meteosat")
    sensor_mse = {names[key]: squared[key] / counts[key] for key in squared if counts[key]}
    result = {"sensor_mse": sensor_mse, "sensor_rmse": {key: float(np.sqrt(value)) for key, value in sensor_mse.items()}}
    result["weighted_rmse"] = sensor_weighted_rmse(sensor_mse, weights)
    return result


@torch.no_grad()
def save_oof(model: torch.nn.Module, dataset: NowcastingDataset, cache: Cache, device: torch.device, destination: Path, batch_size: int, workers: int) -> None:
    """Persist aligned OOF arrays used for all selection and stacking decisions."""
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=workers, pin_memory=device.type == "cuda")
    model.eval(); predictions = []; targets = []; indices = []
    for batch in loader:
        predictions.append(model_forward(model, batch, device).cpu().numpy())
        targets.append(batch["target"].numpy())
        indices.append(batch["index"].numpy())
    index = np.concatenate(indices)
    np.savez_compressed(
        destination,
        unique_ids=np.asarray(cache.manifest.iloc[index]["unique_id"].astype(str).tolist(), dtype=np.str_),
        locations=np.asarray(cache.manifest.iloc[index]["name_location"].astype(str).tolist(), dtype=np.str_),
        sensors=np.asarray(cache.manifest.iloc[index]["satellite_target"].astype(str).tolist(), dtype=np.str_),
        predictions=np.concatenate(predictions).astype(np.float32),
        targets=np.concatenate(targets).astype(np.float32),
    )


def train(config: dict, fold: str, run_id: str | None = None, max_samples: int | None = None) -> Path:
    ensure_dirs(config); set_seed(int(config["training"]["seed"]))
    cache = Cache(config["paths"]["cache_dir"], "train")
    folds_path = Path(config["paths"]["cache_dir"]) / "train" / "folds.csv"
    if not folds_path.exists():
        materialize_folds(cache.manifest, cache.targets, folds_path, folds=int(config["split"]["folds"]), seed=int(config["split"]["seed"]))
    assignments = pd.read_csv(folds_path).set_index("unique_id")["fold"]
    assigned = cache.manifest["unique_id"].map(assignments).to_numpy(dtype=int)
    if fold == "all":
        train_indices = np.arange(cache.count)
        validation_indices = np.array([], dtype=np.int64)
    elif fold.startswith("location:"):
        location = fold.split(":", 1)[1]
        validation_indices = np.flatnonzero(cache.manifest["name_location"].to_numpy() == location)
        if not len(validation_indices):
            raise ValueError(f"Unknown location for LOLO validation: {location}")
        train_indices = np.flatnonzero(cache.manifest["name_location"].to_numpy() != location)
    else:
        validation_indices = np.flatnonzero(assigned == int(fold))
        train_indices = np.flatnonzero(assigned != int(fold))
    if max_samples:
        generator = np.random.default_rng(int(config["training"]["seed"]))
        train_indices = generator.choice(train_indices, size=min(max_samples, len(train_indices)), replace=False)
        validation_indices = generator.choice(validation_indices, size=min(max_samples, len(validation_indices)), replace=False) if len(validation_indices) else validation_indices
    train_locations = set(cache.manifest.iloc[train_indices]["name_location"])
    validation_locations = set(cache.manifest.iloc[validation_indices]["name_location"])
    if train_locations & validation_locations:
        raise AssertionError("Location leakage in fold split")
    mean, std = fold_normalizer(cache, train_indices, max_samples_per_sensor=int(config["training"]["normalization_samples_per_sensor"]), seed=int(config["training"]["seed"]))
    train_dataset = NowcastingDataset(cache, train_indices, mean, std, with_targets=True, augment=bool(config["training"].get("flip_augmentation", False)), with_future_frame=float(config["training"].get("future_satellite_weight", 0.0)) > 0)
    valid_dataset = NowcastingDataset(cache, validation_indices, mean, std, with_targets=True) if len(validation_indices) else None
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    loader_args = {"batch_size": int(config["training"]["batch_size"]), "num_workers": int(config["training"]["num_workers"]), "pin_memory": device.type == "cuda"}
    observed = np.bincount(np.asarray(cache.sensors[train_indices]), minlength=3).astype(np.float64)
    observed /= observed.sum()
    desired = np.array([config["split"]["sensor_weights"][name] for name in ("goes", "himawari", "meteosat")], dtype=np.float64)
    sensor_loss_weights = desired / np.maximum(observed, 1e-12)
    sensor_loss_weights /= np.dot(observed, sensor_loss_weights)
    sensor_loss_weights_tensor = torch.as_tensor(sensor_loss_weights, device=device, dtype=torch.float32) if bool(config["training"].get("sensor_weighted_loss", False)) else None
    heavy_rain_power = float(config["training"].get("heavy_rain_sampling_power", 0.0))
    location_balanced = bool(config["training"].get("location_balanced_sampling", False))
    if heavy_rain_power > 0 or location_balanced:
        weights = np.ones(len(train_indices), dtype=np.float64)
        if location_balanced:
            locations = cache.manifest.iloc[train_indices]["name_location"].to_numpy()
            _, inverse = np.unique(locations, return_inverse=True)
            counts = np.bincount(inverse)
            weights *= 1.0 / counts[inverse]
        energy = np.asarray(cache.targets[train_indices], dtype=np.float32).mean(axis=(1, 2))
        if heavy_rain_power > 0:
            weights *= 1.0 + np.power(energy / max(float(np.quantile(energy, 0.9)), 1e-6), heavy_rain_power)
        sampler = WeightedRandomSampler(torch.as_tensor(weights, dtype=torch.double), num_samples=len(weights), replacement=True, generator=torch.Generator().manual_seed(int(config["training"]["seed"])))
        train_loader = DataLoader(train_dataset, sampler=sampler, shuffle=False, **loader_args)
    else:
        train_loader = DataLoader(train_dataset, shuffle=True, generator=torch.Generator().manual_seed(int(config["training"]["seed"])), **loader_args)
    valid_loader = DataLoader(valid_dataset, shuffle=False, **loader_args) if valid_dataset else None
    model = build_model(config).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=float(config["training"]["lr"]), weight_decay=float(config["training"]["weight_decay"]))
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=int(config["training"]["epochs"]))
    use_amp = bool(config["training"]["amp"]) and device.type == "cuda"
    scaler = torch.cuda.amp.GradScaler(enabled=use_amp)
    run_id = run_id or f"{config['model']['name']}-fold{fold}-{config_hash(config)}-{int(time.time())}"
    run_dir = Path(config["paths"]["experiments_dir"]) / run_id; run_dir.mkdir(parents=True, exist_ok=False)
    provenance = {
        "git_revision": git_revision(), "device": str(device), "torch": torch.__version__,
        "cuda": torch.version.cuda, "gpu_name": torch.cuda.get_device_name(0) if device.type == "cuda" else None,
        "seed": int(config["training"]["seed"]), "config_hash": config_hash(config), "started_at": time.time(), "sensor_loss_weights": sensor_loss_weights.tolist(),
    }
    (run_dir / "config.json").write_text(json.dumps(config, indent=2, sort_keys=True), encoding="utf-8")
    (run_dir / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True), encoding="utf-8")
    np.savez(run_dir / "normalizer.npz", mean=mean, std=std)
    best_score, stale, history = float("inf"), 0, []
    for epoch in range(1, int(config["training"]["epochs"]) + 1):
        model.train(); running, seen = 0.0, 0
        optimizer.zero_grad(set_to_none=True)
        for step, batch in enumerate(train_loader, start=1):
            image = batch["image"].to(device, non_blocking=True); target = batch["target"].to(device, non_blocking=True)
            with torch.autocast(device_type=device.type, enabled=use_amp):
                prediction, aux = model_forward(model, batch, device, return_aux=True)
                future_image = batch["future_image"].to(device, non_blocking=True) if "future_image" in batch else None
                future_band_mask = batch["future_band_mask"].to(device, non_blocking=True) if "future_band_mask" in batch else None
                loss = loss_function(prediction, target, config, sensor=batch["sensor"].to(device, non_blocking=True), sensor_loss_weights=sensor_loss_weights_tensor, aux=aux, image=image, band_mask=batch["band_mask"].to(device, non_blocking=True), future_image=future_image, future_band_mask=future_band_mask) / int(config["training"]["grad_accumulation"])
            scaler.scale(loss).backward()
            if step % int(config["training"]["grad_accumulation"]) == 0 or step == len(train_loader):
                scaler.step(optimizer); scaler.update(); optimizer.zero_grad(set_to_none=True)
            running += float(loss.item()) * int(config["training"]["grad_accumulation"]) * image.shape[0]; seen += image.shape[0]
        scheduler.step()
        report = {"epoch": epoch, "train_loss": running / max(seen, 1), "learning_rate": optimizer.param_groups[0]["lr"]}
        if valid_loader:
            report.update(evaluate(model, valid_loader, device, config["split"]["sensor_weights"]))
            score = report["weighted_rmse"]
        else:
            score = report["train_loss"]
        history.append(report)
        if score < best_score:
            best_score, stale = score, 0
            torch.save({"model": model.state_dict(), "config": config, "fold": fold, "run_id": run_id, "best_score": best_score, "git_revision": git_revision()}, run_dir / "best.pt")
        else:
            stale += 1
        (run_dir / "metrics.json").write_text(json.dumps({"best_score": best_score, "history": history, "fold": fold, "train_locations": sorted(train_locations), "validation_locations": sorted(validation_locations), "git_revision": git_revision()}, indent=2), encoding="utf-8")
        if valid_loader and stale >= int(config["training"]["early_stopping_patience"]):
            break
    if valid_dataset:
        checkpoint = torch.load(run_dir / "best.pt", map_location=device, weights_only=False)
        model.load_state_dict(checkpoint["model"])
        save_oof(model, valid_dataset, cache, device, run_dir / "oof.npz", int(config["training"]["batch_size"]), int(config["training"]["num_workers"]))
    return run_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a fold-safe nowcasting model.")
    parser.add_argument("--config", default="configs/base.yaml")
    parser.add_argument("--fold", default="0", help="0-4 for OOF training, or 'all' for final training")
    parser.add_argument("--run-id")
    parser.add_argument("--max-samples", type=int, help="Small deterministic smoke-run cap")
    args = parser.parse_args()
    result = train(load_config(args.config), args.fold, args.run_id, args.max_samples)
    print(result)


if __name__ == "__main__":
    main()
