// DOM references
const form = document.getElementById("searchForm");
const input = document.getElementById("addressInput");
// const preview = document.getElementById("addressPreview");
const btn = document.getElementById("searchBtn");
const formAlert = document.getElementById("formAlert");
const mempoolLinkEl = document.getElementById("mempoolLink");
const riskProbabilityEl = document.getElementById("riskProbability");
const statTxsEl = document.getElementById("statTxs");
const statWalletsEl = document.getElementById("statWallets");
const statSentEl = document.getElementById("statSent");
const statReceivedEl = document.getElementById("statReceived");
const statFirstEl = document.getElementById("statFirst");
const statLastEl = document.getElementById("statLast");
const findingsListEl = document.getElementById("findingsList");
const detailCopyButtons = Array.from(document.querySelectorAll(".detail-copy-btn"));

// Static config
const defaultButtonHtml = btn.innerHTML;
const MEMPOOL_ADDRESS_URL = "https://mempool.space/address/";
// const EMPTY_ADDRESS_PREVIEW = "Enter a new valid bitcoin address...";
const FINDINGS_EMPTY_TEXT = "Run an analysis to see the main risk signals.";
const FINDINGS_NONE_TEXT = "No explainable reasons were returned for this wallet.";
const FINDINGS_LOADING_TEXT = "Analyzing wallet activity...";
const DETAIL_EXPLANATION_PLACEHOLDER = "Detailed explanation coming soon.";

const RISK_LABELS = {
  very_high: "Very High Risk",
  high: "High Risk",
  mixed_signal: "Mixed Signal",
  low: "Low Risk",
  very_low: "Very Low Risk",
};

const detailValueElements = {
  statSent: statSentEl,
  statReceived: statReceivedEl,
  statFirst: statFirstEl,
  statLast: statLastEl,
};

let alertTimeoutId = null;


function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function getInputAddress() {
  return input.value.trim();
}

function formatRiskLabel(value) {
  if (!value) {
    return "Unknown";
  }

  return RISK_LABELS[value] || String(value);
}

function formatBtc(value) {
  const numeric = Number(value);

  if (!Number.isFinite(numeric)) {
    return "-";
  }

  if (numeric === 0) {
    return "0 BTC";
  }

  if (Math.abs(numeric) < 0.0001) {
    return `${numeric.toExponential(2)} BTC`;
  }

  return `${numeric.toFixed(8)} BTC`;
}

function formatNumber(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric.toLocaleString() : "-";
}

function formatBlock(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? `#${numeric.toLocaleString()}` : "-";
}

function getReasonExplanation(reason) {
  const candidates = [
    reason.shap_explanation,
    reason.explanation,
    reason.explanation_why,
    reason.explanation_what,
  ];

  const explanation = candidates.find((value) => typeof value === "string" && value.trim());
  return explanation ? explanation.trim() : DETAIL_EXPLANATION_PLACEHOLDER;
}

// UI helpers
// Wallet preview was deprecated in the template, so its JS has been disabled too.
// function updatePreview(address = getInputAddress()) {
//   preview.textContent = address ? address : EMPTY_ADDRESS_PREVIEW;
// }

function resetRiskLevelState() {
  delete riskProbabilityEl.dataset.risk;
}

function setWalletActions(address) {
  const hasAddress = Boolean(address);

  if (!mempoolLinkEl) {
    return;
  }

  if (hasAddress) {
    mempoolLinkEl.href = `${MEMPOOL_ADDRESS_URL}${encodeURIComponent(address)}`;
    mempoolLinkEl.classList.remove("disabled");
    mempoolLinkEl.setAttribute("aria-disabled", "false");
    return;
  }

  mempoolLinkEl.href = "#";
  mempoolLinkEl.classList.add("disabled");
  mempoolLinkEl.setAttribute("aria-disabled", "true");
}

function setDetailCopyState(button, value) {
  if (!button) {
    return;
  }

  button.disabled = !(value && value !== "-");
}

