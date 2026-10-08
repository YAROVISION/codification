/**
 * Реєстр Дайджестів та Оглядів Судової Практики — Логіка інтерфейсу
 */

let allDigests = [];
let currentFilterCat = "all";
let currentSearchQuery = "";
let currentSortKey = "num";
let currentSortDir = "asc"; // 'asc' | 'desc'

// DOM Elements
const digestsTbody = document.getElementById("digests-tbody");
const categoryChips = document.querySelectorAll(".category-filter-chips .chip");
const filteredCountBadge = document.getElementById("filtered-count-badge");

const totalPdfsCount = document.getElementById("total-pdfs-count");
const totalMdCount = document.getElementById("total-md-count");
const totalSegCount = document.getElementById("total-seg-count");

const themeBtnLight = document.getElementById("theme-btn-light");
const themeBtnDark = document.getElementById("theme-btn-dark");

// Initialize
document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  setupEventListeners();
  loadDigests();
});

// Setup Events
function setupEventListeners() {
  // Category Filter Chips
  categoryChips.forEach((chip) => {
    chip.addEventListener("click", () => {
      categoryChips.forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      currentFilterCat = chip.getAttribute("data-cat");
      renderTable();
    });
  });

  // Table Sorting
  const sortableHeaders = document.querySelectorAll("th[data-sort]");
  sortableHeaders.forEach((th) => {
    th.addEventListener("click", () => {
      const key = th.getAttribute("data-sort");
      if (currentSortKey === key) {
        currentSortDir = currentSortDir === "asc" ? "desc" : "asc";
      } else {
        currentSortKey = key;
        currentSortDir = key === "num" ? "asc" : "asc";
      }
      updateSortIndicators();
      renderTable();
    });
  });
}

// Update table sort header indicators
function updateSortIndicators() {
  document.querySelectorAll("th[data-sort]").forEach((th) => {
    const key = th.getAttribute("data-sort");
    const indicator = th.querySelector(".sort-indicator");
    th.classList.remove("sort-asc", "sort-desc");
    if (indicator) {
      if (key === currentSortKey) {
        indicator.textContent = currentSortDir === "asc" ? "▲" : "▼";
        th.classList.add(currentSortDir === "asc" ? "sort-asc" : "sort-desc");
      } else {
        indicator.textContent = "↕";
      }
    }
  });
}

// Load digests from server API with static fallback
async function loadDigests() {
  try {
    let data = null;
    try {
      const res = await fetch("/api/digests");
      if (res.ok) {
        data = await res.json();
      }
    } catch (e) {
      // API not reachable directly
    }

    if (!data || !Array.isArray(data) || data.length === 0) {
      const fallbackRes = await fetch("digests_data.json?v=" + Date.now());
      if (!fallbackRes.ok) {
        throw new Error(`HTTP error! status: ${fallbackRes.status}`);
      }
      data = await fallbackRes.json();
    }

    allDigests = data;
    
    // Update summary counters
    updateSummaryStats(allDigests);

    // Initial render
    updateSortIndicators();
    renderTable();
  } catch (err) {
    console.error("Помилка завантаження дайджестів:", err);
    if (digestsTbody) {
      digestsTbody.innerHTML = `
        <tr class="table-error-row">
          <td colspan="5">
            <div class="table-error-msg">
              <span class="error-icon">⚠️</span>
              <span>Не вдалося завантажити реєстр дайджестів (${err.message}). Перевірте з'єднання з сервером.</span>
            </div>
          </td>
        </tr>
      `;
    }
  }
}

// Update header stat cards
function updateSummaryStats(digests) {
  const totalPdfs = digests.length;
  const totalMd = digests.filter((d) => d.has_markdown).length;
  const totalSegs = digests.reduce((acc, d) => acc + (d.segments_count || 0), 0);

  if (totalPdfsCount) totalPdfsCount.textContent = totalPdfs.toLocaleString("uk-UA");
  if (totalMdCount) totalMdCount.textContent = `${totalMd} / ${totalPdfs}`;
  if (totalSegCount) totalSegCount.textContent = totalSegs.toLocaleString("uk-UA");
}

