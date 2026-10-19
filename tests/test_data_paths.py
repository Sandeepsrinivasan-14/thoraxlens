"""Tests for machine-independent data locations (no torch needed)."""
import csv
from pathlib import Path

import pytest

import data_paths
from data_paths import ROOT, load_config, read_splits

REPO = Path(__file__).resolve().parent.parent


def test_default_config_is_repo_relative():
    cfg = load_config(local=REPO / "does-not-exist.yaml")
    images_dir = cfg["data"]["images_dir"]
    assert images_dir == str(ROOT / "data" / "images")
    assert "Users" not in images_dir


def test_local_yaml_overrides_only_listed_keys(tmp_path):
    local = tmp_path / "local.yaml"
    local.write_text("data:\n  images_dir: C:/somewhere/else/images\n")
    cfg = load_config(local=local)
    assert cfg["data"]["images_dir"] == "C:/somewhere/else/images"  # Windows absolute kept as is
    assert cfg["data"]["test_list"] == str(ROOT / "data" / "test_list.txt")  # untouched default
    assert cfg["seed"] == 42


def test_read_splits_builds_paths_from_config(tmp_path):
    splits = tmp_path / "splits.csv"
    splits.write_text("image,labels,split\n00000001_000.png,Cardiomegaly,train\n00000002_000.png,,test\n")
    cfg = {"data": {"images_dir": str(tmp_path / "imgs")}}
    df = read_splits(config=cfg, splits_csv=splits)
    assert list(df["image"]) == ["00000001_000.png", "00000002_000.png"]  # order unchanged
    assert df["path"].tolist() == [str(tmp_path / "imgs" / n) for n in df["image"]]


def test_read_splits_ignores_stale_machine_paths(tmp_path):
    splits = tmp_path / "splits.csv"
    splits.write_text("image,split,path\na.png,train,C:\\Users\\someone\\a.png\n")
    df = read_splits(config={"data": {"images_dir": "/data/images"}}, splits_csv=splits)
    assert df["path"].iloc[0] == str(Path("/data/images") / "a.png")


def test_committed_splits_csv_has_no_machine_paths():
    with open(REPO / "outputs" / "splits.csv", newline="") as f:
        header = next(csv.reader(f))
    assert "path" not in header and "image" in header
    head = (REPO / "outputs" / "splits.csv").read_text(errors="ignore")[:20000]
    assert "Users" not in head


@pytest.mark.parametrize("name", ["configs/default.yaml", "run_training.ps1", "ui/run_ui.bat",
                                  "chain_seeds.sh", "chain_convnext.sh"])
def test_no_hardcoded_user_directories(name):
    assert "sndps" not in (REPO / name).read_text()
