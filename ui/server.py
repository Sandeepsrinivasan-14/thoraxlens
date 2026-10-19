"""ThoraxLens local web app: upload a chest X-ray, get 14 finding scores from the final ensemble.

    python ui/server.py            # then open http://127.0.0.1:8000
    python ui/server.py --port 8100 --no-browser

Research use only. Not a medical device. The three models (CoAtNet-0@224, DenseNet121@320,
ConvNeXt-Tiny@320) stay loaded on the GPU between requests; images never leave this machine.
"""
import argparse
import collections
import io
import json
import sys
import threading
import time
import uuid
import webbrowser
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
import common  # noqa: E402
from common import DISEASES, OUTPUTS, gpu_batch, tta_views  # noqa: E402

DATA = HERE / "data"
STATIC = HERE / "static"
CAL = json.loads((DATA / "calibration.json").read_text())
SAMPLES = json.loads((DATA / "samples.json").read_text()) if (DATA / "samples.json").exists() else []
MAX_BYTES = 40 * 1024 * 1024

# key, display name, checkpoint arch, input px, TTA mode (chosen on validation), ensemble weight
MODELS = [
    ("coatnet", "CoAtNet-0", "coatnet_0_rw_224.sw_in1k", 224, "scale", CAL["weights"]["coatnet"]),
    ("densenet320", "DenseNet121", "densenet121", 320, "scale", CAL["weights"]["densenet320"]),
    ("convnext320", "ConvNeXt-Tiny", "convnext_tiny.fb_in22k_ft_in1k", 320, "flipscale", CAL["weights"]["convnext320"]),
]
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
LOCK = threading.Lock()
NET = {}
CACHE = collections.OrderedDict()  # analysis id -> dict(arr320=uint8, ...)
CAM_CACHE = {}
STATE = {"loaded": False, "error": None, "load_s": None}


def ckpt_dir(arch, px):
    tag = ("" if arch == "densenet121" else f"_{arch}") + ("" if px == 224 else f"_{px}")
    return OUTPUTS / f"checkpoints{tag}" / "best.pt"


def load_models():
    t0 = time.time()
    try:
        for key, _name, arch, px, _mode, _w in MODELS:
            common.ARCH = arch
            ck = torch.load(ckpt_dir(arch, px), map_location="cpu", weights_only=False)
            m = common.build_model(pretrained=False)
            m.load_state_dict(ck["model"])
            NET[key] = m.to(DEVICE).eval()
        warm = np.zeros((320, 320), np.uint8)  # first call per model pays cuDNN autotune; do it now
        for key, _n, _a, px, mode, _w in MODELS:
            score(NET[key], warm[:px, :px], mode)
        STATE["loaded"] = True
    except Exception as e:  # surfaced through /api/health
        STATE["error"] = repr(e)
    STATE["load_s"] = round(time.time() - t0, 1)


