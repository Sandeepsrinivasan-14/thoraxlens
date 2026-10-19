"""Statistical validation of the final ensemble from cached predictions (CPU only, no training).

1. split integrity   2. patient-level bootstrap CIs (+ paired differences)  3. per-class CIs
4. weight-fitting stability (bootstrap the VAL set, refit)  5. calibration (ECE/Brier, Platt on val)
6. AUPRC  7. subgroups (sex, view, age)  8. val -> test generalisation gap
Writes outputs/validation/validation_report_stats.txt
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

import ensemble2
from common import DISEASES, OUTPUTS, load_config
from data_paths import read_splits

P = OUTPUTS / "preds"
OUT = OUTPUTS / "validation"
rng = np.random.default_rng(0)
L = []


def say(s=""):
    print(s, flush=True)
    L.append(s)


def ld(f):
    z = np.load(P / f)
    return z["y"], z["p"]


def auc_w(y, p, w):
    r = []
    for i in range(y.shape[1]):
        if 0 < y[:, i].sum() < len(y):
            r.append(roc_auc_score(y[:, i], p[:, i], sample_weight=w))
    return np.array(r)


def fast_auc(y, p):
    return ensemble2.mean_auc(y, p)


df = read_splits()
test = df[df["split"] == "test"].reset_index(drop=True)
val = df[df["split"] == "val"].reset_index(drop=True)

# ---- 1. split integrity ----------------------------------------------------
say("== 1. Split integrity ==")
pat = {s: set(df[df.split == s].patient_id) for s in ("train", "val", "test")}
say(f"patients train/val/test: {len(pat['train'])}/{len(pat['val'])}/{len(pat['test'])}; "
    f"overlaps train-val {len(pat['train'] & pat['val'])}, train-test {len(pat['train'] & pat['test'])}, "
    f"val-test {len(pat['val'] & pat['test'])}")
img = {s: set(df[df.split == s].image) for s in ("train", "val", "test")}
tl = {l.strip() for l in open(load_config()["data"]["test_list"]) if l.strip()}
say(f"test images == official NIH test_list.txt: {img['test'] == tl} ({len(tl)} images); "
    f"duplicate image ids in splits: {df.image.duplicated().sum()}")

# ---- load predictions ---------------------------------------------------------
yt, p_cnx = ld("_convnext_tiny.fb_in22k_ft_in1k_320_test_flipscale.npz")
_, p_dn320 = ld("_320_test_scale.npz")
_, p_coat = ld("_coatnet_0_rw_224.sw_in1k_test_scale.npz")
_, p_dn224 = ld("_densenet121_test_flipscale.npz")
_, p_cnx224 = ld("_convnext_tiny.fb_in22k_ft_in1k_test_flipscale.npz")
final = 0.05 * p_coat + 0.30 * p_dn320 + 0.65 * p_cnx
uni5 = np.mean([p_dn224, p_cnx224, p_coat, p_dn320, p_cnx], axis=0)
base = np.mean([ld(f"{t}_test_none.npz")[1] for t in
                ("_densenet121", "_convnext_tiny.fb_in22k_ft_in1k", "_coatnet_0_rw_224.sw_in1k")], axis=0)
ens224tta = np.mean([p_dn224, p_cnx224, p_coat], axis=0)
systems = {"final 5-model fitted (reported)": final, "original baseline (3x224, no TTA)": base,
           "3x224 + TTA": ens224tta, "best single ConvNeXt@320": p_cnx,
           "single DenseNet@320": p_dn320, "5-model uniform": uni5}

# ---- 2. patient-level bootstrap ------------------------------------------------
say("\n== 2. Test AUROC with 95% patient-level bootstrap CI (1000 resamples) ==")
pids = test.patient_id.values
upat, inv = np.unique(pids, return_inverse=True)
B = 1000
boot = {k: [] for k in systems}
for b in range(B):
    cnt = np.bincount(rng.integers(0, len(upat), len(upat)), minlength=len(upat))
    w = cnt[inv].astype(float)
    for k, p in systems.items():
        boot[k].append(auc_w(yt, p, w))
boot = {k: np.array(v) for k, v in boot.items()}  # B x 14
mb = {k: v.mean(axis=1) for k, v in boot.items()}
for k, p in systems.items():
    lo, hi = np.percentile(mb[k], [2.5, 97.5])
    say(f"{k:<36s} {fast_auc(yt, p):.4f}  [{lo:.4f}, {hi:.4f}]")
say("\nPaired differences (same resampled patients), mean AUROC:")
ref = "final 5-model fitted (reported)"
for k in list(systems)[1:]:
    d = mb[ref] - mb[k]
    lo, hi = np.percentile(d, [2.5, 97.5])
    say(f"final - {k:<34s} {fast_auc(yt, final) - fast_auc(yt, systems[k]):+.4f}  [{lo:+.4f}, {hi:+.4f}]  "
        f"P(final better)={np.mean(d > 0):.3f}")

say("\n== 3. Per-class test AUROC, 95% CI (final ensemble) ==")
fb = boot[ref]
pt = auc_w(yt, final, None)
for i, d in enumerate(DISEASES):
    lo, hi = np.percentile(fb[:, i], [2.5, 97.5])
    say(f"{d:<20s} {pt[i]:.4f}  [{lo:.4f}, {hi:.4f}]   n_pos={int(yt[:, i].sum())}")

# ---- 4. weight-fit stability ---------------------------------------------------
say("\n== 4. Stability of val-fitted weights (bootstrap val patients, refit, score on test) ==")
specs = ["densenet121@224", "convnext@224", "coatnet@224", "densenet121@320", "convnext@320"]
vf = ["_densenet121_val_flipscale.npz", "_convnext_tiny.fb_in22k_ft_in1k_val_flipscale.npz",
      "_coatnet_0_rw_224.sw_in1k_val_scale.npz", "_320_val_scale.npz",
      "_convnext_tiny.fb_in22k_ft_in1k_320_val_flipscale.npz"]
yv = ld(vf[0])[0]
pv = np.stack([ld(f)[1] for f in vf])
pts = np.stack([p_dn224, p_cnx224, p_coat, p_dn320, p_cnx])
vp = val.patient_id.values
uv, vinv = np.unique(vp, return_inverse=True)
by_pat = [np.where(vinv == u)[0] for u in range(len(uv))]
ws, ts = [], []
for b in range(30):
    pick = rng.integers(0, len(uv), len(uv))
    rows = np.concatenate([by_pat[u] for u in pick])
    w, _ = ensemble2.fit_weights(yv[rows], pv[:, rows])
    ws.append(w)
    ts.append(fast_auc(yt, np.tensordot(w, pts, 1)))
ws = np.array(ws)
say("mean weight per model over 30 refits: " + ", ".join(f"{s}={m:.2f}" for s, m in zip(specs, ws.mean(0))))
say(f"test AUROC with refit weights: mean {np.mean(ts):.4f}, min {np.min(ts):.4f}, max {np.max(ts):.4f} "
    f"(uniform 5-model {fast_auc(yt, uni5):.4f}, reported {fast_auc(yt, final):.4f})")

# ---- 5. calibration ------------------------------------------------------------
say("\n== 5. Calibration of final ensemble (test) ==")
fv = 0.05 * ld(vf[2])[1] + 0.30 * ld(vf[3])[1] + 0.65 * ld(vf[4])[1]


def ece(y, p, bins=10):
    e, n = 0.0, len(y)
    ix = np.minimum((p * bins).astype(int), bins - 1)
    for b in range(bins):
        m = ix == b
        if m.any():
            e += m.sum() / n * abs(y[m].mean() - p[m].mean())
    return e


def logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


rows = []
cal = np.zeros_like(final)
for i, d in enumerate(DISEASES):
    lr = LogisticRegression(C=1e6, max_iter=1000).fit(logit(fv[:, i:i + 1]), yv[:, i])
    cal[:, i] = lr.predict_proba(logit(final[:, i:i + 1]))[:, 1]
    rows.append((d, yt[:, i].mean(), final[:, i].mean(), ece(yt[:, i], final[:, i]), ece(yt[:, i], cal[:, i]),
                 brier_score_loss(yt[:, i], final[:, i]), brier_score_loss(yt[:, i], cal[:, i])))
c = pd.DataFrame(rows, columns=["disease", "prevalence", "mean_pred_raw", "ECE_raw", "ECE_platt", "Brier_raw", "Brier_platt"])
say(c.round(4).to_string(index=False))
say(f"mean ECE raw {c.ECE_raw.mean():.4f} -> after per-class Platt scaling fitted on val {c.ECE_platt.mean():.4f}; "
    f"AUROC is unchanged by monotone recalibration ({fast_auc(yt, cal):.4f}).")
say("NOTE: training used pos_weight (up to 50x) so raw outputs over-predict rare findings; use the Platt-"
    "calibrated values (or per-class thresholds) if real probabilities are needed.")

# ---- 6. AUPRC -----------------------------------------------------------------
say("\n== 6. Average precision (AUPRC) vs prevalence (test) ==")
ap = [average_precision_score(yt[:, i], final[:, i]) for i in range(14)]
for i, d in enumerate(DISEASES):
    say(f"{d:<20s} AP {ap[i]:.3f}  prevalence {yt[:, i].mean():.3f}")
say(f"mean AP {np.mean(ap):.3f}")

# ---- 7. subgroups ---------------------------------------------------------------
say("\n== 7. Subgroup mean AUROC (test, final ensemble) ==")
age = pd.to_numeric(test.age, errors="coerce")
groups = {"sex=M": test.sex == "M", "sex=F": test.sex == "F", "view=PA": test.view == "PA",
          "view=AP": test.view == "AP", "age<40": age < 40, "age 40-64": (age >= 40) & (age < 65), "age>=65": age >= 65}
for g, m in groups.items():
    m = m.values
    a = auc_w(yt[m], final[m], None)
    say(f"{g:<10s} n={m.sum():>6d}  mean AUROC {np.nanmean(a):.4f}  ({len(a)} classes scorable)")

# ---- 8. val -> test gap -----------------------------------------------------------
say("\n== 8. Validation vs test (same TTA mode) ==")
for s, f, pt_ in zip(specs, vf, pts):
    say(f"{s:<18s} val {fast_auc(yv, ld(f)[1]):.4f}  test {fast_auc(yt, pt_):.4f}")
say(f"{'final ensemble':<18s} val {fast_auc(yv, fv):.4f}  test {fast_auc(yt, final):.4f}")
(OUT / "validation_report_stats.txt").write_text("\n".join(L))
