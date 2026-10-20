"""Build the static data files the ThoraxLens UI reads (CPU only, uses cached predictions).

Writes ui/data/metrics.json (curves, calibration, thresholds, comparisons, subgroups, training logs,
dataset stats), ui/data/calibration.json (what the server needs at inference time) and a set of small
sample images with their NIH labels under ui/static/samples/.

Run from the pipeline folder:  python ui/build_ui_data.py
Everything is derived from outputs/preds/*.npz, outputs/validation/validation_report_stats.txt,
outputs/train_log*.csv and outputs/splits.csv. No model is run and no test-set choice is made here:
thresholds and Platt calibration are fitted on the validation set only.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, precision_recall_curve, roc_auc_score, roc_curve

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import DISEASES, OUTPUTS  # noqa: E402
from data_paths import read_splits  # noqa: E402

P = OUTPUTS / "preds"
DATA = HERE / "data"
SAMPLES = HERE / "static" / "samples"
DATA.mkdir(exist_ok=True)
SAMPLES.mkdir(parents=True, exist_ok=True)

NICE = {"Pleural_Thickening": "Pleural thickening"}
nice = lambda d: NICE.get(d, d)  # noqa: E731


def ld(name):
    z = np.load(P / name)
    return z["y"], z["p"]


def logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


# ---------------------------------------------------------------- predictions
WEIGHTS = {"coatnet": 0.05, "densenet320": 0.30, "convnext320": 0.65}
yv, c_v = ld("_coatnet_0_rw_224.sw_in1k_val_scale.npz")
_, d_v = ld("_320_val_scale.npz")
_, n_v = ld("_convnext_tiny.fb_in22k_ft_in1k_320_val_flipscale.npz")
yt, c_t = ld("_coatnet_0_rw_224.sw_in1k_test_scale.npz")
_, d_t = ld("_320_test_scale.npz")
_, n_t = ld("_convnext_tiny.fb_in22k_ft_in1k_320_test_flipscale.npz")
fv = WEIGHTS["coatnet"] * c_v + WEIGHTS["densenet320"] * d_v + WEIGHTS["convnext320"] * n_v
ft = WEIGHTS["coatnet"] * c_t + WEIGHTS["densenet320"] * d_t + WEIGHTS["convnext320"] * n_t

# ---------------------------------------------------------------- per-class AUROC CI (from the validation report)
stats = (OUTPUTS / "validation" / "validation_report_stats.txt").read_text()
ci = {}
for m in re.finditer(r"^(\w+)\s+([\d.]+)\s+\[([\d.]+), ([\d.]+)\]\s+n_pos=(\d+)", stats, re.M):
    ci[m.group(1)] = (float(m.group(2)), float(m.group(3)), float(m.group(4)), int(m.group(5)))
assert len(ci) == 14, "could not parse per-class CIs"

# ---------------------------------------------------------------- calibration + thresholds (validation only)
platt, rel, thr, classes = [], [], [], []
fgrid = np.unique(np.concatenate([np.linspace(0, 1, 101), np.logspace(-3, 0, 30)]))
rgrid = np.linspace(0, 1, 101)
cal_t = np.zeros_like(ft)
for i, d in enumerate(DISEASES):
    lr = LogisticRegression(C=1e6, max_iter=1000).fit(logit(fv[:, i:i + 1]), yv[:, i])
    a, b = float(lr.coef_[0, 0]), float(lr.intercept_[0])
    platt.append({"a": a, "b": b})
    sig = lambda z: 1 / (1 + np.exp(-z))  # noqa: E731
    cal_t[:, i] = sig(a * logit(ft[:, i]) + b)

    # reliability (test): 10 uniform bins, raw vs calibrated
    def bins(p, y, k=10):
        ix = np.minimum((p * k).astype(int), k - 1)
        out = []
        for j in range(k):
            m = ix == j
            out.append({"n": int(m.sum()), "pred": float(p[m].mean()) if m.any() else None,
                        "obs": float(y[m].mean()) if m.any() else None})
        return out
    rel.append({"raw": bins(ft[:, i], yt[:, i]), "cal": bins(cal_t[:, i], yt[:, i])})

    # operating points chosen on validation
    fpr_v, tpr_v, th_v = roc_curve(yv[:, i], fv[:, i])
    j = int(np.argmax(tpr_v - fpr_v))
    t_bal = float(th_v[j])
    k = int(np.where(tpr_v >= 0.90)[0][0])
    t_sens = float(th_v[k])

    def op(t):
        pred = ft[:, i] >= t
        y = yt[:, i] == 1
        tp, fp, fn, tn = int((pred & y).sum()), int((pred & ~y).sum()), int((~pred & y).sum()), int((~pred & ~y).sum())
        return {"thr_raw": t, "thr_cal": float(sig(a * logit(np.array(t)) + b)),
                "sens": tp / max(tp + fn, 1), "spec": tn / max(tn + fp, 1),
                "ppv": tp / max(tp + fp, 1), "npv": tn / max(tn + fn, 1),
                "flag_rate": float(pred.mean()), "tp": tp, "fp": fp, "fn": fn, "tn": tn}
    thr.append({"balanced": op(t_bal), "sensitive": op(t_sens)})

    fpr, tpr, _ = roc_curve(yt[:, i], ft[:, i])
    pr, rc, _ = precision_recall_curve(yt[:, i], ft[:, i])
    # interpolated precision at recall grid (precision envelope)
    env = np.maximum.accumulate(pr[::-1])[::-1]
    prec_g = np.interp(rgrid, rc[::-1], env[::-1])
    auc, lo, hi, npos = ci[d][0], ci[d][1], ci[d][2], ci[d][3]
    classes.append({
        "key": d, "name": nice(d), "auc": round(float(roc_auc_score(yt[:, i], ft[:, i])), 4),
        "ci": [lo, hi], "n_pos": npos, "prevalence": float(yt[:, i].mean()),
        "ap": round(float(average_precision_score(yt[:, i], ft[:, i])), 4),
        "roc": {"fpr": [round(float(x), 4) for x in fgrid],
                "tpr": [round(float(x), 4) for x in np.interp(fgrid, fpr, tpr)]},
        "pr": {"recall": [round(float(x), 3) for x in rgrid], "precision": [round(float(x), 4) for x in prec_g]},
    })
    print(f"{d:<20s} auc {classes[-1]['auc']:.4f} bal thr {t_bal:.3f} sens {thr[-1]['balanced']['sens']:.2f} spec {thr[-1]['balanced']['spec']:.2f}")

mean_auc = float(np.mean([c["auc"] for c in classes]))

# ---------------------------------------------------------------- subgroups from the stats report
sub = []
for m in re.finditer(r"^(sex=\w|view=\w+|age[<>= 0-9-]+?)\s+n=\s*(\d+)\s+mean AUROC ([\d.]+)", stats, re.M):
    sub.append({"group": m.group(1).strip(), "n": int(m.group(2)), "auc": float(m.group(3))})

# ---------------------------------------------------------------- dataset stats
df = read_splits()
age = pd.to_numeric(df["age"], errors="coerce")
dstats = {
    "images": {s: int((df.split == s).sum()) for s in ("train", "val", "test")},
    "patients": {s: int(df[df.split == s].patient_id.nunique()) for s in ("train", "val", "test")},
    "prevalence": {s: [float(df[df.split == s][d].mean()) for d in DISEASES] for s in ("train", "val", "test")},
    "test_sex": {k: int(v) for k, v in df[df.split == "test"].sex.value_counts().items()},
    "test_view": {k: int(v) for k, v in df[df.split == "test"].view.value_counts().items()},
    "test_age_hist": [int(x) for x in np.histogram(age[(df.split == "test") & (age > 0) & (age < 100)], bins=range(0, 101, 10))[0]],
    "no_finding_rate": float((df[DISEASES].sum(axis=1) == 0).mean()),
    "mean_labels_per_positive_image": float(df[df[DISEASES].sum(axis=1) > 0][DISEASES].sum(axis=1).mean()),
}

# ---------------------------------------------------------------- training logs
def log(path):
    d = pd.read_csv(OUTPUTS / path)
    return [{"epoch": int(r.epoch), "loss": float(r.train_loss), "val": float(r.val_mean_auc), "sec": int(r.seconds)} for r in d.itertuples()]


training = {
    "DenseNet121 224": log("final_train_log_4epochs.csv"),
    "ConvNeXt-Tiny 224": log("train_log_convnext_tiny.fb_in22k_ft_in1k.csv"),
    "CoAtNet-0 224": log("train_log_coatnet_0_rw_224.sw_in1k.csv"),
    "DenseNet121 320": log("train_log_320.csv"),
    "ConvNeXt-Tiny 320": log("train_log_convnext_tiny.fb_in22k_ft_in1k_320.csv"),
    "DenseNet121 320 (seed 7)": log("train_log_320_seed7.csv"),
    "ConvNeXt-Tiny 320 (seed 7)": log("train_log_convnext_tiny.fb_in22k_ft_in1k_320_seed7.csv"),
}

# ---------------------------------------------------------------- model comparison / ablation (recorded results)
models = [
    {"id": "densenet224", "name": "DenseNet121", "px": 224, "tta": "flipscale", "val": 0.8408, "test": 0.8118, "weight": 0.0, "family": "Dense-connectivity CNN"},
    {"id": "convnext224", "name": "ConvNeXt-Tiny", "px": 224, "tta": "flipscale", "val": 0.8443, "test": 0.8092, "weight": 0.0, "family": "Modern CNN"},
    {"id": "coatnet", "name": "CoAtNet-0", "px": 224, "tta": "scale", "val": 0.8413, "test": 0.8088, "weight": 0.05, "family": "Conv + attention hybrid"},
    {"id": "densenet320", "name": "DenseNet121", "px": 320, "tta": "scale", "val": 0.8512, "test": 0.8220, "weight": 0.30, "family": "Dense-connectivity CNN"},
    {"id": "convnext320", "name": "ConvNeXt-Tiny", "px": 320, "tta": "flipscale", "val": 0.8587, "test": 0.8241, "weight": 0.65, "family": "Modern CNN"},
]
ablation = [
    {"step": "Original baseline", "detail": "3 models at 224 px, no TTA, uniform", "test": 0.8201},
    {"step": "Add TTA", "detail": "same 3 models, validation-chosen views", "test": 0.8208},
    {"step": "Add 320 px models", "detail": "5 models, uniform average", "test": 0.8273},
    {"step": "Fit weights on validation", "detail": "final 3 non-zero weights", "test": 0.8289},
]
seed = {"seed42": {"densenet320": 0.8201, "convnext320": 0.8229, "ensemble": 0.8289},
        "seed7": {"densenet320": 0.8188, "convnext320": 0.8196, "ensemble": 0.8274}}
bootstrap = {"final": [0.8289, 0.8231, 0.8337],
             "paired": [{"vs": "original baseline", "diff": 0.0088, "ci": [0.0068, 0.0108]},
                        {"vs": "3x224 + TTA", "diff": 0.0081, "ci": [0.0063, 0.0098]},
                        {"vs": "single DenseNet 320", "diff": 0.0068, "ci": [0.0048, 0.0090]},
                        {"vs": "best single (ConvNeXt 320)", "diff": 0.0048, "ci": [0.0040, 0.0056]},
                        {"vs": "5-model uniform", "diff": 0.0016, "ci": [0.0005, 0.0026]}]}

# ---------------------------------------------------------------- calibration summary
def ece(y, p, bins=10):
    ix = np.minimum((p * bins).astype(int), bins - 1)
    return sum((ix == b).sum() / len(y) * abs(y[ix == b].mean() - p[ix == b].mean()) for b in range(bins) if (ix == b).any())


calib = {"ece_raw": float(np.mean([ece(yt[:, i], ft[:, i]) for i in range(14)])),
         "ece_cal": float(np.mean([ece(yt[:, i], cal_t[:, i]) for i in range(14)]))}

metrics = {
    "project": "ThoraxLens", "mean_auc": mean_auc, "ap_mean": float(np.mean([c["ap"] for c in classes])),
    "classes": classes, "reliability": rel, "thresholds": thr, "calibration": calib, "subgroups": sub,
    "dataset": dstats, "training": training, "models": models, "ablation": ablation, "seed": seed,
    "bootstrap": bootstrap, "weights": WEIGHTS,
}
(DATA / "metrics.json").write_text(json.dumps(metrics, separators=(",", ":")))
(DATA / "calibration.json").write_text(json.dumps({
    "diseases": DISEASES, "names": [nice(d) for d in DISEASES], "platt": platt,
    "thresholds": thr, "weights": WEIGHTS}, indent=1))
print("mean auc", round(mean_auc, 4), "ECE raw/cal", round(calib["ece_raw"], 3), round(calib["ece_cal"], 3))

# ---------------------------------------------------------------- sample images (random test positives, seeded)
test = df[df.split == "test"]
rng = np.random.default_rng(2026)
pick, used = [], set()
targets = ["Pneumothorax", "Effusion", "Cardiomegaly", "Mass", "Edema", "Emphysema", "Pneumonia", "Atelectasis", "Nodule"]
nlab = test[DISEASES].sum(axis=1)
for d in targets:
    cand = test[(test[d] == 1) & (nlab == 1) & (test.view == "PA") & (~test.image.isin(used))]
    row = cand.iloc[int(rng.integers(len(cand)))]
    pick.append(row)
    used.add(row.image)
for _ in range(3):
    cand = test[(nlab == 0) & (test.view == "PA") & (~test.image.isin(used))]
    row = cand.iloc[int(rng.integers(len(cand)))]
    pick.append(row)
    used.add(row.image)
samples = []
for k, row in enumerate(pick):
    im = Image.open(row.path).convert("L").resize((640, 640), Image.BILINEAR)
    sid = f"s{k + 1:02d}"
    im.save(SAMPLES / f"{sid}.jpg", quality=88)
    labels = [d for d in DISEASES if row[d] == 1]
    samples.append({"id": sid, "file": f"/static/samples/{sid}.jpg", "labels": [nice(x) for x in labels],
                    "age": int(row.age), "sex": row.sex, "view": row["view"], "image": row.image,
                    "src": str(row.image)})
(DATA / "samples.json").write_text(json.dumps(samples, indent=1))
print("samples:", len(samples))
