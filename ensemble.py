"""Average the test predictions of several trained models and report per-class AUROC.

Usage: python ensemble.py densenet121 convnext_tiny.fb_in22k_ft_in1k [more archs...]
Each arch uses its own checkpoints_<arch>/best.pt (densenet121 uses checkpoints/best.pt).
"""
import sys

import numpy as np
import pandas as pd
import torch

import common
from common import CACHE_PATH, DISEASES, OUTPUTS, cache_batches, load_config, per_class_auc, predict
from data_paths import read_splits


def predictions(arch, test_df, bs, device):
    common.ARCH = arch  # build_model reads the module-level ARCH
    tag = "" if arch == "densenet121" else f"_{arch}"
    ck = torch.load(OUTPUTS / f"checkpoints{tag}" / "best.pt", map_location=device, weights_only=False)
    model = common.build_model(pretrained=False).to(device)
    model.load_state_dict(ck["model"])
    y, p = predict(model, cache_batches(CACHE_PATH, test_df, bs, shuffle=False), device)
    del model
    torch.cuda.empty_cache()
    return y, p


def main(archs):
    cfg = load_config()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    df = read_splits()
    test_df = df[df["split"] == "test"]
    ys, ps = None, []
    for a in archs:
        y, p = predictions(a, test_df, cfg["train"]["batch_size"] * 2, device)
        ys = y
        ps.append(p)
        print(f"{a}: mean test AUROC {np.nanmean(per_class_auc(y, p)):.4f}")
    auc = per_class_auc(ys, np.mean(ps, axis=0))
    res = pd.DataFrame({"disease": DISEASES, "auroc": auc.round(4)})
    res.to_csv(OUTPUTS / "test_auroc_ensemble.csv", index=False)
    print(res.to_string(index=False))
    print(f"\nensemble mean test AUROC: {np.nanmean(auc):.4f}")


if __name__ == "__main__":
    main(sys.argv[1:])
