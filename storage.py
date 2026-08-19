"""Filesystem layout. Every record is a JSON file next to the images it describes.

  <DATA_ROOT>/
    settings.json
    events/
      <event_id>/
        event.json
        originals/            uploaded photos, untouched
        thumbs/               small JPEGs for the gallery
        cache/                face vectors from the last run (optional)
        persons/
          <person_id>/
            person.json       name + which faces were picked as reference
            ref.npy           averaged reference vector
            candidates/       face crops shown in the picker
        output/
          <Person Name>/      matched photos, copied here
        results.json          what the last run found
"""

import hashlib
import json
import re
import shutil
import unicodedata
import uuid
from datetime import datetime
from pathlib import Path

from config import EVENTS_DIR, ensure_dirs, DATA_ROOT

USERS_FILE = DATA_ROOT / "users.json"

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def get_users() -> dict:
    if not USERS_FILE.exists():
        import config
        admin_user = config.get("admin_username")
        admin_pass = config.get("admin_password")
        users = {admin_user: hash_password(admin_pass)}
        write_json(USERS_FILE, users)
        return users
    return read_json(USERS_FILE, {})

def create_user(username: str, password: str):
    users = get_users()
    if username in users:
        raise ValueError("User already exists")
    users[username] = hash_password(password)
    write_json(USERS_FILE, users)

def verify_user(username: str, password: str) -> bool:
    users = get_users()
    if username not in users:
        return False
    return users[username] == hash_password(password)

IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".heic", ".heif"}


def new_id() -> str:
    return uuid.uuid4().hex[:10]


def now() -> str:
    # Microseconds, not seconds: two people added in the same second must still
    # sort in the order they were entered.
    return datetime.now().isoformat(timespec="microseconds")


def safe_name(text: str, fallback: str = "unnamed") -> str:
    """Folder-safe on both macOS and Windows."""
    text = unicodedata.normalize("NFKD", str(text or "")).strip()
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", text)
    text = re.sub(r"\s+", " ", text).strip(" .")
    if text.upper().split(".")[0] in {
        "CON", "PRN", "AUX", "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }:
        text = f"_{text}"
    return text[:80] or fallback


def read_json(path: Path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def write_json(path: Path, payload) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


# ---------------------------------------------------------------- events

def event_dir(event_id: str) -> Path:
    return EVENTS_DIR / safe_name(event_id)


def originals_dir(event_id: str) -> Path:
    return event_dir(event_id) / "originals"


def thumbs_dir(event_id: str) -> Path:
    return event_dir(event_id) / "thumbs"


def cache_dir(event_id: str) -> Path:
    return event_dir(event_id) / "cache"


def persons_dir(event_id: str) -> Path:
    return event_dir(event_id) / "persons"


def output_dir(event_id: str) -> Path:
    return event_dir(event_id) / "output"


def create_event(name: str, event_id: str = None) -> dict:
    ensure_dirs()
    if not event_id:
        event_id = new_id()
    record = {
        "id": event_id,
        "name": (name or "Untitled event").strip(),
        "created": now(),
    }
    for folder in (originals_dir, thumbs_dir, persons_dir, cache_dir, output_dir):
        folder(event_id).mkdir(parents=True, exist_ok=True)
    write_json(event_dir(event_id) / "event.json", record)
    return record


def get_event(event_id: str):
    record = read_json(event_dir(event_id) / "event.json")
    if not record:
        return None
    record["photo_count"] = len(list_photos(event_id))
    record["person_count"] = len(list_persons(event_id))
    record["has_results"] = (event_dir(event_id) / "results.json").exists()
    record["has_cache"] = (cache_dir(event_id) / "vectors.npy").exists()
    return record


def list_events() -> list:
    ensure_dirs()
    events = []
    for folder in EVENTS_DIR.iterdir():
        if folder.is_dir():
            record = get_event(folder.name)
            if record:
                events.append(record)
    return sorted(events, key=lambda e: e["created"], reverse=True)


def delete_event(event_id: str) -> None:
    shutil.rmtree(event_dir(event_id), ignore_errors=True)


def list_photos(event_id: str) -> list:
    folder = originals_dir(event_id)
    if not folder.exists():
        return []
    names = [
        p.name for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_TYPES
    ]
    return sorted(names)


def unique_filename(folder: Path, filename: str) -> str:
    stem = safe_name(Path(filename).stem, "photo")
    suffix = Path(filename).suffix.lower()
    if suffix not in IMAGE_TYPES:
        suffix = ".jpg"
    candidate = f"{stem}{suffix}"
    counter = 1
    while (folder / candidate).exists():
        candidate = f"{stem}_{counter}{suffix}"
        counter += 1
    return candidate


# ---------------------------------------------------------------- persons

def person_dir(event_id: str, person_id: str) -> Path:
    return persons_dir(event_id) / safe_name(person_id)


def create_person(event_id: str, name: str) -> dict:
    person_id = new_id()
    record = {
        "id": person_id,
        "name": (name or "Unnamed").strip(),
        "created": now(),
        "refs": [],
        "ready": False,
    }
    (person_dir(event_id, person_id) / "candidates").mkdir(parents=True, exist_ok=True)
    write_json(person_dir(event_id, person_id) / "person.json", record)
    return record


def get_person(event_id: str, person_id: str):
    return read_json(person_dir(event_id, person_id) / "person.json")


def save_person(event_id: str, record: dict) -> dict:
    write_json(person_dir(event_id, record["id"]) / "person.json", record)
    return record


def list_persons(event_id: str) -> list:
    folder = persons_dir(event_id)
    if not folder.exists():
        return []
    people = []
    for child in folder.iterdir():
        if child.is_dir():
            record = read_json(child / "person.json")
            if record:
                people.append(record)
    return sorted(people, key=lambda p: p["created"])


def delete_person(event_id: str, person_id: str) -> None:
    record = get_person(event_id, person_id)
    shutil.rmtree(person_dir(event_id, person_id), ignore_errors=True)
    if record:
        shutil.rmtree(output_dir(event_id) / safe_name(record["name"]), ignore_errors=True)


def results_path(event_id: str) -> Path:
    return event_dir(event_id) / "results.json"
