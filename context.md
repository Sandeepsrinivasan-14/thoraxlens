# ChestX-ray14 Project – Full Context

Last updated: 2026-10-16. Status: COMPLETE. Improvement plan finished; best = 5-model ensemble, test mean AUROC **0.8289** (baseline 0.8201). Inference script: predict.py. Details in section 13.

## 1. Goal
Build a complete multi-label chest X-ray classifier for the NIH ChestX-ray14 dataset from scratch (no external source code), in
`C:\Users\sndps\Downloads\ChestXray-NIHCC\pipeline`. Requirements from the user:
- Train fast on the full GPU.
- Training must be resumable after shutdown/offline and auto-start at logon.
- Report epoch times, validation AUROC and test AUROC.
- Show progress in chat (user does not want to run commands or check terminals; user is often away).

## 2. Dataset
- 112,120 frontal chest X-rays, 14 disease labels (Atelectasis, Cardiomegaly, Effusion, Infiltration, Mass, Nodule, Pneumonia, Pneumothorax, Consolidation, Edema, Emphysema, Fibrosis, Pleural_Thickening, Hernia) + "No Finding".
- Multi-label; strong class imbalance (Hernia only 86 test positives).
- Images: `C:\Users\sndps\Downloads\ChestXray-NIHCC\ChestXray14_all\images`
- Metadata: `C:\Users\sndps\Downloads\Data_Entry_2017_v2020.csv`
- Official lists: `C:\Users\sndps\Downloads\train_val_list.txt`, `test_list.txt` (images and metadata live in different folders).
- Splits (patient-level, no leakage): train 77,724 / val 8,800 / test 25,596 (val = 10% of train/val patients).
- Quality findings: 519 images are RGBA (known anomaly, handled by converting to grayscale); some age=0 rows; all images 1024x1024. Full integrity check of all 112,120 images passed (`outputs/integrity_full.log`).

## 3. Pipeline files (`pipeline/`)
| File | Purpose |
|---|---|
| `configs/default.yaml` | All hyperparameters/paths (epochs now 4) |
| `prepare_splits.py` | Builds patient-level train/val/test splits |
| `cache_images.py` | Resizes all images to 224x224 uint8 into `outputs/images_224.npy` (memory-mapped) |
| `check_integrity.py` | Verifies every image opens/has expected size |
| `common.py` | Model, data/caching helpers (`cache_batches`, `gpu_batch`), GPU augmentation, AUROC utilities |
| `train.py` | Training loop; auto-resumes from `last.pt`; evaluates test set at end |
| `evaluate.py` | Standalone test AUROC reporter using best checkpoint |
| `explain.py` | Grad-CAM + gradient counterfactual explanations |
| `run_training.ps1` | Wrapper launched by Scheduled Task `ChestXrayTraining` (logs to `outputs/train_stdout.log`) |
| `requirements.txt` | Python deps |

## 4. Model and training setup
- DenseNet121, ImageNet pretrained, first conv adapted to 1 channel, 14-way head.
- Loss: BCEWithLogitsLoss with `pos_weight` (capped at 50) to counter imbalance.
- Optimiser: AdamW, lr 1e-4, weight decay 1e-5; CosineAnnealingLR with T_max = epochs.
- AMP fp16 + GradScaler; batch size 32; seed 42; input 224x224.
- Zero-copy pipeline: whole uint8 cache in memory-map, batches moved to GPU and augmented on GPU; no DataLoader workers (earlier DataLoader version stalled/was starved by low free RAM).
- Resumability: `last.pt` atomically saved every epoch (model+optimizer+scheduler+scaler+epoch+log), `best.pt` saved on best val AUROC; relaunching `train.py` resumes automatically.
- Auto-start: Windows Scheduled Task `ChestXrayTraining` (at logon). **Now disabled** since training is finished.

## 5. Results
### Run 1 (10 epochs, cosine T_max=10) – overfit
Best val AUROC at epoch 3 (0.8353); test mean AUROC **0.8005**. Backups: `outputs/run1_10epochs/`, `outputs/checkpoints/best_run1.pt`.

### Final run (4 epochs, cosine T_max=4) – chosen
| Epoch | Train loss | Val mean AUROC | Seconds |
|---|---|---|---|
| 1 | 0.95608 | 0.81656 | 5256 (GPU contention) |
| 2 | 0.85651 | 0.82915 | 882 |
| 3 | 0.78069 | 0.83537 | 696 |
| 4 | 0.69718 | 0.83797 | 1105 (partial contention) |

