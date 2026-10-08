/**
 * Markdown Viewer Logic — Інтерактивний рідер оглядів судової практики
 */

let rawMarkdownText = "";
let parsedSegments = [];
let activeSegmentId = "";

// DOM Elements
const docTitleEl = document.getElementById("doc-title");
const metaSegCountEl = document.getElementById("meta-seg-count");
const metaCatEl = document.getElementById("meta-cat");
const metaFilenameEl = document.getElementById("meta-filename");
const sidebarNavEl = document.getElementById("sidebar-nav");
const sidebarTotalCountEl = document.getElementById("sidebar-total-count");
const renderViewEl = document.getElementById("render-view");
const rawViewEl = document.getElementById("raw-view");
const rawCodeTextEl = document.getElementById("raw-code-text");
const searchInputEl = document.getElementById("viewer-search");
const btnModeRender = document.getElementById("btn-mode-render");
const btnModeRaw = document.getElementById("btn-mode-raw");
const btnCopyAll = document.getElementById("btn-copy-all");
const btnPdfLink = document.getElementById("btn-pdf-link");
const toastEl = document.getElementById("viewer-toast");
const toastTextEl = document.getElementById("toast-text");
const contentMainEl = document.querySelector(".viewer-content-main");

// Initialize
document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  setupEventListeners();
  loadDocument();
});

// Theme Management
function initTheme() {
  const saved = localStorage.getItem("app_theme") || "dark";
  document.documentElement.setAttribute("data-theme", saved);
  updateThemeButtons(saved);
}

function updateThemeButtons(theme) {
  const lightBtn = document.getElementById("theme-btn-light");
  const darkBtn = document.getElementById("theme-btn-dark");
  if (lightBtn) lightBtn.classList.toggle("active", theme === "light");
  if (darkBtn) darkBtn.classList.toggle("active", theme === "dark");
}

function setupEventListeners() {
  // Theme toggle
  document.getElementById("theme-btn-light")?.addEventListener("click", () => {
    localStorage.setItem("app_theme", "light");
    document.documentElement.setAttribute("data-theme", "light");
    updateThemeButtons("light");
  });

  document.getElementById("theme-btn-dark")?.addEventListener("click", () => {
    localStorage.setItem("app_theme", "dark");
    document.documentElement.setAttribute("data-theme", "dark");
    updateThemeButtons("dark");
  });

  // View Mode Toggles
  btnModeRender?.addEventListener("click", () => setViewMode("render"));
  btnModeRaw?.addEventListener("click", () => setViewMode("raw"));

  // Copy All Markdown
  btnCopyAll?.addEventListener("click", () => {
    if (!rawMarkdownText) return;
    navigator.clipboard.writeText(rawMarkdownText).then(() => {
      showToast("Весь Markdown скопійовано в буфер!");
    });
  });

  // Search Filter
  searchInputEl?.addEventListener("input", (e) => {
    const query = e.target.value.toLowerCase().trim();
    filterSegments(query);
  });

  // Content scroll for scrollspy
  const contentMain = document.querySelector(".viewer-content-main");
  if (contentMain) {
    contentMain.addEventListener("scroll", handleScrollSpy, { passive: true });
  }
}

function setViewMode(mode) {
  if (mode === "render") {
    btnModeRender.classList.add("active");
    btnModeRaw.classList.remove("active");
    renderViewEl.style.display = "flex";
    rawViewEl.style.display = "none";
  } else {
    btnModeRaw.classList.add("active");
    btnModeRender.classList.remove("active");
    renderViewEl.style.display = "none";
    rawViewEl.style.display = "block";
  }
}

