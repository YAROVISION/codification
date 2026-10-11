// State Management
let currentTreeData = null;
let categoryLookup = new Map();
let currentSelectedCode = "10";
let searchDebounceTimer = null;

// DOM Elements
const treeContainer = document.getElementById("tree-container");
const treeLoading = document.getElementById("tree-loading");
const globalSearchInput = document.getElementById("global-search-input");
const searchDropdown = document.getElementById("search-dropdown");
const searchResultsList = document.getElementById("search-results-list");
const searchResultsCount = document.getElementById("search-results-count");
const treeFilterInput = document.getElementById("tree-filter-input");

const btnCollapseAll = document.getElementById("btn-collapse-all");
const btnExpandAll = document.getElementById("btn-expand-all");

const breadcrumbBar = document.getElementById("breadcrumb-bar");
const heroCode = document.getElementById("hero-code");
const heroLevel = document.getElementById("hero-level");
const heroTitle = document.getElementById("hero-title");
const heroBranchUrlBtn = document.getElementById("hero-branch-url-btn");
const heroDirectUrlBtn = document.getElementById("hero-direct-url-btn");
const heroTotalDocsBtnCount = document.getElementById("hero-total-docs-btn-count");
const heroDirectDocsBtnCount = document.getElementById("hero-direct-docs-btn-count");



const subcategoriesGrid = document.getElementById("subcategories-grid");
const subcatsCountBadge = document.getElementById("subcats-count-badge");
const directActsSection = document.getElementById("direct-acts-section");
const directActsGrid = document.getElementById("direct-acts-grid");
const directActsCountBadge = document.getElementById("direct-acts-count-badge");
const directActsModalBackdrop = document.getElementById("direct-acts-modal-backdrop");
const modalActsTitle = document.getElementById("modal-acts-title");
const modalActsCount = document.getElementById("modal-acts-count");
const modalActsClose = document.getElementById("modal-acts-close");
const modalActsList = document.getElementById("modal-acts-list");
const segmentsSection = document.getElementById("segments-section");
const segmentsList = document.getElementById("segments-list");
const segmentsCountBadge = document.getElementById("segments-count-badge");
const crossRefsContent = document.getElementById("cross-refs-content");
const semanticTextPreview = document.getElementById("semantic-text-preview");

const btnCopySemantic = document.getElementById("btn-copy-semantic");
const btnCopyJson = document.getElementById("btn-copy-json");

const statRoots = document.getElementById("stat-roots");
const statTotal = document.getElementById("stat-total");
const statDocs = document.getElementById("stat-docs");

// macOS Liquid Glass Theme Elements
const themeBtnLight = document.getElementById("theme-btn-light");
const themeBtnDark = document.getElementById("theme-btn-dark");
const themeIndicator = document.getElementById("theme-indicator");
const sidebar = document.getElementById("sidebar");

// Mobile Drawer Elements
const mobileSidebarToggle = document.getElementById("mobile-sidebar-toggle");
const mobileSidebarClose = document.getElementById("mobile-sidebar-close");
const sidebarBackdrop = document.getElementById("sidebar-backdrop");
const statRootsMobile = document.getElementById("stat-roots-mobile");
const statTotalMobile = document.getElementById("stat-total-mobile");
const statDocsMobile = document.getElementById("stat-docs-mobile");

function openMobileSidebar() {
  if (sidebar) {
    sidebar.classList.add("open");
  }
  if (sidebarBackdrop) {
    sidebarBackdrop.classList.add("active");
  }
  document.body.classList.add("sidebar-open");
}

function closeMobileSidebar() {
  if (sidebar) {
    sidebar.classList.remove("open");
  }
  if (sidebarBackdrop) {
    sidebarBackdrop.classList.remove("active");
  }
  document.body.classList.remove("sidebar-open");
}

// Initialize application
async function init() {
  initTheme();
  setupEventListeners();
  setupWindowControls();
  loadStats();
  await loadTree();

  // Restore selection from URL hash or default to '10'
  const hash = window.location.hash.replace("#", "");
  if (hash.startsWith("code=")) {
    const code = decodeURIComponent(hash.replace("code=", "").replace(/_/g, " "));
    selectCategory(code);
  } else {
    selectCategory("10");
  }
}

// Theme Management (Liquid Glass macOS Light / Dark Modes)
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

  if (animate) {
    showToast(theme === "light" ? "Світло-блакитну тему активовано" : "Темну тему активовано");
  }
}

function toggleTheme() {
  const current = document.documentElement.getAttribute("data-theme") || "dark";
  applyTheme(current === "dark" ? "light" : "dark");
}