Uncontended speed is ~9–12 min/epoch. Test mean AUROC = **0.8086** (vs 0.8005 run 1).

Per-class test AUROC (n positives):
Atelectasis 0.7606 (3279), Cardiomegaly 0.8939 (1069), Effusion 0.8217 (4658), Infiltration 0.6951 (6112), Mass 0.8223 (1748), Nodule 0.7476 (1623), Pneumonia 0.7128 (555), Pneumothorax 0.8581 (2665), Consolidation 0.7450 (1815), Edema 0.8459 (925), Emphysema 0.9073 (1093), Fibrosis 0.8224 (435), Pleural_Thickening 0.7739 (1143), Hernia 0.9144 (86).

## 6. Explanations
`explain.py` produces Grad-CAM heatmaps and gradient-based counterfactual edits. Checked on 6 test images (incl. weak classes); outputs in `outputs/explain/` and `outputs/explain_picks.txt`. Heart highlighted for Cardiomegaly, affected lung for Pneumothorax; no sign of reliance on borders/text markers.

## 7. Output locations (`pipeline/outputs/`)
- `final_best_4epochs.pt` – **final model** (same as `checkpoints/best.pt`)
- `final_test_auroc_4epochs.csv`, `final_train_log_4epochs.csv` – final metrics
- `test_auroc.csv`, `train_log.csv` – current-run outputs; `train_stdout.log` – append-only history
- `checkpoints/` – `best.pt`, `last.pt`, `best_run1.pt`
- `run1_10epochs/` – all run-1 artifacts (test mean 0.8005)
- `integrity_full.log`, `explain/`, `explain_picks.txt`, `images_224.npy`

## 8. History of what was done
1. Understood dataset, verified file layout and patient-level split integrity, documented quality findings.
2. Wrote the whole pipeline from scratch (splits, cache, model, train, evaluate, explain, integrity).
3. Moved everything onto the GPU (GPU augmentation, uint8 cache, AMP) after user asked for full-GPU speed; replaced DataLoader with zero-copy batching after stalls/memory exhaustion (free RAM was ~128 MB at times).
4. Set up resumable training and the Scheduled Task for auto-start at logon.
5. Run 1 (10 epochs) finished: overfit after epoch 3; test 0.8005.
6. Completed pending items: disabled obsolete scheduled task, ran Grad-CAM check on more images, retrained with 4 epochs (better), ran full 112,120-image integrity check (all ok).
7. Saved final artifacts, restored AC standby timeout to 5 min (hibernate-on-AC remains 0), saved memory notes.

## 9. Problems encountered and how they were solved
- Background tasks killed by session restarts, PC power loss, and 5-min AC sleep → relaunched via Start-ScheduledTask; temporarily disabled AC sleep/hibernate during training (standby restored afterwards).
- Another project's (vaaksetu) tts training shared the 4 GB GPU with LM Studio and starved this run → I suspended the tts processes (NtSuspendProcess) at the user's request "pause"; an auto-guard script was blocked by permissions and abandoned, processes resumed; the tts job later disappeared on its own. Epoch 1 and 4 times of the final run are inflated by this.
- Monitors matching stale "=== exit" lines and `rtk grep` inside Monitor failures → replaced with awk-based watchers.

## 10. How to use / what to do
- Inference/evaluation: load `outputs/final_best_4epochs.pt` (`python evaluate.py` uses `checkpoints/best.pt`, which is identical).
- Retrain: move `checkpoints/last.pt` aside (otherwise it auto-resumes), set `epochs` in `configs/default.yaml`, run `train.py` (or re-enable Scheduled Task `ChestXrayTraining`).
- Check `nvidia-smi` and avoid concurrent GPU jobs (tts training, LM Studio); GPU is 4 GB.
- Nothing further is required for the baseline project (optional improvements: section 13). The other project's tts training may need relaunching on its own side.

