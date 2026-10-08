#!/usr/bin/env python3
"""
Генератор інтерактивних HTML-сторінок взаємозв'язку сегментів оглядів із класифікатором законодавства.
Зберігає згенеровані сторінки у папці correlation/<doc_name>.html.
"""

import os
import sys
import re
import json
import sqlite3
import html
from pathlib import Path

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = "data/classifier.sqlite"
CORRELATION_DIR = Path("correlation")
CORRELATION_DIR.mkdir(parents=True, exist_ok=True)


def extract_reyestr_url(text: str) -> str:
    if not text:
        return ""
    m = re.search(r'https?://reyestr\.court\.gov\.ua/Review/\d+', text)
    return m.group(0) if m else ""


def build_page_for_document(doc_name: str, conn: sqlite3.Connection) -> str:
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT ms.*, c.name AS category_name, c.path_names AS category_path, c.branch_url, c.direct_url
        FROM mapped_segments ms
        LEFT JOIN categories c ON ms.category_code = c.code
        WHERE ms.file_path LIKE ?
        ORDER BY ms.file_path
    """, (f"%{doc_name}%",))

    rows = cur.fetchall()
    if not rows:
        print(f"⚠️ Не знайдено замаплених сегментів для {doc_name}")
        return ""

    total_segments = len(rows)
    avg_conf = sum((r["confidence_score"] or 0) for r in rows) / total_segments if total_segments > 0 else 0
    unique_categories = len(set(r["category_code"] for r in rows if r["category_code"]))

    # Read segment full texts from disk if available
    segments_data = []
    for idx, r in enumerate(rows, 1):
        file_path_str = r["file_path"]
        fpath = Path(file_path_str)
        disk_text = ""
        if fpath.exists():
            try:
                disk_text = fpath.read_text(encoding="utf-8", errors="surrogateescape")
            except Exception:
                pass
        
        full_text = disk_text or r["summary"] or r["reasoning"] or ""
        reyestr_url = extract_reyestr_url(full_text)
        
        # Clean breadcrumb path
        raw_path = r["category_path"] or r["category_name"] or "Не визначено"
        path_crumbs = [p.strip() for p in raw_path.split("/") if p.strip()]

        segments_data.append({
            "idx": idx,
            "filename": fpath.name,
            "file_path": file_path_str,
            "case_number": r["case_number"] or "Не вказана",
            "reyestr_url": reyestr_url,
            "category_code": r["category_code"] or "—",
            "category_name": r["category_name"] or "Невідома рубрика",
            "path_crumbs": path_crumbs,
            "teza": r["teza"] or "",
            "summary": r["summary"] or "",
            "reasoning": r["llm_reasoning"] or "",
            "confidence": r["confidence_score"] or 0.0,
            "full_text": full_text
        })

    pdf_url = f"/documents/pdfs/{doc_name}.pdf"

    # Generate HTML
    html_content = f"""<!DOCTYPE html>
