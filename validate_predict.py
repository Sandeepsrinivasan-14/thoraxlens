"""Check that predict.py (raw PNGs -> final ensemble) reproduces the cached test-set ensemble predictions."""
import subprocess
import sys

import numpy as np
import pandas as pd

from common import DISEASES, OUTPUTS

N = 64
PRED = OUTPUTS / "preds"
PARTS = [("_coatnet_0_rw_224.sw_in1k_test_scale.npz", 0.05),
         ("_320_test_scale.npz", 0.30),
         ("_convnext_tiny.fb_in22k_ft_in1k_320_test_flipscale.npz", 0.65)]

df = pd.read_csv(OUTPUTS / "splits.csv")
test = df[df["split"] == "test"].reset_index(drop=True)
idx = np.sort(np.random.default_rng(0).choice(len(test), N, replace=False))
paths = test["path"].iloc[idx].tolist()
out = OUTPUTS / "validation" / "predict_check.csv"
subprocess.run([sys.executable, "predict.py", *paths, "--out", str(out)],
               check=True, stdout=subprocess.DEVNULL)
got = pd.read_csv(out, index_col=0).values
ref = sum(w * np.load(PRED / f)["p"][idx] for f, w in PARTS)
d = np.abs(got - ref)
rep = (f"predict.py vs cached ensemble on {N} random test images\n"
       f"max abs diff {d.max():.5f}  mean abs diff {d.mean():.6f}\n"
       f"max |diff| relative to prob range: ref min {ref.min():.4f} max {ref.max():.4f}\n"
       f"rank agreement (Spearman, per image over 14 classes) min "
       f"{min(pd.Series(a).corr(pd.Series(b), method='spearman') for a, b in zip(got, ref)):.4f}\n")
print(rep)
(OUTPUTS / "validation" / "predict_check.txt").write_text(rep)
