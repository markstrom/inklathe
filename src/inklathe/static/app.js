const form = document.querySelector("#job-form");
const fileInput = document.querySelector("#files");
const dropZone = document.querySelector("#drop-zone");
const inputPreview = document.querySelector("#input-preview");
const recentPlaceholder = document.querySelector("#recent-placeholder");
const recentActions = document.querySelector("#recent-actions");
const selectionCount = document.querySelector("#selection-count");
const addImages = document.querySelector("#add-images");
const selectAllSources = document.querySelector("#select-all-sources");
const clearSourceSelection = document.querySelector("#clear-source-selection");
const statusBox = document.querySelector("#status");
const results = document.querySelector("#results");
const resultHistory = document.querySelector("#result-history");
const submitButton = form.querySelector("button[type=submit]");
const previewDialog = document.querySelector("#preview-dialog");
const previewZoom = document.querySelector("#preview-zoom");
const previewLarge = document.querySelector("#preview-large");
const previewOriginal = document.querySelector("#preview-original");
const previewTitle = document.querySelector("#preview-title");
const previewMeta = document.querySelector("#preview-meta");
const previewPrevious = document.querySelector("#preview-previous");
const previewNext = document.querySelector("#preview-next");
const previewDownload = document.querySelector("#preview-download");
const previewDelete = document.querySelector("#preview-delete");
const previewCompare = document.querySelector("#preview-compare");
const themeToggle = document.querySelector("#theme-toggle");

const themeModes = ["auto", "light", "dark"];

function savedMode(key, modes, fallback) {
  try {
    const value = localStorage.getItem(key);
    return modes.includes(value) ? value : fallback;
  } catch (_) {
    return fallback;
  }
}

function saveMode(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch (_) {
    // Display controls still work for the current page when storage is unavailable.
  }
}

let themeMode = savedMode("inklathe-theme", themeModes, "auto");

function modeLabel(value) {
  return value[0].toUpperCase() + value.slice(1);
}

function applyThemeMode() {
  if (themeMode === "auto") delete document.documentElement.dataset.theme;
  else document.documentElement.dataset.theme = themeMode;
  themeToggle.textContent = `Theme: ${modeLabel(themeMode)}`;
  themeToggle.title = "Switch between automatic, light, and dark themes";
  themeToggle.setAttribute("aria-label", `Theme: ${themeMode}. Change theme`);
}

function nextMode(current, modes) {
  return modes[(modes.indexOf(current) + 1) % modes.length];
}

themeToggle.addEventListener("click", () => {
  themeMode = nextMode(themeMode, themeModes);
  saveMode("inklathe-theme", themeMode);
  applyThemeMode();
});

applyThemeMode();

let recentSources = [];
let selectedSourceIds = new Set();
let activeBatchIds = [];
let activeSourceId = null;
let activePendingItems = [];
let resultItems = [];
let currentResultId = null;
const textureLabels = {};
const textureMaximums = {};

function formatBytes(bytes) {
  if (bytes === null || bytes === undefined) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} kB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function wearDescription(value) {
  return {
    0: "clean",
    25: "subtle",
    50: "worn",
    75: "heavy",
    100: "extreme",
  }[value] || "custom";
}

function textureDescription(texture) {
  return textureLabels[texture] || texture;
}

function estimatedWearCoverage(value, texture) {
  const maximum = textureMaximums[texture] || 15;
  return maximum * (Math.max(0, Math.min(100, value)) / 100) ** 1.55;
}