// macOS Window Traffic Light Controls
function setupWindowControls() {
  const dotClose = document.querySelector(".mac-dot-close");
  const dotMinimize = document.querySelector(".mac-dot-minimize");
  const dotMaximize = document.querySelector(".mac-dot-maximize");

  if (dotClose) {
    dotClose.addEventListener("click", () => {
      // Close search or clear filter
      globalSearchInput.value = "";
      treeFilterInput.value = "";
      filterTreeNodes("");
      searchDropdown.classList.add("hidden");
      showToast("Пошукові фільтри очищено");
    });
  }

  if (dotMinimize) {
    dotMinimize.addEventListener("click", () => {
      // Toggle sidebar collapse
      if (sidebar) {
        const isHidden = sidebar.style.display === "none";
        sidebar.style.display = isHidden ? "flex" : "none";
        showToast(isHidden ? "Бічну панель показано" : "Бічну панель приховано");
      }
    });
  }

  if (dotMaximize) {
    dotMaximize.addEventListener("click", () => {
      // Toggle fullscreen
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(() => {});
      } else {
        document.exitFullscreen().catch(() => {});
      }
    });
  }
}

// Setup Event Listeners
function setupEventListeners() {
  // Global search input
  globalSearchInput.addEventListener("input", (e) => {
    clearTimeout(searchDebounceTimer);
    const query = e.target.value.trim();
    if (!query) {
      searchDropdown.classList.add("hidden");
      return;
    }
    searchDebounceTimer = setTimeout(() => performSearch(query), 200);
  });

  // Global Keyboard Shortcuts (Ctrl+K or '/' or Alt+T)
  window.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      globalSearchInput.focus();
      globalSearchInput.select();
    }
    if (e.key === "Escape") {
      searchDropdown.classList.add("hidden");
    }
    // Alt+T or Option+T for theme toggle
    if (e.altKey && e.key.toLowerCase() === "t") {
      e.preventDefault();
      toggleTheme();
    }
  });

  // Close search dropdown on click outside
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".search-box-container")) {
      searchDropdown.classList.add("hidden");
    }
  });

  // Tree Filter
  treeFilterInput.addEventListener("input", (e) => {
    filterTreeNodes(e.target.value.trim().toLowerCase());
  });

  // Collapse / Expand All
  btnCollapseAll.addEventListener("click", () => {
    document.querySelectorAll(".tree-children-container").forEach((c) => c.classList.add("collapsed"));
    document.querySelectorAll(".tree-expander").forEach((e) => e.classList.remove("expanded"));
  });

  btnExpandAll.addEventListener("click", () => {
    // Expand top level branches
    document.querySelectorAll(".tree-node-group[data-level='1'] > .tree-children-container").forEach((c) => c.classList.remove("collapsed"));
    document.querySelectorAll(".tree-node-group[data-level='1'] > .tree-node-row .tree-expander").forEach((e) => e.classList.add("expanded"));
  });

  // Copy buttons
  btnCopySemantic.addEventListener("click", () => {
    const text = semanticTextPreview.textContent;
    navigator.clipboard.writeText(text).then(() => {
      showToast("Текстовий опис скопійовано!");
    });
  });

  btnCopyJson.addEventListener("click", async () => {
    const node = categoryLookup.get(currentSelectedCode);
    if (node) {
      navigator.clipboard.writeText(JSON.stringify(node, null, 2)).then(() => {
        showToast("JSON категорію скопійовано!");
      });
    }
  });

  // Mobile Drawer Toggle Listeners
  if (mobileSidebarToggle) {
    mobileSidebarToggle.addEventListener("click", openMobileSidebar);
  }
  if (mobileSidebarClose) {
    mobileSidebarClose.addEventListener("click", closeMobileSidebar);
  }
  if (sidebarBackdrop) {
    sidebarBackdrop.addEventListener("click", closeMobileSidebar);
  }

  // Hash change
  window.addEventListener("hashchange", () => {
    const hash = window.location.hash.replace("#", "");
    if (hash.startsWith("code=")) {
      const code = decodeURIComponent(hash.replace("code=", "").replace(/_/g, " "));
      if (code !== currentSelectedCode) {
        selectCategory(code);
      }
    }
  });
}

// Load System Statistics
async function loadStats() {
  try {
    const res = await fetch("/api/stats");
    if (!res.ok) return;
    const stats = await res.json();
    if (statRoots) statRoots.textContent = stats.root_branches || 28;
    if (statTotal) statTotal.textContent = Number(stats.total_categories).toLocaleString("uk-UA");
    if (statDocs) statDocs.textContent = Number(stats.total_docs_registered).toLocaleString("uk-UA");

    // Populate mobile drawer stats
    if (statRootsMobile) statRootsMobile.textContent = stats.root_branches || 28;
    if (statTotalMobile) statTotalMobile.textContent = Number(stats.total_categories).toLocaleString("uk-UA");
    if (statDocsMobile) statDocsMobile.textContent = Number(stats.total_docs_registered).toLocaleString("uk-UA");
  } catch (err) {
    console.error("Failed to load stats", err);
  }
}