## 11. Environment
Windows 11, PowerShell/Git Bash, 4 GB GPU, low free RAM, Python venv with PyTorch; user email sndpsrinivasan@gmail.com. Claude memory notes: `C:\Users\sndps\.claude\projects\c--Users-sndps-Downloads-ChestXray-NIHCC\memory\` (dataset_layout, training_results, dataset_quality_findings).

## 12. Additional architectures and ensemble (added later)
Select architecture with env var `CXR_ARCH` (default densenet121); each arch has its own `outputs/checkpoints_<arch>/`, `train_log_<arch>.csv`, `test_auroc_<arch>.csv`. Training resumes from `last.pt`.
`cache_batches` now uses a background prefetch thread with pinned memory (removed disk-read stalls; GPU 98-100%, ~114 img/s).

| Model | Best val AUROC | Test AUROC |
|---|---|---|
| DenseNet121 | 0.8380 | 0.8086 |
| ConvNeXt-Tiny (in22k) | 0.8414 | 0.8073 |
| CoAtNet-0 (hybrid conv+attention) | 0.8390 | 0.8073 |
| Ensemble DenseNet+ConvNeXt | - | 0.8172 |
| **Ensemble of all 3** | - | **0.8201** |

Run: `python ensemble.py densenet121 convnext_tiny.fb_in22k_ft_in1k coatnet_0_rw_224.sw_in1k` -> `outputs/test_auroc_ensemble.csv`.
MaxViT-Tiny needs 5.7 GB at batch 32, too big for the 4 GB GPU (would need batch 16 + 2-step gradient accumulation or gradient checkpointing). Not trained.

Trained models and files (all under `pipeline/outputs/`):
| Model | Checkpoint dir | Result CSV |
|---|---|---|
| DenseNet121 | `checkpoints/` (`best.pt`, `last.pt`, `best_run1.pt` = weaker run 1, test 0.8005) | `test_auroc.csv` |
| ConvNeXt-Tiny | `checkpoints_convnext_tiny.fb_in22k_ft_in1k/` | `test_auroc_convnext_tiny.fb_in22k_ft_in1k.csv` |
| CoAtNet-0 | `checkpoints_coatnet_0_rw_224.sw_in1k/` | `test_auroc_coatnet_0_rw_224.sw_in1k.csv` |
| Ensemble | - | `test_auroc_ensemble.csv` |
`best.pt` = best-val weights (used for testing); `last.pt` = last epoch (used for resuming). Logs: `train_stdout_coatnet.log`, `train_stdout_coatnet2.log` (resumed after the first CoAtNet process died silently at epoch 4 step ~1500; relaunching with the same `CXR_ARCH` resumed from the epoch-3 `last.pt`).
All 224 px runs: 4 epochs, batch 32, ~13 min/epoch (CoAtNet epoch 4 took 805 s).
Python: `C:\Users\sndps\AppData\Local\Programs\Python\Python311\python.exe`, run from the `pipeline` dir.

## 13. Possible improvements and the 6-hour plan (decided 2026-10-13; ALL STEPS DONE 2026-10-16)
Analysis: val AUROC ~0.84 but test ~0.81 (test set is larger/harder). Models are likely under-trained (4 epochs) and 224 px loses detail for small findings (nodule, mass, fibrosis, pneumonia). Published results on this dataset are ~0.83-0.85 (512 px, big ensembles); NIH labels are NLP-mined and noisy, which caps the ceiling.

Ideas and expected gain (estimates, not measured): higher resolution 320/384 (+0.01-0.02); longer training 10-12 epochs (+0.005-0.01); EMA/SWA (+0.002-0.004); TTA flip/scale (+0.002-0.005); asymmetric/focal loss (+0.002-0.005, uncertain); more diverse ensemble members (+0.002-0.005); age/sex/view metadata in the head (+0.001-0.003). Candidate models: EfficientNetV2-S, ConvNeXt-Small, MaxViT-Tiny (needs accumulation), Swin-T, DenseNet121 at 320/384. Avoid chest-X-ray weights pretrained on NIH data (e.g. TorchXRayVision) - test leakage. No other datasets (CheXpert/MIMIC) are available.
Gains are not guaranteed and overlap; the full 13-hour plan (3 models at 320 px, 8 epochs each) was judged not clearly worth it.

Agreed plan within ~6 h (~5.6 h planned):
| Step | What | Time |
|---|---|---|
| 1 | Add EMA, TTA (flip + slight scale), configurable image size (e.g. env `CXR_IMG`; `images_224.npy` is currently hardcoded); run TTA on the 3 existing models and re-ensemble | ~0.4 h |
| 2 | Build `outputs/images_320.npy` (uint8, ~11 GB, memory-mapped; same preprocessing/order as the 224 cache) | ~0.7 h |
| 3 | DenseNet121 at 320 px, 5 epochs, EMA (batch 16 x 2 accumulation if batch 32 does not fit 4 GB). **Gate:** after epoch 2 compare val AUROC with the 224 run at the same epoch; if not clearly better, stop and finalize with the TTA ensemble | ~2.3 h |
| 4 | ConvNeXt-Tiny at 320 px, 4 epochs, EMA | ~1.9 h |
| 5 | 5-model ensemble (2 new + 3 existing), TTA, weights fitted on VAL, one test run at the end | ~0.3 h |
Dropped for time: EfficientNetV2-S, MaxViT, ASL loss. Expected ensemble ~0.825-0.835 (not guaranteed). Existing 224 px checkpoints/CSVs must not be overwritten (use a distinct `TAG`, e.g. `_320`). Choose settings by validation AUROC only, never test. Fallback result if nothing helps: 0.8201.
A full handoff prompt for another agent was written in the chat on 2026-10-13 (same content as this plan plus rules: autonomous, GPU only, no other GPU processes, resumable, report progress in chat, update this file and memory when done).

### Progress (2026-10-15)
- Code added: `CXR_IMG/CXR_EPOCHS/CXR_BATCH/CXR_ACCUM/CXR_EMA` env vars (train.py/common.py), EMA, TTA (`evaluate.py`), `ensemble2.py` (per-model TTA chosen on val, val-fitted weights; spec `arch@img`), `chain_convnext.sh` (launch ConvNeXt@320, retries batch 8x4 on OOM). Cache: `outputs/images_320.npy`.
- DenseNet121@320 (5 ep, EMA 0.999, batch 16x2): val 0.8497 (ep4 best), test 0.8201 without TTA, 0.8220 with TTA=scale. Files: `checkpoints_320/`, `train_log_320.csv`, `test_auroc_320.csv`. Gate passed (ep2 val 0.8435 vs 0.838 at 224).
- TTA on 224 models: DenseNet 0.8118, ConvNeXt 0.8092, CoAtNet 0.8088 test; 3-model uniform ensemble 0.8208.
- 4-model ensemble (`python ensemble2.py densenet121 convnext_tiny.fb_in22k_ft_in1k coatnet_0_rw_224.sw_in1k densenet121@320`): uniform val 0.8546 / test 0.8251; fitted weights (0.05/0.25/0.20/0.50) val 0.8559 / **test 0.8263** (chosen on val). Report: `outputs/ensemble_v2_report_4model.txt`.
- ConvNeXt-Tiny@320 (4 ep, EMA, batch 16x2): val 0.8576 (best, ep3), test 0.8229 without TTA, 0.8241 with TTA=flipscale. First launches crashed (native abort in pinned-memory allocator, free RAM ~1.7 GB); fixed by `CXR_PIN=0` (pinned memory off) plus the auto-restart loop in `chain_convnext.sh`. Files: `checkpoints_convnext_tiny.fb_in22k_ft_in1k_320/`, `test_auroc_convnext_tiny.fb_in22k_ft_in1k_320.csv`.
- **FINAL 5-model ensemble** (`python ensemble2.py densenet121 convnext_tiny.fb_in22k_ft_in1k coatnet_0_rw_224.sw_in1k densenet121@320 convnext_tiny.fb_in22k_ft_in1k@320`): uniform val 0.8575 / test 0.8273; fitted weights (DenseNet224 0, ConvNeXt224 0, CoAtNet 0.05, DenseNet@320 0.30, ConvNeXt@320 0.65) val 0.8610 / **test 0.8289** (chosen on val). Files: `outputs/ensemble_v2_report_5model.txt`, `test_auroc_ensemble_v2_5model.csv`. Note: running ensemble2.py in a pipe once crashed at interpreter exit (torch DLL); redirect output to a file instead.

### Inference script (added 2026-10-16)
`python predict.py img1.png [img2.png ...] [--out preds.csv]` runs the final ensemble (CoAtNet@224 w0.05 + DenseNet121@320 w0.30 + ConvNeXt-Tiny@320 w0.65, each with its val-chosen TTA; the 0-weight 224 px DenseNet/ConvNeXt are skipped) and prints the 14 probabilities per image, sorted. Loads one model at a time to fit the 4 GB GPU. Smoke-tested on two test images (00000003_001/002, true label Hernia; scores 0.38 / 0.62 for Hernia): runs end to end. Not a medical device.
Not done (judged not worth it): retraining with lower LR/regularisation, 384+ px, or more architectures; expected gain small/uncertain.

## 14. Validation (done 2026-10-18) and project name
Project name: **ThoraxLens** (chest X-ray multi-label classifier, ensemble of DenseNet121/ConvNeXt-Tiny/CoAtNet). Folder names unchanged.
Full report: `outputs/validation/VALIDATION_REPORT.md` (raw: `validation_report_stats.txt`, `ensemble_seed7_report.txt`, `predict_check.txt`).
Scripts (all re-runnable, use cached predictions in `outputs/preds/`): `validate_stats.py` (integrity, bootstrap CIs, weight stability, calibration, AUPRC, subgroups, val vs test), `validate_predict.py` (predict.py vs cached ensemble), `baseline_preds.py` (no-TTA 224 baseline test preds for paired comparison), `chain_seeds.sh` (seed-7 retrains; `CXR_SEED=7` env var gives separate `*_seed7` checkpoints/logs/CSVs), `ensemble2.py` spec now `arch[@img][#seed]`.
WARNING: `ensemble2.py` overwrites `outputs/ensemble_v2_report.txt` and `test_auroc_ensemble_v2.csv`; the final ones are kept as `*_5model` copies (restore from them after any re-run).
Results: final test AUROC 0.8289, 95% patient-bootstrap CI 0.8231-0.8337; gain over the 0.8201 baseline +0.0088 (CI +0.0068..+0.0108). Split has zero patient overlap and equals the official test list. `predict.py` reproduces the cached ensemble (max diff 0.00007).
Seed-7 repeat: DenseNet@320 test 0.8188 (0.8216 with TTA), ConvNeXt@320 0.8196 (0.8208 with TTA); rebuilt 3-model ensemble test 0.8274. Run-to-run spread ~0.001-0.003 per model, ~0.0015 for the ensemble.
Known limits: raw scores are not calibrated probabilities (mean ECE 0.30; per-class Platt on val -> 0.009; AUROC unchanged); AUPRC mean 0.301; PA 0.824 vs AP 0.809; age<40 0.792 lowest; no external-site test; several intermediate systems were scored on test during development.
Note: a transient CUDA error (CUDNN_STATUS_EXECUTION_FAILED_CUDA_DRIVER) hit the ConvNeXt seed-7 run mid-epoch 1; chain_seeds.sh restarted it automatically. An ensemble2.py run also once stopped silently mid-way; rerunning resumes from cached preds.

## 15. Web app, cleanup and document (2026-10-18)
- **Web app** `ui/` (FastAPI + vanilla JS, offline): `python ui/server.py` (or `ui\run_ui.bat`) -> http://127.0.0.1:8000. Tabs: Analyze (upload/paste/12 NIH samples, streamed per-model progress, 14 findings vs validation-chosen thresholds, risk % via Platt, per-model scores, Grad-CAM on DenseNet121@320, viewer tools, history, JSON/CSV/print), Performance, Models, Validation, About. Details in `ui/README.md`. Data files are built by `ui/build_ui_data.py` from `outputs/preds` (thresholds and Platt fitted on VAL only); deep link `/?sample=s04&heat=1&reveal=1&theme=light`. Verified: no console errors (dark/light, desktop/mobile), uploads of L/RGBA/16-bit/colour images and a bad file (415).
- **Cleanup** `cleanup.py` (dry run by default, `--apply` for the safe set; opt-in `--resume-states` ~1.85 GB of last.pt of finished runs, `--caches` ~16 GB rebuildable image caches). Applied 2026-10-18: removed __pycache__, UI dev leftovers, empty logs, two SHA-256-verified duplicates in `outputs/run1_10epochs/` (freed ~124 MB). Log: `outputs/validation/cleanup_log.txt`. Never touched: every best.pt, final_best_4epochs.pt (identical to checkpoints/best.pt, documented as final), preds, CSVs, reports, dataset. Root helper scripts (`_dl_worker*.sh`, `organize_chestxray14.ps1`, `_download_logs/`) left in place (organize script uses the current directory).
- **Document**: "ThoraxLens: Technical and Clinical Overview" (Claude Docs artifact https://claude.ai/code/artifact/41701720-f53f-4afb-a2ff-4a27cca79c12), ~75% technical / 25% clinical, with architecture diagram, ablation chart and per-finding AUROC chart. Its last section ("Reproducing the work") could not be filled because the Docs connector disconnected; the same content is in `REPRODUCE.md`.
- Project name: ThoraxLens.
