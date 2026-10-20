"""Train DenseNet121 for 14-label chest X-ray classification.

Resumable: after every epoch the full state (model, optimizer, scheduler, scaler, log)
is saved to outputs/checkpoints/last.pt. Re-running this script continues from the
next epoch, so a shutdown only costs the epoch in progress.

Best-by-validation weights go to outputs/checkpoints/best.pt.
When all epochs are done it runs evaluate.py automatically.
"""
import os
import time

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

import evaluate
from common import (CACHE_PATH, CKPT_PATH, DISEASES, EMA, OUTPUTS, TAG, build_model, cache_batches,
                    gpu_batch, load_config, per_class_auc, predict)
from data_paths import read_splits

LAST_PATH = CKPT_PATH.parent / "last.pt"


def compute_pos_weight(frame, cap):
    pos = frame[DISEASES].sum().values.astype(float)
    neg = len(frame) - pos
    return torch.tensor(np.minimum(neg / np.maximum(pos, 1), cap), dtype=torch.float32)


def atomic_save(obj, path):
    # Write a temp file then rename, so an interrupted save never leaves a half-written file.
    tmp = path.with_suffix(path.suffix + ".tmp")
    torch.save(obj, tmp)
    os.replace(tmp, path)


def main():
    cfg = load_config()
    d, t = cfg["data"], cfg["train"]
    # Optional overrides (defaults reproduce the original 224 px runs exactly):
    # CXR_EPOCHS, CXR_BATCH (micro-batch), CXR_ACCUM (grad-accumulation steps), CXR_EMA (decay, 0=off)
    t["epochs"] = int(os.environ.get("CXR_EPOCHS", t["epochs"]))
    accum = int(os.environ.get("CXR_ACCUM", "1"))
    t["batch_size"] = int(os.environ.get("CXR_BATCH", t["batch_size"]))
    ema_decay = float(os.environ.get("CXR_EMA", "0"))
    cfg["seed"] = int(os.environ.get("CXR_SEED", cfg["seed"]))
    torch.manual_seed(cfg["seed"])
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("device:", device)
    torch.backends.cudnn.benchmark = True  # autotune conv kernels; ~13% faster here

    df = read_splits()
    train_df = df[df["split"] == "train"]
    val_df = df[df["split"] == "val"]
    if t["train_subset"]:
        train_df = train_df.sample(t["train_subset"], random_state=cfg["seed"])
    assert CACHE_PATH.exists(), "run cache_images.py first"
    print(f"train {len(train_df)}  val {len(val_df)}  source: cache")

    n_steps = -(-len(train_df) // t["batch_size"])  # ceil (micro-batches)
    def train_batches(epoch):
        return cache_batches(CACHE_PATH, train_df, t["batch_size"], shuffle=True,
                             seed=cfg["seed"] + epoch)
    def val_batches():
        return cache_batches(CACHE_PATH, val_df, t["batch_size"] * 2, shuffle=False)

    model = build_model(t["pretrained"]).to(device)
    pos_weight = None
    if t["class_weighted"]:
        pos_weight = compute_pos_weight(train_df, t["max_pos_weight"]).to(device)
        print("pos_weight:", dict(zip(DISEASES, pos_weight.cpu().numpy().round(2))))
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)

    optimizer = torch.optim.AdamW(model.parameters(), lr=t["lr"], weight_decay=t["weight_decay"])
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=t["epochs"])
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")
    ema = EMA(model, ema_decay) if ema_decay > 0 else None
    print(f"epochs {t['epochs']}  micro-batch {t['batch_size']} x accum {accum}  ema {ema_decay}", flush=True)

    # ---- resume from the last completed epoch, if any -----------------------
    start_epoch, best, log = 1, -1.0, []
    if LAST_PATH.exists():
        ck = torch.load(LAST_PATH, map_location=device, weights_only=False)
        model.load_state_dict(ck["model"])
        optimizer.load_state_dict(ck["optimizer"])
        scheduler.load_state_dict(ck["scheduler"])
        if ck["scaler"]:  # empty when saved from a disabled scaler (CPU)
            scaler.load_state_dict(ck["scaler"])
        if ema is not None and ck.get("ema"):
            ema.model.load_state_dict(ck["ema"])
            ema.updates = ck["ema_updates"]
        start_epoch, best, log = ck["epoch"] + 1, ck["best"], ck["log"]
        print(f"resumed after epoch {ck['epoch']} (best val AUROC {best:.4f})", flush=True)

    CKPT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # ---- train --------------------------------------------------------------
    for epoch in range(start_epoch, t["epochs"] + 1):
        model.train()
        optimizer.zero_grad(set_to_none=True)
        t0, total, n = time.time(), 0.0, 0
        for step, (x, y) in enumerate(train_batches(epoch), 1):
            x = gpu_batch(x, True, device)
            y = y.to(device, non_blocking=True)
            with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=device.type == "cuda"):
                logits = model(x)
            loss = criterion(logits.float(), y)
            scaler.scale(loss / accum).backward()
            if step % accum == 0:
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad(set_to_none=True)
                if ema is not None:
                    ema.update(model)
            total += loss.item() * len(x)
            n += len(x)
            if step % 500 == 0:
                print(f"  epoch {epoch} step {step}/{n_steps} loss {total / n:.4f}", flush=True)
        scheduler.step()

        eval_model = ema.model if ema is not None else model
        yv, pv = predict(eval_model, val_batches(), device)
        val_auc = float(np.nanmean(per_class_auc(yv, pv)))
        row = {"epoch": epoch, "train_loss": round(total / n, 5),
               "val_mean_auc": round(val_auc, 5), "seconds": round(time.time() - t0)}
        log.append(row)
        print(row, flush=True)

        if val_auc > best:
            best = val_auc
            atomic_save({"model": eval_model.state_dict(), "epoch": epoch,
                         "val_mean_auc": val_auc, "config": cfg}, CKPT_PATH)
            print(f"  saved best checkpoint (val AUROC {val_auc:.4f})", flush=True)

        # Full state after every epoch, so a restart continues from here.
        atomic_save({"model": model.state_dict(), "optimizer": optimizer.state_dict(),
                     "scheduler": scheduler.state_dict(), "scaler": scaler.state_dict(),
                     "epoch": epoch, "best": best, "log": log, "config": cfg,
                     "ema": ema.model.state_dict() if ema is not None else None,
                     "ema_updates": ema.updates if ema is not None else 0}, LAST_PATH)
        pd.DataFrame(log).to_csv(OUTPUTS / f"train_log{TAG}.csv", index=False)

    print("training done. best val mean AUROC:", round(best, 4), flush=True)
    evaluate.main()


if __name__ == "__main__":
    main()
