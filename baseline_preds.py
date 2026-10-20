"""Cache plain (no-TTA) test predictions of the three 224 px baseline models, for a paired comparison."""
import numpy as np, pandas as pd, torch
import common
from common import OUTPUTS, cache_batches, predict, per_class_auc
from data_paths import read_splits

device = torch.device("cuda")
df = read_splits()
test = df[df["split"] == "test"]
cache = OUTPUTS / "images_224.npy"
for arch, tag in [("densenet121", ""), ("convnext_tiny.fb_in22k_ft_in1k", "_convnext_tiny.fb_in22k_ft_in1k"),
                  ("coatnet_0_rw_224.sw_in1k", "_coatnet_0_rw_224.sw_in1k")]:
    common.ARCH = arch
    ck = torch.load(OUTPUTS / f"checkpoints{tag}" / "best.pt", map_location=device, weights_only=False)
    m = common.build_model(pretrained=False).to(device)
    m.load_state_dict(ck["model"])
    y, p = predict(m, cache_batches(cache, test, 32, shuffle=False), device, tta="none")
    np.savez(OUTPUTS / "preds" / f"{tag or '_densenet121'}_test_none.npz", y=y, p=p)
    print(arch, round(float(np.nanmean(per_class_auc(y, p))), 4), flush=True)
    del m; torch.cuda.empty_cache()
