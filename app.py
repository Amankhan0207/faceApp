"""FaceSort: sort event photos into per-person folders.

Minimal test harness version: SINGLE EVENT ONLY ("workspace").
"""

import os
import sys
from pathlib import Path

# Fix missing libcublasLt.so.12 / libcudnn.so.9 errors on Linux by restarting the process
# with LD_LIBRARY_PATH configured to point to pip-installed nvidia packages before ONNX initializes.
if sys.platform.startswith("linux"):
    try:
        major, minor = sys.version_info[:2]
        for venv_parent in [Path(__file__).parent, Path.cwd()]:
            site_packages = venv_parent / ".venv" / "lib" / f"python{major}.{minor}" / "site-packages"
            if site_packages.exists():
                nvidia_libs = [str(p.resolve()) for p in site_packages.glob("nvidia/*/lib")]
                if nvidia_libs:
                    old_ld = os.environ.get("LD_LIBRARY_PATH", "")
                    paths_to_add = [p for p in nvidia_libs if p not in old_ld]
                    if paths_to_add:
                        new_ld = ":".join(paths_to_add) + (":" + old_ld if old_ld else "")
                        os.environ["LD_LIBRARY_PATH"] = new_ld
                        os.execve(sys.executable, [sys.executable] + sys.argv, os.environ)
                        break
    except Exception:
        pass

import io
import shutil
from pathlib import Path

import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import login_template

import config
import engine
import processor
import storage

app = FastAPI(title="FaceSort - Test Harness")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

STATIC = Path(__file__).parent / "static"

SESSION_PREFIX = "facesort_session_active_"

def get_current_user(request: Request) -> str | None:
    session_token = request.cookies.get("session_token")
    if session_token and session_token.startswith(SESSION_PREFIX):
        username = session_token[len(SESSION_PREFIX):]
        # Verify user still exists in database
        if username in storage.get_users():
            return username
    return None

def get_user_role(request: Request) -> str | None:
    user = get_current_user(request)
    if not user:
        return None
    users = storage.get_users()
    return users.get(user, {}).get("usertype")

def is_admin_or_super(request: Request) -> bool:
    role = get_user_role(request)
    return role in ["super_admin", "admin"]

def is_super_admin(request: Request) -> bool:
    return get_user_role(request) == "super_admin"

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    if path in ["/api/login", "/api/logout", "/api/register", "/api/auth/google", "/favicon.ico"]:
        return await call_next(request)
    username = get_current_user(request)
    is_auth = (username is not None)
    if path.startswith("/api/"):
        if not is_auth:
            return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
        return await call_next(request)
    if path in ["/", "/index.html"]:
        if not is_auth:
            g_client_id = config.get("google_client_id") or ""
            html = login_template.get_login_html().replace("{{GOOGLE_CLIENT_ID}}", g_client_id)
            return HTMLResponse(content=html)
    return await call_next(request)


def require_event(event_id: str):
    record = storage.get_event(event_id)
    if not record:
        raise HTTPException(404, "Event not found.")
    return record


def require_person(event_id: str, person_id: str):
    record = storage.get_person(event_id, person_id)
    if not record:
        raise HTTPException(404, "Person not found.")
    return record


# ---------------------------------------------------------------- auth

class LoginIn(BaseModel):
    username: str
    password: str

class RegisterIn(BaseModel):
    username: str
    password: str
    name: str = ""
    email: str = ""
    mobile: str = ""

class CreateUserIn(BaseModel):
    username: str
    password: str
    name: str
    email: str
    mobile: str
    usertype: str

@app.post("/api/login")
def login(body: LoginIn, response: Response):
    if storage.verify_user(body.username, body.password):
        response.set_cookie(
            key="session_token",
            value=f"{SESSION_PREFIX}{body.username}",
            httponly=True,
            samesite="lax",
            max_age=3600 * 24 * 7
        )
        return {"detail": "Authenticated"}
    raise HTTPException(status_code=401, detail="Invalid username or password")

@app.post("/api/register")
def register(body: RegisterIn):
    username = body.username.strip()
    password = body.password.strip()
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password cannot be empty")
    try:
        storage.create_user_full(
            username=username,
            password=password,
            name=body.name.strip(),
            email=body.email.strip(),
            mobile=body.mobile.strip(),
            usertype="member"
        )
        return {"detail": "Account created successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/logout")