<html lang="uk" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Взаємозв'язок із класифікацією: {html.escape(doc_name)} — Кодифікатор Законодавства</title>
  <meta name="description" content="Карта відповідності та семантичного зв'язку між сегментами огляду {html.escape(doc_name)} та рубриками класифікатора.">

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  
  <script>
    (function() {{
      const savedTheme = localStorage.getItem('app_theme') || 'dark';
      document.documentElement.setAttribute('data-theme', savedTheme);
    }})();
  </script>

  <style>
    :root {{
      --font-main: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
      
      --bg-primary: #0b0f19;
      --bg-secondary: #111827;
      --bg-card: rgba(17, 24, 39, 0.75);
      --bg-card-hover: rgba(24, 34, 53, 0.9);
      --bg-surface: #1f2937;
      --border-color: rgba(255, 255, 255, 0.08);
      --border-focus: #3b82f6;
      
      --text-primary: #f3f4f6;
      --text-secondary: #9ca3af;
      --text-muted: #6b7280;
      
      --accent-blue: #3b82f6;
      --accent-blue-glow: rgba(59, 130, 246, 0.2);
      --accent-green: #10b981;
      --accent-green-bg: rgba(16, 185, 129, 0.12);
      --accent-purple: #8b5cf6;
      --accent-amber: #f59e0b;
      --accent-amber-bg: rgba(245, 158, 11, 0.12);
      
      --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.3);
      --shadow-md: 0 8px 24px rgba(0, 0, 0, 0.4);
      --shadow-glow: 0 0 20px var(--accent-blue-glow);
      --radius-sm: 6px;
      --radius-md: 10px;
      --radius-lg: 16px;
      --transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }}

    [data-theme="light"] {{
      --bg-primary: #f8fafc;
      --bg-secondary: #ffffff;
      --bg-card: rgba(255, 255, 255, 0.9);
      --bg-card-hover: #ffffff;
      --bg-surface: #f1f5f9;
      --border-color: rgba(0, 0, 0, 0.08);
      --border-focus: #2563eb;
      
      --text-primary: #0f172a;
      --text-secondary: #475569;
      --text-muted: #94a3b8;
      
      --accent-blue: #2563eb;
      --accent-blue-glow: rgba(37, 99, 235, 0.12);
      --accent-green: #059669;
      --accent-green-bg: rgba(5, 150, 105, 0.1);
      --accent-purple: #7c3aed;
      --accent-amber: #d97706;
      --accent-amber-bg: rgba(217, 119, 6, 0.1);
      
      --shadow-sm: 0 2px 6px rgba(0, 0, 0, 0.04);
      --shadow-md: 0 10px 25px rgba(0, 0, 0, 0.06);
      --shadow-glow: 0 0 15px var(--accent-blue-glow);
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    body {{
      font-family: var(--font-main);
      background-color: var(--bg-primary);
      color: var(--text-primary);
      line-height: 1.6;
      min-height: 100vh;
      padding-bottom: 60px;
    }}

    /* Header Nav */
    .top-bar {{
      position: sticky;
      top: 0;
      z-index: 50;
      background: var(--bg-card);
      backdrop-filter: blur(16px);
      border-bottom: 1px solid var(--border-color);
      padding: 12px 24px;
    }}

    .top-bar-inner {{
      max-width: 1400px;
      margin: 0 auto;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }}

    .brand-link {{
      display: flex;
      align-items: center;
      gap: 10px;
      text-decoration: none;
      color: var(--text-primary);
      font-weight: 700;
      font-size: 1.1rem;
    }}

    .back-btn {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 14px;
      background: var(--bg-surface);
      color: var(--text-primary);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      text-decoration: none;
      font-size: 0.88rem;
      font-weight: 600;
      transition: var(--transition);
    }}

    .back-btn:hover {{
      background: var(--accent-blue);
      color: #fff;
      border-color: var(--accent-blue);
      box-shadow: var(--shadow-glow);
      transform: translateX(-2px);
    }}

    .header-actions {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}

    .btn-action {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 7px 12px;
      background: var(--bg-surface);
      color: var(--text-secondary);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      text-decoration: none;
      font-size: 0.84rem;
      font-weight: 500;
      cursor: pointer;
      transition: var(--transition);
    }}

    .btn-action:hover {{
      color: var(--text-primary);
      background: var(--bg-card-hover);
      border-color: var(--border-focus);
    }}

    .btn-pdf {{
      background: var(--accent-blue-glow);
      color: var(--accent-blue);
      border-color: rgba(59, 130, 246, 0.3);
    }}
    .btn-pdf:hover {{
      background: var(--accent-blue);
      color: #fff;
    }}

    /* Main Container */
    .container {{
      max-width: 1400px;
      margin: 28px auto 0;
      padding: 0 24px;
    }}

    /* Hero Section */
    .hero-card {{
      background: linear-gradient(135deg, rgba(37, 99, 235, 0.1) 0%, rgba(139, 92, 246, 0.05) 100%), var(--bg-secondary);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-lg);
      padding: 28px;
      margin-bottom: 24px;
      box-shadow: var(--shadow-md);
      position: relative;
      overflow: hidden;
    }}

    .hero-card::before {{
      content: '';
      position: absolute;
      top: -50%;
      right: -20%;
      width: 400px;
      height: 400px;
      background: radial-gradient(circle, rgba(59, 130, 246, 0.15) 0%, transparent 70%);
      pointer-events: none;
    }}

    .hero-title-group {{
      margin-bottom: 20px;
    }}

    .hero-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 10px;
      background: var(--accent-green-bg);
      color: var(--accent-green);
      border-radius: 999px;
      font-size: 0.78rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 10px;
    }}

    .hero-title {{
      font-size: 1.75rem;
      font-weight: 800;
      color: var(--text-primary);
      margin-bottom: 6px;
    }}

    .hero-subtitle {{
      color: var(--text-secondary);
      font-size: 0.95rem;
      font-family: var(--font-mono);
    }}

    /* Stats Grid */
    .stats-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
      margin-top: 20px;
    }}

    .stat-box {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      padding: 16px 20px;
      backdrop-filter: blur(8px);
    }}

    .stat-label {{
      font-size: 0.8rem;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      font-weight: 600;
      margin-bottom: 4px;
    }}

    .stat-value {{
      font-size: 1.6rem;
      font-weight: 800;
      color: var(--text-primary);
      display: flex;
      align-items: baseline;
      gap: 6px;
    }}

    .stat-value.highlight {{
      color: var(--accent-blue);
    }}

    .stat-value.success {{
      color: var(--accent-green);
    }}

    /* Controls Bar */
    .controls-bar {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      padding: 14px 20px;
      margin-bottom: 24px;
    }}

    .search-box {{
      flex: 1;
      min-width: 280px;
      position: relative;
    }}

    .search-icon {{
      position: absolute;
      left: 14px;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text-muted);
      pointer-events: none;
    }}

    .search-input {{
      width: 100%;
      padding: 10px 14px 10px 42px;
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      color: var(--text-primary);
      font-size: 0.92rem;
      font-family: inherit;
      outline: none;
      transition: var(--transition);
    }}

    .search-input:focus {{
      border-color: var(--border-focus);
      box-shadow: 0 0 0 3px var(--accent-blue-glow);
    }}

    .filter-count {{
      font-size: 0.88rem;
      color: var(--text-secondary);
      font-weight: 600;
    }}

    /* Segments List */
    .segments-list {{
      display: flex;
      flex-direction: column;
      gap: 16px;
    }}

    .segment-card {{
      background: var(--bg-card);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      padding: 22px;
      transition: var(--transition);
      position: relative;
    }}

    .segment-card:hover {{
      background: var(--bg-card-hover);
      border-color: rgba(59, 130, 246, 0.35);
      box-shadow: var(--shadow-md);
      transform: translateY(-2px);
    }}

    .card-top {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 14px;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--border-color);
    }}

    .card-meta-left {{
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }}

    .seg-num-badge {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 28px;
      height: 28px;
      background: var(--bg-surface);
      color: var(--text-secondary);
      border-radius: 50%;
      font-size: 0.82rem;
      font-weight: 700;
      border: 1px solid var(--border-color);
    }}

    .file-badge {{
      font-family: var(--font-mono);
      font-size: 0.85rem;
      font-weight: 600;
      padding: 4px 10px;
      background: var(--bg-surface);
      color: var(--text-primary);
      border-radius: var(--radius-sm);
      border: 1px solid var(--border-color);
    }}

    .case-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 0.88rem;
      font-weight: 700;
      color: var(--accent-blue);
      background: var(--accent-blue-glow);
      padding: 4px 10px;
      border-radius: var(--radius-sm);
      text-decoration: none;
      transition: var(--transition);
    }}

    .case-badge:hover {{
      background: var(--accent-blue);
      color: #fff;
      transform: translateY(-1px);
    }}

    .conf-badge {{
      display: inline-flex;
      align-items: center;
      gap: 5px;
      font-size: 0.82rem;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 999px;
      background: var(--accent-green-bg);
      color: var(--accent-green);
    }}

    /* Category Breadcrumbs */
    .category-section {{
      margin-bottom: 16px;
    }}

    .cat-code-pill {{
      display: inline-block;
      font-family: var(--font-mono);
      font-size: 0.8rem;
      font-weight: 700;
      padding: 2px 8px;
      background: rgba(139, 92, 246, 0.15);
      color: var(--accent-purple);
      border: 1px solid rgba(139, 92, 246, 0.3);
      border-radius: 4px;
      margin-bottom: 6px;
    }}

    .breadcrumbs {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 6px;
      font-size: 0.88rem;
      color: var(--text-secondary);
      line-height: 1.4;
    }}

    .crumb-sep {{
      color: var(--text-muted);
      font-size: 0.75rem;
    }}

    .crumb-leaf {{
      color: var(--text-primary);
      font-weight: 700;
    }}

    /* Legal Position / Thesis */
    .thesis-box {{
      background: var(--bg-surface);
      border-left: 3px solid var(--accent-blue);
      border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
      padding: 14px 16px;
      margin-bottom: 14px;
      font-size: 0.94rem;
      color: var(--text-primary);
      line-height: 1.55;
    }}

    .thesis-label {{
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--accent-blue);
      font-weight: 700;
      margin-bottom: 4px;
    }}

    /* LLM Reasoning */
    .reasoning-box {{
      font-size: 0.84rem;
      color: var(--text-muted);
      line-height: 1.5;
      padding: 8px 12px;
      background: rgba(255, 255, 255, 0.02);
      border-radius: var(--radius-sm);
      display: flex;
      align-items: flex-start;
      gap: 8px;
    }}

    .reasoning-box svg {{
      flex-shrink: 0;
      margin-top: 3px;
      color: var(--accent-amber);
    }}

    /* Details Toggle */
    .details-toggle {{
      margin-top: 12px;
    }}

    details summary {{
      font-size: 0.82rem;
      font-weight: 600;
      color: var(--text-muted);
      cursor: pointer;
      user-select: none;
      transition: var(--transition);
    }}

    details summary:hover {{
      color: var(--text-primary);
    }}

    .fulltext-content {{
      margin-top: 10px;
      padding: 12px;
      background: var(--bg-primary);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      font-size: 0.85rem;
      color: var(--text-secondary);
      white-space: pre-wrap;
      font-family: inherit;
    }}

    /* Empty state */
    .no-results {{
      text-align: center;
      padding: 60px 20px;
      background: var(--bg-card);
      border-radius: var(--radius-md);
      border: 1px solid var(--border-color);
      color: var(--text-muted);
      display: none;
    }}
  </style>
