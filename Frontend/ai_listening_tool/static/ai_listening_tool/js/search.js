"use strict";
import "./config.js";

// Configuration
const API_BASE_URL = RM_TOOL_CONFIG.API_BASE;
const DEFAULT_COMPANY = "EcoDrive Motors";
const API_TIMEOUT = 5000; // 5 second timeout

/**
 * Fetch with timeout
 */
function fetchWithTimeout(url, options = {}, timeout = API_TIMEOUT) {
  return Promise.race([
    fetch(url, options),
    new Promise((_, reject) =>
      setTimeout(() => reject(new Error('Request timeout')), timeout)
    )
  ]);
}

/**
 * Fetch trending topics from the API
 */
async function fetchTrendingTopics(company = DEFAULT_COMPANY) {
  const trendingList = document.getElementById("trendingTopicsList");
  if (!trendingList) return;

  try {
    // Show loading state
    trendingList.innerHTML = '<li class="rm-loading">Loading trending topics...</li>';

    const params = new URLSearchParams({
      company: company,
      threshold: "0.5",
      limit: "10",
      full: "0"
    });

    const response = await fetchWithTimeout(`${API_BASE_URL}/cards/trending/?${params}`);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const topics = await response.json();

    // Clear loading and populate
    trendingList.innerHTML = "";

    if (!topics || topics.length === 0) {
      trendingList.innerHTML = '<li class="rm-empty">No trending topics found at this time.</li>';
      return;
    }

    topics.forEach(topic => {
      const li = document.createElement("li");
      li.textContent = topic;
      trendingList.appendChild(li);
    });

  } catch (error) {
    console.error("Error fetching trending topics:", error);
    // Show a more user-friendly fallback
    trendingList.innerHTML = `
      <li>Multi-Cancer Early Detection / Liquid Biopsies</li>
      <li>Tele-health and Remote Patient Monitoring</li>
      <li>Home Health & Hospital at Home Models</li>
      <li>Interoperability & Health Data Flow</li>
      <li>Behavioral Health Integration into Primary Care</li>
    `;
    // Add a subtle note
    const note = document.createElement("li");
    note.style.fontSize = "12px";
    note.style.color = "#999";
    note.style.fontStyle = "italic";
    note.textContent = "(Using cached data - API unavailable)";
    trendingList.appendChild(note);
  }
}

/**
 * Fetch AI-generated ideas from the API
 */
async function fetchIdeas(company = DEFAULT_COMPANY) {
  const ideasList = document.getElementById("ideasList");
  if (!ideasList) return;

  try {
    // Show loading state
    ideasList.innerHTML = '<li class="rm-loading">Loading ideas...</li>';

    const params = new URLSearchParams({
      company: company,
      type: "all",
      limit: "10"
    });

    const response = await fetchWithTimeout(`${API_BASE_URL}/ai/ideas/?${params}`);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    const insights = data.insights || [];

    // Clear loading and populate
    ideasList.innerHTML = "";

    if (insights.length === 0) {
      ideasList.innerHTML = '<li class="rm-empty">No ideas available at this time.</li>';
      return;
    }

    insights.forEach(insight => {
      const li = document.createElement("li");

      const title = insight.title || insight.idea || "Untitled";
      const description = insight.description || insight.summary || insight.explanation || "";

      const strong = document.createElement("strong");
      strong.textContent = title;
      li.appendChild(strong);

      if (description) {
        li.appendChild(document.createTextNode(" — " + description));
      }

      ideasList.appendChild(li);
    });

  } catch (error) {
    console.error("Error fetching ideas:", error);
    // Show fallback content
    ideasList.innerHTML = `
      <li><strong>Community Health Data Hubs</strong> — open dashboards tracking local health metrics, setting benchmark data, allowing policy and practice decisions....</li>
      <li><strong>Climate & Health Initiatives</strong> — hospital heat index programs and air quality monitoring with alerts focused on vulnerable patient populations....</li>
      <li><strong>Health Literacy Campaigns</strong> — workshops and digital resources helping patients understand treatment options, insurance terms, and preventive care measures....</li>
    `;
    // Add a subtle note
    const note = document.createElement("li");
    note.style.fontSize = "12px";
    note.style.color = "#999";
    note.style.fontStyle = "italic";
    note.textContent = "(Using cached data - API unavailable)";
    ideasList.appendChild(note);
  }
}

/**
 * Initialize the page
 */
document.addEventListener("DOMContentLoaded", () => {
  console.log("Page loaded successfully!");

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

  // Load data from API endpoints on page load (non-blocking)
  // Wrap in setTimeout to ensure it doesn't block page rendering
  setTimeout(() => {
    fetchTrendingTopics().catch(err => console.error("Failed to load trending topics:", err));
    fetchIdeas().catch(err => console.error("Failed to load ideas:", err));
  }, 0);
});

