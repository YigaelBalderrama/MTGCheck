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

function updatePreview(file) {
  selectedFile = file;
  clearResults();

  if (!file) {
    previewImage.removeAttribute("src");
    previewImage.classList.remove("is-visible");
    emptyPreview.hidden = false;
    setStatus("Esperando imagen");
    setMessage("");
    return;
  }

  const previewUrl = URL.createObjectURL(file);
  previewImage.src = previewUrl;
  previewImage.onload = () => URL.revokeObjectURL(previewUrl);
  previewImage.classList.add("is-visible");
  emptyPreview.hidden = true;
  setStatus("Imagen lista", "ready");
  setMessage(file.name);
}

function formatPercent(value) {
  if (typeof value !== "number") {
    return "N/D";
  }
  return `${Math.round(value * 100)}%`;
}

function formatMoney(prices) {
  if (!prices) {
    return "";
  }
  const entries = Object.entries(prices).filter(([, value]) => value);
  return entries.length
    ? entries.map(([currency, value]) => `${currency.toUpperCase()} ${value}`).join(" · ")
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

function renderMetrics(payload) {
  metrics.innerHTML = `
    <div><strong>${payload.cards_detected ?? 0}</strong><span>detectadas</span></div>
    <div><strong>${payload.cards_recognized ?? 0}</strong><span>reconocidas</span></div>
    <div><strong>${payload.processing_time_ms ?? 0} ms</strong><span>proceso</span></div>
  `;
}

function renderCard(card) {
  const cardElement = document.createElement("article");
  cardElement.className = "result-card";

  const imageUrl = card.image_url || "";
  const prices = formatMoney(card.prices);
  const title = card.name || card.detected_text || "Carta sin reconocer";
  const setLine = [card.set_name, card.set_code, card.collector_number]
    .filter(Boolean)
    .join(" · ");

  cardElement.innerHTML = `
    <div class="art-frame">
      ${
        imageUrl
          ? `<img src="${escapeHtml(imageUrl)}" alt="${escapeHtml(title)}">`
          : `<div class="missing-art">Sin imagen</div>`
      }
    </div>
    <div class="card-body">
      <div class="card-title-row">
        <h3>${escapeHtml(title)}</h3>
        <span>${formatPercent(card.confidence)}</span>
      </div>
      <p class="detected-text">${escapeHtml(card.detected_text || "Texto no detectado")}</p>
      <dl>
        <div><dt>OCR</dt><dd>${formatPercent(card.ocr_confidence)}</dd></div>
        <div><dt>Matching</dt><dd>${formatPercent(card.name_match_confidence)}</dd></div>
        <div><dt>Deteccion</dt><dd>${formatPercent(card.detection_confidence)}</dd></div>
      </dl>
      ${setLine ? `<p class="set-line">${escapeHtml(setLine)}</p>` : ""}
      ${prices ? `<p class="prices">${escapeHtml(prices)}</p>` : ""}
      ${
        card.scryfall_url
          ? `<a class="scryfall-link" href="${escapeHtml(card.scryfall_url)}" target="_blank" rel="noreferrer">Ver en Scryfall</a>`
          : ""
      }
    </div>
  `;
  return cardElement;
}

function renderCards(cards) {
  cardsGrid.innerHTML = "";
  if (!cards || cards.length === 0) {
    setMessage("No se detectaron cartas completas en la imagen.", "warning");
    return;
  }

  const fragment = document.createDocumentFragment();
  cards.forEach((card) => fragment.appendChild(renderCard(card)));
  cardsGrid.appendChild(fragment);
}

async function recognizeSelectedImage() {
  if (!selectedFile) {
    setMessage("Selecciona una imagen antes de reconocer cartas.", "error");
    setStatus("Falta imagen", "error");
    return;
  }

  const body = new FormData();
  body.append("image", selectedFile);

  submitButton.disabled = true;
  setStatus("Analizando", "busy");
  const endpoint = form.dataset.endpoint || "/api/cards/recognize";
  setMessage(`Enviando imagen al endpoint ${endpoint}...`);
  clearResults();

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      body,
    });
    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.error?.message || "No se pudo reconocer la imagen.");
    }

    renderMetrics(payload);
    renderCards(payload.cards);
    setStatus("Completado", "success");
    setMessage("Reconocimiento completado.", "success");
  } catch (error) {
    setStatus("Error", "error");
    setMessage(error.message, "error");
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
  const file = event.dataTransfer.files[0];
  if (!file) {
    return;
  }
  fileInput.files = event.dataTransfer.files;
  updatePreview(file);
});
