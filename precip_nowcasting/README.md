# Solafune precipitation nowcasting

This isolated package predicts 41x41 GPM-IMERG precipitation tiles from up to
three preceding 16-band geostationary satellite frames. It uses only the supplied
competition archives. The existing workspace application is intentionally not
used or modified.

## Setup

Create a Python 3.10+ environment with CUDA-compatible PyTorch, then install:

```powershell
cd precip_nowcasting
python -m pip install -r requirements.txt
```

Update `configs/base.yaml` if the supplied archives or artifact drive are in a
different location. Keep all data and derived cache artifacts outside version
control. The cache is approximately 32 GB for 40,686 train samples and 23 GB
for 29,090 evaluation samples at 128x128 uint8.

## Reproducible workflow

```powershell
python preprocess_train.py --archive C:/Users/shobh/Downloads/train_dataset_b1c74968f2f24eaeb2852b47b80a581e.zip --cache-dir artifacts/cache --image-size 128
python preprocess_test.py --archive C:/Users/shobh/Downloads/evaluation_dataset_ba14cc1598034cc689eaf39b4f80c09d.zip --cache-dir artifacts/cache --image-size 128

# Optional TIFF-decoding smoke test; use a separate cache because it is intentionally incomplete.
python preprocess_train.py --archive C:/Users/shobh/Downloads/train_dataset_b1c74968f2f24eaeb2852b47b80a581e.zip --cache-dir artifacts/smoke-cache --image-size 128 --max-samples 64

# Run this only after the complete train cache above exists.
python audit_data.py --archive C:/Users/shobh/Downloads/train_dataset_b1c74968f2f24eaeb2852b47b80a581e.zip --cache-dir artifacts/cache --split train
python train.py --config configs/spectral_smoke.yaml --fold 0 --max-samples 64
python train.py --config configs/spectral_motion.yaml --fold 0

# Repeat folds 0..4. Train selected model(s) on all rows only after OOF selection.
python evaluate_oof.py --runs artifacts/experiments/fold0 artifacts/experiments/fold1 artifacts/experiments/fold2 artifacts/experiments/fold3 artifacts/experiments/fold4 --output artifacts/experiments/temporal-oof.json

# The inexpensive selection stage is always sequential and uses the fixed 0/2/4 folds.
python screen_experiment.py --config configs/spectral_motion.yaml --run-prefix motion-screen --baseline-runs artifacts/experiments/temporal-fold0 artifacts/experiments/temporal-fold2 artifacts/experiments/temporal-fold4 --output artifacts/experiments/motion-screen.json

# Finalist stress test: run each named location independently, then aggregate.
python train.py --config configs/spectral_motion.yaml --fold location:aceh --run-id lolo-aceh
python evaluate_lolo.py --runs artifacts/experiments/lolo-aceh [...one run per location...] --output artifacts/experiments/lolo.json

# Compare a second complete candidate or fit a validated ensemble from two complete OOF sets.
python fit_ensemble.py --candidate artifacts/experiments/a0 artifacts/experiments/a1 artifacts/experiments/a2 artifacts/experiments/a3 artifacts/experiments/a4 --candidate artifacts/experiments/b0 artifacts/experiments/b1 artifacts/experiments/b2 artifacts/experiments/b3 artifacts/experiments/b4 --output artifacts/experiments/ensemble_weights.npz

python train.py --config configs/base.yaml --fold all --run-id temporal-final-seed1
python predict.py --config configs/base.yaml --checkpoints artifacts/experiments/temporal-final-seed1/best.pt --output artifacts/submissions/predictions.npz --submission artifacts/submissions/final.zip
python audit_submission.py --submission artifacts/submissions/final.zip --evaluation-zip C:/Users/shobh/Downloads/evaluation_dataset_ba14cc1598034cc689eaf39b4f80c09d.zip
```

`preprocess_train.py` and `preprocess_test.py` are separate as required by the
competition. The cache keeps imagery as uint8 and calculates normalizers only
from a fold's training locations at training time. This prevents a validation
location from affecting feature scaling. Records with fewer than three input
frames are represented by a frame-availability mask; masked slots never enter
temporal fusion. A small number of supplied frames have fewer than 16 bands;
their unavailable trailing channels are neutral-padded with a per-band mask.
The main `spectral_motion` model receives those masks directly, uses the known
physical band-group ordering of every sensor, aligns earlier features to the
latest observation, and estimates occurrence and conditional intensity
separately. `spectral_simvp` is a no-warp temporal alternative for validated
ensemble diversity.

## Experiment policy

- The only model-selection score is sensor-weighted, location-held-out OOF
  RMSE. Random sample splits are prohibited.
- Retain a change only when it gains at least 0.002 RMSE and a paired,
  location-bootstrap confidence interval supports it; inspect per-sensor RMSE
  before accepting it.
- The optional `pretrained_resnet18` configuration is a benchmark branch only.
  Record its license, source, checksum, and OOF outcome in `THIRD_PARTY.md`
  before it can be a finalist.
- Do not use external raw data. Do not submit more than one or two qualified
  submissions per day. Delete competition data and derived caches when the
  event ends, as required by the rules.

Configuration variants inherit from `configs/base.yaml`: `latest_unet.yaml`
is the latest-frame baseline, `pretrained_resnet18.yaml` is the documented
weight benchmark, and `smoke.yaml` validates the GPU training path quickly.

## Submission contract

The writer copies `evaluation_target.csv`, uses the provided sample TIFFs as
templates, writes finite nonnegative Float32 41x41 predictions, and archives
only the required root-level `evaluation_target.csv` and `test_files/` entries.
The auditor checks that contract before upload.
