"""The run: one pass over the album, extracting face vectors and caching them.

In this minimal test build, we do not require people to be ready to run detection.
Processing just populates cache/vectors.npy and cache/index.json.
Matching is calculated on-the-fly when viewing results.
"""

import shutil
import threading
import time
from pathlib import Path

import numpy as np

import config
import engine
import storage

_jobs = {}
_jobs_lock = threading.Lock()


def _blank(event_id):
    return {
        "event_id": event_id,
        "state": "idle",
        "done": 0,
        "total": 0,
        "faces_found": 0,
        "current": "",
        "device": "",
        "started": None,
        "finished": None,
        "seconds_left": None,
        "message": "",
        "counts": {},
    }


def get_status(event_id):
    with _jobs_lock:
        job = _jobs.get(event_id)
        return dict(job) if job else _blank(event_id)


def is_running(event_id):
    return get_status(event_id)["state"] == "running"


def _update(event_id, **fields):
    with _jobs_lock:
        job = _jobs.setdefault(event_id, _blank(event_id))
        job.update(fields)


def cancel(event_id):
    with _jobs_lock:
        job = _jobs.get(event_id)
        if job and job["state"] == "running":
            job["state"] = "cancelling"
            return True
    return False


def _cancelled(event_id):
    with _jobs_lock:
        job = _jobs.get(event_id)
        return bool(job and job["state"] == "cancelling")


def run(event_id):
    settings = config.load()
    photos = storage.list_photos(event_id)

    if not photos:
        _update(event_id, state="error", message="This event has no photos yet.")
        return

    try:
        _, device = engine.get_engine()
    except Exception as exc:  # model download or driver problem
        _update(event_id, state="error", message=f"Could not load the face model: {exc}")
        return

    _update(
        event_id,
        state="running",
        done=0,
        total=len(photos),
        faces_found=0,
        device=device,
        started=storage.now(),
        finished=None,
        message="",
        counts={},
    )

    min_face = int(settings["min_face_px"])
    max_side = int(settings["max_image_side"])
    originals = storage.originals_dir(event_id)

    cache_vectors, cache_index = [], []
    started = time.time()
    faces_found = 0

    for position, filename in enumerate(photos, start=1):
        if _cancelled(event_id):
            _update(event_id, state="cancelled", message=f"Stopped after {position - 1} photos.")
            return

        try:
            bgr = engine.load_bgr(originals / filename, max_side=max_side)
            faces = engine.detect(bgr, min_face)
        except Exception:
            faces = []  # unreadable file, keep going rather than abort the run

        if faces:
            vectors = [f.normed_embedding for f in faces]
            faces_found += len(faces)

            for face, vector in zip(faces, vectors):
                cache_vectors.append(engine.normalise(vector))
                cache_index.append({
                    "photo": filename,
                    "bbox": [round(float(v), 1) for v in face.bbox],
                    "det": round(float(face.det_score), 3),
                })

        elapsed = time.time() - started
        rate = position / elapsed if elapsed else 0
        _update(
            event_id,
            done=position,
            faces_found=faces_found,
            current=filename,
            seconds_left=round((len(photos) - position) / rate) if rate else None,
            counts={},
        )

    # Save the cache to disk
    folder = storage.cache_dir(event_id)
    folder.mkdir(parents=True, exist_ok=True)
    if cache_vectors:
        np.save(folder / "vectors.npy", np.stack(cache_vectors).astype(np.float32))
        storage.write_json(folder / "index.json", cache_index)
    else:
        np.save(folder / "vectors.npy", np.zeros((0, 512), dtype=np.float32))
        storage.write_json(folder / "index.json", [])

    elapsed = time.time() - started
    _update(
        event_id,
        state="done",
        finished=storage.now(),
        current="",
        seconds_left=0,
        message=f"Done — {len(photos)} / {len(photos)} photos processed, {faces_found} faces found, {int(elapsed // 60)}m {int(elapsed % 60)}s",
    )


def start(event_id):
    if is_running(event_id):
        return False
    blank = _blank(event_id)
    blank.pop("event_id", None)
    _update(event_id, **blank)
    thread = threading.Thread(target=_guarded, args=(event_id,), daemon=True)
    thread.start()
    return True


def _guarded(event_id):
    try:
        run(event_id)
    except Exception as exc:
        status = get_status(event_id)
        done = status.get("done", 0)
        total = status.get("total", 0)
        _update(event_id, state="error", message=f"Stopped — processed {done} / {total}, then failed: {exc}")


def match_person(event_id, person_id, threshold=None):
    if threshold is None:
        threshold = float(config.get("threshold"))
    else:
        threshold = float(threshold)

    # 1. Check if cache exists
    cache_dir = storage.cache_dir(event_id)
    vectors_path = cache_dir / "vectors.npy"
    index_path = cache_dir / "index.json"
    if not vectors_path.exists() or not index_path.exists():
        raise FileNotFoundError("Please run Process Photos first.")

    # 2. Check if person's reference exists
    ref_path = storage.person_dir(event_id, person_id) / "ref.npy"
    if not ref_path.exists():
        raise FileNotFoundError("Please select reference faces for this person first.")

    # 3. Load cache and reference
    cache_vectors = np.load(vectors_path)
    cache_index = storage.read_json(index_path, [])
    ref_vector = np.load(ref_path)

    # If no faces were detected in the workspace, return empty list
    if len(cache_vectors) == 0 or len(cache_index) == 0:
        return []

    # 4. Compute similarities
    scores = engine.similarity_matrix(cache_vectors, [ref_vector])[:, 0]

    # 5. Group by photo and find max score
    photo_scores = {}
    for idx, item in enumerate(cache_index):
        photo = item["photo"]
        score = float(scores[idx])
        if photo not in photo_scores or score > photo_scores[photo]:
            photo_scores[photo] = score

    # 6. Filter by threshold and sort
    matches = []
    for photo, score in photo_scores.items():
        if score >= threshold:
            matches.append({
                "photo": photo,
                "score": round(score, 4),
            })

    # Sort descending
    matches.sort(key=lambda m: m["score"], reverse=True)
    return matches