def logout(response: Response):
    response.delete_cookie(key="session_token")
    return {"detail": "Logged out"}

class GoogleAuthIn(BaseModel):
    id_token: str

@app.post("/api/auth/google")
def google_auth(body: GoogleAuthIn, response: Response):
    client_id = config.get("google_client_id")
    if not client_id:
        raise HTTPException(400, "Google Client ID is not configured on server")
        
    import urllib.request
    import urllib.parse
    import json
    
    verify_url = f"https://oauth2.googleapis.com/tokeninfo?id_token={urllib.parse.quote(body.id_token)}"
    try:
        req = urllib.request.Request(verify_url)
        with urllib.request.urlopen(req) as res:
            info = json.loads(res.read().decode("utf-8"))
    except Exception as e:
        raise HTTPException(401, f"Failed to verify Google ID token: {e}")
        
    if info.get("aud") != client_id:
        raise HTTPException(401, "Audience mismatch in ID token")
        
    email = info.get("email")
    name = info.get("name", "")
    
    if not email:
        raise HTTPException(400, "Google account does not share email address")
        
    username = email.split("@")[0].replace(".", "_")
    
    users = storage.get_users()
    if username not in users:
        import uuid
        random_pass = uuid.uuid4().hex
        storage.create_user_full(
            username=username,
            password=random_pass,
            name=name,
            email=email,
            mobile="",
            usertype="member"
        )
    
    response.set_cookie(
        key="session_token",
        value=f"{SESSION_PREFIX}{username}",
        httponly=True,
        samesite="lax",
        max_age=3600 * 24 * 7
    )
    return {"detail": "Authenticated via Google"}

# ---------------------------------------------------------------- user management

@app.get("/api/users")
def list_users(request: Request):
    if not is_super_admin(request):
        raise HTTPException(status_code=403, detail="Only Super Admin can view user list")
    users = storage.get_users()
    return [
        {
            "username": username,
            "name": u.get("name", ""),
            "email": u.get("email", ""),
            "mobile": u.get("mobile", ""),
            "usertype": u.get("usertype", "member")
        }
        for username, u in users.items()
    ]

@app.post("/api/users")
def admin_create_user(body: CreateUserIn, request: Request):
    if not is_super_admin(request):
        raise HTTPException(status_code=403, detail="Only Super Admin can create users")
    username = body.username.strip()
    password = body.password.strip()
    usertype = body.usertype.strip()
    if not username or not password or not usertype:
        raise HTTPException(status_code=400, detail="Username, password, and usertype are required")
    if usertype not in ["super_admin", "admin", "member"]:
        raise HTTPException(status_code=400, detail="Invalid usertype")
    try:
        storage.create_user_full(
            username=username,
            password=password,
            name=body.name.strip(),
            email=body.email.strip(),
            mobile=body.mobile.strip(),
            usertype=usertype
        )
        return {"detail": "User created successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/users/{username}")
