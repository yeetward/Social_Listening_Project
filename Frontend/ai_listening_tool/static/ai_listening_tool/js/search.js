"use strict";
import "./config.js";

// Configuration
const API_BASE_URL = RM_TOOL_CONFIG.API_BASE;
const DEFAULT_COMPANY = "EcoDrive Motors";
const API_TIMEOUT = 60000; // 60 seconds timeout - AI operations can take time

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
async function fetchTrendingTopics(companyId = "69072b397c33c037fd2da784") {
  const trendingList = document.getElementById("trendingTopicsList");
  if (!trendingList) return;

  try {
    // Show loading state
    trendingList.innerHTML = '<li class="rm-loading">Loading trending topics...</li>';

    const params = new URLSearchParams({
      company_id: companyId,
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
 * Fetch news feed from the API
 */
async function fetchNewsFeed(companyId = "69072b397c33c037fd2da784") {
  const newsFeedList = document.getElementById("newsFeedList");
  if (!newsFeedList) return;

  try {
    // Show loading state
    newsFeedList.innerHTML = '<li class="rm-loading">Loading news feed...</li>';

    const params = new URLSearchParams({
      company_id: companyId,
      limit: "2",
      max_age_days: "7"
    });

    const response = await fetchWithTimeout(`${API_BASE_URL}/cards/newsfeed/?${params}`);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    const items = data.items || [];

    // Clear loading and populate
    newsFeedList.innerHTML = "";

    if (items.length === 0) {
      newsFeedList.innerHTML = '<li class="rm-empty">No news feed items available at this time.</li>';
      return;
    }

    items.forEach(item => {
      const li = document.createElement("li");

      const title = item.title || "Untitled";
      const description = item.description || "";
      const url = item.url || "";

      // Make the title clickable if URL exists
      if (url) {
        const titleLink = document.createElement("a");
        titleLink.href = url;
        titleLink.target = "_blank";
        titleLink.rel = "noopener noreferrer";
        titleLink.style.textDecoration = "none";
        
        const strong = document.createElement("strong");
        strong.textContent = title;
        strong.style.cursor = "pointer";
        strong.style.transition = "color 0.2s ease";
        
        // Add hover effect - red highlight like top topics pills
        titleLink.addEventListener("mouseenter", () => {
          strong.style.color = "#e63946";
        });
        titleLink.addEventListener("mouseleave", () => {
          strong.style.color = "";
        });
        
        titleLink.appendChild(strong);
        li.appendChild(titleLink);
      } else {
        const strong = document.createElement("strong");
        strong.textContent = title;
        li.appendChild(strong);
      }

      if (description) {
        li.appendChild(document.createTextNode(" " + description));
      }

      newsFeedList.appendChild(li);
    });

  } catch (error) {
    console.error("Error fetching news feed:", error);
    // Show fallback content
    newsFeedList.innerHTML = `
      <li><strong>Apple Watch gets FDA clearance for hypertension detection</strong> A new FDA-approved feature that assesses how blood vessels respond to heart beats, helping detect early signs of cardiovascular risk.</li>
      <li><strong>Climate & Health Initiatives — Regional heat policy</strong> Hospitals and healthcare systems are launching heat management initiatives aimed at protecting patients from extreme weather.</li>
    `;
    // Add a subtle note
    const note = document.createElement("li");
    note.style.fontSize = "12px";
    note.style.color = "#999";
    note.style.fontStyle = "italic";
    note.textContent = "(Using cached data - API unavailable)";
    newsFeedList.appendChild(note);
  }
}

/**
 * Handle search form submission
 */
async function handleSearch(subject) {
  if (!subject || !subject.trim()) {
    const errEl = document.getElementById("err");
    if (errEl) errEl.textContent = "Please enter a search term";
    return;
  }

  // Get button reference outside try block for proper scope
  const submitBtn = document.querySelector("#searchForm button[type='submit']");
  const originalText = submitBtn?.textContent || "Search";

  try {
    // Show loading state
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = "Searching...";
    }

    // POST to /api/search/ to initiate search
    // Use extra long timeout since this fetches from multiple sources
    const response = await fetchWithTimeout(`${API_BASE_URL}/search/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        subject: subject.trim(),
        limit: 100,
        fetch_limit: 120,
        persist_pool_limit: 500,
        days: 7,
      }),
    }, 120000); // 2 minutes for search initiation

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    const historyId = data.history_id;

    if (!historyId) {
      throw new Error("No history_id returned from API");
    }

    // Log the counts to diagnose data fetching issues
    console.log("Search initiated:", {
      history_id: historyId,
      counts: data.counts,
      message: data.message
    });

    // Warn if no data was fetched
    if (data.counts && data.counts.fetched_total === 0) {
      console.warn("⚠️ Warning: No data was fetched from sources. Check your API keys or source configuration.");
    }

    // Store history_id and subject for the results page
    sessionStorage.setItem("rm_history_id", historyId);
    sessionStorage.setItem("rm_subject", subject.trim());
    sessionStorage.setItem("rm_days", "7");
    sessionStorage.setItem("rm_priority", "all");

    // Redirect to results page with loading flag (note: app is under /tool/ prefix)
    // The 'loading=1' parameter tells results page to use existing history_id instead of creating new one
    window.location.href = `/tool/results/?subject=${encodeURIComponent(subject.trim())}&loading=1`;

  } catch (error) {
    console.error("Search error:", error);
    const errEl = document.getElementById("err");
    if (errEl) errEl.textContent = `Error: ${error.message}`;

    // Reset button
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = originalText;
    }
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

  // Intercept form submission to use our API workflow
  form.addEventListener("submit", (e) => {
    e.preventDefault(); // Prevent default form submission
    const subject = (input?.value || "").trim();
    handleSearch(subject);
  });

  // Optional: pills auto-fill and submit
  document.querySelectorAll(".rm-pill[data-topic]").forEach(b => {
    b.addEventListener("click", () => {
      if (!input) return;
      input.value = b.dataset.topic || "";
      handleSearch(b.dataset.topic || "");
    });
  });

  // Load data from API endpoints on page load (non-blocking)
  // Wrap in setTimeout to ensure it doesn't block page rendering
  setTimeout(() => {
    fetchTrendingTopics().catch(err => console.error("Failed to load trending topics:", err));
    fetchIdeas().catch(err => console.error("Failed to load ideas:", err));
    fetchNewsFeed().catch(err => console.error("Failed to load news feed:", err));
  }, 0);
});

