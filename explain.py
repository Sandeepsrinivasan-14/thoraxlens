"""Explain a prediction for one test image.

Two methods:
  gradcam         Grad-CAM heatmap: where the model looks for a given disease.
  counterfactual  Smallest image edit (gradient-based) that pushes the disease
                  probability below cf_threshold. Shows what the model would need
                  to "not see" to call the finding absent. This is a model-based
                  counterfactual, not a clinical one.

Usage:
  python explain.py --image 00000013_005.png --disease Effusion --method both
"""
import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from PIL import Image

from common import (CKPT_PATH, DISEASES, OUTPUTS, build_model, build_transforms, load_config)


class GradCAM:
    """Hooks the last conv block; weights each channel by its mean gradient."""

    def __init__(self, model, layer):
        self.model = model
        self.acts, self.grads = None, None
        layer.register_forward_hook(self._save)

    def _save(self, module, inp, out):
        if not out.requires_grad:  # forward ran under torch.no_grad(); nothing to hook
            return
        self.acts = out
        out.register_hook(lambda g: setattr(self, "grads", g))

    def __call__(self, x, class_idx):
        logits = self.model(x)
        self.model.zero_grad(set_to_none=True)
        logits[0, class_idx].backward()
        weights = self.grads.mean(dim=(2, 3), keepdim=True)
        cam = F.relu((weights * self.acts).sum(dim=1, keepdim=True))
        cam = F.interpolate(cam, size=x.shape[-2:], mode="bilinear", align_corners=False)[0, 0]
        cam = cam.detach().cpu().numpy()
        return (cam - cam.min()) / (cam.max() - cam.min() + 1e-8)


def counterfactual(model, x, class_idx, cfg, device):
    """Optimise an additive edit delta so that P(disease) drops below cf_threshold.

    Loss = P(disease | x + delta) + l2 * ||delta||^2. Stops early once the threshold is met.
    The edited image is clamped to the normalised range of valid pixel values.
    """
    e = cfg["explain"]
    lo, hi = x.min().item(), x.max().item()
    delta = torch.zeros_like(x, requires_grad=True)
    opt = torch.optim.Adam([delta], lr=e["cf_lr"])
    with torch.no_grad():
        p0 = torch.sigmoid(model(x))[0, class_idx].item()
    p = p0
    for step in range(e["cf_steps"]):
        x_cf = torch.clamp(x + delta, lo, hi)
        p_t = torch.sigmoid(model(x_cf))[0, class_idx]
        loss = p_t + e["cf_l2"] * (delta ** 2).sum()
        opt.zero_grad()
        loss.backward()
        opt.step()
        p = p_t.item()
        if p < e["cf_threshold"]:
            break
    x_cf = torch.clamp(x + delta, lo, hi).detach()
    with torch.no_grad():
        p_final = torch.sigmoid(model(x_cf))[0, class_idx].item()
    return x_cf, p0, p_final, step + 1


def save_gradcam_panel(path, original, heat, title):
    fig, axes = plt.subplots(1, 2, figsize=(8, 4.2))
    axes[0].imshow(original, cmap="gray")
    axes[0].set_title("original")
    axes[1].imshow(original, cmap="gray")
    axes[1].imshow(heat, cmap="jet", alpha=0.4)
    axes[1].set_title("Grad-CAM overlay")
    for a in axes:
        a.axis("off")
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def save_counterfactual_panel(path, original, edited, delta, title):
    lim = np.abs(delta).max() + 1e-8
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.2))
    axes[0].imshow(original, cmap="gray")
    axes[0].set_title("original")
    axes[1].imshow(edited, cmap="gray")
    axes[1].set_title("counterfactual")
    im = axes[2].imshow(delta, cmap="bwr", vmin=-lim, vmax=lim)
    axes[2].set_title("edit (red = added, blue = removed)")
    fig.colorbar(im, ax=axes[2], fraction=0.046)
    for a in axes:
        a.axis("off")
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True, help="image file name, e.g. 00000013_005.png")
    ap.add_argument("--disease", required=True, choices=DISEASES)
    ap.add_argument("--method", default="both", choices=["gradcam", "counterfactual", "both"])
    args = ap.parse_args()

    cfg = load_config()
    d = cfg["data"]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(CKPT_PATH, map_location=device, weights_only=False)
    model = build_model(pretrained=False).to(device)
    model.load_state_dict(ckpt["model"])
    model.eval()
    for p_ in model.parameters():
        p_.requires_grad_(True)  # needed for backprop to the input

    img = Image.open(f"{d['images_dir']}/{args.image}").convert("L")
    x = build_transforms(d["image_size"], train=False)(img).unsqueeze(0).to(device)
    class_idx = DISEASES.index(args.disease)
    shown = np.asarray(img.resize((d["image_size"], d["image_size"])), dtype=np.float32) / 255.0

    out_dir = OUTPUTS / "explain"
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{args.image.rsplit('.', 1)[0]}_{args.disease}"

    if args.method in ("gradcam", "both"):
        heat = GradCAM(model, model.features)(x, class_idx)
        with torch.no_grad():
            prob = torch.sigmoid(model(x))[0, class_idx].item()
        path = out_dir / f"{stem}_gradcam.png"
        save_gradcam_panel(path, shown, heat, f"{args.disease}  P={prob:.3f}")
        print("wrote", path)

    if args.method in ("counterfactual", "both"):
        x_cf, p0, p1, steps = counterfactual(model, x, class_idx, cfg, device)
        # Undo Normalize(mean=0.5, std=0.25) so the panels show real intensities.
        orig_vis = x[0, 0].cpu().numpy() * 0.25 + 0.5
        cf_vis = x_cf[0, 0].cpu().numpy() * 0.25 + 0.5
        delta = cf_vis - orig_vis
        path = out_dir / f"{stem}_counterfactual.png"
        save_counterfactual_panel(path, orig_vis, cf_vis, delta,
                                  f"{args.disease}: P {p0:.3f} -> {p1:.3f} in {steps} steps")
        print(f"counterfactual: P({args.disease}) {p0:.3f} -> {p1:.3f} "
              f"(threshold {cfg['explain']['cf_threshold']}), steps {steps}")
        print("edit L2 norm:", round(float(np.linalg.norm(delta)), 3))
        print("wrote", path)
        print("NOTE: this shows what the model relies on, not verified clinical change.")


if __name__ == "__main__":
    main()