</head>
<body>

  <!-- Top Navigation -->
  <header class="top-bar">
    <div class="top-bar-inner">
      <a href="/digest.html" class="back-btn" title="Повернутися до реєстру дайджестів">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>
        <span>Реєстр дайджестів</span>
      </a>

      <div class="header-actions">
        <a href="{pdf_url}" target="_blank" class="btn-action btn-pdf" title="Відкрити оригінальний PDF">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          <span>Оригінал PDF</span>
        </a>
        <button id="theme-toggle-btn" class="btn-action" title="Перемкнути тему">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
        </button>
      </div>
    </div>
  </header>

  <main class="container">
    
    <!-- Hero Summary -->
    <section class="hero-card">
      <div class="hero-title-group">
        <span class="hero-badge">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
          Взаємозв'язок із класифікацією
        </span>
        <h1 class="hero-title">{html.escape(doc_name)}</h1>
        <p class="hero-subtitle">Семантичний мапінг та класифікація правових позицій судової практики</p>
      </div>

      <div class="stats-grid">
        <div class="stat-box">
          <div class="stat-label">Замаплено сегментів</div>
          <div class="stat-value highlight">{total_segments}</div>
        </div>
        <div class="stat-box">
          <div class="stat-label">Середня впевненість</div>
          <div class="stat-value success">{avg_conf * 100:.1f}%</div>
        </div>
        <div class="stat-box">
          <div class="stat-label">Охоплено рубрик</div>
          <div class="stat-value">{unique_categories}</div>
        </div>
      </div>
    </section>

    <!-- Search & Filter Controls -->
    <div class="controls-bar">
      <div class="search-box">
        <svg class="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        <input type="text" id="filter-input" class="search-input" placeholder="Пошук за номером справи, текстом позиції, кодом рубрики або файлом...">
      </div>
      <div id="filter-count" class="filter-count">Показано {total_segments} із {total_segments}</div>
    </div>

    <!-- Segments List -->
    <div id="segments-container" class="segments-list">
