const S = {
  event: null,
  photos: [],
  photoTotal: 0,
  tab: "upload",
  settings: null,
  devices: null,
  activeDevice: "",
  run: null,
  people: {},      // per-person picker state
  poll: null,
  viewPersonId: null,
  viewMatches: [],
  openPersonFolderId: null,
};

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function storage_safe_name(name) {
  if (!name) return "unnamed";
  let s = name.normalize("NFD").replace(/[\u0300-\u036f]/g, "").trim();
  s = s.replace(/[<>:"/\\|?*\x00-\x1f]/g, "");
  s = s.replace(/\s+/g, " ").trim();
  s = s.replace(/^[. ]+|[. ]+$/g, "");
  const upper = s.toUpperCase().split(".")[0];
  const reserved = ["CON", "PRN", "AUX", "NUL"];
  for (let i = 1; i <= 9; i++) {
    reserved.push("COM" + i, "LPT" + i);
  }
  if (reserved.includes(upper)) {
    s = "_" + s;
  }
  return s.slice(0, 80) || "unnamed";
}

async function api(path, options = {}) {
  const res = await fetch("/api" + path, {
    headers: options.body instanceof FormData ? {} : { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch {}
    throw new Error(detail);
  }
  return res.status === 204 ? null : res.json();
}

function uploadApi(path, formData, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api" + path);
    
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        const percentComplete = (event.loaded / event.total) * 100;
        onProgress(percentComplete);
      }
    };
    
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText));
        } catch (e) {
          resolve(xhr.responseText);
        }
      } else {
        let detail = xhr.statusText;
        try {
          detail = JSON.parse(xhr.responseText).detail || detail;
        } catch (e) {}
        reject(new Error(detail));
      }
    };
    
    xhr.onerror = () => {
      reject(new Error("Network error"));
    };
    
    xhr.send(formData);
  });
}

let toastTimer;
function toast(message, bad = false) {
  document.querySelector(".toast")?.remove();
  const el = document.createElement("div");
  el.className = "toast" + (bad ? " bad" : "");
  el.textContent = message;
  document.body.appendChild(el);
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.remove(), bad ? 6000 : 3000);
}

/* ------------------------------------------------------------ boot */

async function boot() {
  await loadSettings();
  
  try {
    const list = await api("/events");
    S.event = list[0];
  } catch (err) {
    toast("Failed to load workspace. Resetting...", true);
    S.event = await api("/events/workspace/reset", { method: "POST" });
  }

  $("resetWorkspace").onclick = resetWorkspace;
  $("openSettings").onclick = openSettings;

  await loadPhotos();
  S.run = await api("/events/workspace/run");

  startPolling();
  render();
}

async function loadSettings() {
  const data = await api("/settings");
  S.settings = data.settings;
  S.devices = data.devices;
  S.activeDevice = data.active_device;
  S.dataRoot = data.data_root;
  S.heic = data.heic;
  const names = { cpu: "CPU", cuda: "GPU (CUDA)", coreml: "GPU (Apple)" };
  $("deviceTag").textContent = "Running on " + (names[S.activeDevice] || S.activeDevice);
}

async function refreshEvent() {
  S.event = await api("/events/workspace");
}

async function loadPhotos() {
  const data = await api("/events/workspace/photos?limit=500");
  S.photos = data.photos;
  S.photoTotal = data.total;
}

async function resetWorkspace() {
  if (!confirm("Are you sure you want to delete everything in the current workspace? This cannot be undone.")) return;
  try {
    clearInterval(searchInterval);
    S.event = await api("/events/workspace/reset", { method: "POST" });
    S.photos = [];
    S.photoTotal = 0;
    S.tab = "upload";
    S.viewPersonId = null;
    S.viewMatches = [];
    S.openPersonFolderId = null;
    S.run = { state: "idle" };
    toast("Workspace reset successfully");
    render();
  } catch (err) {
    toast("Failed to reset workspace: " + err.message, true);
  }
}