def delete_user(username: str, request: Request):
    if not is_super_admin(request):
        raise HTTPException(status_code=403, detail="Only Super Admin can delete users")
    if username == config.get("admin_username"):
        raise HTTPException(status_code=400, detail="Cannot delete default Super Admin account")
    try:
        storage.delete_user(username)
        return {"detail": "User deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------- settings

class SettingsPatch(BaseModel):
    device: str | None = None
    model: str | None = None
    det_size: int | None = None
    max_image_side: int | None = None
    min_face_px: int | None = None
    threshold: float | None = None
    cache_embeddings: bool | None = None
    thumb_size: int | None = None
    copy_mode: str | None = None
    google_client_id: str | None = None


@app.get("/api/settings")
def read_settings(request: Request):
    settings = config.load()
    devices = engine.available_devices()
    return {
        "settings": settings,
        "devices": devices,
        "active_device": engine.resolve_device(settings["device"]),
        "data_root": str(config.DATA_ROOT),
        "heic": engine.HEIC_OK,
        "is_admin": is_admin_or_super(request),
        "is_super_admin": is_super_admin(request),
        "google_client_id": settings.get("google_client_id", ""),
    }


@app.put("/api/settings")
def write_settings(patch: SettingsPatch, request: Request):
    if not is_admin_or_super(request):
        raise HTTPException(status_code=403, detail="Only Admins can modify settings")
    values = {k: v for k, v in patch.model_dump().items() if v is not None}
    if "threshold" in values:
        values["threshold"] = max(0.1, min(0.95, float(values["threshold"])))
    if "det_size" in values:
        values["det_size"] = max(320, min(1600, int(values["det_size"])))
    settings = config.save(values)
    if {"device", "model", "det_size"} & values.keys():
        engine.unload()  # reload on next use with the new device
    return {"settings": settings, "active_device": engine.resolve_device(settings["device"])}


# ---------------------------------------------------------------- events (workspace-only)

@app.get("/api/events")
def get_events():
    # Maintain compatibility with boot checks by returning list with only workspace
    workspace = storage.get_event("workspace")
    if not workspace:
        workspace = storage.create_event("Workspace", "workspace")
    return [workspace]


@app.get("/api/events/{event_id}")
def get_one_event(event_id: str):
    record = require_event(event_id)
    record["persons"] = storage.list_persons(event_id)
    return record


@app.post("/api/events/{event_id}/reset")
def reset_workspace(event_id: str, request: Request):
    if not is_admin_or_super(request):
        raise HTTPException(status_code=403, detail="Only Admins can reset workspace")
    if event_id != "workspace":
        raise HTTPException(400, "Only the 'workspace' event is supported.")
    # Cancel any running job
    processor.cancel("workspace")
    storage.delete_event("workspace")
    record = storage.create_event("Workspace", "workspace")
    record["persons"] = []
    return record


@app.post("/api/events/{event_id}/photos")
async def upload_photos(event_id: str, files: list[UploadFile] = File(...)):
    require_event(event_id)
    originals = storage.originals_dir(event_id)
    thumbs = storage.thumbs_dir(event_id)
    originals.mkdir(parents=True, exist_ok=True)
    thumbs.mkdir(parents=True, exist_ok=True)

    saved, skipped = [], []
    for upload in files:
        suffix = Path(upload.filename or "").suffix.lower()
        if suffix not in storage.IMAGE_TYPES:
            skipped.append(upload.filename)
            continue
        name = storage.unique_filename(originals, upload.filename)
        target = originals / name
        with target.open("wb") as handle:
            shutil.copyfileobj(upload.file, handle)
        try:
            engine.make_thumbnail(target, thumbs / f"{name}.jpg", config.get("thumb_size"))
            saved.append(name)
        except Exception:
            target.unlink(missing_ok=True)
            skipped.append(upload.filename)
    return {"saved": saved, "skipped": skipped, "total": len(storage.list_photos(event_id))}


@app.get("/api/events/{event_id}/photos")
def get_photos(event_id: str, offset: int = 0, limit: int = 200):
    require_event(event_id)
    names = storage.list_photos(event_id)
    return {"total": len(names), "offset": offset, "photos": names[offset: offset + limit]}


@app.get("/api/events/{event_id}/photos/{name}")
def get_photo(event_id: str, name: str, thumb: bool = False):
    require_event(event_id)
    safe = Path(name).name
    path = (storage.thumbs_dir(event_id) / f"{safe}.jpg") if thumb else (
        storage.originals_dir(event_id) / safe
    )
    if not path.exists():
        raise HTTPException(404, "Photo not found.")
    return FileResponse(path)


# ---------------------------------------------------------------- persons

class PersonIn(BaseModel):
    name: str


class ScanIn(BaseModel):
    photos: list[str]


class RefsIn(BaseModel):
    picks: list[str]  # "<photo>::<face index>"


@app.post("/api/events/{event_id}/persons")
def post_person(event_id: str, body: PersonIn):
    require_event(event_id)
    if not body.name.strip():
        raise HTTPException(400, "Enter a name for this person.")
    return storage.create_person(event_id, body.name)


@app.delete("/api/events/{event_id}/persons/{person_id}")
def remove_person(event_id: str, person_id: str):
    require_person(event_id, person_id)
    storage.delete_person(event_id, person_id)
    return {"deleted": person_id}


@app.post("/api/events/{event_id}/persons/{person_id}/scan")
def scan_reference_photos(event_id: str, person_id: str, body: ScanIn):
    require_event(event_id)
    person = require_person(event_id, person_id)
    if not body.photos:
        raise HTTPException(400, "Pick at least one photo showing this person.")

    settings = config.load()
    folder = storage.person_dir(event_id, person_id) / "candidates"
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True, exist_ok=True)

    candidates, vectors = [], []
    try:
        for filename in body.photos[:12]:
            path = storage.originals_dir(event_id) / Path(filename).name
            if not path.exists():
                continue
            bgr = engine.load_bgr(path, max_side=int(settings["max_image_side"]))
            faces = engine.detect(bgr, int(settings["min_face_px"]))
            for index, face in enumerate(faces[:12]):
                key = f"{path.name}::{index}"
                crop = folder / f"{storage.safe_name(key.replace('::', '_'))}.jpg"
                if not engine.crop_face(bgr, face.bbox, crop):
                    continue
                candidates.append({
                    "key": key,
                    "photo": path.name,
                    "index": index,
                    "crop": crop.name,
                    "det": round(float(face.det_score), 3),
                    "width": int(face.bbox[2] - face.bbox[0]),
                })
                vectors.append(engine.normalise(face.normed_embedding))
    except Exception as exc:
        raise HTTPException(500, f"Could not read those photos: {exc}")

    if not candidates:
        raise HTTPException(
            422,
            "No faces found in those photos. Try clearer shots, or lower the minimum face size in Settings.",
        )

    np.save(folder / "vectors.npy", np.stack(vectors).astype(np.float32))
    storage.write_json(folder / "candidates.json", candidates)
    person["candidates"] = len(candidates)
    storage.save_person(event_id, person)
    return {"candidates": candidates}


