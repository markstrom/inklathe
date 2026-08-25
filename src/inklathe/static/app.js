const form = document.querySelector("#job-form");
const fileInput = document.querySelector("#files");
const dropZone = document.querySelector("#drop-zone");
const inputPreview = document.querySelector("#input-preview");
const statusBox = document.querySelector("#status");
const results = document.querySelector("#results");
const resultHistory = document.querySelector("#result-history");
const submitButton = form.querySelector("button[type=submit]");
const previewDialog = document.querySelector("#preview-dialog");
const previewLarge = document.querySelector("#preview-large");
const previewTitle = document.querySelector("#preview-title");
const previewMeta = document.querySelector("#preview-meta");

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

function openPreview(url, name, meta) {
  previewLarge.src = url;
  previewLarge.alt = name;
  previewTitle.textContent = name;
  previewMeta.textContent = meta;
  previewDialog.showModal();
}

function card(url, name, options = {}) {
  const figure = document.createElement("figure");
  figure.className = "preview";

  const previewButton = document.createElement("button");
  previewButton.className = "preview-open";
  previewButton.type = "button";
  previewButton.title = `View ${name} larger`;
  const image = document.createElement("img");
  image.src = url;
  image.alt = name;
  previewButton.append(image);
  previewButton.addEventListener("click", () => openPreview(url, name, options.meta || ""));

  const caption = document.createElement("figcaption");
  const captionHeading = document.createElement("div");
  captionHeading.className = "caption-heading";
  const captionName = document.createElement("strong");
  captionName.textContent = name;
  captionHeading.append(captionName);
  if (options.downloadable) {
    const download = document.createElement("a");
    download.className = "download-icon";
    download.href = url;
    download.download = name;
    download.title = `Download ${name}`;
    download.setAttribute("aria-label", `Download ${name}`);
    download.innerHTML = `
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 3v12m0 0 5-5m-5 5-5-5M5 20h14" />
      </svg>
    `;
    captionHeading.append(download);
  }
  const metadata = document.createElement("span");
  metadata.textContent = options.meta || "Click the image for a full-size view";
  caption.append(captionHeading, metadata);
  figure.append(previewButton, caption);
  return figure;
}

function previewFiles() {
  inputPreview.replaceChildren();
  for (const file of fileInput.files) {
    inputPreview.append(
      card(URL.createObjectURL(file), file.name, { meta: `${formatBytes(file.size)} · original` }),
    );
  }
}

fileInput.addEventListener("change", previewFiles);
const grungeSlider = document.querySelector("#grunge");
grungeSlider.addEventListener("input", (event) => {
  const value = Number(event.target.value);
  document.querySelector("#grunge-value").textContent = `${value} · ${grungeDescription(value)}`;
});
document.querySelector("#preview-close").addEventListener("click", () => previewDialog.close());
previewDialog.addEventListener("click", (event) => {
  if (event.target === previewDialog) previewDialog.close();
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
dropZone.addEventListener("drop", (event) => {
  fileInput.files = event.dataTransfer.files;
  previewFiles();
});

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

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  submitButton.disabled = true;
  statusBox.hidden = false;
  statusBox.className = "status";
  statusBox.textContent = "Uploading…";
  try {
    const response = await fetch("/api/jobs", { method: "POST", body: new FormData(form) });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || "Upload failed");
    await poll(body.id);
  } catch (error) {
    showPollError(error);
  }
});

async function poll(jobId) {
  const response = await fetch(`/api/jobs/${jobId}`);
  const job = await response.json();
  statusBox.textContent = `Processing ${job.completed} of ${job.total}…`;
  if (job.state === "failed") throw new Error(job.error || "Processing failed");
  if (job.state !== "complete") {
    setTimeout(() => poll(jobId).catch(showPollError), 500);
    return;
  }
  renderRun(job);
  statusBox.hidden = true;
  submitButton.disabled = false;
}

function renderRun(job) {
  const runResults = document.createDocumentFragment();
  for (const file of job.files) {
    const size = `${file.output.width}×${file.output.height} px · ${formatBytes(file.output.bytes)}`;
    const grunge = `Grunge ${job.settings.grunge} · ${grungeDescription(job.settings.grunge)}`;
    runResults.append(
      card(file.download, file.name, {
        downloadable: true,
        meta: `${size} · ${grunge}`,
      }),
    );
  }
  resultHistory.prepend(runResults);
  results.hidden = false;
}

function showPollError(error) {
  statusBox.hidden = false;
  statusBox.classList.add("failed");
  statusBox.textContent = error.message;
  submitButton.disabled = false;
}

loadCapabilities().catch(() => {});