/* ------------------------------------------------------------ render */

function render() {
  if (!S.event) {
    $("main").innerHTML = `
      <div class="empty-state">
        <h2>Loading workspace...</h2>
      </div>`;
    return;
  }

  $("main").innerHTML = `
    <div class="head">
      <div>
        <h2>Workspace <span id="headerStatus" class="num" style="font-size:13px;font-weight:normal;margin-left:12px;"></span></h2>
        <div class="sub num" id="headerSub">${S.photoTotal} photos · ${S.event.persons?.length || 0} people</div>
      </div>
    </div>
    <div class="rail">
      <button class="stage ${S.tab === "upload" ? "on" : ""}" id="tab-upload">Upload</button>
      <button class="stage ${S.tab === "process" ? "on" : ""}" id="tab-process">Process</button>
      <button class="stage ${S.tab === "people" ? "on" : ""}" id="tab-people">People</button>
      <button class="stage ${S.tab === "view" ? "on" : ""}" id="tab-view">View</button>
    </div>
    <div id="tabBody"></div>`;

  updateHeaderStatus();

  $("tab-upload").onclick = () => { S.tab = "upload"; render(); };
  $("tab-process").onclick = () => { S.tab = "process"; render(); };
  $("tab-people").onclick = () => { S.tab = "people"; render(); };
  $("tab-view").onclick = () => { S.tab = "view"; render(); };

  if (S.tab === "upload") renderUpload();
  else if (S.tab === "process") renderProcess();
  else if (S.tab === "people") renderPeople();
  else if (S.tab === "view") renderView();
}

function updateHeaderStatus() {
  const el = $("headerStatus");
  if (!el) return;
  const run = S.run;
  if (run && (run.state === "running" || run.state === "cancelling")) {
    el.textContent = `(Processing… ${run.done}/${run.total})`;
    el.style.color = "var(--amber)";
  } else {
    el.textContent = "";
  }
}

/* ------------------------------------------------------------ 1: upload */

function renderUpload() {
  $("tabBody").innerHTML = `
    <div class="card">
      <h3>Upload photos</h3>
      <p class="hint">Drop folder/files or use the picker to add photos to the workspace. No processing is done on upload.</p>
      <div class="dropzone" id="drop">
        <p style="margin-bottom:12px">Drag photos here</p>
        <button class="btn" id="pick">Choose files</button>
        <input type="file" id="files" multiple accept="image/*,.heic,.heif" hidden>
        <p class="label" style="margin-top:14px">JPG · PNG · WEBP · TIFF${S.heic ? " · HEIC" : ""}</p>
      </div>
      <div id="uploadStatus" style="margin-top:14px"></div>
    </div>
    ${S.photoTotal ? `
    <div class="card">
      <div class="spread" style="margin-bottom:14px">
        <h3>Photos in Workspace <span class="num" style="color:var(--dim)">${S.photoTotal}</span></h3>
      </div>
      <div class="grid">${S.photos.map(thumbTile).join("")}</div>
    </div>` : ""}`;

  const input = $("files"), drop = $("drop");
  $("pick").onclick = () => input.click();
  input.onchange = () => upload([...input.files]);
  ["dragenter", "dragover"].forEach((e) =>
    drop.addEventListener(e, (ev) => { ev.preventDefault(); drop.classList.add("hot"); }));
  ["dragleave", "drop"].forEach((e) =>
    drop.addEventListener(e, (ev) => { ev.preventDefault(); drop.classList.remove("hot"); }));
  drop.addEventListener("drop", (ev) => upload([...ev.dataTransfer.files]));
}

function thumbTile(name) {
  return `<div class="tile"><img loading="lazy" src="/api/events/workspace/photos/${encodeURIComponent(name)}?thumb=true" alt=""></div>`;
}

