"""Shared code: config, labels, dataset, model, prediction and metrics."""
import os
import queue
import threading
from pathlib import Path

import math

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.transforms as T
import yaml
from PIL import Image
from sklearn.metrics import roc_auc_score
from torch.utils.data import Dataset
from torchvision import models

ROOT = Path(__file__).resolve().parent
OUTPUTS = ROOT / "outputs"
# Architecture is chosen with the CXR_ARCH env var. DenseNet121 keeps the original paths;
# every other model writes to its own checkpoints_<arch>/ folder and *_<arch>.csv files.
ARCH = os.environ.get("CXR_ARCH", "densenet121")
# Input resolution is chosen with CXR_IMG (default 224 = original behaviour and file names).
IMG = int(os.environ.get("CXR_IMG", "224"))
# Optional CXR_SEED re-trains with another random seed into separate files (suffix _seed<N>).
SEED = os.environ.get("CXR_SEED")
TAG = (("" if ARCH == "densenet121" else f"_{ARCH}") + ("" if IMG == 224 else f"_{IMG}")
       + (f"_seed{SEED}" if SEED else ""))
CKPT_PATH = OUTPUTS / f"checkpoints{TAG}" / "best.pt"

# 14 disease labels. "No Finding" is represented as all-zeros.
DISEASES = [
    "Atelectasis", "Cardiomegaly", "Effusion", "Infiltration", "Mass", "Nodule",
    "Pneumonia", "Pneumothorax", "Consolidation", "Edema", "Emphysema",
    "Fibrosis", "Pleural_Thickening", "Hernia",
]


def load_config(path=ROOT / "configs" / "default.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


def read_list(path):
    with open(path) as f:
        return {line.strip() for line in f if line.strip()}


def build_transforms(size, train):
    ops = [T.Resize((size, size))]
    if train:
        ops.append(T.RandomAffine(degrees=5, translate=(0.03, 0.03), scale=(0.95, 1.05)))
    # No horizontal flips: laterality matters for chest findings.
    ops += [T.ToTensor(), T.Normalize(mean=[0.5], std=[0.25])]
    return T.Compose(ops)


CACHE_PATH = OUTPUTS / f"images_{IMG}.npy"  # built by cache_images.py


class ChestXrayDataset(Dataset):
    """Reads from the pre-resized uint8 cache when available (fast), else from the PNGs.

    The cache row for each image is its row in outputs/splits.csv, which is also
    frame.index, so frames must come from splits.csv without re-indexing.
    """

    def __init__(self, frame, transform, cache_path=None):
        self.paths = frame["path"].tolist()
        self.rows = frame.index.values
        self.labels = frame[DISEASES].values.astype(np.float32)
        self.transform = transform
        self.cache_path = cache_path
        self._cache = None  # opened lazily per worker; memmaps don't pickle well

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, i):
        if self.cache_path is not None:
            if self._cache is None:
                self._cache = np.load(self.cache_path, mmap_mode="r")
            img = Image.fromarray(np.array(self._cache[self.rows[i]]), mode="L")
        else:
            # convert("L") explicitly handles RGBA / palette images.
            img = Image.open(self.paths[i]).convert("L")
        return self.transform(img), torch.from_numpy(self.labels[i])


def build_model(pretrained=True):
    if ARCH != "densenet121":
        import timm  # pretrained weights are downloaded on first use
        return timm.create_model(ARCH, pretrained=pretrained, in_chans=1,
                                 num_classes=len(DISEASES))
    weights = models.DenseNet121_Weights.IMAGENET1K_V1 if pretrained else None
    model = models.densenet121(weights=weights)
    # Grayscale input: collapse the RGB first conv into one channel.
    old = model.features.conv0
    new = nn.Conv2d(1, old.out_channels, old.kernel_size, old.stride, old.padding, bias=False)
    with torch.no_grad():
        new.weight.copy_(old.weight.sum(dim=1, keepdim=True))
    model.features.conv0 = new
    model.classifier = nn.Linear(model.classifier.in_features, len(DISEASES))
    return model


