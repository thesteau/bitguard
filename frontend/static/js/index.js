// For indexhtml

const form = document.getElementById("searchForm");
const input = document.getElementById("addressInput");
const preview = document.getElementById("addressPreview");
const btn = document.getElementById("searchBtn");
const depthSelect = document.getElementById("depthSelect");

const riskScoreEl = document.getElementById("riskScore");
// const predictedTypeEl = document.getElementById("predictedType");
const confidenceEl = document.getElementById("confidence");
const recommendationEl = document.getElementById("recommendation");

function updatePreview() {
  const value = input.value.trim();
  preview.textContent = value ? value : "Enter a new valid bitcoin address...";
}

function setEmpty() {
  riskScoreEl.textContent = "None";
  // predictedTypeEl.textContent = "None";
  confidenceEl.textContent = "?.??";
  recommendationEl.textContent = "Unknown";
  recommendationEl.className = "danger";
}

function setLoading() {
  btn.disabled = true;
  btn.textContent = "…";

  riskScoreEl.textContent = "…";
  // predictedTypeEl.textContent = "…";
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
  // predictedTypeEl.textContent = data.predicted_type ?? "None";

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
  const depth = Number(depthSelect?.value ?? 0);
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
      body: JSON.stringify({ address, depth }),
    });

    const payload = await res.json();

    if (!res.ok) {
      recommendationEl.textContent = `Error`;
      recommendationEl.className = "danger";
      clearLoading();
      return;
    }

    setResult(payload);
  } catch (err) {
    console.error("Error submitting form:", err);
  }

  clearLoading();
});

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

document.getElementById("searchForm").addEventListener("submit", async function(e) {

  e.preventDefault();

  const input = document.getElementById("addressInput");
  const depth = document.getElementById("depthSelect").value;
  const addr = input.value.trim();

  if (!(addr.startsWith("bc1") || addr.startsWith("1") || addr.startsWith("3"))) {
    showFormAlert("Please enter a valid Bitcoin address starting with a 1, 3, or bc1.");
    input.focus();
    return;
  }

  try {
    const response = await fetch("/submit", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        address: addr,
        depth: parseInt(depth, 10)
      })
    });

    if (!response.ok) {

      let message = "Server returned an error.";

      const data = await response.json();
      if (data.detail) {
        message = data.detail;
      }

      showFormAlert(message);
      return;
    }

  } catch (err) {
    showFormAlert("Could not reach the server. Please try again.");
  }

});