function syncDetailCopyButtons() {
  detailCopyButtons.forEach((button) => {
    const targetId = button.dataset.copyTarget;
    const targetEl = targetId ? detailValueElements[targetId] : null;
    const value = targetEl?.textContent?.trim() || "";

    setDetailCopyState(button, value);
  });
}

function flashCopyButton(button) {
  if (!button) {
    return;
  }

  button.classList.add("copied");
  window.setTimeout(() => {
    button.classList.remove("copied");
  }, 1200);
}

async function copyValue(value, errorMessage, button) {
  try {
    await navigator.clipboard.writeText(value);
    flashCopyButton(button);
  } catch (error) {
    showFormAlert(errorMessage);
    console.error(errorMessage, error);
  }
}

function renderFindings(reasons) {
  if (!Array.isArray(reasons) || reasons.length === 0) {
    findingsListEl.innerHTML = `<div class="finding-empty">${FINDINGS_NONE_TEXT}</div>`;
    return;
  }

  findingsListEl.innerHTML = reasons.map((reason) => {
    const direction = reason.direction === "decreases_risk" ? "decreases_risk" : "increases_risk";
    const directionLabel = direction === "decreases_risk" ? "Decreases Risk" : "Increases Risk";
    const explanation = getReasonExplanation(reason);

    return `
      <div class="finding-item">
        <div class="finding-title-row">
          <p class="finding-title">${escapeHtml(reason.display_name || reason.feature || "Unnamed signal")}</p>
          <span class="finding-badge ${direction}">${directionLabel}</span>
        </div>
        <button type="button" class="finding-explanation-toggle" aria-expanded="true">Explanation</button>
        <div class="finding-explanation">
          <p class="finding-explanation-text">${escapeHtml(explanation)}</p>
        </div>
      </div>
    `;
  }).join("");
}

function setEmpty() {
  riskProbabilityEl.textContent = "Unknown";
  statTxsEl.textContent = "-";
  statWalletsEl.textContent = "-";
  statSentEl.textContent = "-";
  statReceivedEl.textContent = "-";
  statFirstEl.textContent = "-";
  statLastEl.textContent = "-";
  findingsListEl.innerHTML = `<div class="finding-empty">${FINDINGS_EMPTY_TEXT}</div>`;

  resetRiskLevelState();
  setWalletActions("");
  syncDetailCopyButtons();
}

function setLoading() {
  btn.disabled = true;
  btn.innerHTML = '<span class="search-icon">...</span><span>Analyze</span>';

  riskProbabilityEl.textContent = "Checking...";
  statTxsEl.textContent = "...";
  statWalletsEl.textContent = "...";
  statSentEl.textContent = "...";
  statReceivedEl.textContent = "...";
  statFirstEl.textContent = "...";
  statLastEl.textContent = "...";
  findingsListEl.innerHTML = `<div class="finding-empty">${FINDINGS_LOADING_TEXT}</div>`;

  resetRiskLevelState();
  setWalletActions("");
  syncDetailCopyButtons();
}

function clearLoading() {
  btn.disabled = false;
  btn.innerHTML = defaultButtonHtml;
}

function setResult(data) {
  const address = data.bitcoin_wallet || getInputAddress();

  // updatePreview(address);

  riskProbabilityEl.textContent = formatRiskLabel(data.risk_probability);
  statTxsEl.textContent = formatNumber(data.total_txs_analyzed);
  statWalletsEl.textContent = formatNumber(data.total_wallets_analyzed);
  statSentEl.textContent = formatBtc(data.btc_sent);
  statReceivedEl.textContent = formatBtc(data.btc_received);
  statFirstEl.textContent = formatBlock(data.first_active_block);
  statLastEl.textContent = formatBlock(data.last_active_block);

  resetRiskLevelState();
  if (data.risk_probability) {
    riskProbabilityEl.dataset.risk = String(data.risk_probability);
  }

  setWalletActions(address);
  syncDetailCopyButtons();
  renderFindings(data.top_reasons);
}

