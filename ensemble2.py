"""Ensemble with per-model TTA and validation-fitted weights (does not touch ensemble.py outputs).

Usage: python ensemble2.py densenet121 convnext_tiny.fb_in22k_ft_in1k@... densenet121@320 ...
Spec = <arch>[@<img size>] (default 224). Checkpoint dir follows common.py naming:
checkpoints{_arch unless densenet121}{_img unless 224}/best.pt, cache images_<img>.npy.

For each model: pick the TTA mode with the best VAL mean AUROC (none/flip/scale/flipscale),
then predict test with that mode only. Ensemble weights are fitted on VAL (greedy search on the
simplex, maximising val mean AUROC). The test set is only scored, never used for any choice.
Predictions are cached in outputs/preds/ so reruns are cheap. Writes
outputs/test_auroc_ensemble_v2.csv and outputs/ensemble_v2_report.txt.
"""
import itertools
import sys

import numpy as np
import pandas as pd
import torch

import common
from common import DISEASES, OUTPUTS, cache_batches, per_class_auc, predict

MODES = ["none", "flip", "scale", "flipscale"]
PRED = OUTPUTS / "preds"


def parse(spec):
    """<arch>[@<img>][#<seed>] -> (arch, img, seed or None)"""
    spec, _, seed = spec.partition("#")
    arch, _, img = spec.partition("@")
    return arch, int(img or 224), (seed or None)


def tag_of(arch, img, seed=None):
    return (("" if arch == "densenet121" else f"_{arch}") + ("" if img == 224 else f"_{img}")
            + (f"_seed{seed}" if seed else ""))


def mean_auc(y, p):
    return float(np.nanmean(per_class_auc(y, p)))


def model_preds(spec, frames, device):
    """Return dict: split -> (labels, probs) with the TTA mode chosen on val; plus mode, val auc."""
    arch, img, seed = parse(spec)
    tag = tag_of(arch, img, seed)
    cache = OUTPUTS / f"images_{img}.npy"
    PRED.mkdir(exist_ok=True)
    model = None

    def run(split, mode):
        nonlocal model
        f = PRED / f"{tag or '_densenet121'}_{split}_{mode}.npz"
        if f.exists():
            z = np.load(f)
            return z["y"], z["p"]
        if model is None:
            common.ARCH = arch
            ck = torch.load(OUTPUTS / f"checkpoints{tag}" / "best.pt", map_location=device,
                            weights_only=False)
            model = common.build_model(pretrained=False).to(device)
            model.load_state_dict(ck["model"])
        y, p = predict(model, cache_batches(cache, frames[split], 32, shuffle=False), device, tta=mode)
        np.savez(f, y=y, p=p)
        return y, p

    scores = {m: mean_auc(*run("val", m)) for m in MODES}
    best = max(scores, key=scores.get)
    print(f"{spec}: val AUROC by TTA {({k: round(v, 4) for k, v in scores.items()})} -> {best}", flush=True)
    out = {"val": run("val", best), "test": run("test", best), "mode": best, "scores": scores}
    del model
    torch.cuda.empty_cache()
    return out


def fit_weights(yv, pvs, step=0.05):
    """Greedy coordinate search on the simplex maximising val mean AUROC."""
    k = len(pvs)
    w = np.ones(k) / k
    cur = mean_auc(yv, np.tensordot(w, pvs, 1))
    for _ in range(30):
        improved = False
        for i, j in itertools.permutations(range(k), 2):
            if w[j] < step - 1e-9:
                continue
            w2 = w.copy()
            w2[i] += step
            w2[j] -= step
            s = mean_auc(yv, np.tensordot(w2, pvs, 1))
            if s > cur + 1e-6:
                w, cur, improved = w2, s, True
        if not improved:
            break
    return w, cur


def main(specs):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    df = pd.read_csv(OUTPUTS / "splits.csv")
    frames = {"val": df[df["split"] == "val"], "test": df[df["split"] == "test"]}
    res = {s: model_preds(s, frames, device) for s in specs}
    yv, yt = res[specs[0]]["val"][0], res[specs[0]]["test"][0]
    pv = np.stack([res[s]["val"][1] for s in specs])
    pt = np.stack([res[s]["test"][1] for s in specs])

    lines = []
    for s in specs:
        lines.append(f"{s}: TTA={res[s]['mode']} val {mean_auc(yv, res[s]['val'][1]):.4f} "
                     f"test {mean_auc(yt, res[s]['test'][1]):.4f}")
    w_u = np.ones(len(specs)) / len(specs)
    w_f, val_f = fit_weights(yv, pv)
    lines.append(f"uniform weights : val {mean_auc(yv, np.tensordot(w_u, pv, 1)):.4f} "
                 f"test {mean_auc(yt, np.tensordot(w_u, pt, 1)):.4f}")
    lines.append(f"fitted weights {dict(zip(specs, w_f.round(2)))}: val {val_f:.4f} "
                 f"test {mean_auc(yt, np.tensordot(w_f, pt, 1)):.4f}")
    # final choice made on VAL only
    use_fit = val_f > mean_auc(yv, np.tensordot(w_u, pv, 1)) + 0.0005
    w = w_f if use_fit else w_u
    auc = per_class_auc(yt, np.tensordot(w, pt, 1))
    out = pd.DataFrame({"disease": DISEASES, "auroc": auc.round(4)})
    out.to_csv(OUTPUTS / "test_auroc_ensemble_v2.csv", index=False)
    lines.append(f"FINAL ({'fitted' if use_fit else 'uniform'} weights, chosen on val): "
                 f"ensemble mean test AUROC {np.nanmean(auc):.4f}")
    txt = "\n".join(lines) + "\n\n" + out.to_string(index=False)
    (OUTPUTS / "ensemble_v2_report.txt").write_text(txt)
    print(txt)


if __name__ == "__main__":
    main(sys.argv[1:])
