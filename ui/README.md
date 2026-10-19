# ThoraxLens web app

A local reading-room style UI for the final ensemble. Research use only; not a medical device. Images never leave the machine.

## Run

```
python ui/server.py            # opens http://127.0.0.1:8000
python ui/server.py --port 8100 --no-browser
ui\run_ui.bat                  # Windows launcher (same thing)
```

Needs the packages already used by the pipeline plus `fastapi` and `uvicorn`. The three models (CoAtNet-0 @224, DenseNet121 @320, ConvNeXt-Tiny @320)
load once onto the GPU with a warm-up pass (about 20 s); an analysis then takes about 1 s on an RTX 3050 laptop GPU.
Deep link: `/?sample=s04&heat=1&reveal=1&theme=light` runs a sample on load.

## What is in it

| Tab | Content |
|---|---|
| Analyze | Drop, paste or pick an X-ray (or one of 12 NIH test samples). Live pipeline progress, 14 findings ranked against each finding's validation-chosen threshold, risk % (Platt-calibrated) or raw score, per-model scores, balanced or high-sensitivity operating point, Grad-CAM heatmap (DenseNet121), zoom/pan/brightness/contrast/invert, history, JSON/CSV export, printable report. |
| Performance | AUROC with bootstrap intervals, ROC and PR curves, reliability diagrams (raw vs calibrated), operating-point table, subgroups, confusion matrix. |
| Models | The five models and their weights, what moved the score, training curves, seed repeat, recipe. |
| Validation | The validation record, paired gains, known limits. |
| About | Data split and demographics, pipeline, findings glossary. |

Shortcuts: `1`-`5` sections, `U` open, `H` heatmap, `I` invert, `+`/`-`/`R` zoom, `B` threshold, `T` theme, `?` help.

## Files

- `server.py` FastAPI backend: `/api/analyze` (streams per-model progress), `/api/cam` (Grad-CAM), `/api/metrics`, `/api/config`, `/api/health`.
- `static/` `index.html`, `app.css`, `app.js` (vanilla, no dependencies, works offline), `samples/` (12 test images).
- `data/` `metrics.json`, `calibration.json`, `samples.json`, built by `build_ui_data.py` from the cached predictions
  (thresholds and Platt calibration are fitted on the validation set only). Rebuild with `python ui/build_ui_data.py`.
- `screenshots/` reference captures.

## Notes

- The heatmap is Grad-CAM on DenseNet121 at the end of dense block 3. It is a sanity check; it has not been validated against ground-truth regions.
- "Flagged" means the raw ensemble score is at or above the finding's threshold. The balanced threshold maximises sensitivity + specificity on validation;
  the high-sensitivity one gives 90% sensitivity on validation. Precision depends on prevalence and is low for rare findings.
- Inputs are converted to grayscale and squashed to a square like the training data. Warnings appear for colour, low resolution, odd aspect ratio or a bright (possibly inverted) border.
