# Reproducing ThoraxLens

All commands run from the `pipeline` folder with `C:\Users\sndps\AppData\Local\Programs\Python\Python311\python.exe` (Python 3.11, torch 2.12 + cu130, timm 1.0.27).
Settings are environment variables, so the original 224 px runs keep their file names.

## 1. Data and caches (Git Bash syntax; the chain_*.sh scripts show the same variables)

```
python prepare_splits.py                          # patient-level split -> outputs/splits.csv
CXR_IMG=224 python cache_images.py                # outputs/images_224.npy  (5.3 GB)
CXR_IMG=320 python cache_images.py                # outputs/images_320.npy  (11 GB)
```

## 2. Training (resumable; re-run the same command to continue)

```
# 224 px models (no EMA)
CXR_ARCH=densenet121 python train.py
CXR_ARCH=convnext_tiny.fb_in22k_ft_in1k python train.py
CXR_ARCH=coatnet_0_rw_224.sw_in1k python train.py

# 320 px models (EMA, micro-batch 16 x 2 accumulation)
CXR_IMG=320 CXR_EMA=0.999 CXR_BATCH=16 CXR_ACCUM=2 CXR_ARCH=densenet121 CXR_EPOCHS=5 python train.py
CXR_IMG=320 CXR_EMA=0.999 CXR_BATCH=16 CXR_ACCUM=2 CXR_ARCH=convnext_tiny.fb_in22k_ft_in1k CXR_EPOCHS=4 CXR_PIN=0 python train.py
# add CXR_SEED=7 for the seed-repeat runs (see chain_seeds.sh)
```

## 3. Ensemble and validation

```
python ensemble2.py densenet121 convnext_tiny.fb_in22k_ft_in1k coatnet_0_rw_224.sw_in1k densenet121@320 convnext_tiny.fb_in22k_ft_in1k@320
python baseline_preds.py        # no-TTA 224 baseline test predictions (for the paired comparison)
python validate_stats.py        # integrity, bootstrap CIs, weight stability, calibration, AUPRC, subgroups
python validate_predict.py      # predict.py vs cached ensemble
```

`ensemble2.py` overwrites `outputs/ensemble_v2_report.txt` and `test_auroc_ensemble_v2.csv`; the final ones are kept as `*_5model` copies.
Spec syntax: `arch[@img][#seed]`, for example `densenet121@320#7`.

## 4. Inference and app

```
python predict.py image1.png image2.png --out preds.csv
python ui/build_ui_data.py      # rebuild UI metrics and samples from cached predictions
python ui/server.py             # web app at http://127.0.0.1:8000
python cleanup.py               # dry run of the safe cleanup (add --apply)
```

## 5. File map

| Path | What it is |
| --- | --- |
| `common.py`, `train.py`, `evaluate.py` | Models, EMA, TTA, GPU augmentation; resumable training; plain test evaluation |
| `ensemble2.py`, `predict.py` | Ensemble with validation-chosen TTA and weights; inference on raw images |
| `validate_stats.py`, `validate_predict.py`, `baseline_preds.py` | Validation checks |
| `ui/` | Web app (`server.py`, `static/`, `data/`, `README.md`) |
| `cleanup.py` | Safe, dry-run-by-default cleanup |
| `outputs/checkpoints*/best.pt` | Best (EMA) weights per model; never deleted by cleanup |
| `outputs/preds/` | Cached validation and test predictions |
| `outputs/validation/` | Validation report and logs (`VALIDATION_REPORT.md`) |
| `outputs/images_224.npy`, `images_320.npy` | Rebuildable uint8 image caches |
| `context.md` | Full project notes and history |