@app.get("/api/events/{event_id}/persons/{person_id}/crops/{name}")
def get_crop(event_id: str, person_id: str, name: str):
    path = storage.person_dir(event_id, person_id) / "candidates" / Path(name).name
    if not path.exists():
        raise HTTPException(404, "Face crop not found.")
    return FileResponse(path)


@app.post("/api/events/{event_id}/persons/{person_id}/reference")
def set_reference(event_id: str, person_id: str, body: RefsIn):
    person = require_person(event_id, person_id)
    folder = storage.person_dir(event_id, person_id) / "candidates"
    candidates = storage.read_json(folder / "candidates.json", [])
    if not candidates or not (folder / "vectors.npy").exists():
        raise HTTPException(400, "Scan the reference photos again before picking faces.")
    if not body.picks:
        raise HTTPException(400, "Click this person's face in at least one photo.")

    vectors = np.load(folder / "vectors.npy")
    lookup = {c["key"]: i for i, c in enumerate(candidates)}
    chosen = [vectors[lookup[key]] for key in body.picks if key in lookup]
    if not chosen:
        raise HTTPException(400, "Those faces are no longer available. Scan again.")

    reference = engine.average_reference(chosen)
    np.save(storage.person_dir(event_id, person_id) / "ref.npy", reference)

    person["refs"] = body.picks
    person["ready"] = True
    person["ref_count"] = len(chosen)
    storage.save_person(event_id, person)
    return person


# ---------------------------------------------------------------- run & matches

@app.post("/api/events/{event_id}/run")
def start_run(event_id: str):
    require_event(event_id)
    if not processor.start(event_id):
        raise HTTPException(409, "This event is already being processed.")
    return processor.get_status(event_id)


@app.get("/api/events/{event_id}/run")
def run_status(event_id: str):
    return processor.get_status(event_id)


@app.post("/api/events/{event_id}/run/stop")
def stop_run(event_id: str):
    return {"stopping": processor.cancel(event_id)}


@app.get("/api/events/{event_id}/persons/{person_id}/matches")
def get_person_matches(event_id: str, person_id: str, threshold: float | None = None):
    require_event(event_id)
    require_person(event_id, person_id)
    try:
        matches = processor.match_person(event_id, person_id, threshold)
        return {"matches": matches, "threshold": threshold or float(config.get("threshold"))}
    except FileNotFoundError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        raise HTTPException(500, f"Error calculating matches: {exc}")


app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    config.ensure_dirs()
    if not storage.get_event("workspace"):
        storage.create_event("Workspace", "workspace")

    print(f"\n  FaceSort Test Harness ->  http://0.0.0.0:9090")
    print(f"  Data folder: {config.DATA_ROOT}\n")
    uvicorn.run(app, host="0.0.0.0", port=9090, log_level="warning")
