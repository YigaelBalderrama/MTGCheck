const form = document.querySelector("#recognition-form");
const fileInput = document.querySelector("#image-input");
const dropZone = document.querySelector("#drop-zone");
const previewImage = document.querySelector("#preview-image");
const emptyPreview = document.querySelector("#empty-preview");
const submitButton = document.querySelector("#submit-button");
const statusPill = document.querySelector("#status-pill");
const message = document.querySelector("#message");
const metrics = document.querySelector("#metrics");
const cardsGrid = document.querySelector("#cards-grid");

const acceptedTypes = new Set(["image/png", "image/jpeg", "image/webp"]);
let selectedFile = null;

function setStatus(text, state = "idle") {
  statusPill.textContent = text;
  statusPill.dataset.state = state;
}

function setMessage(text, state = "info") {
  message.textContent = text;
  message.dataset.state = state;
  message.hidden = !text;
}

function clearResults() {
  metrics.innerHTML = "";
  cardsGrid.innerHTML = "";
}

function validateFile(file) {
  if (!file) {
    return "Choose an image before scanning.";
  }

  if (!acceptedTypes.has(file.type)) {
    return "Use a PNG, JPG, or WEBP image.";
  }

  return "";
}

function updatePreview(file) {
  clearResults();

  const validationError = validateFile(file);
  if (validationError) {
    selectedFile = null;
    previewImage.removeAttribute("src");
    previewImage.classList.remove("is-visible");
    emptyPreview.hidden = false;
    setStatus("Waiting for image");
    setMessage(file ? validationError : "", file ? "error" : "info");
    return;
  }

  selectedFile = file;
  const previewUrl = URL.createObjectURL(file);
  previewImage.src = previewUrl;
  previewImage.onload = () => URL.revokeObjectURL(previewUrl);
  previewImage.classList.add("is-visible");
  emptyPreview.hidden = true;
  setStatus("Image ready", "ready");
  setMessage(file.name);
}

function formatPercent(value) {
  if (typeof value !== "number") {
    return "N/A";
  }
  return `${Math.round(value * 100)}%`;
}

function formatMoney(prices) {
  if (!prices) {
    return "";
  }

  const entries = Object.entries(prices).filter(([, value]) => value);
  return entries.length
    ? entries.map(([currency, value]) => `${currency.toUpperCase()} ${value}`).join(" - ")
    : "";
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function readResponsePayload(response) {
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }

  const text = await response.text();
  return {
    error: {
      message: text || `Request failed with status ${response.status}.`,
    },
  };
}

function renderMetrics(payload) {
  metrics.innerHTML = `
    <div><strong>${payload.cards_detected ?? 0}</strong><span>Detected</span></div>
    <div><strong>${payload.cards_recognized ?? 0}</strong><span>Recognized</span></div>
    <div><strong>${payload.processing_time_ms ?? 0} ms</strong><span>Runtime</span></div>
  `;
}

function renderCard(card) {
  const cardElement = document.createElement("article");
  cardElement.className = "result-card";

  const imageUrl = card.image_url || "";
  const prices = formatMoney(card.prices);
  const title = card.name || card.detected_text || "Unrecognized card";
  const setLine = [card.set_name, card.set_code, card.collector_number]
    .filter(Boolean)
    .join(" - ");

  cardElement.innerHTML = `
    <div class="art-frame">
      ${
        imageUrl
          ? `<img src="${escapeHtml(imageUrl)}" alt="${escapeHtml(title)}">`
          : `<div class="missing-art">No image</div>`
      }
    </div>
    <div class="card-body">
      <div class="card-title-row">
        <h3>${escapeHtml(title)}</h3>
        <span>${formatPercent(card.confidence)}</span>
      </div>
      <p class="detected-text">${escapeHtml(card.detected_text || "No title text detected")}</p>
      <dl>
        <div><dt>OCR</dt><dd>${formatPercent(card.ocr_confidence)}</dd></div>
        <div><dt>Match</dt><dd>${formatPercent(card.name_match_confidence)}</dd></div>
        <div><dt>Shape</dt><dd>${formatPercent(card.detection_confidence)}</dd></div>
      </dl>
      ${setLine ? `<p class="set-line">${escapeHtml(setLine)}</p>` : ""}
      ${prices ? `<p class="prices">${escapeHtml(prices)}</p>` : ""}
      ${
        card.scryfall_url
          ? `<a class="scryfall-link" href="${escapeHtml(card.scryfall_url)}" target="_blank" rel="noreferrer">Open in Scryfall</a>`
          : ""
      }
    </div>
  `;
  return cardElement;
}

function renderCards(cards) {
  cardsGrid.innerHTML = "";
  if (!cards || cards.length === 0) {
    setMessage("No complete cards were detected in this image.", "warning");
    return;
  }

  const fragment = document.createDocumentFragment();
  cards.forEach((card) => fragment.appendChild(renderCard(card)));
  cardsGrid.appendChild(fragment);
}

async function recognizeSelectedImage() {
  const validationError = validateFile(selectedFile);
  if (validationError) {
    setMessage(validationError, "error");
    setStatus("Image required", "error");
    return;
  }

  const endpoint = form.dataset.endpoint || "/api/cards/recognize";
  const body = new FormData();
  body.append("image", selectedFile, selectedFile.name || "cards-upload.png");

  submitButton.disabled = true;
  setStatus("Scanning", "busy");
  setMessage(`Uploading image to ${endpoint}...`);
  clearResults();

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        Accept: "application/json",
      },
      credentials: "same-origin",
      body,
    });
    const payload = await readResponsePayload(response);

    if (!response.ok) {
      throw new Error(payload.error?.message || `Request failed with status ${response.status}.`);
    }

    renderMetrics(payload);
    renderCards(payload.cards);
    setStatus("Complete", "success");
    setMessage("Scan complete.", "success");
  } catch (error) {
    setStatus("Request failed", "error");
    setMessage(error.message || "The scan request failed.", "error");
  } finally {
    submitButton.disabled = false;
  }
}

fileInput.addEventListener("change", (event) => {
  updatePreview(event.target.files[0] || null);
});

form.addEventListener("submit", (event) => {
  event.preventDefault();
  recognizeSelectedImage();
});

dropZone.addEventListener("dragover", (event) => {
  event.preventDefault();
  dropZone.classList.add("is-dragging");
});

dropZone.addEventListener("dragleave", () => {
  dropZone.classList.remove("is-dragging");
});

dropZone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropZone.classList.remove("is-dragging");
  updatePreview(event.dataTransfer.files[0] || null);
});
