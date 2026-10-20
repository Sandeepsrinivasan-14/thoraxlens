"""Machine-independent data locations. Deliberately free of torch so it is cheap to import/test.

Where the NIH ChestX-ray14 files live is configured, not hard-coded:

* ``configs/default.yaml`` holds repo-relative defaults (``data/...``).
* ``configs/local.yaml`` (git-ignored, optional) overrides them for your machine.
* Relative paths are resolved against the repository root; absolute paths (POSIX or
  Windows ``C:/...``) are used as written.
"""
import re
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent
OUTPUTS = ROOT / "outputs"
DEFAULT_CONFIG = ROOT / "configs" / "default.yaml"
LOCAL_CONFIG = ROOT / "configs" / "local.yaml"

_DATA_PATH_KEYS = ("metadata_csv", "images_dir", "train_val_list", "test_list")
_WINDOWS_ABS = re.compile(r"^[A-Za-z]:[\\/]")


def _merge(base, override):
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = value
    return base


def _resolve(value):
    value = str(value)
    if _WINDOWS_ABS.match(value) or Path(value).is_absolute():
        return value
    return str(ROOT / value)


def load_config(path=DEFAULT_CONFIG, local=None):
    """Load the YAML config, overlay ``configs/local.yaml`` if present, resolve data paths."""
    with open(path) as f:
        cfg = yaml.safe_load(f)
    local = LOCAL_CONFIG if local is None else Path(local)
    if local.exists():
        with open(local) as f:
            _merge(cfg, yaml.safe_load(f) or {})
    data = cfg.get("data", {})
    for key in _DATA_PATH_KEYS:
        if data.get(key):
            data[key] = _resolve(data[key])
    return cfg


def read_splits(config=None, splits_csv=None):
    """Read ``outputs/splits.csv`` and attach a ``path`` column for *this* machine.

    The committed CSV stores only image file names; the directory comes from the config, so the
    file contains no machine-specific paths. Row order (and therefore the image-cache index) is
    untouched.
    """
    df = pd.read_csv(OUTPUTS / "splits.csv" if splits_csv is None else splits_csv)
    images_dir = Path((config or load_config())["data"]["images_dir"])
    df["path"] = [str(images_dir / name) for name in df["image"]]
    return df