// Load Tree Data
async function loadTree() {
  try {
    const res = await fetch("/api/tree");
    const data = await res.json();
    currentTreeData = Array.isArray(data) ? data : (data.tree || []);

    // Build fast lookup map
    buildLookupMap(currentTreeData);

    // Render tree DOM
    renderTree(currentTreeData);
    treeLoading.style.display = "none";
  } catch (err) {
    console.error("Failed to load tree", err);
    treeLoading.innerHTML = `<span style="color: #f43f5e;">Помилка завантаження дерева</span>`;
  }
}

function buildLookupMap(nodes) {
  for (const node of nodes) {
    categoryLookup.set(node.code, node);
    if (node.children && node.children.length > 0) {
      buildLookupMap(node.children);
    }
  }
}

// Render Tree DOM
function renderTree(nodes, parentEl = treeContainer, level = 1) {
  for (const node of nodes) {
    const group = document.createElement("div");
    group.className = "tree-node-group";
    group.dataset.code = node.code;
    group.dataset.level = level;
    group.dataset.search = (node.code + " " + node.clean_name).toLowerCase();

    const row = document.createElement("div");
    row.className = "tree-node-row";
    row.id = `tree-row-${cssSafe(node.code)}`;

    const hasChildren = node.children && node.children.length > 0;

    const expander = document.createElement("span");
    expander.className = `tree-expander ${hasChildren ? "" : "empty"}`;
    expander.innerHTML = `<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M9 18l6-6-6-6"/></svg>`;

    const codeSpan = document.createElement("span");
    codeSpan.className = "tree-code";
    codeSpan.textContent = node.code;

    const titleSpan = document.createElement("span");
    titleSpan.className = "tree-title";
    titleSpan.textContent = node.clean_name;
    titleSpan.title = `${node.code} ${node.clean_name}`;

    const badge = document.createElement("span");
    badge.className = "tree-badge";
    badge.textContent = Number(node.total_docs_count).toLocaleString("uk-UA");

    row.appendChild(expander);
    row.appendChild(codeSpan);
    row.appendChild(titleSpan);
    row.appendChild(badge);

    group.appendChild(row);

    // Children Container
    if (hasChildren) {
      const childrenContainer = document.createElement("div");
      childrenContainer.className = "tree-children-container collapsed";
      renderTree(node.children, childrenContainer, level + 1);
      group.appendChild(childrenContainer);

      // Expander click toggles
      expander.addEventListener("click", (e) => {
        e.stopPropagation();
        toggleNodeExpansion(group);
      });
    }

    // Row click selects category
    row.addEventListener("click", () => {
      selectCategory(node.code);
      if (hasChildren) {
        const cContainer = group.querySelector(".tree-children-container");
        if (cContainer && cContainer.classList.contains("collapsed")) {
          toggleNodeExpansion(group, true);
        }
      }
    });

    parentEl.appendChild(group);
  }
}

function toggleNodeExpansion(group, forceOpen = null) {
  const expander = group.querySelector(":scope > .tree-node-row .tree-expander");
  const childrenContainer = group.querySelector(":scope > .tree-children-container");
  if (!childrenContainer) return;

  const isCollapsed = childrenContainer.classList.contains("collapsed");
  const shouldOpen = forceOpen !== null ? forceOpen : isCollapsed;

  if (shouldOpen) {
    childrenContainer.classList.remove("collapsed");
    expander?.classList.add("expanded");
  } else {
    childrenContainer.classList.add("collapsed");
    expander?.classList.remove("expanded");
  }
}