// Load Document from Query Params
async function loadDocument() {
  const params = new URLSearchParams(window.location.search);
  let filePath = params.get("file") || "";
  const docName = params.get("doc") || "";

  if (!filePath && docName) {
    filePath = `/documents/markdown/${encodeURIComponent(docName)}/${encodeURIComponent(docName)}.md`;
  }

  if (!filePath) {
    filePath = "/documents/markdown/Oglyad_KKS_02_2026/Oglyad_KKS_02_2026.md";
  }

  const cleanDocName = docName || filePath.split("/").slice(-2)[0] || "Огляд";
  docTitleEl.textContent = cleanDocName.replace(/_/g, " ");
  metaFilenameEl.textContent = filePath.split("/").pop() || "";
  
  // Set PDF link if available
  const pdfUrl = `/documents/pdfs/${encodeURIComponent(cleanDocName)}.pdf`;
  if (btnPdfLink) {
    btnPdfLink.href = pdfUrl;
  }

  try {
    const res = await fetch(filePath);
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    }
    rawMarkdownText = await res.text();
    rawCodeTextEl.textContent = rawMarkdownText;

    parseAndRenderMarkdown(rawMarkdownText, cleanDocName);
  } catch (err) {
    console.error("Помилка завантаження Markdown:", err);
    docTitleEl.textContent = "Помилка завантаження";
    renderViewEl.innerHTML = `
      <div class="preamble-card" style="border-color: rgba(239, 68, 68, 0.4);">
        <h2 style="color: #ef4444; margin-top: 0;">⚠️ Не вдалося завантажити файл</h2>
        <p style="color: var(--text-dim);">${escapeHtml(err.message)}</p>
        <p style="color: var(--text-dim); font-size: 13px;">Шлях до файлу: <code>${escapeHtml(filePath)}</code></p>
      </div>
    `;
  }
}

// Parse Markdown structure into segments
function parseAndRenderMarkdown(text, docName) {
  const parts = text.split(/(<!-- === SEGMENT: [^>]+ === -->)/g);
  parsedSegments = [];

  let initialPreamble = "";
  let segmentIndex = 1;

  for (let i = 0; i < parts.length; i++) {
    const p = parts[i];
    if (p.startsWith("<!-- === SEGMENT:")) {
      const tagContent = p.replace("<!-- === SEGMENT:", "").replace("=== -->", "").trim();
      const body = parts[i + 1] ? parts[i + 1].trim() : "";
      i++; // Skip body in next iteration

      const isPreamble = tagContent.includes("PREAMBLE");
      const isTech = isPreamble || tagContent.includes("Технічний") || tagContent.includes("ТЕХНІЧНИЙ") || tagContent.includes("РОЗДІЛ") || tagContent.includes("ЧАСТИНИ");

      let id = tagContent.split("|")[0].trim();
      let title = tagContent.includes("|") ? tagContent.split("|")[1].trim() : tagContent;

      title = title.replace(/Технічний сегмент\.?\s*/i, "")
                   .replace(/НЕ ПІДЛЯГАЄ РОЗПОДІЛУ\.?\s*/i, "")
                   .replace(/\|\s*$/, "")
                   .trim();

      parsedSegments.push({
        rawTag: p,
        tagContent,
        id,
        title: title || id,
        body,
        isPreamble,
        isTech,
        index: segmentIndex++
      });
    } else if (i === 0 && p.trim()) {
      initialPreamble = p.trim();
    }
  }

  // Update Counters
  const legalSegments = parsedSegments.filter(s => !s.isTech && s.body);
  metaSegCountEl.textContent = `${legalSegments.length} правових позицій`;
  sidebarTotalCountEl.textContent = legalSegments.length;

  // Render Sidebar
  renderSidebarNav(parsedSegments);

  // Render Main Stream
  renderMainStream(initialPreamble, parsedSegments);
}

// Render Table of Contents in Sidebar
function renderSidebarNav(segments) {
  let navHtml = "";

  segments.forEach((seg, idx) => {
    if (seg.isPreamble) {
      navHtml += `
        <a href="#seg-block-${idx}" class="nav-item nav-section-header" data-seg-target="seg-block-${idx}">
          <span class="nav-item-title">📋 Вступ та загальні відомості</span>
        </a>
      `;
      return;
    }

    if (seg.isTech) {
      navHtml += `
        <a href="#seg-block-${idx}" class="nav-item nav-section-header" data-seg-target="seg-block-${idx}">
          <span class="nav-item-title">${escapeHtml(seg.title)}</span>
        </a>
      `;
    } else if (seg.body) {
      const shortTitle = seg.title.replace(/^\d+(\.\d+)*\.\s*/, "");
      navHtml += `
        <a href="#seg-block-${idx}" class="nav-item" data-seg-target="seg-block-${idx}">
          <span class="nav-badge-id">${escapeHtml(seg.id)}</span>
          <span class="nav-item-title">${escapeHtml(shortTitle)}</span>
        </a>
      `;
    }
  });

  sidebarNavEl.innerHTML = navHtml;
}

