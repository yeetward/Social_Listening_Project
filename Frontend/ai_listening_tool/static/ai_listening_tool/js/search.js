"use strict";

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("searchForm");
  if (!form) return;

  // Pick the visible text input only
  const input = form.querySelector('input[name="subject"]:not([type="hidden"])');

  // Persist defaults; do NOT call preventDefault
  form.addEventListener("submit", () => {
    const subject = (input?.value || "").trim();
    sessionStorage.setItem("rm_subject", subject);
    sessionStorage.setItem("rm_days", "7");
    sessionStorage.setItem("rm_priority", "all");
  });

  // Optional: pills auto-fill and submit
  document.querySelectorAll(".rm-pill[data-topic]").forEach(b => {
    b.addEventListener("click", () => {
      if (!input) return;
      input.value = b.dataset.topic || "";
      form.requestSubmit?.() || form.submit();
    });
  });
});