"""

    for s in segments_data:
        case_html = ""
        if s["reyestr_url"]:
            case_html = f"""<a href="{html.escape(s['reyestr_url'])}" target="_blank" rel="noopener" class="case-badge" title="Відкрити судове рішення в ЄДРСР">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                <span>{html.escape(s['case_number'])}</span>
            </a>"""
        else:
            case_html = f"""<span class="file-badge">{html.escape(s['case_number'])}</span>"""

        crumbs_html = ""
        for c_idx, crumb in enumerate(s["path_crumbs"]):
            is_last = (c_idx == len(s["path_crumbs"]) - 1)
            cls = "crumb-leaf" if is_last else "crumb"
            crumbs_html += f'<span class="{cls}">{html.escape(crumb)}</span>'
            if not is_last:
                crumbs_html += '<span class="crumb-sep">›</span>'

        conf_pct = f"{s['confidence'] * 100:.0f}%"

        html_content += f"""
      <article class="segment-card" data-search="{html.escape((s['filename'] + ' ' + s['case_number'] + ' ' + s['category_code'] + ' ' + s['category_name'] + ' ' + s['teza'] + ' ' + s['reasoning']).lower())}">
        <div class="card-top">
          <div class="card-meta-left">
            <span class="seg-num-badge">{s['idx']}</span>
            <span class="file-badge">{html.escape(s['filename'])}</span>
            {case_html}
          </div>
          <div class="conf-badge">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
            <span>{conf_pct} точність</span>
          </div>
        </div>

        <div class="category-section">
          <span class="cat-code-pill">{html.escape(s['category_code'])}</span>
          <div class="breadcrumbs">
            {crumbs_html}
          </div>
        </div>

        <div class="thesis-box">
          <div class="thesis-label">Правова позиція / Теза:</div>
          <div>{html.escape(s['teza'] or s['summary'])}</div>
        </div>

        {f'''<div class="reasoning-box">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
          <div>{html.escape(s['reasoning'])}</div>
        </div>''' if s['reasoning'] else ''}

        <div class="details-toggle">
          <details>
            <summary>Показати повний нормалізований текст сегмента</summary>
            <div class="fulltext-content">{html.escape(s['full_text'])}</div>
          </details>
        </div>
      </article>
