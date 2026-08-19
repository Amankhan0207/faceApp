"""Face detection and embedding. The only part of the app that touches a model.

Two ONNX models run locally (no API, no internet after first download):
  RetinaFace  finds faces and returns boxes
  ArcFace     turns each face into a 512-number vector

The device is chosen from settings and can be switched at runtime; the model
reloads on the next call.
"""

import threading

import numpy as np
from PIL import Image, ImageOps

import config

try:
    import pillow_heif

    pillow_heif.register_heif_opener()
    HEIC_OK = True
except ImportError:
    HEIC_OK = False


_engine_lock = threading.Lock()
_engine = None
_engine_key = None


def available_devices() -> dict:
    """What this machine can actually run, for the settings screen."""
    result = {"cpu": True, "cuda": False, "coreml": False, "providers": [], "error": None}
    try:
        import onnxruntime as ort

        providers = ort.get_available_providers()
        result["providers"] = providers
        result["cuda"] = "CUDAExecutionProvider" in providers
        result["coreml"] = "CoreMLExecutionProvider" in providers
    except ImportError as exc:
        result["error"] = str(exc)
    return result


def resolve_device(preference: str) -> str:
    """Turn the 'auto' setting into a concrete device, falling back safely."""
    devices = available_devices()
    if preference == "cuda":
        return "cuda" if devices["cuda"] else "cpu"
    if preference == "coreml":
        return "coreml" if devices["coreml"] else "cpu"
    if preference == "auto":
        if devices["cuda"]:
            return "cuda"
        if devices["coreml"]:
            return "coreml"
    return "cpu"


def _providers_for(device: str) -> list:
    if device == "cuda":
        return ["CUDAExecutionProvider", "CPUExecutionProvider"]
    if device == "coreml":
        return ["CoreMLExecutionProvider", "CPUExecutionProvider"]
    return ["CPUExecutionProvider"]


def get_engine():
    """Load the model, or reuse it if the relevant settings have not changed."""
    global _engine, _engine_key

    settings = config.load()
    device = resolve_device(settings["device"])
    key = (device, settings["model"], int(settings["det_size"]))

    with _engine_lock:
        if _engine is not None and _engine_key == key:
            return _engine, device

        from insightface.app import FaceAnalysis

        app = FaceAnalysis(
            name=settings["model"],
            providers=_providers_for(device),
            allowed_modules=["detection", "recognition"],
        )
        app.prepare(
            ctx_id=0 if device == "cuda" else -1,
            det_size=(int(settings["det_size"]), int(settings["det_size"])),
        )
        _engine, _engine_key = app, key
        return app, device


def unload():
    """Drop the loaded model so the next call picks up new settings."""
    global _engine, _engine_key
    with _engine_lock:
        _engine, _engine_key = None, None


# ---------------------------------------------------------------- images

def load_bgr(path, max_side=None):
    """Read an image as BGR for the model, honouring EXIF rotation.

    Phone photos carry a rotation flag rather than rotated pixels. Ignoring it
    feeds the detector sideways faces, which it will simply miss.
    """
    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
        if max_side:
            longest = max(img.size)
            if longest > max_side:
                scale = max_side / longest
                new_size = (max(1, int(img.width * scale)), max(1, int(img.height * scale)))
                img = img.resize(new_size, Image.LANCZOS)
        rgb = np.asarray(img)
    return rgb[:, :, ::-1].copy()


def make_thumbnail(src, dest, size):
    with Image.open(src) as img:
        img = ImageOps.exif_transpose(img).convert("RGB")
        img.thumbnail((size, size), Image.LANCZOS)
        dest.parent.mkdir(parents=True, exist_ok=True)
        img.save(dest, "JPEG", quality=82, optimize=True)


def crop_face(bgr, bbox, dest, pad=0.35, size=200):
    """Save a padded square crop of one face for the picker."""
    height, width = bgr.shape[:2]
    x1, y1, x2, y2 = [float(v) for v in bbox]
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    half = max(x2 - x1, y2 - y1) * (1 + pad) / 2
    left = max(0, int(cx - half))
    top = max(0, int(cy - half))
    right = min(width, int(cx + half))
    bottom = min(height, int(cy + half))
    if right <= left or bottom <= top:
        return False
    patch = bgr[top:bottom, left:right][:, :, ::-1]
    dest.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(patch).resize((size, size), Image.LANCZOS).save(
        dest, "JPEG", quality=88
    )
    return True


# ---------------------------------------------------------------- faces

def detect(bgr, min_face_px):
    """Return faces sorted largest first, small ones dropped."""
    app, _ = get_engine()
    faces = app.get(bgr)
    kept = []
    for face in faces:
        x1, y1, x2, y2 = face.bbox
        if (x2 - x1) < min_face_px or (y2 - y1) < min_face_px:
            continue
        kept.append(face)
    kept.sort(key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]), reverse=True)
    return kept


def normalise(vector):
    vector = np.asarray(vector, dtype=np.float32)
    norm = np.linalg.norm(vector)
    return vector / norm if norm else vector


def average_reference(vectors):
    """Blend several reference faces into one vector.

    Averaging a few shots of the same person cancels out the quirks of any
    single frame: an odd angle, a squint, harsh flash.
    """
    stacked = np.stack([normalise(v) for v in vectors])
    return normalise(stacked.mean(axis=0))


def similarity_matrix(face_vectors, reference_vectors):
    """Cosine similarity for every face against every reference, in one dot product."""
    if not len(face_vectors) or not len(reference_vectors):
        return np.zeros((len(face_vectors), len(reference_vectors)), dtype=np.float32)
    faces = np.stack([normalise(v) for v in face_vectors])
    refs = np.stack([normalise(v) for v in reference_vectors])
    return faces @ refs.T
