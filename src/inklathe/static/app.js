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
const historyNote = document.querySelector(".history-note");
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
const favoritePresetSelect = document.querySelector("#favorite-preset");
const saveFavoriteButton = document.querySelector("#save-favorite");
const deleteFavoriteButton = document.querySelector("#delete-favorite");
const favoriteDialog = document.querySelector("#favorite-dialog");
const favoriteNameInput = document.querySelector("#favorite-name");
const confirmFavoriteButton = document.querySelector("#confirm-favorite");
const cancelFavoriteButton = document.querySelector("#cancel-favorite");
const settingsOpen = document.querySelector("#settings-open");
const settingsDialog = document.querySelector("#settings-dialog");
const settingsClose = document.querySelector("#settings-close");
const settingsRecheck = document.querySelector("#settings-recheck");
const settingsCopy = document.querySelector("#settings-copy");
const settingsRemove = document.querySelector("#settings-remove");
const upscalerStatus = document.querySelector("#upscaler-status");
const lucidaStatus = document.querySelector("#lucida-status");
const settingsWorkerNote = document.querySelector("#settings-worker-note");

const themeModes = ["auto", "light", "dark"];
const favoriteStorageKey = "inklathe-favorite-presets";
const favoriteSettingNames = [
  "upscale",
  "scale",
  "background",
  "halftone",
  "texture",
  "grunge",
  "seed",
];

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

function loadFavoritePresets() {
  try {
    const parsed = JSON.parse(localStorage.getItem(favoriteStorageKey) || "[]");
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((favorite) => (
      favorite
      && typeof favorite.id === "string"
      && typeof favorite.name === "string"
      && favorite.settings
      && typeof favorite.settings === "object"
    ));
  } catch (_) {
    return [];
  }
}

let favoritePresets = loadFavoritePresets();
let capabilitiesReady = false;

function storeFavoritePresets() {
  try {
    localStorage.setItem(favoriteStorageKey, JSON.stringify(favoritePresets));
  } catch (_) {
    window.alert("The favorite could not be saved in this browser.");
  }
}

function renderFavoritePresets(selectedId = favoritePresetSelect.value) {
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = favoritePresets.length > 0
    ? "Choose favorite…"
    : "No favorites saved";
  favoritePresetSelect.replaceChildren(placeholder);
  for (const favorite of favoritePresets) {
    const option = document.createElement("option");
    option.value = favorite.id;
    option.textContent = favorite.name;
    favoritePresetSelect.append(option);
  }
  favoritePresetSelect.disabled = !capabilitiesReady || favoritePresets.length === 0;
  favoritePresetSelect.value = favoritePresets.some(({ id }) => id === selectedId)
    ? selectedId
    : "";
  deleteFavoriteButton.disabled = favoritePresetSelect.value === "";
}

function currentFavoriteSettings() {
  return Object.fromEntries(favoriteSettingNames.map((name) => [
    name,
    form.elements.namedItem(name).value,
  ]));
}

function setFavoriteControl(name, value) {
  const control = form.elements.namedItem(name);
  if (!control) return false;
  if (control instanceof HTMLSelectElement) {
    const option = [...control.options].find((item) => item.value === String(value));
    if (!option || option.disabled) return false;
  }
  control.value = String(value);
  return control.value === String(value);
}

function applyFavorite(favorite) {
  const unavailable = favoriteSettingNames.filter((name) => (
    favorite.settings[name] === undefined
      ? false
      : !setFavoriteControl(name, favorite.settings[name])
  ));
  wearSelect.disabled = textureSelect.value === "none";
  if (unavailable.length > 0) {
    window.alert(`Some saved settings are not currently available: ${unavailable.join(", ")}.`);
  }
}

function openFavoriteEditor() {
  const selected = favoritePresets.find(({ id }) => id === favoritePresetSelect.value);
  favoriteNameInput.value = selected?.name || "";
  favoriteDialog.showModal();
  favoriteNameInput.focus();
  favoriteNameInput.select();
}