"""

    html_content += f"""
    </div>

    <div id="no-results" class="no-results">
      <h3>За вказаним пошуковим запитом нічого не знайдено</h3>
      <p style="margin-top: 8px;">Спробуйте змінити ключові слова або очистити пошуковий рядок.</p>
    </div>

  </main>

  <script>
    // Theme toggle
    const themeBtn = document.getElementById('theme-toggle-btn');
    themeBtn.addEventListener('click', () => {{
      const current = document.documentElement.getAttribute('data-theme') || 'dark';
      const next = current === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('app_theme', next);
    }});

    // Live search filter
    const searchInput = document.getElementById('filter-input');
    const cards = document.querySelectorAll('.segment-card');
    const countBadge = document.getElementById('filter-count');
    const noResults = document.getElementById('no-results');
    const totalCount = {total_segments};

    searchInput.addEventListener('input', (e) => {{
      const query = e.target.value.trim().toLowerCase();
      let visible = 0;

      cards.forEach(card => {{
        const text = card.getAttribute('data-search') || '';
        if (!query || text.includes(query)) {{
          card.style.display = 'block';
          visible++;
        }} else {{
          card.style.display = 'none';
        }}
      }});

      countBadge.textContent = `Показано ${{visible}} із ${{totalCount}}`;
      noResults.style.display = (visible === 0) ? 'block' : 'none';
    }});
  </script>
</body>
</html>
"""
    out_file = CORRELATION_DIR / f"{doc_name}.html"
    out_file.write_text(html_content, encoding="utf-8")
    
    # Also save in public/correlation/ for direct static serving
    pub_corr = Path("public/correlation")
    pub_corr.mkdir(parents=True, exist_ok=True)
    (pub_corr / f"{doc_name}.html").write_text(html_content, encoding="utf-8")

    print(f"✅ Згенеровано correlation сторінку: {out_file} ({total_segments} сегментів)")
    return str(out_file)


def build_all():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT substr(file_path, 20, instr(substr(file_path, 20), '/') - 1) as doc_name
        FROM mapped_segments
        WHERE file_path LIKE 'documents/segments/%'
    """)
    doc_names = [r[0] for r in cur.fetchall() if r[0]]
    print(f"Будуємо correlation сторінки для {len(doc_names)} оглядів...")
    for d in doc_names:
        build_page_for_document(d, conn)
    conn.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        doc = sys.argv[1]
        conn = sqlite3.connect(DB_PATH)
        build_page_for_document(doc, conn)
        conn.close()
    else:
        build_all()
