"""Settings, stored as a single JSON file. No database anywhere in this project."""

import json
import os
import threading
from pathlib import Path

# Everything lives under one folder. Override with the FACESORT_DATA env var.
DATA_ROOT = Path(os.environ.get("FACESORT_DATA", Path.home() / "FaceSort")).expanduser()
EVENTS_DIR = DATA_ROOT / "events"
SETTINGS_FILE = DATA_ROOT / "settings.json"

DEFAULTS = {
    # auto | cpu | cuda | coreml
    "device": "auto",
    "model": "buffalo_l",
    # Detector input square. Bigger finds smaller faces but runs slower.
    "det_size": 640,
    # Long edge cap before detection. Protects memory on 45MP files.
    "max_image_side": 2200,
    # Faces narrower than this are ignored (back row of group shots).
    "min_face_px": 40,
    # Cosine similarity cut-off for "same person".
    "threshold": 0.42,
    # Keep face vectors after a run so re-matching is instant.
    "cache_embeddings": True,
    "thumb_size": 420,
    # Copy matched files, or hard-link them to save disk.
    "copy_mode": "copy",
    "admin_username": "admin",
    "admin_password": "admin123",
    "google_client_id": "",
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_user": "",
    "smtp_password": "",
}

_lock = threading.Lock()
_cache = None


def ensure_dirs():
    EVENTS_DIR.mkdir(parents=True, exist_ok=True)


def load():
    global _cache
    with _lock:
        if _cache is not None:
            return dict(_cache)
        ensure_dirs()
        values = dict(DEFAULTS)
        if SETTINGS_FILE.exists():
            try:
                values.update(json.loads(SETTINGS_FILE.read_text()))
            except (json.JSONDecodeError, OSError):
                pass
        _cache = values
        return dict(values)


def save(patch: dict):
    global _cache
    values = load()
    for key, value in patch.items():
        if key in DEFAULTS:
            values[key] = value
    with _lock:
        ensure_dirs()
        SETTINGS_FILE.write_text(json.dumps(values, indent=2))
        _cache = values
    return dict(values)


def get(key):
    return load()[key]