function saveCurrentFavorite() {
  const selected = favoritePresets.find(({ id }) => id === favoritePresetSelect.value);
  const name = favoriteNameInput.value.trim();
  if (!name) return;
  const sameName = favoritePresets.find((favorite) => (
    favorite.name.toLocaleLowerCase() === name.toLocaleLowerCase()
  ));
  if (sameName && sameName.id !== selected?.id
      && !window.confirm(`Replace the existing favorite “${sameName.name}”?`)) return;
  const id = sameName?.id || selected?.id || `favorite-${Date.now().toString(36)}`;
  const favorite = { id, name, settings: currentFavoriteSettings() };
  const existingIndex = favoritePresets.findIndex((item) => item.id === id);
  if (existingIndex >= 0) favoritePresets[existingIndex] = favorite;
  else favoritePresets.push(favorite);
  storeFavoritePresets();
  renderFavoritePresets(id);
  favoriteDialog.close();
}

function deleteCurrentFavorite(skipConfirmation = false) {
  const favorite = favoritePresets.find(({ id }) => id === favoritePresetSelect.value);
  if (!favorite) return;
  if (!skipConfirmation && !window.confirm(`Delete the favorite “${favorite.name}”?`)) return;
  favoritePresets = favoritePresets.filter(({ id }) => id !== favorite.id);
  storeFavoritePresets();
  renderFavoritePresets();
}

renderFavoritePresets();

let recentSources = [];
let selectedSourceIds = new Set();
let isSubmitting = false;
let runSequence = 0;
const activeRuns = new Map();
let resultItems = [];
let currentResultId = null;
let maxImagePixels = null;
const textureLabels = {};
const halftoneLabels = { none: "Solid ink" };

function formatBytes(bytes) {
  if (bytes === null || bytes === undefined) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} kB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function sourceMetadata(source) {
  const dimensions = source.width && source.height
    ? `${source.width}×${source.height} px · `
    : "";
  return `${dimensions}${formatBytes(source.file.size)}`;
}

function formatMegapixels(pixels) {
  return `${(pixels / 1_000_000).toFixed(1)} MP`;
}

function processingLimitError(sources) {
  if (!maxImagePixels) return null;
  const upscale = form.elements.namedItem("upscale").value;
  const scale = upscale === "none"
    ? 1
    : Number(form.elements.namedItem("scale").value);
  for (const source of sources) {
    if (!source.width || !source.height) continue;
    const width = source.width * scale;
    const height = source.height * scale;
    const pixels = width * height;
    if (pixels <= maxImagePixels) continue;
    return `${source.file.name} would become ${width}×${height} `
      + `(${formatMegapixels(pixels)}) at ${scale}×, above this server's `
      + `${formatMegapixels(maxImagePixels)} image limit. Choose a lower scale or no upscaling.`;
  }
  return null;
}

function wearDescription(value) {
  return {
    25: "subtle",
    50: "worn",
    75: "heavy",
    100: "extreme",
  }[value] || "custom";
}

function textureDescription(texture) {
  return textureLabels[texture] || texture;
}

function textureMenuLabel(label) {
  return label.replace(/\s*·\s*G\d+\s*$/, "");
}

function halftoneDescription(halftone) {
  return halftoneLabels[halftone] || halftone;
}

function wearSummary(value) {
  return `Wear ${wearDescription(value)}`;
}

function treatmentSummary(halftone, wear, texture) {
  const parts = [];
  if (halftone !== "none") parts.push(halftoneDescription(halftone));
  if (texture !== "none" && wear > 0) {
    parts.push(textureDescription(texture), wearSummary(wear));
  } else {
    parts.push("No wear");
  }
  return parts.join(" · ");
}

function sourceId(file) {
  return `${file.name}:${file.size}:${file.lastModified}`;
}