def cache_batches(cache_path, frame, batch_size, shuffle, seed=0):
    """Yield (uint8 images, labels) batches straight from the pre-resized cache.

    No worker processes: the cache rows are cheap to read and all augmentation
    runs on the GPU in gpu_batch(), so the CPU never sits in the training loop.
    """
    cache = np.load(cache_path, mmap_mode="r")
    rows = frame.index.values
    labels = frame[DISEASES].values.astype(np.float32)
    order = np.random.default_rng(seed).permutation(len(rows)) if shuffle else np.arange(len(rows))
    def produce():
        for i in range(0, len(order), batch_size):
            idx = np.sort(order[i:i + batch_size])
            x = torch.from_numpy(cache[rows[idx]])
            if os.environ.get("CXR_PIN", "1") == "1":
                x = x.pin_memory()
            yield x, torch.from_numpy(labels[idx])

    # Read the next batches in a background thread so the GPU never waits on disk.
    q = queue.Queue(maxsize=8)
    done = object()

    def worker():
        try:
            for item in produce():
                q.put(item)
            q.put(done)
        except BaseException as e:  # surface loader errors in the training loop
            q.put(e)

    threading.Thread(target=worker, daemon=True).start()
    while True:
        item = q.get()
        if item is done:
            return
        if isinstance(item, BaseException):
            raise item
        yield item


def gpu_batch(x, train, device):
    """uint8 (B, S, S) -> normalized float (B, 1, S, S) on the GPU.

    Same preprocessing as build_transforms: [0,1] scaling, optional small random
    affine (rotation 5 deg, translate 3%, scale 0.95-1.05; zero fill), then
    Normalize(mean 0.5, std 0.25). No flips, since laterality matters.
    """
    x = x.to(device, non_blocking=True).unsqueeze(1).float().div_(255)
    if train:
        b = x.shape[0]
        ang = (torch.rand(b, device=device) * 2 - 1) * math.radians(5)
        scale = 0.95 + 0.1 * torch.rand(b, device=device)
        tx = (torch.rand(b, device=device) * 2 - 1) * 0.06  # 3% of width in [-1, 1] coords
        ty = (torch.rand(b, device=device) * 2 - 1) * 0.06
        cos, sin = torch.cos(ang) * scale, torch.sin(ang) * scale
        theta = torch.stack([torch.stack([cos, -sin, tx], 1),
                             torch.stack([sin, cos, ty], 1)], 1)
        grid = F.affine_grid(theta, list(x.shape), align_corners=False)
        x = F.grid_sample(x, grid, mode="bilinear", padding_mode="zeros", align_corners=False)
    return (x - 0.5) / 0.25


def tta_views(x, mode):
    """Yield test-time views of a normalized (B,1,S,S) batch.

    mode: none | flip | scale | flipscale. Scale views zoom by 5% in/out (same affine
    convention as training). Flip is optional because laterality matters; it is
    only used when it helps validation AUROC.
    """
    yield x
    if mode in ("flip", "flipscale"):
        yield torch.flip(x, dims=[3])
    if mode in ("scale", "flipscale"):
        for s in (0.95, 1.05):
            b = x.shape[0]
            theta = torch.zeros(b, 2, 3, device=x.device, dtype=x.dtype)
            theta[:, 0, 0] = s
            theta[:, 1, 1] = s
            grid = F.affine_grid(theta, list(x.shape), align_corners=False)
            # pad value is the normalized black level so borders match training's zero fill
            yield F.grid_sample(x + 2.0, grid, mode="bilinear", padding_mode="zeros",
                                align_corners=False) - 2.0


@torch.no_grad()
def predict(model, batches, device, tta="none"):
    """batches yields (uint8 images, labels) from cache_batches."""
    model.eval()
    probs, labels = [], []
    for x, y in batches:
        x = gpu_batch(x, False, device)
        acc = 0
        n = 0
        for v in tta_views(x, tta):
            with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=device.type == "cuda"):
                acc = acc + torch.sigmoid(model(v).float())
            n += 1
        probs.append((acc / n).cpu())
        labels.append(y)
    return torch.cat(labels).numpy(), torch.cat(probs).numpy()


class EMA:
    """Exponential moving average of model weights (buffers are copied)."""

    def __init__(self, model, decay=0.999):
        import copy
        self.model = copy.deepcopy(model).eval()
        for p in self.model.parameters():
            p.requires_grad_(False)
        self.decay = decay
        self.updates = 0

    @torch.no_grad()
    def update(self, model):
        self.updates += 1
        d = min(self.decay, (1 + self.updates) / (10 + self.updates))
        for e, m in zip(self.model.state_dict().values(), model.state_dict().values()):
            if e.dtype.is_floating_point:
                e.mul_(d).add_(m.detach(), alpha=1 - d)
            else:
                e.copy_(m)


def per_class_auc(y, p):
    """AUROC per disease; NaN where the class has no positives or no negatives."""
    out = []
    for i in range(y.shape[1]):
        ok = 0 < y[:, i].sum() < len(y)
        out.append(roc_auc_score(y[:, i], p[:, i]) if ok else np.nan)
    return np.array(out)