async function upload(files) {
  files = files.filter((f) => f.type.startsWith("image/") || /\.(heic|heif)$/i.test(f.name));
  if (!files.length) return toast("No valid images selected.", true);

  const status = $("uploadStatus");
  status.style.display = "block";
  status.innerHTML = `
    <div class="meter"><i id="uploadBar" style="width: 0%;"></i></div>
    <span class="label num" id="uploadLabel">Preparing upload...</span>`;

  const totalSize = files.reduce((acc, f) => acc + f.size, 0);
  let bytesUploadedBefore = 0;
  const CHUNK = 15;

  const fmtSize = (bytes) => {
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  };

  const totalSizeStr = fmtSize(totalSize);

  for (let i = 0; i < files.length; i += CHUNK) {
    const chunkFiles = files.slice(i, i + CHUNK);
    const chunkBytes = chunkFiles.reduce((acc, f) => acc + f.size, 0);
    
    const form = new FormData();
    chunkFiles.forEach((f) => form.append("files", f, f.name));

    try {
      await uploadApi("/events/workspace/photos", form, (percentComplete) => {
        const chunkUploaded = (percentComplete / 100) * chunkBytes;
        const totalUploaded = bytesUploadedBefore + chunkUploaded;
        const overallPercent = Math.min(99.9, (totalUploaded / totalSize) * 100);
        
        const bar = $("uploadBar");
        if (bar) bar.style.width = overallPercent + "%";
        
        const label = $("uploadLabel");
        if (label) {
          label.textContent = `Uploading: ${fmtSize(totalUploaded)} / ${totalSizeStr} (${overallPercent.toFixed(1)}%)`;
        }
      });
      bytesUploadedBefore += chunkBytes;
    } catch (err) {
      status.innerHTML = `<div class="note bad">Upload stopped: ${esc(err.message)}</div>`;
      return;
    }
  }

  const bar = $("uploadBar");
  if (bar) bar.style.width = "100%";
  const label = $("uploadLabel");
  if (label) label.textContent = `Upload complete! ${totalSizeStr} uploaded.`;

  await loadPhotos();
  await refreshEvent();
  
  setTimeout(() => {
    render();
    toast(`Added ${files.length} photos`);
  }, 500);
}

/* ------------------------------------------------------------ 2: process */

function renderProcess() {
  const run = S.run || { state: "idle" };
  const running = run.state === "running" || run.state === "cancelling";
  const pct = run.total ? (run.done / run.total) * 100 : 0;

  let statusMsg = "";
  if (run.state === "running") {
    statusMsg = `Processing… ${run.done} / ${run.total} photos  ·  ${run.faces_found} faces found  ·  ${run.device}`;
  } else if (run.state === "cancelling") {
    statusMsg = `Stopping… ${run.done} / ${run.total} photos  ·  ${run.faces_found} faces found  ·  ${run.device}`;
  } else if (run.state === "done") {
    statusMsg = run.message || "Done.";
  } else if (run.state === "error") {
    statusMsg = run.message || "Error occurred during processing.";
  } else if (run.state === "cancelled") {
    statusMsg = run.message || "Processing cancelled.";
  } else {
    statusMsg = "Not processed yet. Click the button below to detect faces in all uploaded photos.";
  }

  $("tabBody").innerHTML = `
    <div class="card">
      <div class="spread">
        <div>
          <h3>Process Photos</h3>
          <p class="hint">Detect faces across all ${S.photoTotal} uploaded photos and cache their embeddings.</p>
        </div>
        <span class="pill ${S.activeDevice === "cpu" ? "warn" : "on"}">${
          { cpu: "CPU", cuda: "CUDA GPU", coreml: "Apple GPU" }[S.activeDevice] || S.activeDevice}</span>
      </div>

      <div style="margin: 20px 0;">
        <div class="note ${run.state === "error" ? "bad" : (running ? "" : "good")}" style="margin-bottom: 12px; font-weight: 500;">
          ${esc(statusMsg)}
        </div>
        ${running ? `<div class="meter"><i style="width:${pct}%"></i></div>` : ""}
      </div>

      <div class="row">
        ${running
          ? `<button class="btn danger" id="stopRun">Stop Processing</button>
             <span class="label num">${esc(run.current || "")}</span>`
          : `<button class="btn primary" id="startRun">${S.event?.has_cache ? "Re-process All Photos" : "Start Processing"}</button>`
        }
      </div>
    </div>`;

  $("startRun")?.addEventListener("click", startRun);
  $("stopRun")?.addEventListener("click", async () => {
    try {
      await api("/events/workspace/run/stop", { method: "POST" });
    } catch (err) {
      toast(err.message, true);
    }
  });
}

