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

const metricTotalDocs = document.getElementById("metric-total-docs");
const metricDirectDocs = document.getElementById("metric-direct-docs");
const metricChildrenCount = document.getElementById("metric-children-count");

const subcategoriesGrid = document.getElementById("subcategories-grid");
const subcatsCountBadge = document.getElementById("subcats-count-badge");
const crossRefsContent = document.getElementById("cross-refs-content");
const semanticTextPreview = document.getElementById("semantic-text-preview");

const btnCopySemantic = document.getElementById("btn-copy-semantic");
const btnCopyJson = document.getElementById("btn-copy-json");

const statRoots = document.getElementById("stat-roots");
const statTotal = document.getElementById("stat-total");
const statDocs = document.getElementById("stat-docs");

// Initialize application
async function init() {
  setupEventListeners();
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

  // Global Keyboard Shortcuts (Ctrl+K or '/')
  window.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      globalSearchInput.focus();
      globalSearchInput.select();
    }
    if (e.key === "Escape") {
      searchDropdown.classList.add("hidden");
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
    statRoots.textContent = stats.root_branches || 28;
    statTotal.textContent = Number(stats.total_categories).toLocaleString("uk-UA");
    statDocs.textContent = Number(stats.total_docs_registered).toLocaleString("uk-UA");
  } catch (err) {
    console.error("Failed to load stats", err);
  }
}

// Load Tree Data
async function loadTree() {
  try {
    const res = await fetch("/api/tree");
    const data = await res.json();
    currentTreeData = data.tree || [];

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

  // Links
  if (cat.branch_url) {
    heroBranchUrlBtn.href = cat.branch_url;
    heroBranchUrlBtn.style.display = "inline-flex";
  } else {
    heroBranchUrlBtn.style.display = "none";
  }

  if (cat.direct_url) {
    heroDirectUrlBtn.href = cat.direct_url;
    heroDirectUrlBtn.style.display = "inline-flex";
  } else {
    heroDirectUrlBtn.style.display = "none";
  }

  heroTotalDocsBtnCount.textContent = Number(cat.total_docs_count).toLocaleString("uk-UA");
  heroDirectDocsBtnCount.textContent = Number(cat.direct_docs_count).toLocaleString("uk-UA");

  // Metrics
  metricTotalDocs.textContent = Number(cat.total_docs_count).toLocaleString("uk-UA");
  metricDirectDocs.textContent = Number(cat.direct_docs_count).toLocaleString("uk-UA");
  const childrenList = cat.children || [];
  metricChildrenCount.textContent = childrenList.length;
  subcatsCountBadge.textContent = childrenList.length;

  // Breadcrumbs
  renderBreadcrumbs(cat);

  // Subcategories Grid
  renderSubcategories(childrenList);

  // Cross-references
  renderCrossReferences(cat.relations || [], cat.cross_references);

  // Semantic Embeddings Text
  const semText = cat.semantic_text || `Категорія: ${cat.clean_name}. Ієрархічний шлях: ${cat.path_names}. Код класифікатора: ${cat.code} (Рівень ${cat.level}). Кількість документів: ${cat.total_docs_count}.`;
  semanticTextPreview.textContent = semText;
}

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
  const toast = document.createElement("div");
  toast.textContent = msg;
  toast.style.position = "fixed";
  toast.style.bottom = "24px";
  toast.style.right = "24px";
  toast.style.background = "linear-gradient(135deg, #0284c7, #2563eb)";
  toast.style.color = "#fff";
  toast.style.padding = "10px 18px";
  toast.style.borderRadius = "8px";
  toast.style.boxShadow = "0 8px 20px rgba(0,0,0,0.5)";
  toast.style.zIndex = "9999";
  toast.style.fontSize = "13px";
  toast.style.fontWeight = "600";
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 2500);
}

// Kickoff
document.addEventListener("DOMContentLoaded", init);