function addRecentSources(files) {
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
  if (!source) return;
  if (!skipConfirmation && !window.confirm(`Remove ${source.file.name} from recent images?`)) {
    return;
  }
  URL.revokeObjectURL(source.url);
  recentSources = recentSources.filter((item) => item.id !== source.id);
  selectedSourceIds.delete(source.id);
  renderRecentSources();
}

const DROP_PROMPT_MIN_WIDTH = 160;

function updateDropPromptVisibility() {
  if (recentSources.length === 0) {
    recentPlaceholder.hidden = false;
    return;
  }
  const previews = [...inputPreview.querySelectorAll(".source-preview")];
  const gap = Number.parseFloat(getComputedStyle(inputPreview).gap) || 0;
  const usedWidth = previews.reduce((total, preview) => total + preview.offsetWidth, 0);
  const availableWidth = inputPreview.clientWidth - usedWidth - (gap * previews.length);
  recentPlaceholder.hidden = availableWidth < DROP_PROMPT_MIN_WIDTH;
}

function sourceQueueState(sourceIdValue) {
  let queued = false;
  for (const run of activeRuns.values()) {
    const index = run.batchIds.indexOf(sourceIdValue);
    if (index < 0 || index < run.completed) continue;
    if (run.state === "processing" && index === run.completed) return "processing";
    queued = true;
  }
  return queued ? "queued" : null;
}

function renderRecentSources() {
  inputPreview.replaceChildren();
  recentPlaceholder.disabled = false;
  recentActions.hidden = recentSources.length === 0;
  selectionCount.textContent = `${selectedSourceIds.size} of ${recentSources.length} selected`;
  addImages.disabled = false;
  selectAllSources.disabled = selectedSourceIds.size === recentSources.length;
  clearSourceSelection.disabled = selectedSourceIds.size === 0;
  for (const source of recentSources) {
    const queueState = sourceQueueState(source.id);
    const figure = document.createElement("figure");
    figure.className = "source-preview";
    figure.classList.toggle("selected", selectedSourceIds.has(source.id));
    figure.classList.toggle("processing", queueState === "processing");
    figure.classList.toggle("queued", queueState === "queued");

    const select = document.createElement("button");
    select.type = "button";
    select.className = "source-select";
    select.disabled = false;
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
      if (selectedSourceIds.has(source.id)) selectedSourceIds.delete(source.id);
      else selectedSourceIds.add(source.id);
      renderRecentSources();
    });

    if (queueState) {
      const badge = document.createElement("span");
      badge.className = `processing-badge ${queueState}`;
      badge.textContent = queueState;
      select.append(badge);
    }

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "card-icon danger";
    remove.disabled = false;
    remove.title = `Remove ${source.file.name} from recent images (Alt-click to skip confirmation)`;
    remove.setAttribute("aria-label", `Remove ${source.file.name} from recent images`);
    remove.innerHTML = `
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M4 7h16M9 3h6l1 4H8l1-4Zm-2 4 1 14h8l1-14M10 11v6m4-6v6" />
      </svg>
    `;
    remove.addEventListener("click", (event) => removeRecentSource(source.id, event.altKey));

    const caption = document.createElement("figcaption");
    const captionHeading = document.createElement("div");
    captionHeading.className = "caption-heading";
    const captionName = document.createElement("strong");
    captionName.textContent = source.file.name;
    const actions = document.createElement("div");
    actions.className = "card-actions";
    actions.append(remove);
    captionHeading.append(captionName, actions);

    const metadata = document.createElement("span");
    metadata.textContent = sourceMetadata(source);
    caption.append(captionHeading, metadata);

    const updateDimensions = () => {
      source.width = image.naturalWidth;
      source.height = image.naturalHeight;
      metadata.textContent = sourceMetadata(source);
    };
    if (image.complete && image.naturalWidth) updateDimensions();
    else image.addEventListener("load", updateDimensions, { once: true });

    figure.append(select, caption);
    inputPreview.append(figure);
  }
  inputPreview.append(recentPlaceholder);
  updateDropPromptVisibility();
}