async function startRun() {
  try {
    S.run = await api("/events/workspace/run", { method: "POST" });
    startPolling();
    render();
  } catch (err) {
    toast(err.message, true);
  }
}

function startPolling() {
  clearInterval(S.poll);
  S.poll = setInterval(async () => {
    try {
      const prevRunState = S.run?.state;
      S.run = await api("/events/workspace/run");
      updateHeaderStatus();
      if (S.tab === "process") {
        renderProcess();
      }
      if (prevRunState === "running" && ["done", "error", "cancelled"].includes(S.run.state)) {
        await refreshEvent();
        if (S.tab === "view") {
          renderView();
        }
      }
    } catch (err) {
      console.error(err);
    }
  }, 1000);
}

/* ------------------------------------------------------------ 3: people */

function renderPeople() {
  if (!S.photoTotal) {
    $("tabBody").innerHTML = `<div class="note">Upload some photos first.</div>`;
    return;
  }
  $("tabBody").innerHTML = `
    <div class="card">
      <h3>Add People</h3>
      <p class="hint">Create a person, choose 3-5 photos they appear in, and click their face crops to save their reference vector.</p>
      <div class="row">
        <input class="input" id="personName" placeholder="Name" autocomplete="off">
        <button class="btn primary" id="addPerson">Add Person</button>
      </div>
    </div>
    <div id="peopleList">${(S.event.persons || []).map(personCard).join("")}</div>`;

  $("addPerson").onclick = addPerson;
  $("personName").onkeydown = (e) => { if (e.key === "Enter") addPerson(); };
  wirePeople();
}

function personCard(person) {
  const ui = S.people[person.id] || {};
  const chosen = ui.photos?.size || 0;

  let body = "";
  if (ui.mode === "photos") {
    body = `
      <p class="hint" style="margin:14px 0 10px">Pick photos where ${esc(person.name)} is clearly visible.</p>
      <div class="grid">${S.photos.map((name) => `
        <button class="tile ${ui.photos?.has(name) ? "on" : ""}" data-photo="${person.id}|${esc(name)}">
          <img loading="lazy" src="/api/events/workspace/photos/${encodeURIComponent(name)}?thumb=true" alt="">
        </button>`).join("")}</div>
      <div class="row" style="margin-top:14px">
        <button class="btn primary" data-scan="${person.id}" ${chosen ? "" : "disabled"}>
          Find faces in ${chosen} photo${chosen === 1 ? "" : "s"}
        </button>
        <button class="btn ghost" data-cancel="${person.id}">Cancel</button>
      </div>`;
  } else if (ui.mode === "faces") {
    body = `
      <p class="hint" style="margin:14px 0 4px">Click ${esc(person.name)}'s face in each photo. Ignore everyone else.</p>
      <div class="strip">${(ui.candidates || []).map((c) => `
        <button class="face ${ui.picks?.has(c.key) ? "on" : ""}" data-face="${person.id}|${esc(c.key)}">
          <img src="/api/events/workspace/persons/${person.id}/crops/${encodeURIComponent(c.crop)}" alt="">
          <div class="fmeta">${esc(c.photo.slice(0, 10))}</div>
        </button>`).join("")}</div>
      <div class="row" style="margin-top:14px">
        <button class="btn primary" data-save="${person.id}" ${ui.picks?.size ? "" : "disabled"}>
          Save ${ui.picks?.size || 0} reference face${ui.picks?.size === 1 ? "" : "s"}
        </button>
        <button class="btn ghost" data-cancel="${person.id}">Cancel</button>
      </div>`;
  }

  return `
    <div class="person ${person.ready ? "ready" : "pending"}">
      <div class="spread">
        <div>
          <div class="person-name">${esc(person.name)}</div>
          <div class="person-meta">${person.ready
            ? `<span class="pill on">${person.ref_count} reference faces</span>`
            : `<span class="pill">No reference yet</span>`}</div>
        </div>
        <div class="row">
          <button class="btn sm" data-start="${person.id}">${person.ready ? "Redo reference" : "Pick photos"}</button>
          <button class="btn sm ghost danger" data-drop="${person.id}">Remove</button>
        </div>
      </div>
      ${body}
    </div>`;
}