// Select and Display Category
async function selectCategory(code) {
  if (!code) return;
  currentSelectedCode = code;

  // Update URL hash without jumping
  window.history.replaceState(null, "", `#code=${encodeURIComponent(code.replace(/ /g, "_"))}`);

  // Highlight active tree row
  document.querySelectorAll(".tree-node-row.active").forEach((r) => r.classList.remove("active"));
  const targetRow = document.getElementById(`tree-row-${cssSafe(code)}`);
  if (targetRow) {
    targetRow.classList.add("active");
    // Expand all parent nodes in tree
    expandParentsInTree(targetRow);
    targetRow.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  // Close mobile sidebar if open on smaller screens
  if (window.innerWidth <= 900) {
    closeMobileSidebar();
  }

  // Fetch detailed data from server API or lookup map
  try {
    const res = await fetch(`/api/category?code=${encodeURIComponent(code)}`);
    const cat = await res.json();
    renderCategoryDetails(cat);
  } catch (err) {
    console.error("Error loading category details", err);
    const cached = categoryLookup.get(code);
    if (cached) renderCategoryDetails(cached);
  }
}

function expandParentsInTree(rowEl) {
  let parent = rowEl.parentElement;
  while (parent && parent !== treeContainer) {
    if (parent.classList.contains("tree-children-container")) {
      parent.classList.remove("collapsed");
      const group = parent.parentElement;
      const expander = group?.querySelector(":scope > .tree-node-row .tree-expander");
      expander?.classList.add("expanded");
    }
    parent = parent.parentElement;
  }
}

// Render Category Details in Main Panel
function renderCategoryDetails(cat) {
  heroCode.textContent = cat.code;
  heroLevel.textContent = `Рівень ${cat.level} • ${getLevelLabel(cat.level)}`;
  heroTitle.textContent = cat.clean_name;

  // Action Links / Tabs
  if (cat.branch_url) {
    heroBranchUrlBtn.href = cat.branch_url;
    heroBranchUrlBtn.classList.remove("hidden");
    heroBranchUrlBtn.style.removeProperty("display");
  } else {
    heroBranchUrlBtn.classList.add("hidden");
    heroBranchUrlBtn.style.display = "none";
  }

  let directActs = cat.direct_acts || [];
  if (typeof directActs === "string") {
    try {
      directActs = JSON.parse(directActs);
    } catch (e) {
      directActs = [];
    }
  }
  if (!Array.isArray(directActs)) {
    directActs = [];
  }

  if (directActs.length > 0) {
    heroDirectUrlBtn.removeAttribute("target");
    heroDirectUrlBtn.href = "#direct-acts-section";
    heroDirectUrlBtn.onclick = (e) => {
      e.preventDefault();
      const sec = document.getElementById("direct-acts-section");
      if (sec) {
        sec.classList.remove("hidden");
        sec.scrollIntoView({ behavior: "smooth", block: "start" });
        sec.classList.add("highlight-pulse");
        setTimeout(() => sec.classList.remove("highlight-pulse"), 1500);
      }
    };
    heroDirectUrlBtn.classList.remove("hidden");
    heroDirectUrlBtn.style.removeProperty("display");
    heroDirectDocsBtnCount.textContent = `(${directActs.length})`;
  } else if (cat.direct_url && !cat.direct_url.includes("find/a?text=") && !cat.direct_url.includes("main/jj")) {
    heroDirectUrlBtn.href = cat.direct_url;
    heroDirectUrlBtn.setAttribute("target", "_blank");
    heroDirectUrlBtn.onclick = null;
    heroDirectUrlBtn.classList.remove("hidden");
    heroDirectUrlBtn.style.removeProperty("display");
    const directDocs = Number(cat.direct_docs_count || 0);
    heroDirectDocsBtnCount.textContent = directDocs > 0 ? `(${directDocs.toLocaleString("uk-UA")})` : "";
  } else {
    heroDirectUrlBtn.classList.add("hidden");
    heroDirectUrlBtn.style.display = "none";
  }

  const totalDocs = Number(cat.total_docs_count || 0);
  heroTotalDocsBtnCount.textContent = totalDocs > 0 ? `(${totalDocs.toLocaleString("uk-UA")})` : "";

  // Subcategories count badge
  const childrenList = cat.children || [];
  if (subcatsCountBadge) {
    subcatsCountBadge.textContent = childrenList.length;
  }

  // Breadcrumbs
  renderBreadcrumbs(cat);

  // Subcategories Grid
  renderSubcategories(childrenList);

  // Direct Acts (Базові закони)
  renderDirectActs(directActs, cat.clean_name);

  // Judicial Practice Segments
  if (typeof renderSegments === "function") {
    renderSegments(cat.segments);
  }

  // Cross-references
  renderCrossReferences(cat.relations || [], cat.cross_references);

  // Semantic Embeddings Text
  const semText = cat.semantic_text || `Категорія: ${cat.clean_name}. Ієрархічний шлях: ${cat.path_names}. Код класифікатора: ${cat.code} (Рівень ${cat.level}). Кількість документів: ${cat.total_docs_count}.`;
  semanticTextPreview.textContent = semText;
}

// Render Direct Laws & Acts
function renderDirectActs(directActs, catName) {
  if (!directActsSection || !directActsGrid) return;

  directActsGrid.innerHTML = "";

  if (!directActs || directActs.length === 0) {
    directActsSection.classList.add("hidden");
    if (directActsCountBadge) directActsCountBadge.textContent = "0";
    return;
  }

  directActsSection.classList.remove("hidden");
  if (directActsCountBadge) {
    directActsCountBadge.textContent = directActs.length;
  }

  directActs.forEach((act) => {
    const card = document.createElement("a");
    card.className = "direct-act-card";
    card.href = act.url || "#";
    card.target = "_blank";
    card.rel = "noopener noreferrer";
    card.title = `Відкрити офіційний текст на порталі ВРУ: ${act.title}`;

    card.innerHTML = `
      <div class="direct-act-top">
        <span class="direct-act-badge">${escapeHtml(act.type || "Закон України")}</span>
        <span class="direct-act-icon-btn" title="Відкрити закон на ВРУ">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
            <polyline points="15 3 21 3 21 9"></polyline>
            <line x1="10" y1="14" x2="21" y2="3"></line>
          </svg>
        </span>
      </div>
      <div class="direct-act-title">${escapeHtml(act.title)}</div>
      ${act.number ? `<div class="direct-act-number">📜 ${escapeHtml(act.number)}</div>` : ""}
      ${act.description ? `<div class="direct-act-desc">${escapeHtml(act.description)}</div>` : ""}
    `;

    directActsGrid.appendChild(card);
  });
}

// Open Direct Acts Modal
function openDirectActsModal(categoryName, directActs) {
  if (!directActsModalBackdrop || !modalActsList || !directActs || directActs.length === 0) {
    closeDirectActsModal();
    return;
  }
  if (modalActsTitle) modalActsTitle.textContent = `Прямі закони: ${categoryName}`;
  if (modalActsCount) modalActsCount.textContent = directActs.length;
  modalActsList.innerHTML = "";

  directActs.forEach((act) => {
    const item = document.createElement("a");
    item.className = "modal-act-item";
    item.href = act.url || "#";
    item.target = "_blank";
    item.rel = "noopener noreferrer";
    item.title = `Відкрити офіційний текст на порталі ВРУ: ${act.title}`;

    item.innerHTML = `
      <div class="modal-act-info">
        <span class="modal-act-type">${escapeHtml(act.type || "Закон України")}</span>
        <div class="modal-act-title">${escapeHtml(act.title)}</div>
        ${act.number ? `<div class="modal-act-number">📜 ${escapeHtml(act.number)}</div>` : ""}
        ${act.description ? `<div class="modal-act-desc">${escapeHtml(act.description)}</div>` : ""}
      </div>
      <div class="modal-act-open-btn">
        <span>Відкрити закон</span>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
          <polyline points="15 3 21 3 21 9"></polyline>
          <line x1="10" y1="14" x2="21" y2="3"></line>
        </svg>
      </div>
    `;

    modalActsList.appendChild(item);
  });

  directActsModalBackdrop.style.display = "flex";
  directActsModalBackdrop.classList.remove("hidden");
  document.body.style.overflow = "hidden";
}

// Close Direct Acts Modal
function closeDirectActsModal() {
  if (directActsModalBackdrop) {
    directActsModalBackdrop.style.display = "none";
    directActsModalBackdrop.classList.add("hidden");
  }
  document.body.style.removeProperty("overflow");
}

// Modal event listeners setup
if (modalActsClose) {
  modalActsClose.addEventListener("click", closeDirectActsModal);
}
if (directActsModalBackdrop) {
  directActsModalBackdrop.addEventListener("click", (e) => {
    if (e.target === directActsModalBackdrop) {
      closeDirectActsModal();
    }
  });
}
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && directActsModalBackdrop && !directActsModalBackdrop.classList.contains("hidden")) {
    closeDirectActsModal();
  }
});

