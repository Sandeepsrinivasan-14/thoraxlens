"""Predict 14 chest-X-ray findings for one or more images with the final ensemble.

Usage:  python predict.py image1.png [image2.png ...] [--out preds.csv]

Uses the models and weights chosen on validation (see outputs/ensemble_v2_report_5model.txt);
the two 224 px models that got weight 0 are skipped. Same preprocessing as the training cache:
grayscale, bilinear resize, [0,1] -> (x-0.5)/0.25. Research use only - not a medical device.
"""
import argparse
import gc

import numpy as np
import pandas as pd
import torch
from PIL import Image

import common
from common import DISEASES, OUTPUTS, gpu_batch, tta_views

# (arch, image size, TTA mode, ensemble weight)
MODELS = [
    ("coatnet_0_rw_224.sw_in1k", 224, "scale", 0.05),
    ("densenet121", 320, "scale", 0.30),
    ("convnext_tiny.fb_in22k_ft_in1k", 320, "flipscale", 0.65),
]


def load(path, size):
    img = Image.open(path).convert("L").resize((size, size), Image.BILINEAR)
    return np.asarray(img, dtype=np.uint8)


@torch.no_grad()
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+")
    ap.add_argument("--out", default=None, help="optional CSV path")
    args = ap.parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    total = np.zeros((len(args.images), len(DISEASES)))
    for arch, size, mode, w in MODELS:
        tag = ("" if arch == "densenet121" else f"_{arch}") + ("" if size == 224 else f"_{size}")
        common.ARCH = arch
        ck = torch.load(OUTPUTS / f"checkpoints{tag}" / "best.pt", map_location=device, weights_only=False)
        model = common.build_model(pretrained=False).to(device)
        model.load_state_dict(ck["model"])
        model.eval()
        x = torch.from_numpy(np.stack([load(p, size) for p in args.images]))
        x = gpu_batch(x, False, device)
        acc, n = 0, 0
        for v in tta_views(x, mode):
            with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=device.type == "cuda"):
                acc = acc + torch.sigmoid(model(v).float())
            n += 1
        total += w * (acc / n).cpu().numpy()
        del model
        gc.collect()
        torch.cuda.empty_cache()
    df = pd.DataFrame(total, columns=DISEASES, index=[str(p) for p in args.images])
    for name, row in df.iterrows():
        print(f"\n{name}")
        for d, p in row.sort_values(ascending=False).items():
            print(f"  {d:<20s} {p:.3f}")
    if args.out:
        df.to_csv(args.out)
        print("\nwrote", args.out)


if __name__ == "__main__":
    main()