new ResizeObserver(updateDropPromptVisibility).observe(inputPreview);

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
    const indicator = document.createElement("span");
    indicator.className = item.waiting ? "result-queue-icon" : "result-spinner";
    indicator.setAttribute("aria-hidden", "true");
    if (item.waiting) {
      indicator.innerHTML = `
        <svg viewBox="0 0 24 24">
          <path d="M4 6h16M4 12h16M4 18h10m3-2 3 2-3 2" />
        </svg>
      `;
    }
    const progress = document.createElement("strong");
    progress.textContent = item.progress;
    const progressDetail = document.createElement("span");
    progressDetail.className = "result-progress-detail";
    progressDetail.textContent = item.progressDetail || "";
    progressDetail.hidden = !item.progressDetail;
    placeholder.append(indicator, progress, progressDetail);

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
  historyNote.textContent = activeRuns.size > 0
    ? `${activeRuns.size} active ${activeRuns.size === 1 ? "run" : "runs"} · Newest first`
    : "Newest first";
}

function addPendingRun(batch) {
  runSequence += 1;
  const token = `${Date.now()}:${runSequence}`;
  const wear = Number(wearSelect.value);
  const settings = treatmentSummary(
    halftoneSelect.value,
    wear,
    textureSelect.value,
  );
  const run = {
    token,
    number: runSequence,
    jobId: null,
    state: "uploading",
    completed: 0,
    batchIds: batch.map((source) => source.id),
    items: batch.map((source, index) => ({
      id: `pending:${token}:${index}`,
      pending: true,
      index,
      name: source.file.name,
      progress: index === 0 ? "Uploading" : "Waiting for upload",
      progressDetail: "",
      waiting: index !== 0,
      meta: settings,
    })),
  };
  activeRuns.set(token, run);
  resultItems = [...run.items, ...resultItems];
  renderResults();
  renderRecentSources();
  return run;
}

function resultFromFile(job, file) {
  const size = `${file.output.width}×${file.output.height} px · ${formatBytes(file.output.bytes)}`;
  const treatment = treatmentSummary(
    job.settings.halftone || "none",
    job.settings.grunge,
    job.settings.texture,
  );
  return {
    id: `${job.id}:${file.index}`,
    pending: false,
    index: file.index,
    name: file.name,
    thumbnailUrl: file.preview,
    url: file.download,
    sourceUrl: file.source,
    deleteUrl: file.delete,
    meta: `${size} · ${treatment}`,
  };
}

function updatePendingRun(run, job) {
  run.state = job.state;
  run.completed = job.completed;
  const finished = new Map(job.files.map((file) => [file.index, file]));
  for (const item of run.items) {
    const file = finished.get(item.index);
    if (file) {
      Object.assign(item, resultFromFile(job, file));
      continue;
    }
    if (job.state === "queued") {
      item.progress = "Waiting in queue";
      item.progressDetail = "";
      item.waiting = true;
    } else {
      const active = item.index === job.completed;
      const step = Number(job.progress?.step);
      const totalSteps = Number(job.progress?.total_steps);
      const hasStepProgress = step > 0 && totalSteps > 0;
      item.progress = active
        ? (hasStepProgress ? `Processing step ${step} of ${totalSteps}` : "Processing")
        : `Queued image ${item.index + 1} of ${job.total}`;
      item.progressDetail = active && hasStepProgress ? (job.progress?.label || "") : "";
      item.waiting = !active;
    }
  }
  renderResults();
  renderRecentSources();
}

function clearUnfinishedPendingItems(run) {
  const unfinishedIds = new Set(
    run.items.filter((item) => item.pending).map((item) => item.id),
  );
  resultItems = resultItems.filter((item) => !unfinishedIds.has(item.id));
  renderResults();
}