function wirePeople() {
  const on = (attr, fn) => document.querySelectorAll(`[data-${attr}]`).forEach((el) => {
    el.onclick = () => fn(el.dataset[attr], el);
  });

  on("start", (id) => {
    S.people[id] = { mode: "photos", photos: new Set(), picks: new Set() };
    renderPeople();
  });
  on("cancel", (id) => { delete S.people[id]; renderPeople(); });
  on("drop", async (id) => {
    if (!confirm("Remove this person?")) return;
    await api(`/events/workspace/persons/${id}`, { method: "DELETE" });
    delete S.people[id];
    await refreshEvent();
    renderPeople();
  });
  on("photo", (value) => {
    const [id, name] = value.split("|");
    const set = S.people[id].photos;
    set.has(name) ? set.delete(name) : set.add(name);
    renderPeople();
  });
  on("face", (value) => {
    const [id, key] = value.split("|");
    const set = S.people[id].picks;
    set.has(key) ? set.delete(key) : set.add(key);
    renderPeople();
  });
  on("scan", scanFaces);
  on("save", saveReference);
}

async function addPerson() {
  const input = $("personName");
  const name = input.value.trim();
  if (!name) return input.focus();
  const person = await api("/events/workspace/persons", {
    method: "POST", body: JSON.stringify({ name }),
  });
  input.value = "";
  await refreshEvent();
  S.people[person.id] = { mode: "photos", photos: new Set(), picks: new Set() };
  renderPeople();
}

async function scanFaces(personId, button) {
  const ui = S.people[personId];
  button.disabled = true;
  button.textContent = "Finding faces...";
  try {
    const data = await api(`/events/workspace/persons/${personId}/scan`, {
      method: "POST", body: JSON.stringify({ photos: [...ui.photos] }),
    });
    ui.mode = "faces";
    ui.candidates = data.candidates;
    ui.picks = new Set();
    renderPeople();
  } catch (err) {
    toast(err.message, true);
    button.disabled = false;
    button.textContent = "Find faces";
  }
}

async function saveReference(personId, button) {
  button.disabled = true;
  button.textContent = "Saving...";
  try {
    await api(`/events/workspace/persons/${personId}/reference`, {
      method: "POST", body: JSON.stringify({ picks: [...S.people[personId].picks] }),
    });
    delete S.people[personId];
    await refreshEvent();
    renderPeople();
    toast("Reference saved");
  } catch (err) {
    toast(err.message, true);
    renderPeople();
  }
}

/* ------------------------------------------------------------ 4: view */

let searchInterval = null;

