# FaceSort

Sort an event album into one folder per person. Upload the photos, name the few
people who want their shots, click their face, and let it run.

No database. No cloud. Everything is files on your own disk.

---

## Setup

**macOS**

```bash
cd facesort
./run.sh
```

**Windows**

```
run.bat
```

Both scripts create a virtual environment and install everything on first run,
then open the app at **http://127.0.0.1:8000**

The first sort also downloads the face model (about 300 MB, once). After that
the app works offline.

Requires Python 3.10 or newer.

### If you have an NVIDIA GPU

CPU is the default and works everywhere. For roughly ten times the speed:

```bash
pip uninstall onnxruntime
pip install onnxruntime-gpu
```

Then open **Settings** and set the device to **NVIDIA GPU (CUDA)**. If CUDA is
missing the app falls back to CPU instead of failing. Apple Silicon can try
**Apple GPU (CoreML)**, though gains there are modest.

---

## How it works

**1. Photos.** Drag the album in. Files are copied and thumbnailed. Nothing is
analysed yet.

**2. People.** Add a name, pick 3 to 5 photos that person appears in, then click
their face in each. Only those few photos are scanned at this point, so it is
quick even on a huge album. The picked faces are averaged into one reference
vector, which cancels out the quirks of any single frame.

**3. Sort.** One pass over the album. Each photo is decoded, every face in it is
turned into a vector, and that vector is compared against all your named people
at once. Vectors are discarded as the run moves on, so memory stays flat.
Checking five people costs virtually the same as checking one, because the
expensive part is the detection, not the comparison.

**4. Folders.** Matches appear sorted by confidence, least certain last. Click
any photo to pull it out of the folder. Then download a ZIP per person, or open
the output folder directly.

---

## Where files go

```
~/FaceSort/                        (Windows: C:\Users\you\FaceSort)
  settings.json
  events/<event id>/
    event.json
    originals/                     your uploads, untouched
    thumbs/                        gallery previews
    cache/                         face vectors from the last run
    persons/<person id>/
      person.json                  name and which faces were picked
      ref.npy                      averaged reference vector
      candidates/                  face crops from the picker
    output/<Person Name>/          the matched photos
    results.json
```

Point somewhere else with the `FACESORT_DATA` environment variable.

---

## Settings

| Setting | What it does |
| --- | --- |
| **Processing device** | Auto, CPU, CUDA, or CoreML. Falls back to CPU when unavailable. |
| **Match threshold** | How similar a face must be to count. 0.42 suits most events. Lower catches more photos and more mistakes. |
| **Smallest face** | Faces narrower than this are skipped. Raise it if the back row of group shots causes wrong matches. |
| **Detector size** | Larger finds smaller faces, slower per photo. |
| **Keep face vectors** | Lets you change the threshold or add a person later without rescanning. Roughly 2 KB per face, numbers only, no images. |
| **Filling folders** | Copy files, or hard link to save disk space (same drive only). |

---

## Notes from real use

**Speed.** Around 0.5 to 1.0 seconds per photo on CPU, so a 2000 photo album
takes 20 to 35 minutes. On a CUDA GPU the same album takes 2 to 4 minutes.

**Someone shows up late.** With vector caching on, adding a sixth person after
the run is over does not need another full pass. Add them, then use **Re-match
from cache** and it finishes in seconds.

**Look-alike relatives.** Siblings and cousins at the same function are where
false matches come from. This is why the review step exists. Do not hand a
client a folder you have not looked at.

**Threshold tuning.** If someone says photos are missing, drop the threshold to
around 0.38 and re-match. If a folder has strangers in it, push it up towards
0.50. With caching on, each attempt takes seconds.

**iPhone photos.** HEIC is handled by `pillow-heif`, installed automatically.
EXIF rotation is applied before detection, otherwise sideways photos lose faces.

---

## Layout

| File | Role |
| --- | --- |
| `app.py` | HTTP routes and the server |
| `engine.py` | The only file that touches the face model |
| `processor.py` | The run: scan, match, fill folders |
| `storage.py` | Filesystem layout, JSON records |
| `config.py` | Settings |
| `static/` | The interface, plain HTML and JS, no build step |