// Render table according to active filter, search and sort
function renderTable() {
  if (!digestsTbody) return;

  let filtered = allDigests.filter((item) => {
    // Category match
    if (currentFilterCat !== "all") {
      if (!item.category.toLowerCase().includes(currentFilterCat.toLowerCase())) {
        return false;
      }
    }

    // Search query match
    if (currentSearchQuery) {
      const q = currentSearchQuery;
      const matchFile = item.filename.toLowerCase().includes(q);
      const matchCat = item.category.toLowerCase().includes(q);
      const matchMd = (item.has_markdown ? "так" : "ні").includes(q);
      const matchSeg = (item.has_segments ? "так" : "ні").includes(q);
      if (!matchFile && !matchCat && !matchMd && !matchSeg) {
        return false;
      }
    }

    return true;
  });

  // Sorting
  filtered.sort((a, b) => {
    let valA = a[currentSortKey];
    let valB = b[currentSortKey];

    if (currentSortKey === "num") {
      valA = Number(valA);
      valB = Number(valB);
    } else if (typeof valA === "boolean") {
      valA = valA ? 1 : 0;
      valB = valB ? 1 : 0;
    } else if (typeof valA === "string") {
      valA = valA.toLowerCase();
      valB = valB.toLowerCase();
    }

    if (valA < valB) return currentSortDir === "asc" ? -1 : 1;
    if (valA > valB) return currentSortDir === "asc" ? 1 : -1;
    return a.num - b.num;
  });

  // Update badge count
  if (filteredCountBadge) {
    filteredCountBadge.textContent = `Знайдено: ${filtered.length} із ${allDigests.length}`;
  }

  if (filtered.length === 0) {
    digestsTbody.innerHTML = `
      <tr class="table-empty-row">
        <td colspan="5">
          <div class="empty-state-card">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
            <p>За вказаними критеріями дайджестів не знайдено</p>
          </div>
        </td>
      </tr>
    `;
    return;
  }

  // Generate HTML Rows
  const rowsHtml = filtered.map((item, index) => {
    const docName = item.name_no_ext || item.filename.replace(/\.pdf$/i, "");
    const mdUrl = item.markdown_url || `/documents/markdown/${encodeURIComponent(docName)}/${encodeURIComponent(docName)}.md`;
    const correlationUrl = item.correlation_url || `/correlation/${encodeURIComponent(docName)}.html`;

    const viewerUrl = `/viewer.html?file=${encodeURIComponent(mdUrl)}&doc=${encodeURIComponent(docName)}`;

    const mdBadge = item.has_markdown
      ? `<a href="${viewerUrl}" target="_blank" rel="noopener noreferrer" class="badge badge-success badge-interactive" title="Відкрити розмічений Markdown рідер (${docName})">
           <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
           <span>Так</span>
           <svg class="icon-open-external" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
         </a>`
      : `<span class="badge badge-neutral">Ні</span>`;

    const segBadge = item.has_segments
      ? `<a href="${correlationUrl}" target="_blank" rel="noopener noreferrer" class="badge badge-success badge-interactive" title="Відкрити сторінку взаємозв'язку сегментів із класифікатором (${docName})">
           <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
           <span>Так</span>
           <span class="badge-count">${item.segments_count}</span>
           <svg class="icon-open-external" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
         </a>`
      : `<span class="badge badge-neutral">Ні</span>`;

    const catBadgeClass = getCategoryBadgeClass(item.category);

    return `
      <tr class="digest-row" data-num="${item.num}">
        <td class="td-num">${item.num}</td>
        <td class="td-file">
          <a href="${item.url}" target="_blank" rel="noopener noreferrer" class="pdf-link" title="Відкрити PDF: ${item.filename}">
            <svg class="pdf-file-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
              <polyline points="10 9 9 9 8 9"/>
            </svg>
            <span class="file-name-text">${escapeHtml(item.filename)}</span>
          </a>
        </td>
        <td class="td-status">${mdBadge}</td>
        <td class="td-status">${segBadge}</td>
        <td class="td-cat">
          <span class="badge badge-category ${catBadgeClass}">${escapeHtml(item.category)}</span>
        </td>
      </tr>
    `;
  }).join("");

  digestsTbody.innerHTML = rowsHtml;
}

// Category color styling
function getCategoryBadgeClass(category) {
  const cat = category.toLowerCase();
  if (cat.includes("ккс")) return "cat-kks";
  if (cat.includes("кгс")) return "cat-kgs";
  if (cat.includes("кас")) return "cat-kas";
  if (cat.includes("кцс")) return "cat-kcs";
  if (cat.includes("велика палата")) return "cat-vp";
  if (cat.includes("єспл")) return "cat-espl";
  if (cat.includes("союз") || cat.includes("суд єс")) return "cat-ses";
  return "cat-general";
}

function escapeHtml(text) {
  if (!text) return "";
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Theme Management
function initTheme() {
  const savedTheme = localStorage.getItem("app_theme") || "dark";
  applyTheme(savedTheme, false);

  if (themeBtnLight) {
    themeBtnLight.addEventListener("click", () => applyTheme("light"));
  }
  if (themeBtnDark) {
    themeBtnDark.addEventListener("click", () => applyTheme("dark"));
  }
}

function applyTheme(theme, animate = true) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("app_theme", theme);

  if (theme === "light") {
    themeBtnLight?.classList.add("active");
    themeBtnDark?.classList.remove("active");
  } else {
    themeBtnDark?.classList.add("active");
    themeBtnLight?.classList.remove("active");
  }
}