// Render Main Content Stream
function renderMainStream(initialPreamble, segments) {
  let html = "";

  if (initialPreamble) {
    html += renderPreambleCard({ body: initialPreamble, index: 0 });
  }

  segments.forEach((seg, idx) => {
    if (seg.isPreamble) {
      html += renderPreambleCard(seg, idx);
    } else if (seg.isTech) {
      html += `
        <div id="seg-block-${idx}" class="section-divider-banner" data-seg-id="${escapeHtml(seg.id)}">
          <h3 class="section-divider-title">${escapeHtml(seg.title)}</h3>
          <span class="section-divider-badge">${escapeHtml(seg.id)}</span>
        </div>
      `;
    } else if (seg.body) {
      html += renderSegmentCard(seg, idx);
    }
  });

  renderViewEl.innerHTML = html;
  setupCardInteractivity();
}

// Render Preamble Card using Markdown
function renderPreambleCard(seg, idx = 0) {
  let renderedContent = "";
  if (window.marked && typeof window.marked.parse === "function") {
    renderedContent = window.marked.parse(seg.body);
  } else {
    renderedContent = seg.body.split("\n\n").map(p => `<p>${escapeHtml(p)}</p>`).join("");
  }

  return `
    <div class="preamble-card" id="seg-block-${idx}">
      <div class="preamble-details">${renderedContent}</div>
    </div>
  `;
}

