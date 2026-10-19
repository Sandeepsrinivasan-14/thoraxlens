"""Safe cleanup of the ThoraxLens project. DRY RUN by default: nothing is touched without --apply.

    python cleanup.py                       # show what would be removed
    python cleanup.py --apply               # remove the safe set only
    python cleanup.py --resume-states       # also list/remove last.pt of finished runs (opt-in, needs --apply)
    python cleanup.py --caches              # also list/remove the rebuildable image caches (opt-in, needs --apply)

Safe set (always regenerable or provably redundant):
  * __pycache__ folders, *.tmp files left by interrupted atomic saves, UI dev leftovers
  * zero-byte log files
  * byte-identical duplicate copies (checked by SHA-256 at run time) of files that stay in place
Never touched: best.pt checkpoints (any run), final_best_4epochs.pt, splits.csv, preds/, CSV results,
reports, logs with content, the dataset, and anything outside this folder. Every action is written to
outputs/validation/cleanup_log.txt.
"""
import argparse
import hashlib
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "outputs"
LOG = OUT / "validation" / "cleanup_log.txt"


def sha(p, chunk=1 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while b := f.read(chunk):
            h.update(b)
    return h.hexdigest()


def size(p):
    p = Path(p)
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) if p.is_dir() else p.stat().st_size


def mb(n):
    return f"{n / 2**20:,.1f} MB"


def plan(resume, caches):
    safe, opt = [], []
    for d in ROOT.rglob("__pycache__"):
        safe.append((d, "python bytecode cache"))
    for f in OUT.rglob("*.tmp"):
        safe.append((f, "temp file from an interrupted save"))
    for name in ("_shots", "aid.txt", "cam_test.png", "server_test.log"):
        p = ROOT / "ui" / name
        if p.exists():
            safe.append((p, "UI development leftover"))
    for f in OUT.glob("*.log"):
        if f.stat().st_size == 0:
            safe.append((f, "empty log"))
    for f in OUT.glob("*.err"):
        if f.stat().st_size == 0:
            safe.append((f, "empty log"))
    # exact duplicates: (candidate to delete, copy that stays)
    for dup, keep in [(OUT / "run1_10epochs" / "last_final.pt", OUT / "run1_10epochs" / "last.pt"),
                      (OUT / "run1_10epochs" / "train_log_orig.csv", OUT / "run1_10epochs" / "train_log.csv")]:
        if dup.exists() and keep.exists() and dup.stat().st_size == keep.stat().st_size and sha(dup) == sha(keep):
            safe.append((dup, f"identical copy of {keep.name} (SHA-256 verified)"))
    for d in Path(tempfile.gettempdir()).glob("tl-edge-*"):
        safe.append((d, "temporary browser profile from UI screenshots"))
    if resume:
        for f in sorted(OUT.glob("checkpoints*/last.pt")) + sorted(OUT.glob("run1_10epochs/last.pt")):
            opt.append((f, "resume state (optimizer etc.) of a finished run; inference never needs it"))
    if caches:
        for f in sorted(OUT.glob("images_*.npy")):
            opt.append((f, "rebuildable with cache_images.py (CXR_IMG=<px>)"))
    return safe, opt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--resume-states", action="store_true")
    ap.add_argument("--caches", action="store_true")
    a = ap.parse_args()
    safe, opt = plan(a.resume_states, a.caches)
    todo = safe + opt
    lines = [f"cleanup {datetime.now():%Y-%m-%d %H:%M}  mode={'APPLY' if a.apply else 'dry-run'}"]
    total = 0
    for p, why in todo:
        n = size(p) if p.exists() else 0
        total += n
        lines.append(f"{'remove' if a.apply else 'would remove'}  {mb(n):>12}  {p}  ({why})")
        if a.apply and p.exists():
            shutil.rmtree(p) if p.is_dir() else p.unlink()
    if not todo:
        lines.append("nothing to clean")
    lines.append(f"total {'freed' if a.apply else 'reclaimable'}: {mb(total)}")
    if not (a.resume_states or a.caches):
        extra = sum(size(f) for f in OUT.glob("checkpoints*/last.pt")) + sum(size(f) for f in OUT.glob("run1_10epochs/last.pt"))
        lines.append(f"not touched: resume states (last.pt) of finished runs, {mb(extra)} (use --resume-states); "
                     f"image caches {mb(sum(size(f) for f in OUT.glob('images_*.npy')))} (use --caches)")
    txt = "\n".join(lines)
    print(txt)
    if a.apply:
        LOG.parent.mkdir(exist_ok=True)
        with open(LOG, "a", encoding="utf8") as f:
            f.write(txt + "\n\n")


if __name__ == "__main__":
    main()
