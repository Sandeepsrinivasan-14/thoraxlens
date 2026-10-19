"""Evaluate the best checkpoint on the official test split (per-disease AUROC)."""
import os

import numpy as np
import pandas as pd
import torch

from common import (CACHE_PATH, CKPT_PATH, DISEASES, OUTPUTS, TAG, build_model, cache_batches,
                    load_config, per_class_auc, predict)


def main():
    cfg = load_config()
    t = cfg["train"]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    torch.backends.cudnn.benchmark = True  # autotune conv kernels; ~13% faster here

    ckpt = torch.load(CKPT_PATH, map_location=device, weights_only=False)
    model = build_model(pretrained=False).to(device)
    model.load_state_dict(ckpt["model"])
    print(f"loaded epoch {ckpt['epoch']} (val mean AUROC {ckpt['val_mean_auc']:.4f})")

    df = pd.read_csv(OUTPUTS / "splits.csv")
    test_df = df[df["split"] == "test"]  # keep index: it is the cache row
    batches = cache_batches(CACHE_PATH, test_df, 32, shuffle=False)
    y, p = predict(model, batches, device, tta=os.environ.get("CXR_TTA", "none"))
    auc = per_class_auc(y, p)
    results = pd.DataFrame({"disease": DISEASES, "auroc": auc.round(4),
                            "n_positive": y.sum(axis=0).astype(int)})
    results.to_csv(OUTPUTS / f"test_auroc{TAG}.csv", index=False)
    print(results.to_string(index=False))
    print(f"\nmean test AUROC (classes with both labels present): {np.nanmean(auc):.4f}")
    print("wrote", OUTPUTS / f"test_auroc{TAG}.csv")


if __name__ == "__main__":
    main()