function openResultPreview(id) {
  currentResultId = id;
  setPreviewCompare(false);
  updateResultPreview();
  if (!previewDialog.open) previewDialog.showModal();
}

function availablePreviewItems() {
  return resultItems.filter((item) => !item.pending);
}

function updateResultPreview() {
  const previewItems = availablePreviewItems();
  const index = previewItems.findIndex((item) => item.id === currentResultId);
  if (index < 0) return;
  const item = previewItems[index];
  previewLarge.src = item.url;
  previewLarge.alt = item.name;
  previewOriginal.src = item.sourceUrl;
  previewTitle.textContent = item.name;
  previewMeta.textContent = item.meta;
  previewDownload.href = item.url;
  previewDownload.download = item.name;
  previewPrevious.disabled = index === 0;
  previewNext.disabled = index === previewItems.length - 1;
  setPreviewZoom(false);
}

function setPreviewCompare(comparing) {
  previewZoom.classList.toggle("comparing", comparing);
  previewCompare.setAttribute("aria-pressed", String(comparing));
  previewCompare.setAttribute("aria-label", comparing ? "Hide original lens" : "Show original lens");
  previewCompare.dataset.tooltip = comparing
    ? "Hide original comparison (C)"
    : "Compare with original (C)";
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
  const previewItems = availablePreviewItems();
  const index = previewItems.findIndex((item) => item.id === currentResultId);
  const nextIndex = index + offset;
  if (index < 0 || nextIndex < 0 || nextIndex >= previewItems.length) return;
  currentResultId = previewItems[nextIndex].id;
  updateResultPreview();
}

async function deleteResult(id, skipConfirmation = false) {
  const index = resultItems.findIndex((item) => item.id === id);
  if (index < 0) return;
  const item = resultItems[index];
  if (!skipConfirmation && !window.confirm(`Delete ${item.name}? This cannot be undone.`)) return;
  const response = await fetch(item.deleteUrl, { method: "DELETE" });
  if (!response.ok) {
    showError(new Error("Could not delete the result"));
    return;
  }
  resultItems.splice(index, 1);
  renderResults();
  if (currentResultId !== id) return;
  const previewItems = availablePreviewItems();
  if (previewItems.length === 0) {
    currentResultId = null;
    previewDialog.close();
    return;
  }
  currentResultId = previewItems[Math.min(index, previewItems.length - 1)].id;
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
const halftoneSelect = document.querySelector("#halftone");
textureSelect.addEventListener("change", () => {
  wearSelect.disabled = textureSelect.value === "none";
});
favoritePresetSelect.addEventListener("change", () => {
  const favorite = favoritePresets.find(({ id }) => id === favoritePresetSelect.value);
  deleteFavoriteButton.disabled = !favorite;
  if (favorite) applyFavorite(favorite);
});
saveFavoriteButton.addEventListener("click", openFavoriteEditor);
confirmFavoriteButton.addEventListener("click", saveCurrentFavorite);
cancelFavoriteButton.addEventListener("click", () => favoriteDialog.close());
favoriteNameInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    saveCurrentFavorite();
  }
});
deleteFavoriteButton.addEventListener("click", (event) => deleteCurrentFavorite(event.altKey));
settingsOpen.addEventListener("click", () => settingsDialog.showModal());
settingsClose.addEventListener("click", () => settingsDialog.close());
settingsDialog.addEventListener("click", (event) => {
  if (event.target === settingsDialog) settingsDialog.close();
});
async function copySettingsTemplate(button, template) {
  const originalLabel = button.textContent;
  try {
    await navigator.clipboard.writeText(template);
    button.textContent = "Copied";
  } catch (_) {
    button.textContent = "Copy failed";
  }
  setTimeout(() => { button.textContent = originalLabel; }, 1600);
}

