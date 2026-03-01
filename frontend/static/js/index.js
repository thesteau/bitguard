// For indexhtml

const form = document.getElementById("searchForm");
const input = document.getElementById("addressInput");
const preview = document.getElementById("addressPreview");
const btn = document.getElementById("searchBtn");

const riskScoreEl = document.getElementById("riskScore");
const predictedTypeEl = document.getElementById("predictedType");
const confidenceEl = document.getElementById("confidence");
const recommendationEl = document.getElementById("recommendation");

function updatePreview() {
  const value = input.value.trim();
  preview.textContent = value ? value : "No address entered yet...";
}

function setEmpty() {
  riskScoreEl.textContent = "None";
  predictedTypeEl.textContent = "None";
  confidenceEl.textContent = "?.??";
  recommendationEl.textContent = "Unknown";
  recommendationEl.className = "danger";
}

function setLoading() {
  btn.disabled = true;
  btn.textContent = "…";

  riskScoreEl.textContent = "…";
  predictedTypeEl.textContent = "…";
  confidenceEl.textContent = "…";
  recommendationEl.textContent = "Checking…";
  recommendationEl.className = "warn";
}

function clearLoading() {
  btn.disabled = false;
  btn.textContent = "🔍";
}

function setResult(data) {
  riskScoreEl.textContent = data.risk_score ?? "None";
  predictedTypeEl.textContent = data.predicted_type ?? "None";

  confidenceEl.textContent =
    data.confidence !== undefined && data.confidence !== null
      ? Number(data.confidence).toFixed(2)
      : "?.??";

  const rec = data.recommendation ?? "Unknown";
  recommendationEl.textContent = rec;

  recommendationEl.classList.remove("danger", "warn", "success");

  if (rec === "DO_NOT_SEND") {
    recommendationEl.classList.add("danger");
  } else if (rec === "CAUTION") {
    recommendationEl.classList.add("warn");
  } else if (rec === "SAFE") {
    recommendationEl.classList.add("success");
  } else {
    recommendationEl.classList.add("danger");
  }
}

input.addEventListener("input", updatePreview);

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const address = input.value.trim();
  updatePreview();

  if (!address) {
    setEmpty();
    return;
  }

  setLoading();

  try {
    const res = await fetch("/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ address }),
    });

    const payload = await res.json();

    if (!res.ok) {
      recommendationEl.textContent = payload?.detail || `Error (${res.status})`;
      recommendationEl.className = "danger";
      clearLoading();
      return;
    }

    setResult(payload);
  } catch (err) {
    recommendationEl.textContent = "Network error";
    recommendationEl.className = "danger";
  }

  clearLoading();
});