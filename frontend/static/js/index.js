// For indexhtml

const form = document.getElementById("searchForm");
const input = document.getElementById("addressInput");
const preview = document.getElementById("addressPreview");
const btn = document.getElementById("searchBtn");

const riskScoreEl = document.getElementById("riskScore");
const confidenceEl = document.getElementById("confidence");
const recommendationEl = document.getElementById("recommendation");

function updatePreview() {
  const value = input.value.trim();
  preview.textContent = value ? value : "Enter a new valid bitcoin address...";
}

function setEmpty() {
  riskScoreEl.textContent = "None"
  confidenceEl.textContent = "?.??";
  recommendationEl.textContent = "Unknown";
  recommendationEl.className = "danger";
}

function setLoading() {
  btn.disabled = true;
  btn.textContent = "…";

  riskScoreEl.textContent = "…";
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

function showFormAlert(message) {
  const alertContainer = document.getElementById("formAlert");

  alertContainer.innerHTML = `
    <div class="alert alert-danger alert-dismissible fade show mt-2" role="alert">
      ${message}
      <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    </div>
  `;

  setTimeout(() => {
    alertContainer.innerHTML = "";
  }, 5000);
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const address = input.value.trim();

  updatePreview();

  if (!address) {
    setEmpty();
    return;
  }

  if (!(address.startsWith("bc1") || address.startsWith("1") || address.startsWith("3"))) {
    showFormAlert("Please enter a valid Bitcoin address starting with a 1, 3, or bc1.");
    input.focus();
    setEmpty();
    return;
  }

  setLoading();

  try {
    const res = await fetch("/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ seed_parameter: address }),
    });

    const payload = await res.json();

    if (!res.ok) {
      const message = payload.detail || "Server returned an error.";
      showFormAlert(message);
      recommendationEl.textContent = "Error";
      recommendationEl.className = "danger";
      return;
    }

    setResult(payload);
  } catch (err) {
    showFormAlert("Could not reach the server. Please try again.");
    recommendationEl.textContent = "Error";
    recommendationEl.className = "danger";
    console.error("Error submitting form:", err);
  } finally {
    clearLoading();
  }
});