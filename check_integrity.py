"""Check every image listed in outputs/splits.csv: exists, decodes, and reports mode/size.

Usage:
  python check_integrity.py               # all images
  python check_integrity.py --sample 2000 # random subset for a quick check
"""
import argparse
import os
from collections import Counter
from multiprocessing import Pool

import pandas as pd
from PIL import Image

from common import OUTPUTS


def check(path):
    if not os.path.exists(path):
        return path, "missing", None, None
    try:
        with Image.open(path) as im:
            im.verify()  # detects truncated / corrupt PNG streams
        with Image.open(path) as im:
            return path, "ok", im.mode, im.size
    except Exception as e:
        return path, f"error: {type(e).__name__}", None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    df = pd.read_csv(OUTPUTS / "splits.csv")
    paths = df["path"].tolist()
    if args.sample:
        paths = df["path"].sample(args.sample, random_state=0).tolist()

    with Pool(args.workers) as pool:
        rows = list(pool.imap(check, paths, chunksize=64))

    report = pd.DataFrame(rows, columns=["path", "status", "mode", "size"])
    report.to_csv(OUTPUTS / "integrity_report.csv", index=False)

    print(f"checked: {len(report)}")
    print("status:", report["status"].value_counts().to_dict())
    print("modes:", Counter(report["mode"].dropna()).most_common())
    print("sizes:", Counter(report["size"].dropna().map(str)).most_common(5))
    bad = report[report["status"] != "ok"]
    if len(bad):
        print(f"{len(bad)} problem files, see {OUTPUTS / 'integrity_report.csv'}")


if __name__ == "__main__":
    main()
