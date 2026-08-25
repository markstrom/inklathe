const form = document.querySelector("#job-form");
const fileInput = document.querySelector("#files");
const dropZone = document.querySelector("#drop-zone");
const inputPreview = document.querySelector("#input-preview");
const recentPlaceholder = document.querySelector("#recent-placeholder");
const statusBox = document.querySelector("#status");
const results = document.querySelector("#results");
const resultHistory = document.querySelector("#result-history");
const submitButton = form.querySelector("button[type=submit]");
const previewDialog = document.querySelector("#preview-dialog");
const previewZoom = document.querySelector("#preview-zoom");
const previewLarge = document.querySelector("#preview-large");
const previewTitle = document.querySelector("#preview-title");
const previewMeta = document.querySelector("#preview-meta");
const previewPrevious = document.querySelector("#preview-previous");
const previewNext = document.querySelector("#preview-next");
const previewDownload = document.querySelector("#preview-download");
const previewDelete = document.querySelector("#preview-delete");

let recentSources = [];
let selectedSourceIds = new Set();
let activeBatchIds = [];
let activeSourceId = null;
let resultItems = [];
let currentResultId = null;

function formatBytes(bytes) {
  if (bytes === null || bytes === undefined) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} kB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function grungeDescription(value) {
  if (value === 0) return "none";
  if (value <= 25) return "light";
  if (value <= 60) return "pronounced";
  return "heavy";
}

function sourceId(file) {
  return `${file.name}:${file.size}:${file.lastModified}`;
}

function addRecentSources(files) {
  if (submitButton.disabled) return;
  const accepted = files.filter((file) => file.type.startsWith("image/"));
  const incoming = accepted.map((file) => {
    const id = sourceId(file);
    const existing = recentSources.find((source) => source.id === id);
    return existing || { id, file, url: URL.createObjectURL(file) };
  });
  const incomingIds = new Set(incoming.map((source) => source.id));
  const next = [...incoming, ...recentSources.filter((source) => !incomingIds.has(source.id))]
    .slice(0, 5);
  const keptIds = new Set(next.map((source) => source.id));
  for (const source of recentSources) {
    if (!keptIds.has(source.id)) URL.revokeObjectURL(source.url);
  }
  recentSources = next;
  selectedSourceIds = new Set(incoming.map((source) => source.id).filter((id) => keptIds.has(id)));
  renderRecentSources();
  fileInput.value = "";
}

function renderRecentSources() {
  inputPreview.replaceChildren();
  recentPlaceholder.hidden = recentSources.length > 0;
  for (const source of recentSources) {
    const figure = document.createElement("figure");
    figure.className = "source-preview";
    figure.classList.toggle("selected", selectedSourceIds.has(source.id));
    figure.classList.toggle("processing", activeSourceId === source.id);

    const select = document.createElement("button");
    select.type = "button";
    select.className = "source-select";
    select.setAttribute("aria-pressed", String(selectedSourceIds.has(source.id)));
    select.setAttribute("aria-label", `Select ${source.file.name} for processing`);
    const image = document.createElement("img");
    image.src = source.url;
    image.alt = source.file.name;
    select.append(image);
    select.addEventListener("click", () => {
      if (submitButton.disabled) return;
      if (selectedSourceIds.has(source.id)) selectedSourceIds.delete(source.id);
      else selectedSourceIds.add(source.id);
      renderRecentSources();
    });

    if (activeSourceId === source.id) {
      const badge = document.createElement("span");
      badge.className = "processing-badge";
      badge.textContent = "Processing";
      select.append(badge);
    }

    const caption = document.createElement("figcaption");
    caption.textContent = source.file.name;
    figure.append(select, caption);
    inputPreview.append(figure);
  }
}