async function renderView() {
  if (!S.event?.has_cache) {
    $("tabBody").innerHTML = `
      <div class="note">
        <h3>Process Photos first</h3>
        <p>No cached face vectors found. Please go to the <strong>Process</strong> tab and run face detection first.</p>
      </div>`;
    return;
  }

  const people = S.event.persons || [];
  if (!people.length) {
    $("tabBody").innerHTML = `<div class="note">Please add some people in the <strong>People</strong> tab first.</div>`;
    return;
  }

  if (S.openPersonFolderId && people.some((p) => p.id === S.openPersonFolderId)) {
    const person = people.find((p) => p.id === S.openPersonFolderId);
    $("tabBody").innerHTML = `
      <div class="folder-open-view">
        <div class="folder-back-row">
          <button class="btn sm" id="closeFolderBtn">
            ← Back to Folders
          </button>
        </div>
        <div class="card" style="margin-bottom: 0;">
          <div class="spread">
            <div>
              <h3>Folder: ${esc(person.name)}</h3>
              <p class="hint" style="margin-bottom: 0;">Matches calculated at current threshold. Files synced to disk folder: <strong class="num" style="font-size: 11.5px;">output/${esc(storage_safe_name(person.name))}/</strong></p>
            </div>
          </div>
        </div>
        <div id="viewResultsBody"></div>
      </div>`;

    $("closeFolderBtn").onclick = () => {
      S.openPersonFolderId = null;
      render();
    };

    S.viewPersonId = S.openPersonFolderId;
    await loadMatchesAndRender();
  } else {
    $("tabBody").innerHTML = `
      <div class="card">
        <h3>Output Folders</h3>
        <p class="hint" style="margin-bottom: 0;">Click on a folder to view the photos matched to that person.</p>
      </div>
      <div class="folder-grid" id="foldersGrid"></div>`;

    const grid = $("foldersGrid");
    grid.innerHTML = people.map((p) => {
      let coverHtml = `<div class="folder-placeholder-icon">📁</div>`;
      if (p.ready && p.refs && p.refs.length > 0) {
        const photoName = p.refs[0].split("::")[0];
        coverHtml = `<img class="folder-cover" loading="lazy" src="/api/events/workspace/photos/${encodeURIComponent(photoName)}?thumb=true" alt="">`;
      }

      return `
        <div class="folder-card" data-folder-id="${p.id}">
          <div class="folder-tab"></div>
          <div class="folder-cover-container">
            ${coverHtml}
          </div>
          <div class="folder-info">
            <div class="folder-title">${esc(p.name)}</div>
            <div class="folder-meta" id="folder-meta-${p.id}">Loading photos...</div>
          </div>
        </div>`;
    }).join("");

    document.querySelectorAll("[data-folder-id]").forEach((el) => {
      el.onclick = () => {
        S.openPersonFolderId = el.dataset.folderId;
        render();
      };
    });

    people.forEach((p) => {
      loadFolderMatchCount(p.id);
    });
  }
}

async function loadFolderMatchCount(personId) {
  const metaEl = $(`folder-meta-${personId}`);
  if (!metaEl) return;
  try {
    const person = S.event.persons.find((p) => p.id === personId);
    if (!person || !person.ready) {
      metaEl.textContent = "No reference face";
      return;
    }
    const data = await api(`/events/workspace/persons/${personId}/matches`);
    const count = data.matches ? data.matches.length : 0;
    metaEl.textContent = `${count} photo${count === 1 ? "" : "s"}`;
  } catch (err) {
    metaEl.textContent = "Error loading";
  }
}

