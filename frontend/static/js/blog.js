function renderBlogPosts() {
  const el = document.getElementById("page-data");
  const pageData = el ? JSON.parse(el.textContent) : {};

  const rows = Array.isArray(pageData.blog_data) ? pageData.blog_data : [];

  const container = document.getElementById("posts");
  if (!container) return;

  function escapeHtml(s) {
    return String(s ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function toViewLink(url) {
    const m = String(url || "").match(/\/document\/d\/([^/]+)/);
    return m ? `https://docs.google.com/document/d/${m[1]}/view` : url;
  }

  if (rows.length === 0) {
    container.innerHTML = "<p>No posts yet.</p>";
    return;
  }

  container.innerHTML = rows.map(p => `
    <article style="border:1px solid #ddd; padding:12px; border-radius:10px; margin:10px 0;">
      <h2 style="margin:0 0 6px 0;">${escapeHtml(p.title)}</h2>
      <div style="color:#666; margin-bottom:8px;">
        by <strong>${escapeHtml(p.author)}</strong> · ${escapeHtml(p.date)}
      </div>
      <a href="${escapeHtml(toViewLink(p.link))}" target="_blank" rel="noopener noreferrer">
        Read →
      </a>
    </article>
  `).join("");
};


// Execute on load
renderBlogPosts();