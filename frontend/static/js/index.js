// For indexhtml

const input = document.getElementById("addressInput");
const preview = document.getElementById("addressPreview");
const btn = document.getElementById("searchBtn");

function updatePreview() {
  const value = input.value.trim();
  preview.textContent = value ? value : "No address entered yet...";
}

input.addEventListener("input", updatePreview);
btn.addEventListener("click", updatePreview);


console.log("Hello from the index page")