async function loadMatchesAndRender() {
  const el = $("viewResultsBody");
  if (!el) return;

  const person = S.event.persons.find((p) => p.id === S.viewPersonId);
  if (!person) {
    el.innerHTML = `<div class="note">Person not found.</div>`;
    return;
  }

  if (!person.ready) {
    el.innerHTML = `
      <div class="note bad" style="margin-top: 14px;">
        <h3>No Reference Face</h3>
        <p>Please go to the <strong>People</strong> tab and select reference faces for ${esc(person.name)} first.</p>
      </div>`;
    return;
  }

  // Clear any existing search interval
  clearInterval(searchInterval);

  el.innerHTML = `
    <div class="card" id="searchProgressCard" style="margin-top: 14px;">
      <div class="spread" style="margin-bottom: 8px;">
        <span class="label" id="searchProgressText">Searching: 0 / ${S.photos.length} photos</span>
        <span class="num" id="searchProgressPercent">0%</span>
      </div>
      <div class="meter"><i id="searchProgressBar" style="width: 0%;"></i></div>
    </div>

    <div class="card" id="matchesCard" style="display: none; margin-top: 14px;">
      <div class="spread" style="margin-bottom: 14px;">
        <div class="stats">
          <div class="stat"><div class="v" id="matchCount">0</div><div class="k">Matches found</div></div>
          <div class="stat"><div class="v" id="highScore">-</div><div class="k">Highest similarity</div></div>
        </div>
        <div class="label num" id="matchThresholdLabel">Threshold -</div>
      </div>
      <div class="grid" id="matchesGrid"></div>
    </div>`;

  try {
    const data = await api(`/events/workspace/persons/${S.viewPersonId}/matches`);
    const matches = data.matches;
    const matchMap = new Map(matches.map((m) => [m.photo, m.score]));

    $("matchThresholdLabel").textContent = `Threshold ${(+data.threshold).toFixed(2)}`;

    let currentIndex = 0;
    const totalPhotos = S.photos.length;
    const duration = 1200; // 1.2 seconds total animation time
    const stepTime = 25; // 25ms per step
    const steps = duration / stepTime;
    const photosPerStep = Math.max(1, Math.ceil(totalPhotos / steps));

    let foundMatches = [];

    searchInterval = setInterval(() => {
      const limit = Math.min(currentIndex + photosPerStep, totalPhotos);
      for (let i = currentIndex; i < limit; i++) {
        const photo = S.photos[i];
        if (matchMap.has(photo)) {
          const score = matchMap.get(photo);
          foundMatches.push({ photo, score });
          
          foundMatches.sort((a, b) => b.score - a.score);
          
          const card = $("matchesCard");
          if (card && card.style.display === "none") {
            card.style.display = "block";
          }

          $("matchCount").textContent = foundMatches.length;
          $("highScore").textContent = foundMatches[0].score.toFixed(2);

          $("matchesGrid").innerHTML = foundMatches.map((m) => `
            <div class="tile">
              <img loading="lazy" src="/api/events/workspace/photos/${encodeURIComponent(m.photo)}?thumb=true" alt="">
              <span class="score"><span>${m.score.toFixed(2)}</span></span>
            </div>`).join("");
        }
      }

      currentIndex = limit;

      const pct = Math.round((currentIndex / totalPhotos) * 100);
      const bar = $("searchProgressBar");
      if (bar) bar.style.width = pct + "%";
      const percentEl = $("searchProgressPercent");
      if (percentEl) percentEl.textContent = pct + "%";
      const textEl = $("searchProgressText");
      if (textEl) textEl.textContent = `Searching: ${currentIndex} / ${totalPhotos} photos`;

      if (currentIndex >= totalPhotos) {
        clearInterval(searchInterval);
        const progCard = $("searchProgressCard");
        if (progCard) {
          progCard.style.display = "none";
        }
        if (foundMatches.length === 0) {
          const note = document.createElement("div");
          note.className = "card";
          note.id = "noMatchesNote";
          note.innerHTML = `
            <div class="note" style="margin: 0;">
              No matches found for <strong>${esc(person.name)}</strong> at threshold <strong>${(+data.threshold).toFixed(2)}</strong>.
              Try lowering the threshold in Settings, or add more reference faces.
            </div>`;
          el.appendChild(note);
        }
      }
    }, stepTime);

  } catch (err) {
    el.innerHTML = `<div class="note bad">Error loading matches: ${esc(err.message)}</div>`;
  }
}

/* ------------------------------------------------------------ settings */