function showFormAlert(message) {
  if (alertTimeoutId) {
    clearTimeout(alertTimeoutId);
    alertTimeoutId = null;
  }

  formAlert.innerHTML = `
    <div class="toast-alert" role="alert" aria-live="assertive">
      <div class="toast-copy">
        <p class="toast-title">Error</p>
        <p class="toast-message">${escapeHtml(message)}</p>
      </div>
      <button type="button" class="toast-close" aria-label="Dismiss error">&times;</button>
    </div>
  `;

  const toastEl = formAlert.querySelector(".toast-alert");
  const closeBtn = formAlert.querySelector(".toast-close");

  const dismissAlert = () => {
    if (alertTimeoutId) {
      clearTimeout(alertTimeoutId);
      alertTimeoutId = null;
    }

    if (!toastEl) {
      formAlert.innerHTML = "";
      return;
    }

    toastEl.classList.remove("visible");

    window.setTimeout(() => {
      formAlert.innerHTML = "";
    }, 250);
  };

  closeBtn?.addEventListener("click", dismissAlert, { once: true });

  window.requestAnimationFrame(() => {
    toastEl?.classList.add("visible");
  });

  alertTimeoutId = window.setTimeout(() => {
    alertTimeoutId = null;
    dismissAlert();
  }, 5000);
}

// Event handlers
function handleFindingsClick(event) {
  const toggle = event.target.closest(".finding-explanation-toggle");
  if (!toggle) {
    return;
  }

  const findingItem = toggle.closest(".finding-item");
  if (!findingItem) {
    return;
  }

  const isOpen = findingItem.classList.toggle("open");
  toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
}

async function handleDetailCopyClick(button) {
  const targetId = button.dataset.copyTarget;
  const label = button.dataset.copyLabel || "value";
  const targetEl = targetId ? detailValueElements[targetId] : null;
  const value = targetEl?.textContent?.trim() || "";

  if (!value || value === "-") {
    return;
  }

  await copyValue(value, `Could not copy ${label}.`, button);
}

async function readResponsePayload(response) {
  try {
    return await response.json();
  } catch (parseError) {
    return null;
  }
}

function getResponseErrorMessage(response, payload) {
  if (payload && typeof payload.detail === "string" && payload.detail.trim()) {
    return payload.detail.trim();
  }

  if (response.status === 404) {
    return "Wallet address not found.";
  }

  if (response.status >= 400 && response.status < 500) {
    return "Request could not be processed.";
  }

  return "Server returned an error.";
}

async function handleSubmit(event) {
  event.preventDefault();

  const address = getInputAddress();
  // updatePreview(address);

  if (!address) {
    setEmpty();
    return;
  }

  if (!(address.startsWith("bc1") || address.startsWith("1") || address.startsWith("3"))) {
    showFormAlert("Please enter a valid Bitcoin address starting with a 1, 3, or bc1.");
    input.focus();
    setEmpty();
    // updatePreview(address);
    return;
  }

  setLoading();

  try {
    const response = await fetch("/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ seed_parameter: address }),
    });

    const payload = await readResponsePayload(response);

    if (!response.ok) {
      showFormAlert(getResponseErrorMessage(response, payload));
      setEmpty();
      // updatePreview(address);
      return;
    }

    if (!payload || typeof payload !== "object") {
      showFormAlert("The server returned an unreadable response. Please try again.");
      setEmpty();
      // updatePreview(address);
      return;
    }

    setResult(payload);
  } catch (error) {
    showFormAlert("Could not reach the server. Please try again.");
    setEmpty();
    // updatePreview(address);
    console.error("Error submitting form:", error);
  } finally {
    clearLoading();
  }
}

// Wire up events
// input.addEventListener("input", () => updatePreview());
findingsListEl?.addEventListener("click", handleFindingsClick);

detailCopyButtons.forEach((button) => {
  button.addEventListener("click", () => handleDetailCopyClick(button));
});

form.addEventListener("submit", handleSubmit);

// Initial state
setEmpty();