settingsCopy.addEventListener("click", () => {
  const template = `# Add these lines to the existing services.inklathe block.
services.inklathe = {
  lucidaCommand = "/opt/lucida/.venv/bin/bgr";
  realEsrganBinary = "/opt/realesrgan/realesrgan-ncnn-vulkan";
  realEsrganModelDir = "/opt/realesrgan/models";
  realEsrganModel = "realesrgan-x4plus";
};

# Then apply it from SSH:
sudo nixos-rebuild switch --flake /etc/nixos#server`;
  copySettingsTemplate(settingsCopy, template);
});
settingsRemove.addEventListener("click", () => {
  const template = `# Remove the AI option lines from the existing services.inklathe block,
# or set the optional command paths to null:
services.inklathe = {
  aiUpscalerCommand = null;
  realEsrganBinary = null;
  realEsrganModelDir = null;
  lucidaCommand = null;
};

# Then apply it from SSH:
sudo nixos-rebuild switch --flake /etc/nixos#server

# This disconnects the workers without deleting InkLathe data.
# Remove externally installed AI files separately only after verifying their paths.`;
  copySettingsTemplate(settingsRemove, template);
});
settingsRecheck.addEventListener("click", async () => {
  settingsRecheck.disabled = true;
  settingsRecheck.textContent = "Checking…";
  try {
    await loadCapabilities({ refresh: true });
  } catch (error) {
    updateServiceStatus(upscalerStatus, false);
    updateServiceStatus(lucidaStatus, false);
    settingsWorkerNote.textContent = error.message;
  } finally {
    settingsRecheck.disabled = false;
    settingsRecheck.textContent = "Check again";
  }
});
document.querySelector(".controls").addEventListener("change", () => {
  favoritePresetSelect.value = "";
  deleteFavoriteButton.disabled = true;
});
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
    dropZone.classList.add("dragging");
  });
}
for (const eventName of ["dragleave", "drop"]) {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.remove("dragging");
  });
}
dropZone.addEventListener("drop", (event) => addRecentSources([...event.dataTransfer.files]));

function updateServiceStatus(element, configured) {
  element.textContent = configured ? "Configured" : "Not configured";
  element.classList.toggle("ready", configured);
  element.classList.toggle("missing", !configured);
}

async function loadCapabilities({ refresh = false } = {}) {
  const response = await fetch("/api/health");
  if (!response.ok) throw new Error("Could not read server capabilities");
  const health = await response.json();
  maxImagePixels = Number(health.max_image_pixels) || null;
  const lucida = document.querySelector("#lucida-option");
  const ai = document.querySelector("#ai-option");
  lucida.disabled = !health.capabilities.lucida;
  ai.disabled = !health.capabilities.ai_upscaler;
  if (ai.disabled && form.elements.namedItem("upscale").value === "ai") {
    form.elements.namedItem("upscale").value = "lanczos";
  }
  if (lucida.disabled && form.elements.namedItem("background").value === "lucida") {
    form.elements.namedItem("background").value = "threshold";
  }
  lucida.textContent = `Lucida AI — ${lucida.disabled ? "not configured" : "configured"}`;
  ai.textContent = `AI model — ${ai.disabled ? "not configured" : "configured"}`;
  updateServiceStatus(upscalerStatus, health.capabilities.ai_upscaler);
  updateServiceStatus(lucidaStatus, health.capabilities.lucida);
  settingsWorkerNote.textContent = `${health.workers} image worker · submitted runs are processed in FIFO order.`;
  if (refresh) return health;
  const halftones = health.capabilities.halftones || [];
  const halftoneGroups = new Map();
  for (const treatment of halftones) {
    halftoneLabels[treatment.id] = treatment.label;
    if (!halftoneGroups.has(treatment.category)) {
      const group = document.createElement("optgroup");
      group.label = treatment.category;
      halftoneGroups.set(treatment.category, group);
    }
    const option = document.createElement("option");
    option.value = treatment.id;
    option.textContent = treatment.label;
    halftoneGroups.get(treatment.category).append(option);
  }
  halftoneSelect.append(...halftoneGroups.values());
  const scanned = health.capabilities.bitmap_textures || [];
  if (scanned.length > 0) {
    const groups = new Map();
    for (const texture of scanned) {
      textureLabels[texture.id] = texture.label;
      if (!groups.has(texture.category)) {
        const group = document.createElement("optgroup");
        group.label = texture.category;
        groups.set(texture.category, group);
      }
      const option = document.createElement("option");
      option.value = texture.id;
      option.textContent = textureMenuLabel(texture.label);
      groups.get(texture.category).append(option);
    }
    const none = document.createElement("option");
    none.value = "none";
    none.textContent = "None";
    textureSelect.replaceChildren(none, ...groups.values());
    textureSelect.value = "none";
    wearSelect.value = "50";
    wearSelect.disabled = true;
  } else {
    textureSelect.disabled = true;
    wearSelect.disabled = true;
  }
  capabilitiesReady = true;
  renderFavoritePresets();
  return health;
}