// Render Segment Card with Structured Legal Typography
function renderSegmentCard(seg, idx) {
  let bodyText = seg.body;
  
  // 1. Extract reyestr URL link: <https://reyestr.court.gov.ua/Review/12345> or [url](url)
  let reyestrUrl = "";
  const urlMatch = bodyText.match(/https:\/\/reyestr\.court\.gov\.ua\/Review\/(\d+)/);
  if (urlMatch) {
    reyestrUrl = `https://reyestr.court.gov.ua/Review/${urlMatch[1]}`;
  }

  // 2. Extract Court Decision info
  let decisionBlock = "";
  const decisionMatch = bodyText.match(/(Постанова|Ухвала)\s+([^\.]+?)(?=\s*<http|\s*\[|\s*$)/i);
  if (decisionMatch) {
    decisionBlock = decisionMatch[0].trim();
  }

  // 3. Extract case number & proceeding number
  let caseNum = "";
  const caseMatch = bodyText.match(/справ[іа]\s+№?\s*([0-9a-zа-яіїєґ\/\-]+)/i);
  if (caseMatch) {
    caseNum = `Справа № ${caseMatch[1]}`;
  }

  let procNum = "";
  const procMatch = bodyText.match(/провадження\s+№?\s*([0-9a-zа-яіїєґ\/\-]+)/i);
  if (procMatch) {
    procNum = `(пр. № ${procMatch[1]})`;
  }

  // 4. Extract instance
  let courtInstance = "Касаційний кримінальний суд ВС";
  if (bodyText.includes("ОП ККС ВС") || bodyText.includes("об’єднаної палати") || bodyText.includes("Об’єднана палата")) {
    courtInstance = "ОП ККС ВС";
  } else if (bodyText.includes("Великої Палати") || bodyText.includes("Велика Палата")) {
    courtInstance = "Велика Палата ВС";
  } else if (bodyText.includes("Першої судової палати")) {
    courtInstance = "Перша палата ККС ВС";
  } else if (bodyText.includes("Другої судової палати")) {
    courtInstance = "Друга палата ККС ВС";
  } else if (bodyText.includes("Третьої судової палати")) {
    courtInstance = "Третя палата ККС ВС";
  }

  // 5. Structure Body into sections: Thesis, Circumstances, Prior Courts, KKS Position, Rationale
  let contentText = bodyText;
  if (decisionMatch) {
    contentText = contentText.substring(0, decisionMatch.index).trim();
  }

  const sectionKeywords = [
    { key: "Обставини справи:", label: "Обставини справи", class: "label-circumstances" },
    { key: "Позиції судів першої та апеляційної інстанцій:", label: "Позиції судів 1-ї та апеляційної інстанцій", class: "label-positions" },
    { key: "Позиція ККС:", label: "Позиція ККС", class: "label-kks-position" },
    { key: "Позиція ОП ККС:", label: "Позиція ОП ККС", class: "label-kks-position" },
    { key: "Позиція ВП ВС:", label: "Позиція ВП ВС", class: "label-kks-position" },
    { key: "Обґрунтування позиції ККС:", label: "Обґрунтування позиції ККС", class: "label-rationale" },
    { key: "Обґрунтування позиції ОП ККС:", label: "Обґрунтування позиції ОП ККС", class: "label-rationale" },
    { key: "Обґрунтування позиції ВП ВС:", label: "Обґрунтування позиції ВП ВС", class: "label-rationale" }
  ];

  let bodyHtml = formatLegalText(contentText, sectionKeywords);

  return `
    <article class="segment-card" id="seg-block-${idx}" data-seg-id="${escapeHtml(seg.id)}">
      <div class="segment-card-header">
        <div class="segment-id-tag">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
          <span>СЕГМЕНТ ${escapeHtml(seg.id)}</span>
        </div>
        <div class="segment-title-text">${escapeHtml(seg.title.replace(/^\d+(\.\d+)*\.\s*/, ""))}</div>
        <button type="button" class="btn-copy-anchor" data-copy-seg="${idx}" title="Скопіювати посилання на цей сегмент">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
        </button>
      </div>

      <div class="segment-body">
        ${bodyHtml}
      </div>

      <div class="decision-action-footer">
        <div class="decision-meta-cluster">
          <span class="badge-court-instance">${escapeHtml(courtInstance)}</span>
          ${caseNum ? `<span class="badge-case-number">${escapeHtml(caseNum)}</span>` : ""}
          ${procNum ? `<span class="badge-case-number">${escapeHtml(procNum)}</span>` : ""}
        </div>

        ${reyestrUrl ? `
          <a href="${reyestrUrl}" target="_blank" rel="noopener noreferrer" class="btn-reyestr-link" title="Відкрити судове рішення в ЄДРСР">
            <span>В ЄДРСР</span>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
          </a>
        ` : ""}
      </div>
    </article>
  `;
}

// Format Legal Text into distinct structured blocks
function formatLegalText(text, keywords) {
  let escaped = escapeHtml(text);

  // Highlight Law Article references cleanly
  escaped = escaped.replace(/(?:ч\.\s*\d+\s+)?(?:ст(?:аття|атті|аттей|\.)?\s*\d+[\-\d]*(?:\s*ч\.\s*\d+)?\s*(?:КК|КПК|ЦК|КУпАП|КАСУ|ГК|КВК)(?:\s*України)?)/gi, (match) => {
    return `<span class="law-article-badge">${match}</span>`;
  });

  let firstKeywordIndex = -1;
  let firstKeyword = null;

  for (const kw of keywords) {
    const idx = escaped.indexOf(kw.key);
    if (idx !== -1 && (firstKeywordIndex === -1 || idx < firstKeywordIndex)) {
      firstKeywordIndex = idx;
      firstKeyword = kw;
    }
  }

  let thesisHtml = "";
  let sectionsHtml = "";

  if (firstKeywordIndex > 0) {
    const thesisText = escaped.substring(0, firstKeywordIndex).trim();
    thesisHtml = `<div class="legal-thesis-box">${thesisText}</div>`;
    let remaining = escaped.substring(firstKeywordIndex);

    keywords.forEach(kw => {
      const regex = new RegExp(kw.key.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g');
      remaining = remaining.replace(regex, `<div class="court-section-block"><span class="court-section-label ${kw.class}">${kw.label}</span> `);
    });

    sectionsHtml = remaining.replace(/(<div class="court-section-block">)/g, '</div>$1');
    if (sectionsHtml.startsWith('</div>')) {
      sectionsHtml = sectionsHtml.substring(6) + '</div>';
    } else {
      sectionsHtml = '<div>' + sectionsHtml + '</div>';
    }
  } else {
    thesisHtml = `<div class="legal-thesis-box">${escaped}</div>`;
  }

  return thesisHtml + sectionsHtml;
}

// Setup Card Click & Copy Handlers & Intercept sidebar clicks for smooth scrolling
function setupCardInteractivity() {
  document.querySelectorAll(".btn-copy-anchor").forEach(btn => {
    btn.addEventListener("click", (e) => {
      const idx = btn.getAttribute("data-copy-seg");
      const url = `${window.location.origin}${window.location.pathname}${window.location.search}#seg-block-${idx}`;
      navigator.clipboard.writeText(url).then(() => {
        showToast(`Посилання на сегмент скопійовано!`);
      });
    });
  });

  // Intercept Sidebar links so they scroll inside .viewer-content-main
  document.querySelectorAll(".sidebar-nav-list .nav-item").forEach(link => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      const targetId = link.getAttribute("data-seg-target");
      const targetEl = document.getElementById(targetId);
      if (targetEl) {
        targetEl.scrollIntoView({ behavior: "smooth", block: "start" });
        targetEl.classList.add("highlighted");
        setTimeout(() => targetEl.classList.remove("highlighted"), 2000);
      }
    });
  });

  // Handle Hash Scroll on Initial Load
  if (window.location.hash) {
    const targetId = window.location.hash.replace("#", "");
    const targetEl = document.getElementById(targetId);
    if (targetEl) {
      setTimeout(() => {
        targetEl.scrollIntoView({ behavior: "smooth", block: "start" });
        targetEl.classList.add("highlighted");
      }, 300);
    }
  }
}