# ------------------------------------------------------------------ image helpers
def read_gray(raw):
    """bytes -> (PIL 'L' image, info dict). Handles 8/16-bit grayscale, RGB(A) and palette images."""
    im = Image.open(io.BytesIO(raw))
    info = {"format": im.format, "mode": im.mode, "width": im.width, "height": im.height, "warnings": []}
    if im.mode.startswith("I"):  # 16/32-bit grayscale
        a = np.asarray(im).astype(np.float32)
        lo, hi = np.percentile(a, [0.5, 99.5])
        im = Image.fromarray(np.clip((a - lo) / max(hi - lo, 1) * 255, 0, 255).astype(np.uint8), "L")
    elif im.mode in ("RGB", "RGBA", "P"):
        rgb = np.asarray(im.convert("RGB")).astype(np.int16)
        if np.abs(rgb[..., 0] - rgb[..., 1]).mean() + np.abs(rgb[..., 1] - rgb[..., 2]).mean() > 10:
            info["warnings"].append("The image has colour; it was converted to grayscale. Check that it is a radiograph.")
        im = im.convert("L")
    else:
        im = im.convert("L")
    a = np.asarray(im)
    info["mean"] = float(a.mean())
    info["std"] = float(a.std())
    ar = im.width / im.height
    if abs(ar - 1) > 0.2:
        info["warnings"].append(f"Aspect ratio {ar:.2f}: the image is squashed to a square, as in training (NIH images are square).")
    if min(im.width, im.height) < 512:
        info["warnings"].append("Low resolution (under 512 px). Fine findings may be missed.")
    if a.std() < 25:
        info["warnings"].append("Very low contrast; this may not be a chest radiograph.")
    k = max(a.shape[0] // 10, 1)
    frame = np.concatenate([a[:k].ravel(), a[-k:].ravel(), a[:, :k].ravel(), a[:, -k:].ravel()])
    if frame.mean() > 170:
        info["warnings"].append("The image border is very bright; it may be inverted (white background). Models were trained on dark-background films. Try the invert tool and re-run.")
    return im, info


def prep(im, px):
    return np.asarray(im.resize((px, px), Image.BILINEAR), dtype=np.uint8)


@torch.no_grad()
def score(model, arr, mode):
    x = gpu_batch(torch.from_numpy(arr)[None], False, DEVICE)
    acc, n = 0, 0
    for v in tta_views(x, mode):
        with torch.autocast(device_type=DEVICE.type, dtype=torch.float16, enabled=DEVICE.type == "cuda"):
            acc = acc + torch.sigmoid(model(v).float())
        n += 1
    return (acc / n)[0].cpu().numpy()


def calibrate(p):
    out = []
    for i, c in enumerate(CAL["platt"]):
        z = np.log(np.clip(p[i], 1e-6, 1 - 1e-6) / (1 - np.clip(p[i], 1e-6, 1 - 1e-6)))
        out.append(float(1 / (1 + np.exp(-(c["a"] * z + c["b"])))))
    return out


# ------------------------------------------------------------------ app
app = FastAPI(title="ThoraxLens", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.on_event("startup")
def _startup():
    threading.Thread(target=load_models, daemon=True).start()


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-store"})


@app.get("/api/health")
def health():
    gpu = None
    if DEVICE.type == "cuda":
        gpu = {"name": torch.cuda.get_device_name(0),
               "mem_used_mb": round(torch.cuda.memory_allocated() / 2**20),
               "mem_total_mb": round(torch.cuda.get_device_properties(0).total_memory / 2**20)}
    return {"ok": STATE["loaded"], "error": STATE["error"], "device": DEVICE.type, "gpu": gpu,
            "load_seconds": STATE["load_s"],
            "models": [{"key": k, "name": n, "px": px, "tta": mode, "weight": w, "loaded": k in NET}
                       for k, n, _a, px, mode, w in MODELS],
            "torch": torch.__version__}


@app.get("/api/config")
def config():
    return {"calibration": CAL,
            "samples": [{k: v for k, v in s.items() if k != "src"} for s in SAMPLES]}


@app.get("/api/metrics")
def metrics():
    return FileResponse(DATA / "metrics.json", media_type="application/json")


@app.post("/api/analyze")
async def analyze(file: UploadFile | None = File(None), sample: str | None = Form(None)):
    if not STATE["loaded"]:
        raise HTTPException(503, STATE["error"] or "Models are still loading, try again in a few seconds.")
    if sample:
        s = next((x for x in SAMPLES if x["id"] == sample), None)
        if not s:
            raise HTTPException(404, "unknown sample")
        p = Path(s["src"])
        raw = p.read_bytes() if p.exists() else (STATIC / "samples" / f"{sample}.jpg").read_bytes()
    elif file is not None:
        raw = await file.read()
        if len(raw) > MAX_BYTES:
            raise HTTPException(413, "File too large (limit 40 MB).")
    else:
        raise HTTPException(400, "send a file or a sample id")
    try:
        im, info = read_gray(raw)
    except Exception:
        raise HTTPException(415, "Could not read this file as an image. Use PNG or JPEG (DICOM is not supported).")

    aid = uuid.uuid4().hex[:12]

    def gen():
        t_all = time.time()
        with LOCK:
            yield json.dumps({"event": "start", "id": aid, "info": info}) + "\n"
            t0 = time.time()
            arrs = {224: prep(im, 224), 320: prep(im, 320)}
            yield json.dumps({"event": "stage", "name": "preprocess", "ms": round((time.time() - t0) * 1000)}) + "\n"
            total = np.zeros(len(DISEASES))
            for key, name, _arch, px, mode, w in MODELS:
                t1 = time.time()
                p = score(NET[key], arrs[px], mode)
                total += w * p
                yield json.dumps({"event": "model", "key": key, "name": name, "px": px, "tta": mode, "weight": w,
                                  "scores": [round(float(v), 5) for v in p],
                                  "ms": round((time.time() - t1) * 1000)}) + "\n"
            CACHE[aid] = {"arr320": arrs[320]}
            while len(CACHE) > 8:
                CACHE.popitem(last=False)
            yield json.dumps({"event": "done", "id": aid,
                              "ensemble": [round(float(v), 5) for v in total],
                              "calibrated": [round(v, 5) for v in calibrate(total)],
                              "total_ms": round((time.time() - t_all) * 1000), "device": DEVICE.type}) + "\n"

    return StreamingResponse(gen(), media_type="application/x-ndjson")


_LUT = None


def lut():
    global _LUT
    if _LUT is None:
        import matplotlib
        cm = matplotlib.colormaps["turbo"]
        _LUT = (cm(np.linspace(0, 1, 256))[:, :3] * 255).astype(np.uint8)
    return _LUT


def grad_cam(arr, cls):
    """Grad-CAM on DenseNet121@320, taken at the end of denseblock3 (20 x 20 cells)."""
    model = NET["densenet320"]
    x = gpu_batch(torch.from_numpy(arr)[None], False, DEVICE).requires_grad_(True)
    h, A = x, None
    with torch.enable_grad():
        for name, m in model.features.named_children():
            h = m(h)
            if name == "denseblock3":
                A = h
                A.retain_grad()
        out = F.adaptive_avg_pool2d(F.relu(h), 1).flatten(1)
        logit = model.classifier(out)[0, cls]
        model.zero_grad(set_to_none=True)
        logit.backward()
    w = A.grad.mean(dim=(2, 3), keepdim=True)
    cam = F.relu((w * A).sum(1, keepdim=True))
    cam = F.interpolate(cam, size=(320, 320), mode="bilinear", align_corners=False)[0, 0].detach().cpu().numpy()
    cam = cam - cam.min()
    return cam / (cam.max() + 1e-8)


@app.get("/api/cam")
def cam(id: str, cls: int):
    if id not in CACHE:
        raise HTTPException(404, "analysis expired, run it again")
    if not 0 <= cls < len(DISEASES):
        raise HTTPException(400, "bad class")
    key = (id, cls)
    if key not in CAM_CACHE:
        with LOCK:
            c = grad_cam(CACHE[id]["arr320"], cls)
        idx = (c * 255).astype(np.uint8)
        rgba = np.dstack([lut()[idx], (np.clip(c, 0, 1) ** 0.8 * 210).astype(np.uint8)])
        buf = io.BytesIO()
        Image.fromarray(rgba, "RGBA").save(buf, "PNG")
        CAM_CACHE[key] = buf.getvalue()
        if len(CAM_CACHE) > 60:
            CAM_CACHE.pop(next(iter(CAM_CACHE)))
    return Response(CAM_CACHE[key], media_type="image/png", headers={"Cache-Control": "max-age=600"})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()
    import uvicorn
    if not a.no_browser:
        threading.Timer(2.0, lambda: webbrowser.open(f"http://{a.host}:{a.port}")).start()
    uvicorn.run(app, host=a.host, port=a.port, log_level="warning")