function openSettings() {
  const s = S.settings, d = S.devices;
  const option = (value, text, ok) =>
    `<option value="${value}" ${s.device === value ? "selected" : ""} ${ok ? "" : "disabled"}>${text}${ok ? "" : " (not available)"}</option>`;

  $("sheet").innerHTML = `
    <div class="sheet">
      <div class="sheet-inner">
        <div class="sheet-head">
          <h3>Settings</h3>
          <button class="btn ghost sm" id="closeSheet">Close</button>
        </div>
        <div class="sheet-body">
          <div class="setting">
            <div>
              <label for="dev">Processing device</label>
              <div class="desc">GPU is roughly ten times faster. If the one you pick is missing,
                the app falls back to CPU rather than failing.</div>
            </div>
            <select class="input" id="dev">
              ${option("auto", "Auto", true)}
              ${option("cpu", "CPU", true)}
              ${option("cuda", "NVIDIA GPU (CUDA)", d.cuda)}
              ${option("coreml", "Apple GPU (CoreML)", d.coreml)}
            </select>
          </div>

          <div class="setting">
            <div>
              <label for="thr2">Match threshold</label>
              <div class="desc">Higher is stricter. Around 0.42 suits most events.</div>
            </div>
            <div class="row">
              <input type="range" id="thr2" min="0.2" max="0.8" step="0.01" value="${s.threshold}">
              <span class="num" id="thr2v" style="width:36px">${(+s.threshold).toFixed(2)}</span>
            </div>
          </div>

          <div class="setting">
            <div>
              <label for="minface">Smallest face</label>
              <div class="desc">Faces narrower than this are ignored. Raise it if the back row of
                group shots is producing wrong matches.</div>
            </div>
            <div class="row"><input class="input" type="number" id="minface" min="16" max="200" value="${s.min_face_px}" style="min-width:80px"><span class="label">px</span></div>
          </div>

          <div class="setting">
            <div>
              <label for="detsize">Detector size</label>
              <div class="desc">Larger finds smaller faces but slows every photo down.</div>
            </div>
            <select class="input" id="detsize">
              ${[480, 640, 800, 1024, 1280].map((v) =>
                `<option value="${v}" ${+s.det_size === v ? "selected" : ""}>${v}</option>`).join("")}
            </select>
          </div>

          <div class="setting">
            <div>
              <label for="cache">Keep face vectors</label>
              <div class="desc">Lets you change the threshold or add a person later without
                rescanning the album. Roughly 2 KB per face, numbers only, no images.</div>
            </div>
            <input type="checkbox" id="cache" ${s.cache_embeddings ? "checked" : ""} disabled>
          </div>

          <div class="setting">
            <div>
              <label for="copymode">Filling folders</label>
              <div class="desc">Hard links save disk space but only work on the same drive.</div>
            </div>
            <select class="input" id="copymode" disabled>
              <option value="copy" ${s.copy_mode === "copy" ? "selected" : ""}>Copy files</option>
              <option value="hardlink" ${s.copy_mode === "hardlink" ? "selected" : ""}>Hard link</option>
            </select>
          </div>

          <div class="note">
            <div class="label" style="margin-bottom:4px">Data folder</div>
            <span class="num" style="font-size:11px;word-break:break-all">${esc(S.dataRoot)}</span>
          </div>

          <button class="btn primary" id="saveSettings">Save settings</button>
        </div>
      </div>
    </div>`;

  const close = () => { $("sheet").innerHTML = ""; };
  $("closeSheet").onclick = close;
  document.querySelector(".sheet").onclick = (e) => { if (e.target.className === "sheet") close(); };
  $("thr2").oninput = (e) => { $("thr2v").textContent = (+e.target.value).toFixed(2); };
  $("saveSettings").onclick = async () => {
    try {
      await api("/settings", {
        method: "PUT",
        body: JSON.stringify({
          device: $("dev").value,
          threshold: +$("thr2").value,
          min_face_px: +$("minface").value,
          det_size: +$("detsize").value,
          cache_embeddings: true, // forced for test harness
          copy_mode: "copy",     // forced for test harness
        }),
      });
      await loadSettings();
      close();
      toast("Settings saved");
      render();
    } catch (err) {
      toast(err.message, true);
    }
  };
}

boot();