function getLevelLabel(level) {
  switch (level) {
    case 1: return "Головна галузь права";
    case 2: return "Підгалузь законодавства";
    case 3: return "Предметна рубрика";
    case 4: return "Спеціалізована підтема";
    default: return "Рубрика";
  }
}

// Render Breadcrumbs
function renderBreadcrumbs(cat) {
  breadcrumbBar.innerHTML = "";

  const ancestors = cat.ancestors || [];
  if (ancestors.length === 0 && cat.path_names) {
    // Fallback if ancestors array not populated
    const names = cat.path_names.split(" / ");
    const codes = (cat.path_codes || "").split(" / ");
    for (let i = 0; i < names.length; i++) {
      ancestors.push({ code: codes[i] || "", clean_name: names[i] });
    }
  }

  ancestors.forEach((anc, idx) => {
    const isCurrent = idx === ancestors.length - 1;
    const span = document.createElement("span");
    span.className = `breadcrumb-item ${isCurrent ? "current" : ""}`;
    span.textContent = anc.clean_name;

    if (!isCurrent) {
      span.addEventListener("click", () => selectCategory(anc.code));
    }

    breadcrumbBar.appendChild(span);

    if (!isCurrent) {
      const sep = document.createElement("span");
      sep.className = "breadcrumb-sep";
      sep.textContent = "›";
      breadcrumbBar.appendChild(sep);
    }
  });
}

