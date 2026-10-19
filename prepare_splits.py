"""Build outputs/splits.csv: labels and patient-level train/val/test split (image locations come from the config).

Test set = official test_list.txt. Train/val = train_val_list.txt, split by PATIENT so
no patient appears in both train and val.
"""

import numpy as np
import pandas as pd

from common import DISEASES, OUTPUTS, load_config, read_list


def load_metadata(csv_path):
    df = pd.read_csv(csv_path).rename(columns={
        "Image Index": "image",
        "Finding Labels": "labels",
        "Patient ID": "patient_id",
        "Patient Age": "age",
        "Patient Sex": "sex",
        "View Position": "view",
    })
    label_sets = df["labels"].str.split("|")
    for d in DISEASES:
        df[d] = label_sets.apply(lambda s, d=d: int(d in s))
    return df


def main():
    cfg = load_config()
    d = cfg["data"]
    df = load_metadata(d["metadata_csv"])

    trainval_names = read_list(d["train_val_list"])
    test_names = read_list(d["test_list"])
    assert not (trainval_names & test_names), "train_val and test lists overlap"

    tv = df[df["image"].isin(trainval_names)].copy()
    te = df[df["image"].isin(test_names)].copy()
    assert len(tv) + len(te) == len(df), "some images are in neither split list"

    rng = np.random.default_rng(cfg["seed"])
    patients = np.array(sorted(tv["patient_id"].unique()))
    rng.shuffle(patients)
    val_patients = set(patients[: int(len(patients) * d["val_fraction"])])
    tv["split"] = np.where(tv["patient_id"].isin(val_patients), "val", "train")
    te["split"] = "test"

    assert not (set(tv["patient_id"]) & set(te["patient_id"])), "patient leakage across splits"

    out = pd.concat([tv, te], ignore_index=True)

    OUTPUTS.mkdir(exist_ok=True)
    out.to_csv(OUTPUTS / "splits.csv", index=False)
    print(out["split"].value_counts().to_string())
    print("patients per split:", out.groupby("split")["patient_id"].nunique().to_dict())
    print("wrote", OUTPUTS / "splits.csv")


if __name__ == "__main__":
    main()