function resultCard(item) {
  const figure = document.createElement("figure");
  figure.className = "preview";
  figure.dataset.resultId = item.id;

  const open = document.createElement("button");
  open.className = "preview-open";
  open.type = "button";
  open.title = `View ${item.name} larger`;
  const image = document.createElement("img");
  image.src = item.url;
  image.alt = item.name;
  open.append(image);
  open.addEventListener("click", () => openResultPreview(item.id));

  const caption = document.createElement("figcaption");
  const captionHeading = document.createElement("div");
  captionHeading.className = "caption-heading";
  const captionName = document.createElement("strong");
  captionName.textContent = item.name;
  const actions = document.createElement("div");
  actions.className = "card-actions";

  const download = document.createElement("a");
  download.className = "card-icon";
  download.href = item.url;
  download.download = item.name;
  download.title = `Download ${item.name}`;
  download.setAttribute("aria-label", `Download ${item.name}`);
  download.innerHTML = `
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 3v12m0 0 5-5m-5 5-5-5M5 20h14" />
    </svg>
  `;

  const remove = document.createElement("button");
  remove.className = "card-icon danger";
  remove.type = "button";
  remove.title = `Delete ${item.name} (Alt-click to skip confirmation)`;
  remove.setAttribute("aria-label", `Delete ${item.name}`);
  remove.innerHTML = `
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 7h16M9 3h6l1 4H8l1-4Zm-2 4 1 14h8l1-14M10 11v6m4-6v6" />
    </svg>
  `;
  remove.addEventListener("click", (event) => deleteResult(item.id, event.altKey));

  actions.append(download, remove);
  captionHeading.append(captionName, actions);
  const metadata = document.createElement("span");
  metadata.textContent = item.meta;
  caption.append(captionHeading, metadata);
  figure.append(open, caption);
  return figure;
}

function renderResults() {
  resultHistory.replaceChildren(...resultItems.map(resultCard));
  results.hidden = resultItems.length === 0;
}

function openResultPreview(id) {
  currentResultId = id;
  updateResultPreview();
  if (!previewDialog.open) previewDialog.showModal();
}

function updateResultPreview() {
  const index = resultItems.findIndex((item) => item.id === currentResultId);
  if (index < 0) return;
  const item = resultItems[index];
  previewLarge.src = item.url;
  previewLarge.alt = item.name;
  previewTitle.textContent = item.name;
  previewMeta.textContent = item.meta;
  previewDownload.href = item.url;
  previewDownload.download = item.name;
  previewPrevious.disabled = index === 0;
  previewNext.disabled = index === resultItems.length - 1;
  setPreviewZoom(false);
}

function setPreviewZoom(zoomed) {
  previewZoom.classList.toggle("zoomed", zoomed);
  previewZoom.setAttribute("aria-pressed", String(zoomed));
  previewZoom.setAttribute("aria-label", zoomed ? "Zoom out" : "Zoom in");
  previewZoom.title = zoomed ? "Click to zoom out" : "Click to zoom in";
  if (!zoomed) {
    previewZoom.style.setProperty("--zoom-x", "50%");
    previewZoom.style.setProperty("--zoom-y", "50%");
  }
}

function panResultPreview(event) {
  if (!previewZoom.classList.contains("zoomed")) return;
  const bounds = previewZoom.getBoundingClientRect();
  const x = Math.max(0, Math.min(1, (event.clientX - bounds.left) / bounds.width));
  const y = Math.max(0, Math.min(1, (event.clientY - bounds.top) / bounds.height));
  previewZoom.style.setProperty("--zoom-x", `${x * 100}%`);
  previewZoom.style.setProperty("--zoom-y", `${y * 100}%`);
}

function moveResultPreview(offset) {
  const index = resultItems.findIndex((item) => item.id === currentResultId);
  const nextIndex = index + offset;
  if (index < 0 || nextIndex < 0 || nextIndex >= resultItems.length) return;
  currentResultId = resultItems[nextIndex].id;
  updateResultPreview();
}

async function deleteResult(id, skipConfirmation = false) {
  const index = resultItems.findIndex((item) => item.id === id);
  if (index < 0) return;
  const item = resultItems[index];
  if (!skipConfirmation && !window.confirm(`Delete ${item.name}? This cannot be undone.`)) return;
  const response = await fetch(item.deleteUrl, { method: "DELETE" });
  if (!response.ok) {
    showPollError(new Error("Could not delete the result"));
    return;
  }
  resultItems.splice(index, 1);
  renderResults();
  if (currentResultId !== id) return;
  if (resultItems.length === 0) {
    currentResultId = null;
    previewDialog.close();
    return;
  }
  currentResultId = resultItems[Math.min(index, resultItems.length - 1)].id;
  updateResultPreview();
}