function setSubmitting(submitting) {
  isSubmitting = submitting;
  submitButton.disabled = submitting;
  form.classList.toggle("is-submitting", submitting);
}

function randomSelectOption(select, { exclude = [] } = {}) {
  const choices = [...select.options].filter((option) => (
    !option.disabled && !exclude.includes(option.value)
  ));
  if (choices.length === 0) return;
  select.value = choices[Math.floor(Math.random() * choices.length)].value;
}

function randomizePrintTreatment() {
  randomSelectOption(halftoneSelect);
  randomSelectOption(textureSelect, { exclude: ["none"] });
  randomSelectOption(wearSelect);
  randomSelectOption(form.elements.namedItem("seed"));
  wearSelect.disabled = textureSelect.value === "none";
  favoritePresetSelect.value = "";
  deleteFavoriteButton.disabled = true;
}

submitButton.addEventListener("click", (event) => {
  if (event.altKey) randomizePrintTreatment();
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (isSubmitting) return;
  const batch = recentSources.filter((source) => selectedSourceIds.has(source.id));
  if (batch.length === 0) {
    showError(new Error("Select at least one of your recent images"));
    return;
  }
  const limitError = processingLimitError(batch);
  if (limitError) {
    showError(new Error(limitError));
    return;
  }
  const run = addPendingRun(batch);
  setSubmitting(true);
  statusBox.hidden = true;
  statusBox.className = "status";
  statusBox.textContent = "";
  try {
    const body = new FormData(form);
    for (const source of batch) body.append("files", source.file, source.file.name);
    const response = await fetch("/api/jobs", { method: "POST", body });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Upload failed");
    run.jobId = payload.id;
    updatePendingRun(run, payload);
    pollRun(run).catch((error) => failRun(run, error));
  } catch (error) {
    failRun(run, error);
  } finally {
    setSubmitting(false);
  }
});

async function pollRun(run) {
  const response = await fetch(`/api/jobs/${run.jobId}`);
  if (!response.ok) throw new Error("Could not read queued run");
  const job = await response.json();
  updatePendingRun(run, job);
  if (job.state === "failed") throw new Error(job.error || "Processing failed");
  if (job.state !== "complete") {
    setTimeout(() => pollRun(run).catch((error) => failRun(run, error)), 500);
    return;
  }
  activeRuns.delete(run.token);
  renderResults();
  renderRecentSources();
}

function failRun(run, error) {
  activeRuns.delete(run.token);
  clearUnfinishedPendingItems(run);
  renderRecentSources();
  showError(error, `Run ${run.number}`);
}

function showError(error, prefix = "") {
  statusBox.hidden = false;
  statusBox.className = "status failed";
  statusBox.textContent = prefix ? `${prefix}: ${error.message}` : error.message;
}

loadCapabilities().catch(() => {});