function wearSummary(value, texture) {
  if (value === 0) return "Wear 0 · clean";
  const coverage = estimatedWearCoverage(value, texture);
  const digits = coverage < 10 ? 1 : 0;
  return `Wear ${value} · ${wearDescription(value)} · ~${coverage.toFixed(digits)}% ink`;
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

function removeRecentSource(id, skipConfirmation = false) {
  const source = recentSources.find((item) => item.id === id);
  if (!source || submitButton.disabled) return;
  if (!skipConfirmation && !window.confirm(`Remove ${source.file.name} from recent images?`)) {
    return;
  }
  URL.revokeObjectURL(source.url);
  recentSources = recentSources.filter((item) => item.id !== source.id);
  selectedSourceIds.delete(source.id);
  renderRecentSources();
}

function renderRecentSources() {
  inputPreview.replaceChildren();
  recentPlaceholder.hidden = recentSources.length > 0;
  recentPlaceholder.disabled = submitButton.disabled;
  recentActions.hidden = recentSources.length === 0;
  selectionCount.textContent = `${selectedSourceIds.size} of ${recentSources.length} selected`;
  addImages.disabled = submitButton.disabled;
  selectAllSources.disabled = submitButton.disabled || selectedSourceIds.size === recentSources.length;
  clearSourceSelection.disabled = submitButton.disabled || selectedSourceIds.size === 0;
  for (const source of recentSources) {
    const figure = document.createElement("figure");
    figure.className = "source-preview";
    figure.classList.toggle("selected", selectedSourceIds.has(source.id));
    figure.classList.toggle("processing", activeSourceId === source.id);

    const select = document.createElement("button");
    select.type = "button";
    select.className = "source-select";
    select.disabled = submitButton.disabled;
    select.setAttribute("aria-pressed", String(selectedSourceIds.has(source.id)));
    select.setAttribute("aria-label", `Select ${source.file.name} for processing`);
    const image = document.createElement("img");
    image.src = source.url;
    image.alt = source.file.name;
    select.append(image);
    if (selectedSourceIds.has(source.id)) {
      const selected = document.createElement("span");
      selected.className = "source-selected";
      selected.textContent = "✓";
      selected.setAttribute("aria-hidden", "true");
      select.append(selected);
    }
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

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "source-remove";
    remove.disabled = submitButton.disabled;
    remove.title = `Remove ${source.file.name} from recent images (Alt-click to skip confirmation)`;
    remove.setAttribute("aria-label", `Remove ${source.file.name} from recent images`);
    remove.innerHTML = `
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M4 7h16M9 3h6l1 4H8l1-4Zm-2 4 1 14h8l1-14M10 11v6m4-6v6" />
      </svg>
    `;
    remove.addEventListener("click", (event) => removeRecentSource(source.id, event.altKey));

    const caption = document.createElement("figcaption");
    caption.textContent = source.file.name;
    figure.append(select, remove, caption);
    inputPreview.append(figure);
  }
}

function resultCard(item) {
  const figure = document.createElement("figure");
  figure.className = "preview";
  figure.dataset.resultId = item.id;

  if (item.pending) {
    figure.classList.add("pending");
    const placeholder = document.createElement("div");
    placeholder.className = "result-pending";
    placeholder.setAttribute("role", "status");
    placeholder.setAttribute("aria-label", `${item.name}: ${item.progress}`);
    const spinner = document.createElement("span");
    spinner.className = "result-spinner";
    spinner.setAttribute("aria-hidden", "true");
    const progress = document.createElement("strong");
    progress.textContent = item.progress;
    placeholder.append(spinner, progress);

    const caption = document.createElement("figcaption");
    const captionName = document.createElement("strong");
    captionName.textContent = item.name;
    const metadata = document.createElement("span");
    metadata.textContent = item.meta;
    caption.append(captionName, metadata);
    figure.append(placeholder, caption);
    return figure;
  }

  const open = document.createElement("button");
  open.className = "preview-open";
  open.type = "button";
  open.title = `View ${item.name} larger`;
  const image = document.createElement("img");
  image.src = item.thumbnailUrl || item.url;
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

function addPendingRun(batch) {
  const token = Date.now();
  const wear = Number(wearSelect.value);
  const settings = `${textureDescription(textureSelect.value)} · ${wearSummary(wear, textureSelect.value)}`;
  activePendingItems = batch.map((source, index) => ({
    id: `pending:${token}:${index}`,
    pending: true,
    index,
    name: source.file.name,
    progress: index === 0 ? `Uploading 1 of ${batch.length}` : `Queued ${index + 1} of ${batch.length}`,
    meta: settings,
  }));
  resultItems = [...activePendingItems, ...resultItems];
  renderResults();
}

function resultFromFile(job, file) {
  const size = `${file.output.width}×${file.output.height} px · ${formatBytes(file.output.bytes)}`;
  const wear = `${textureDescription(job.settings.texture)} · ${wearSummary(job.settings.grunge, job.settings.texture)}`;
  return {
    id: `${job.id}:${file.index}`,
    pending: false,
    index: file.index,
    name: file.name,
    thumbnailUrl: file.preview,
    url: file.download,
    sourceUrl: file.source,
    deleteUrl: file.delete,
    meta: `${size} · ${wear}`,
  };
}

function updatePendingRun(job) {
  const finished = new Map(job.files.map((file) => [file.index, file]));
  for (const item of activePendingItems) {
    const file = finished.get(item.index);
    if (file) {
      Object.assign(item, resultFromFile(job, file));
      continue;
    }
    item.progress = item.index === job.completed
      ? `Processing ${item.index + 1} of ${job.total}`
      : `Queued ${item.index + 1} of ${job.total}`;
  }
  renderResults();
}

function clearUnfinishedPendingItems() {
  const unfinishedIds = new Set(
    activePendingItems.filter((item) => item.pending).map((item) => item.id),
  );
  resultItems = resultItems.filter((item) => !unfinishedIds.has(item.id));
  activePendingItems = [];
  renderResults();
}

function openResultPreview(id) {
  currentResultId = id;
  setPreviewCompare(false);
  updateResultPreview();
  if (!previewDialog.open) previewDialog.showModal();
}

function updateResultPreview() {
  const index = resultItems.findIndex((item) => item.id === currentResultId);
  if (index < 0) return;
  const item = resultItems[index];
  previewLarge.src = item.url;
  previewLarge.alt = item.name;
  previewOriginal.src = item.sourceUrl;
  previewTitle.textContent = item.name;
  previewMeta.textContent = item.meta;
  previewDownload.href = item.url;
  previewDownload.download = item.name;
  previewPrevious.disabled = index === 0;
  previewNext.disabled = index === resultItems.length - 1;
  setPreviewZoom(false);
}

function setPreviewCompare(comparing) {
  previewZoom.classList.toggle("comparing", comparing);
  previewCompare.setAttribute("aria-pressed", String(comparing));
  previewCompare.setAttribute("aria-label", comparing ? "Hide original lens" : "Show original lens");
  previewCompare.dataset.tooltip = comparing
    ? "Hide original comparison (C)"
    : "Compare with original (C)";
  if (!comparing) previewZoom.classList.remove("pointer-inside");
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

function movePreviewPointer(event) {
  const bounds = previewZoom.getBoundingClientRect();
  const x = Math.max(0, Math.min(1, (event.clientX - bounds.left) / bounds.width));
  const y = Math.max(0, Math.min(1, (event.clientY - bounds.top) / bounds.height));
  previewZoom.style.setProperty("--lens-x", `${x * bounds.width}px`);
  previewZoom.style.setProperty("--lens-y", `${y * bounds.height}px`);
  if (previewZoom.classList.contains("zoomed")) {
    previewZoom.style.setProperty("--zoom-x", `${x * 100}%`);
    previewZoom.style.setProperty("--zoom-y", `${y * 100}%`);
  }
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
recentPlaceholder.addEventListener("click", () => fileInput.click());
addImages.addEventListener("click", () => fileInput.click());
selectAllSources.addEventListener("click", () => {
  selectedSourceIds = new Set(recentSources.map((source) => source.id));
  renderRecentSources();
});
clearSourceSelection.addEventListener("click", () => {
  selectedSourceIds.clear();
  renderRecentSources();
});
const wearSelect = document.querySelector("#wear");
const textureSelect = document.querySelector("#texture");
document.querySelector("#preview-close").addEventListener("click", () => previewDialog.close());
previewZoom.addEventListener("click", () => {
  setPreviewZoom(!previewZoom.classList.contains("zoomed"));
});
previewZoom.addEventListener("pointerenter", () => previewZoom.classList.add("pointer-inside"));
previewZoom.addEventListener("pointerleave", () => previewZoom.classList.remove("pointer-inside"));
previewZoom.addEventListener("pointermove", movePreviewPointer);
previewCompare.addEventListener("click", () => {
  setPreviewCompare(!previewZoom.classList.contains("comparing"));
});
previewPrevious.addEventListener("click", () => moveResultPreview(-1));
previewNext.addEventListener("click", () => moveResultPreview(1));
previewDelete.addEventListener("click", (event) => deleteResult(currentResultId, event.altKey));
previewDialog.addEventListener("click", (event) => {
  if (event.target === previewDialog) previewDialog.close();
});
previewDialog.addEventListener("close", () => {
  setPreviewZoom(false);
  setPreviewCompare(false);
});
document.addEventListener("keydown", (event) => {
  if (!previewDialog.open) return;
  if (event.key === "ArrowLeft") {
    event.preventDefault();
    moveResultPreview(-1);
  } else if (event.key === "ArrowRight") {
    event.preventDefault();
    moveResultPreview(1);
  } else if (event.key.toLowerCase() === "c") {
    event.preventDefault();
    setPreviewCompare(!previewZoom.classList.contains("comparing"));
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
  const scanned = health.capabilities.bitmap_textures || [];
  if (scanned.length > 0) {
    const groups = new Map();
    for (const texture of scanned) {
      textureLabels[texture.id] = texture.label;
      textureMaximums[texture.id] = texture.maximum_percent;
      if (!groups.has(texture.category)) {
        const group = document.createElement("optgroup");
        group.label = texture.category;
        groups.set(texture.category, group);
      }
      const option = document.createElement("option");
      option.value = texture.id;
      option.textContent = texture.label;
      groups.get(texture.category).append(option);
    }
    textureSelect.replaceChildren(...groups.values());
    textureSelect.value = scanned[0].id;
    wearSelect.value = "50";
  } else {
    textureSelect.disabled = true;
    wearSelect.value = "0";
    wearSelect.disabled = true;
  }
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
  addPendingRun(batch);
  setBusy(true);
  statusBox.hidden = true;
  statusBox.className = "status";
  statusBox.textContent = "";
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
  updatePendingRun(job);
  activeSourceId = activeBatchIds[job.completed] || null;
  renderRecentSources();
  if (job.state === "failed") throw new Error(job.error || "Processing failed");
  if (job.state !== "complete") {
    setTimeout(() => poll(jobId).catch(showPollError), 500);
    return;
  }
  updatePendingRun(job);
  activePendingItems = [];
  activeBatchIds = [];
  activeSourceId = null;
  statusBox.hidden = true;
  setBusy(false);
}

function showPollError(error) {
  clearUnfinishedPendingItems();
  activeBatchIds = [];
  activeSourceId = null;
  statusBox.hidden = false;
  statusBox.className = "status failed";
  statusBox.textContent = error.message;
  setBusy(false);
}

loadCapabilities().catch(() => {});
