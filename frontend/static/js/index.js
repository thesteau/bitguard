// For indexhtml

const input = document.getElementById("addressInput");
const preview = document.getElementById("addressPreview");
const btn = document.getElementById("searchBtn");

function updatePreview() {
  const value = input.value.trim();
  preview.textContent = value || "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa";
}

input.addEventListener("input", updatePreview);
btn.addEventListener("click", updatePreview);


console.log("Hello from the index page")