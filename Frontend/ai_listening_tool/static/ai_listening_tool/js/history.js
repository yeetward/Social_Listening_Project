// path: social-listening-tool/ai_listening_tool/static/ai_listening_tool/js/history.js
"use strict";

// Render one table row
function row(i) {
  const when = i.ts ? new Date(i.ts).toLocaleString() : "";
  return `<tr><td>${i.subject || "Unknown"}</td><td>${i.count ?? 0}</td><td class="ta-right">${when}</td></tr>`;
}

document.addEventListener("DOMContentLoaded", async () => {
  const tbody = document.getElementById("rm-history-body");
  if (!tbody) return;
  tbody.innerHTML = `<tr><td colspan="3">Loading…</td></tr>`;
  try {
    // Uses global helper from api.js
    const data = await window.apiGet("/history/");
    const items = Array.isArray(data?.items) ? data.items : [];
    tbody.innerHTML = items.length ? items.map(row).join("") : `<tr><td colspan="3">No history</td></tr>`;
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="3">Error: ${e.message}</td></tr>`;
  }
});
