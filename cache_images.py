"""Decode and resize every image once into outputs/images_224.npy (uint8, N x S x S).

Training then reads raw pixels from this file instead of decoding 1024x1024 PNGs
on every epoch, which was the bottleneck (about 150 images/s on this CPU).
Row i of the cache = row i of outputs/splits.csv.

Usage:
  python cache_images.py
"""
from functools import partial
from multiprocessing import Pool

import numpy as np
import pandas as pd
from PIL import Image

from common import CACHE_PATH, IMG, OUTPUTS, load_config
from data_paths import read_splits



def load(path, size):
    img = Image.open(path).convert("L").resize((size, size), Image.BILINEAR)
    return np.asarray(img, dtype=np.uint8)


def main():
    cfg = load_config()
    SIZE = IMG
    df = read_splits()
    n = len(df)
    print(f"caching {n} images at {SIZE}x{SIZE} -> {CACHE_PATH}")

    cache = np.lib.format.open_memmap(CACHE_PATH, mode="w+", dtype=np.uint8, shape=(n, SIZE, SIZE))
    with Pool(8) as pool:
        for i, arr in enumerate(pool.imap(partial(load, size=SIZE), df["path"].tolist(), chunksize=64)):
            cache[i] = arr
            if (i + 1) % 10000 == 0:
                print(f"  {i + 1}/{n}")
    cache.flush()
    print("done:", CACHE_PATH)


if __name__ == "__main__":
    main()