// Scrollspy for .viewer-content-main
function handleScrollSpy() {
  const contentMain = document.querySelector(".viewer-content-main");
  if (!contentMain) return;

  const cards = document.querySelectorAll(".segment-card, .section-divider-banner, .preamble-card");
  let currentId = "";

  const containerRect = contentMain.getBoundingClientRect();

  cards.forEach(card => {
    const cardRect = card.getBoundingClientRect();
    // Check if card is in upper part of visible container
    if (cardRect.top <= containerRect.top + 180 && cardRect.bottom >= containerRect.top + 60) {
      currentId = card.id;
    }
  });

  if (currentId && currentId !== activeSegmentId) {
    activeSegmentId = currentId;
    document.querySelectorAll(".sidebar-nav-list .nav-item").forEach(link => {
      const target = link.getAttribute("data-seg-target");
      link.classList.toggle("active", target === currentId);
      if (target === currentId) {
        link.scrollIntoView({ block: "nearest", behavior: "smooth" });
      }
    });
  }
}

// Search Filter
function filterSegments(query) {
  const cards = document.querySelectorAll(".segment-card");
  let matchCount = 0;

  cards.forEach(card => {
    const text = card.textContent.toLowerCase();
    const match = !query || text.includes(query);
    card.style.display = match ? "block" : "none";
    if (match) matchCount++;
  });

  metaSegCountEl.textContent = query ? `Знайдено: ${matchCount}` : `${cards.length} правових позицій`;
}

// Toast notification helper
let toastTimer = null;
function showToast(message) {
  if (toastTimer) clearTimeout(toastTimer);
  toastTextEl.textContent = message;
  toastEl.classList.add("show");
  toastTimer = setTimeout(() => {
    toastEl.classList.remove("show");
  }, 2500);
}

// Helper: Escape HTML
function escapeHtml(str) {
  if (!str) return "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
