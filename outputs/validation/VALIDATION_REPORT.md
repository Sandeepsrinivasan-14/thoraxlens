# ThoraxLens - validation report (2026-10-18)

Final system: 3 models with non-zero weight (CoAtNet-0@224 w0.05, DenseNet121@320 w0.30, ConvNeXt-Tiny@320 w0.65),
each with its validation-chosen test-time augmentation. Test mean AUROC **0.8289** over 14 findings (NIH ChestX-ray14 official test split).
Raw numbers: `validation_report_stats.txt`, `ensemble_seed7_report.txt`, `predict_check.txt`.

## What was checked and the result

| # | Check | Result |
|---|---|---|
| 1 | Split integrity | Patients: train 25,208 / val 2,800 / test 2,797, zero overlap. Test = official NIH `test_list.txt` (25,596 images). No duplicate image IDs. |
| 2 | Confidence interval | Final 0.8289, 95% CI 0.8231-0.8337 (1000 patient-level bootstrap resamples). |
| 3 | Gain over original baseline (3x224, no TTA, 0.8201) | +0.0088, CI +0.0068 to +0.0108, better in 100% of resamples. |
| 4 | Gain over other systems (paired) | vs 3x224+TTA +0.0081; vs best single model +0.0048; vs single DenseNet@320 +0.0068; vs uniform 5-model +0.0016 (CI +0.0005 to +0.0026). |
| 5 | Weight-fit stability | 30 refits on resampled validation data: test AUROC 0.8281-0.8293. Mean weights ConvNeXt@320 0.63, DenseNet@320 0.28, CoAtNet 0.07. |
| 6 | Random-seed repeat | See below. |
| 7 | Calibration | Raw outputs are NOT probabilities (mean ECE 0.300) because training used pos_weight up to 50. Per-class Platt scaling fitted on validation: ECE 0.009; AUROC unchanged. |
| 8 | AUPRC | Mean 0.301. Well above prevalence in every class but low in absolute terms for Pneumonia (0.06), Fibrosis (0.11), Pleural Thickening (0.16). |
| 9 | Subgroups | Male 0.8285, female 0.8285; PA 0.824, AP 0.809; age <40 0.792, 40-64 0.825, 65+ 0.809. |
| 10 | Val vs test | Final val 0.8610, test 0.8289. Every model drops by ~0.03 from val to test; model ranking identical on both. |
| 11 | `predict.py` end to end | 64 random test PNGs: max abs diff vs cached ensemble 0.00007; per-image class ranking identical. |

## Seed repeat (seed 7 vs original seed 42; same data split, same settings)

| Model | seed 42 test (no TTA) | seed 7 test (no TTA) | seed 7 val | seed 7 test with val-chosen TTA |
|---|---|---|---|---|
| DenseNet121@320 | 0.8201 | 0.8188 | 0.8494 | 0.8216 (flipscale) |
| ConvNeXt-Tiny@320 | 0.8229 | 0.8196 | 0.8536 | 0.8208 (scale) |

Full 3-model ensemble rebuilt from the seed-7 models with the same validation-only protocol (CoAtNet 0.13, DenseNet 0.38, ConvNeXt 0.48): val 0.8589, **test 0.8274** (uniform 0.8267).
So the run-to-run spread of a single model is about 0.001-0.003 and of the whole ensemble about 0.0015 (0.8289 vs 0.8274).
Both ensembles beat the original baseline 0.8201 by far more than that spread, so the improvement is not a lucky seed.
Single-model differences under ~0.003 (e.g. ConvNeXt vs DenseNet at 320 px) are within seed noise and should not be over-read.
The reported final number stays 0.8289 (the original, validation-selected system); 0.8274 is the honest replication figure.

## Limits that remain

- One dataset, one hospital system (NIH). No external-site test, so generalisation to other scanners/populations is unknown.
- The test set was scored for several intermediate systems during development (4-model, uniform 5-model, single models). No choice was made from those numbers, but it was not a strictly single test run.
- Labels are NLP-mined from reports and are noisy; the AUROC ceiling is limited by label quality.
- Not a medical device. Research use only.