fileInput.addEventListener("change", () => addRecentSources([...fileInput.files]));
const grungeSlider = document.querySelector("#grunge");
grungeSlider.addEventListener("input", (event) => {
  const value = Number(event.target.value);
  document.querySelector("#grunge-value").textContent = `${value} · ${grungeDescription(value)}`;
});
document.querySelector("#preview-close").addEventListener("click", () => previewDialog.close());
previewZoom.addEventListener("click", () => {
  setPreviewZoom(!previewZoom.classList.contains("zoomed"));
});
previewZoom.addEventListener("pointermove", panResultPreview);
previewPrevious.addEventListener("click", () => moveResultPreview(-1));
previewNext.addEventListener("click", () => moveResultPreview(1));
previewDelete.addEventListener("click", (event) => deleteResult(currentResultId, event.altKey));
previewDialog.addEventListener("click", (event) => {
  if (event.target === previewDialog) previewDialog.close();
});
previewDialog.addEventListener("close", () => setPreviewZoom(false));
document.addEventListener("keydown", (event) => {
  if (!previewDialog.open) return;
  if (event.key === "ArrowLeft") {
    event.preventDefault();
    moveResultPreview(-1);
  } else if (event.key === "ArrowRight") {
    event.preventDefault();
    moveResultPreview(1);
  }
});

for (const eventName of ["dragenter", "dragover"]) {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    if (!submitButton.disabled) dropZone.classList.add("dragging");
  });
}
for (const eventName of ["dragleave", "drop"]) {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.remove("dragging");
  });
}
dropZone.addEventListener("drop", (event) => addRecentSources([...event.dataTransfer.files]));

async function loadCapabilities() {
  const response = await fetch("/api/health");
  const health = await response.json();
  const lucida = document.querySelector("#lucida-option");
  const ai = document.querySelector("#ai-option");
  lucida.disabled = !health.capabilities.lucida;
  ai.disabled = !health.capabilities.ai_upscaler;
  lucida.textContent += lucida.disabled ? " — not installed" : " — ready";
  ai.textContent += ai.disabled ? " — not installed" : " — ready";
}

function setBusy(busy) {
  submitButton.disabled = busy;
  fileInput.disabled = busy;
  form.classList.toggle("is-processing", busy);
  renderRecentSources();
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const batch = recentSources.filter((source) => selectedSourceIds.has(source.id));
  if (batch.length === 0) {
    showPollError(new Error("Select at least one of your recent images"));
    return;
  }
  activeBatchIds = batch.map((source) => source.id);
  activeSourceId = activeBatchIds[0];
  setBusy(true);
  statusBox.hidden = false;
  statusBox.className = "status";
  statusBox.textContent = "Uploading…";
  try {
    const body = new FormData(form);
    for (const source of batch) body.append("files", source.file, source.file.name);
    const response = await fetch("/api/jobs", { method: "POST", body });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Upload failed");
    await poll(payload.id);
  } catch (error) {
    showPollError(error);
  }
});

async function poll(jobId) {
  const response = await fetch(`/api/jobs/${jobId}`);
  const job = await response.json();
  statusBox.textContent = `Processing ${job.completed} of ${job.total}…`;
  activeSourceId = activeBatchIds[job.completed] || null;
  renderRecentSources();
  if (job.state === "failed") throw new Error(job.error || "Processing failed");
  if (job.state !== "complete") {
    setTimeout(() => poll(jobId).catch(showPollError), 500);
    return;
  }
  renderRun(job);
  activeBatchIds = [];
  activeSourceId = null;
  statusBox.hidden = true;
  setBusy(false);
}

function renderRun(job) {
  const newItems = job.files.map((file) => {
    const size = `${file.output.width}×${file.output.height} px · ${formatBytes(file.output.bytes)}`;
    const grunge = `Grunge ${job.settings.grunge} · ${grungeDescription(job.settings.grunge)}`;
    return {
      id: `${job.id}:${file.index}`,
      name: file.name,
      url: file.download,
      deleteUrl: file.delete,
      meta: `${size} · ${grunge}`,
    };
  });
  resultItems = [...newItems, ...resultItems];
  renderResults();
}

function showPollError(error) {
  activeBatchIds = [];
  activeSourceId = null;
  statusBox.hidden = false;
  statusBox.className = "status failed";
  statusBox.textContent = error.message;
  setBusy(false);
}

loadCapabilities().catch(() => {});