// Render Subcategories Cards
function renderSubcategories(children) {
  subcategoriesGrid.innerHTML = "";
  if (!children || children.length === 0) {
    subcategoriesGrid.innerHTML = `<span class="empty-text">У цього вузла немає підрубрик нижчого рівня (це кінцева тема).</span>`;
    return;
  }

  children.forEach((child) => {
    const card = document.createElement("div");
    card.className = "subcat-card";

    card.innerHTML = `
      <div class="subcat-top">
        <span class="subcat-code">${child.code}</span>
        <span class="subcat-count">${Number(child.total_docs_count).toLocaleString("uk-UA")} актів</span>
      </div>
      <div class="subcat-title">${child.clean_name}</div>
    `;

    card.addEventListener("click", () => {
      selectCategory(child.code);
    });

    subcategoriesGrid.appendChild(card);
  });
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Render Judicial Practice Segments with PDF Journal Viewer links
function renderSegments(segments) {
  if (!segmentsSection || !segmentsList) return;

  segmentsList.innerHTML = "";

  if (!segments || segments.length === 0) {
    segmentsSection.classList.add("hidden");
    if (segmentsCountBadge) segmentsCountBadge.textContent = "0";
    return;
  }

  segmentsSection.classList.remove("hidden");
  if (segmentsCountBadge) {
    segmentsCountBadge.textContent = segments.length;
  }

  segments.forEach((seg, index) => {
    const card = document.createElement("article");
    card.className = "segment-card";

    // Визначення назви огляду / журналу за шляхом до сегмента
    let docName = seg.doc_name || "";
    if (!docName && seg.file_path) {
      const parts = seg.file_path.replace(/\\/g, "/").split("/");
      const segIdx = parts.indexOf("segments");
      if (segIdx !== -1 && parts.length > segIdx + 1) {
        docName = parts[segIdx + 1];
      }
    }

    // Надійне формування посилання на PDF-журнал огляду
    let pdfUrl = "";
    let pdfName = "";
    if (seg.pdf_path && seg.pdf_path.toLowerCase().endsWith(".pdf") && !seg.pdf_path.startsWith("http")) {
      const cleanPath = seg.pdf_path.replace(/\\/g, "/").replace(/^\/+/, "");
      pdfUrl = "/" + cleanPath;
      pdfName = seg.pdf_name || cleanPath.split("/").pop() || "Огляд судової практики.pdf";
    } else if (docName) {
      pdfUrl = `/documents/pdfs/${encodeURIComponent(docName)}.pdf`;
      pdfName = `${docName}.pdf`;
    }

    // Визначення посилання на судове рішення в ЄДРСР
    let decisionUrl = seg.decision_url || "";
    if (!decisionUrl && seg.pdf_path && seg.pdf_path.startsWith("http")) {
      decisionUrl = seg.pdf_path;
    }

    const confidencePct = Math.round((seg.confidence_score || 0.95) * 100);

    card.innerHTML = `
      <div class="segment-card-header">
        <div class="segment-badges">
          ${decisionUrl ? `
            <a href="${decisionUrl}" target="_blank" rel="noopener noreferrer" class="segment-badge-case segment-badge-case-link" title="Відкрити повний текст судового рішення у Єдиному державному реєстрі судових рішень (ЄДРСР)">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="m14 13-7.5 7.5c-.83.83-2.17.83-3 0 0 0 0 0 0 0-.83-.83-.83-2.17 0-3L11 10"></path>
                <path d="m16 16 6-6"></path>
                <path d="m8 8 6-6"></path>
                <path d="m9 7 8 8"></path>
                <path d="m21 11-8-8"></path>
              </svg>
              <span>${escapeHtml(seg.case_number || "Справа ВС")}</span>
              <svg class="external-icon-sm" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                <polyline points="15 3 21 3 21 9"></polyline>
                <line x1="10" y1="14" x2="21" y2="3"></line>
              </svg>
            </a>
          ` : `
            <span class="segment-badge-case" title="Номер судового рішення Верховного Суду">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="m14 13-7.5 7.5c-.83.83-2.17.83-3 0 0 0 0 0 0 0-.83-.83-.83-2.17 0-3L11 10"></path>
                <path d="m16 16 6-6"></path>
                <path d="m8 8 6-6"></path>
                <path d="m9 7 8 8"></path>
                <path d="m21 11-8-8"></path>
              </svg>
              ${escapeHtml(seg.case_number || "Справа ВС")}
            </span>
          `}
          <span class="segment-badge-confidence" title="Рівень семантичної відповідності категорії">
            <span class="confidence-dot"></span>
            ${confidencePct}% відповідність
          </span>
        </div>

        ${pdfUrl ? `
          <a href="${pdfUrl}" target="_blank" rel="noopener noreferrer" class="btn-pdf-view" title="Відкрити офіційний випуск журналу огляду (${escapeHtml(pdfName)}) у новій вкладці">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
              <line x1="16" y1="13" x2="8" y2="13"></line>
              <line x1="16" y1="17" x2="8" y2="17"></line>
              <polyline points="10 9 9 9 8 9"></polyline>
            </svg>
            <span>Відкрити журнал (PDF)</span>
            <svg class="external-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
              <polyline points="15 3 21 3 21 9"></polyline>
              <line x1="10" y1="14" x2="21" y2="3"></line>
            </svg>
          </a>
        ` : ''}
      </div>

      <div class="segment-body">
        <h4 class="segment-teza">${escapeHtml(seg.teza || "Правова позиція")}</h4>
        
        ${seg.summary ? `
          <div class="segment-summary">
            <p>${escapeHtml(seg.summary)}</p>
          </div>
        ` : ''}

        ${seg.all_categories && seg.all_categories.length > 1 ? `
          <div class="segment-all-categories">
            <span class="all-categories-title">Всі взаємозв'язки цього сегмента (${seg.all_categories.length}):</span>
            <div class="all-categories-chips">
              ${seg.all_categories.map(ac => `
                <a href="#code=${encodeURIComponent(ac.category_code)}" class="category-chip ${ac.category_code === currentSelectedCode ? 'active' : ''}" title="${escapeHtml(ac.clean_name || '')}">
                  <span class="chip-code">${escapeHtml(ac.category_code)}</span>
                  <span class="chip-name">${escapeHtml(ac.clean_name || '')}</span>
                </a>
              `).join('')}
            </div>
          </div>
        ` : ''}

        <div class="segment-details-collapse hidden" id="seg-details-${seg.id || index}">
          ${seg.circumstances ? `
            <div class="detail-block">
              <div class="detail-label">Фактичні обставини спору:</div>
              <div class="detail-text">${escapeHtml(seg.circumstances)}</div>
            </div>
          ` : ''}
          ${seg.reasoning ? `
            <div class="detail-block">
              <div class="detail-label">Оцінка та мотиви Верховного Суду:</div>
              <div class="detail-text">${escapeHtml(seg.reasoning)}</div>
            </div>
          ` : ''}
          ${seg.llm_reasoning ? `
            <div class="detail-block detail-ai">
              <div class="detail-label">Семантичне обґрунтування класифікації:</div>
              <div class="detail-text">${escapeHtml(seg.llm_reasoning)}</div>
            </div>
          ` : ''}
          ${decisionUrl ? `
            <div class="detail-block detail-court-ref">
              <div class="detail-label">Судове рішення у Реєстрі (ЄДРСР):</div>
              <div class="detail-text">
                <a href="${decisionUrl}" target="_blank" rel="noopener noreferrer" class="pdf-link-inline court-link-inline">
                  ⚖️ <strong>${escapeHtml(seg.case_number || "Рішення Верховного Суду")}</strong> (відкрити повний текст у ЄДРСР)
                </a>
              </div>
            </div>
          ` : ''}
          ${pdfUrl ? `
            <div class="detail-block detail-pdf-ref">
              <div class="detail-label">Офіційний журнал огляду:</div>
              <div class="detail-text">
                <a href="${pdfUrl}" target="_blank" rel="noopener noreferrer" class="pdf-link-inline">
                  📄 <strong>${escapeHtml(pdfName)}</strong> (натисніть для перегляду журналу)
                </a>
              </div>
            </div>
          ` : ''}
        </div>

        <div class="segment-footer">
          <button type="button" class="btn-toggle-details" data-target="seg-details-${seg.id || index}">
            <span class="btn-toggle-text">Показати деталі та мотиви</span>
            <svg class="chevron-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </button>
        </div>
      </div>
    `;

    // Event listener for toggle details
    const toggleBtn = card.querySelector(".btn-toggle-details");
    const detailsBox = card.querySelector(`#seg-details-${seg.id || index}`);
    if (toggleBtn && detailsBox) {
      toggleBtn.addEventListener("click", () => {
        const isHidden = detailsBox.classList.contains("hidden");
        if (isHidden) {
          detailsBox.classList.remove("hidden");
          toggleBtn.querySelector(".btn-toggle-text").textContent = "Приховати деталі";
          toggleBtn.classList.add("expanded");
        } else {
          detailsBox.classList.add("hidden");
          toggleBtn.querySelector(".btn-toggle-text").textContent = "Показати деталі та мотиви";
          toggleBtn.classList.remove("expanded");
        }
      });
    }

    segmentsList.appendChild(card);
  });
}

// Render Cross References
function renderCrossReferences(relations, rawRefs) {
  crossRefsContent.innerHTML = "";
  const refs = [];

  if (relations && relations.length > 0) {
    relations.forEach((r) => {
      refs.push({
        code: r.target_code,
        name: r.target_name || `Рубрика ${r.target_code}`,
        notes: r.notes
      });
    });
  } else if (rawRefs) {
    const parsed = typeof rawRefs === "string" ? JSON.parse(rawRefs) : rawRefs;
    if (Array.isArray(parsed)) {
      parsed.forEach((code) => {
        const target = categoryLookup.get(code);
        refs.push({
          code: code,
          name: target ? target.clean_name : `Рубрика ${code}`,
          notes: "Офіційне перехресне посилання ВРУ"
        });
      });
    }
  }

  if (refs.length === 0) {
    crossRefsContent.innerHTML = `<span class="empty-text">Для цього вузла прямих перехресних відсилок немає</span>`;
    return;
  }

  refs.forEach((ref) => {
    const pill = document.createElement("div");
    pill.className = "ref-pill";
    pill.innerHTML = `
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
        <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
      </svg>
      <span>див. <strong>${ref.code}</strong> — ${ref.name}</span>
    `;

    pill.addEventListener("click", () => {
      selectCategory(ref.code);
    });

    crossRefsContent.appendChild(pill);
  });
}

// Global Live Search
async function performSearch(query) {
  try {
    const res = await fetch(`/api/search?q=${encodeURIComponent(query)}&limit=15`);
    const results = await res.json();

    searchResultsList.innerHTML = "";
    if (results.length === 0) {
      searchResultsCount.textContent = "Нічого не знайдено";
      searchResultsList.innerHTML = `<div style="padding: 12px; color: var(--text-dim); font-size: 13px;">За запитом "${query}" рубрик не знайдено</div>`;
      searchDropdown.classList.remove("hidden");
      return;
    }

    searchResultsCount.textContent = `Знайдено: ${results.length}`;

    results.forEach((item) => {
      const el = document.createElement("div");
      el.className = "search-result-item";
      el.innerHTML = `
        <div class="result-top-line">
          <span class="result-code">${item.code}</span>
          <span class="result-name">${item.clean_name}</span>
          <span class="result-count">${Number(item.total_docs_count).toLocaleString("uk-UA")} актів</span>
        </div>
        <div class="result-path">${item.path_names || ""}</div>
      `;

      el.addEventListener("click", () => {
        searchDropdown.classList.add("hidden");
        globalSearchInput.value = "";
        selectCategory(item.code);
      });

      searchResultsList.appendChild(el);
    });

    searchDropdown.classList.remove("hidden");
  } catch (err) {
    console.error("Search error", err);
  }
}

// Filter Tree Sidebar
function filterTreeNodes(term) {
  if (!term) {
    document.querySelectorAll(".tree-node-group").forEach((g) => (g.style.display = ""));
    return;
  }

  document.querySelectorAll(".tree-node-group").forEach((group) => {
    const match = group.dataset.search.includes(term);
    if (match) {
      group.style.display = "";
      // Ensure parents are visible & expanded
      let p = group.parentElement;
      while (p && p !== treeContainer) {
        if (p.classList.contains("tree-children-container")) {
          p.classList.remove("collapsed");
          p.style.display = "";
        }
        if (p.classList.contains("tree-node-group")) {
          p.style.display = "";
        }
        p = p.parentElement;
      }
    } else {
      // If it contains a matching descendant, keep it visible
      const hasMatchingChild = group.querySelector(`.tree-node-group[data-search*="${term}"]`);
      group.style.display = hasMatchingChild ? "" : "none";
    }
  });
}

function cssSafe(str) {
  return str.replace(/[^a-zA-Z0-9_-]/g, "_");
}

function showToast(msg) {
  const existing = document.querySelector(".mac-toast");
  if (existing) existing.remove();

  const toast = document.createElement("div");
  toast.className = "mac-toast";
  toast.innerHTML = `
    <span class="mac-toast-dot"></span>
    <span class="mac-toast-text">${msg}</span>
  `;
  document.body.appendChild(toast);
  setTimeout(() => {
    toast.classList.add("fade-out");
    setTimeout(() => toast.remove(), 260);
  }, 2200);
}


// Kickoff
document.addEventListener("DOMContentLoaded", init);

