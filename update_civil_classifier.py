#!/usr/bin/env python3
"""
Скрипт реструктуризації категорії 30 'Цивільне законодавство':
1. Підрозділ 30 10: 'Цивільний кодекс України' (структура ЦК України).
2. Підрозділ 30 20: 'Цивільний процесуальний кодекс України' (структура ЦПК України).
3. Підрозділ 30 30: 'Кодекс України з процедур банкрутства' (структура КУзПБ).
4. Підрозділ 30 40: 'Господарський процесуальний кодекс України' (структура ГПК України).
5. Побудова повної структури з конкретизацією до статей кодексів (книги, розділи, підрозділи, глави, параграфи §, без окремих статей).
6. Генерація точних прямих якірних посилань на zakon.rada.gov.ua та пошукових запитів.
7. Оновлення всіх форматів даних:
   - data/classifier.json
   - data/classifier_flat.json
   - data/classifier.sqlite (categories, categories_fts, оновлення mapped_segments)
   - data/classifier.csv
   - data/classifier.md
"""

import os
import sys
import re
import json
import csv
import sqlite3
import urllib.parse
from datetime import datetime
from pathlib import Path

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SCRATCH_DIR = BASE_DIR / "scratch"
CC_PRINT_HTML = SCRATCH_DIR / "cc_print.html"
CPC_PRINT_HTML = SCRATCH_DIR / "cpc_print.html"
BANKRUPTCY_PRINT_HTML = SCRATCH_DIR / "bankruptcy_print.html"
GPC_PRINT_HTML = SCRATCH_DIR / "gpc_print.html"

BASE_CC_URL = "https://zakon.rada.gov.ua/laws/show/435-15"
BASE_CPC_URL = "https://zakon.rada.gov.ua/laws/show/1618-15"
BASE_BANKRUPTCY_URL = "https://zakon.rada.gov.ua/laws/show/2597-19"
BASE_GPC_URL = "https://zakon.rada.gov.ua/laws/show/1798-12"

def smart_title(s: str) -> str:
    parts = s.split('.')
    new_parts = []
    for p in parts:
        p_str = p.strip()
        if not p_str:
            continue
        p_str = p_str[0].upper() + p_str[1:].lower()
        new_parts.append(p_str)
    res = '. '.join(new_parts)
    replacements = {
        'україни': 'України',
        'україні': 'Україні',
        'україна': 'Україна',
        'автономної республіки крим': 'Автономної Республіки Крим',
        'автономна республіка крим': 'Автономна Республіка Крим',
        'єс': 'ЄС',
    }
    for k, v in replacements.items():
        res = re.sub(r'\b' + re.escape(k) + r'\b', v, res, flags=re.IGNORECASE)
    return res

def format_title(text: str) -> str:
    text = text.strip()
    if text.startswith('§'):
        m = re.match(r'^(§\s*\d+\.?)\s*(.*)$', text)
        if m:
            prefix = m.group(1)
            if not prefix.endswith('.'):
                prefix += '.'
            rest = smart_title(m.group(2))
            return f'{prefix} {rest}'
        return text
    if 'ПРИКІНЦЕВІ' in text.upper() and 'ПЕРЕХІДНІ' in text.upper():
        return 'Прикінцеві та перехідні положення'
    if 'ПРИКІНЦЕВІ' in text.upper():
        m_roz = re.match(r'^(Розділ\s+[IVXLCDM]+)\.?\s*(.*)$', text, re.IGNORECASE)
        if m_roz:
            return f'{m_roz.group(1)}. Прикінцеві положення'
        return 'Прикінцеві положення'
    if 'ПЕРЕХІДНІ' in text.upper():
        m_roz = re.match(r'^(Розділ\s+[IVXLCDM]+)\.?\s*(.*)$', text, re.IGNORECASE)
        if m_roz:
            return f'{m_roz.group(1)}. Перехідні положення'
        return 'Перехідні положення'
    m_kn = re.match(r'^(КНИГА\s+[^\s\.]+)\.?\s*(.*)$', text, re.IGNORECASE)
    if m_kn:
        prefix = m_kn.group(1).capitalize()
        rest = smart_title(m_kn.group(2))
        return f'{prefix}. {rest}'
    m_roz = re.match(r'^(Розділ\s+[IVXLCDM]+)\.?\s*(.*)$', text, re.IGNORECASE)
    if m_roz:
        prefix = m_roz.group(1)
        rest = smart_title(m_roz.group(2))
        return f'{prefix}. {rest}'
    m_pid = re.match(r'^(Підрозділ\s+\d+)\.?\s*(.*)$', text, re.IGNORECASE)
    if m_pid:
        prefix = m_pid.group(1)
        rest = smart_title(m_pid.group(2))
        return f'{prefix}. {rest}'
    m_gl = re.match(r'^(Глава\s+[\d\- \.]+)\s+(.*)$', text, re.IGNORECASE)
    if m_gl:
        prefix = m_gl.group(1).strip().rstrip('.')
        prefix = re.sub(r'\s+', '', prefix)
        prefix = f'Глава {prefix[5:]}'
        rest = smart_title(m_gl.group(2))
        return f'{prefix}. {rest}'
    return text

def get_kind(text: str) -> str:
    if text.startswith('КНИГА') or text.startswith('Книга'): return 'book'
    if text.startswith('Розділ') or text.startswith('РОЗДІЛ'): return 'section'
    if text.startswith('Підрозділ') or text.startswith('ПІДРОЗДІЛ'): return 'subsection'
    if text.startswith('Глава') or text.startswith('ГЛАВА'): return 'chapter'
    if text.startswith('§'): return 'paragraph'
    if 'ПРИКІНЦЕВІ' in text.upper() or 'ПЕРЕХІДНІ' in text.upper(): return 'final'
    return 'unknown'

def make_search_url(query: str) -> str:
    encoded = urllib.parse.quote(query)
    return f"https://zakon.rada.gov.ua/laws/main/find?find_text={encoded}"

def extract_civil_code_tree():
    with open(CC_PRINT_HTML, 'r', encoding='utf-8', errors='ignore') as f:
        html = f.read()

    pattern = re.compile(
        r'<p[^>]*>\s*(?:<a\s+name=[\"\'](n\d+)[\"\']\s*></a>\s*)?(.*?)</p>',
        re.DOTALL
    )

    matches = []
    for m in pattern.finditer(html):
        anchor = m.group(1) or ''
        p_body = m.group(2)
        clean_p = re.sub(r'<[^>]+>', ' ', p_body)
        clean_p = ' '.join(clean_p.split())
        if any(clean_p.startswith(k) for k in [
            'КНИГА', 'Розділ', 'РОЗДІЛ', 'Підрозділ', 'ПІДРОЗДІЛ', 'Глава', 'ГЛАВА', '§', 'ПРИКІНЦЕВІ', 'Прикінцеві'
        ]):
            if '{Параграф' not in clean_p:
                matches.append((anchor, clean_p))

    raw_tree = {
        'title': 'Цивільний кодекс України',
        'kind': 'code',
        'anchor': '',
        'children': []
    }

    current_book = None
    current_section = None
    current_subsection = None
    current_chapter = None

    for anchor, raw in matches:
        kind = get_kind(raw)
        title = format_title(raw)
        node = {'title': title, 'kind': kind, 'anchor': anchor, 'children': []}
        
        if kind == 'book' or kind == 'final':
            raw_tree['children'].append(node)
            current_book = node
            current_section = None
            current_subsection = None
            current_chapter = None
        elif kind == 'section':
            current_book['children'].append(node)
            current_section = node
            current_subsection = None
            current_chapter = None
        elif kind == 'subsection':
            target = current_section if current_section else current_book
            target['children'].append(node)
            current_subsection = node
            current_chapter = None
        elif kind == 'chapter':
            if current_subsection:
                current_subsection['children'].append(node)
            elif current_section:
                current_section['children'].append(node)
            elif current_book:
                current_book['children'].append(node)
            else:
                raw_tree['children'].append(node)
            current_chapter = node
        elif kind == 'paragraph':
            current_chapter['children'].append(node)

    return raw_tree

def extract_cpc_tree():
    with open(CPC_PRINT_HTML, 'r', encoding='utf-8', errors='ignore') as f:
        html = f.read()

    pattern = re.compile(
        r'<p[^>]*>\s*(?:<a\s+name=[\"\'](n\d+)[\"\']\s*></a>\s*)?(.*?)</p>',
        re.DOTALL
    )

    matches = []
    for m in pattern.finditer(html):
        anchor = m.group(1) or ''
        p_body = m.group(2)
        clean_p = re.sub(r'<[^>]+>', ' ', p_body)
        clean_p = ' '.join(clean_p.split())
        if any(clean_p.startswith(k) for k in [
            'Розділ', 'РОЗДІЛ', 'Підрозділ', 'ПІДРОЗДІЛ', 'Глава', 'ГЛАВА', '§', 'ПРИКІНЦЕВІ', 'Прикінцеві', 'ПЕРЕХІДНІ', 'Перехідні'
        ]):
            if '{Параграф' not in clean_p:
                matches.append((anchor, clean_p))

    raw_tree = {
        'title': 'Цивільний процесуальний кодекс України',
        'kind': 'code',
        'anchor': '',
        'children': []
    }

    current_section = None
    current_subsection = None
    current_chapter = None

    for anchor, raw in matches:
        kind = get_kind(raw)
        title = format_title(raw)
        node = {'title': title, 'kind': kind, 'anchor': anchor, 'children': []}
        
        if kind == 'section' or kind == 'final':
            raw_tree['children'].append(node)
            current_section = node
            current_subsection = None
            current_chapter = None
        elif kind == 'subsection':
            target = current_section if current_section else raw_tree
            target['children'].append(node)
            current_subsection = node
            current_chapter = None
        elif kind == 'chapter':
            if current_subsection:
                current_subsection['children'].append(node)
            elif current_section:
                current_section['children'].append(node)
            else:
                raw_tree['children'].append(node)
            current_chapter = node
        elif kind == 'paragraph':
            current_chapter['children'].append(node)

    return raw_tree

def extract_bankruptcy_tree():
    with open(BANKRUPTCY_PRINT_HTML, 'r', encoding='utf-8', errors='ignore') as f:
        html = f.read()

    pattern = re.compile(
        r'<p[^>]*>\s*(?:<a\s+name=[\"\'](n\d+)[\"\']\s*></a>\s*)?(.*?)</p>',
        re.DOTALL
    )

    matches = []
    for m in pattern.finditer(html):
        anchor = m.group(1) or ''
        p_body = m.group(2)
        clean_p = re.sub(r'<[^>]+>', ' ', p_body)
        clean_p = ' '.join(clean_p.split())
        if any(clean_p.startswith(k) for k in [
            'КНИГА', 'Книга', 'Розділ', 'РОЗДІЛ', 'Підрозділ', 'ПІДРОЗДІЛ', 'Глава', 'ГЛАВА', '§', 'ПРИКІНЦЕВІ', 'Прикінцеві', 'ПЕРЕХІДНІ', 'Перехідні'
        ]):
            if '{Параграф' not in clean_p:
                matches.append((anchor, clean_p))

    raw_tree = {
        'title': 'Кодекс України з процедур банкрутства',
        'kind': 'code',
        'anchor': '',
        'children': []
    }

    current_book = None
    for anchor, raw in matches:
        kind = get_kind(raw)
        title = format_title(raw)
        node = {'title': title, 'kind': kind, 'anchor': anchor, 'children': []}
        if kind == 'book' or kind == 'final':
            raw_tree['children'].append(node)
            current_book = node
        elif kind == 'section':
            if current_book:
                current_book['children'].append(node)
            else:
                raw_tree['children'].append(node)

    return raw_tree

def extract_gpc_tree():
    with open(GPC_PRINT_HTML, 'r', encoding='utf-8', errors='ignore') as f:
        html = f.read()

    pattern = re.compile(
        r'<p[^>]*>\s*(?:<a\s+name=[\"\'](n\d+)[\"\']\s*></a>\s*)?(.*?)</p>',
        re.DOTALL
    )

    matches = []
    for m in pattern.finditer(html):
        anchor = m.group(1) or ''
        p_body = m.group(2)
        clean_p = re.sub(r'<[^>]+>', ' ', p_body)
        clean_p = ' '.join(clean_p.split())
        if any(clean_p.startswith(k) for k in [
            'Розділ', 'РОЗДІЛ', 'Підрозділ', 'ПІДРОЗДІЛ', 'Глава', 'ГЛАВА', '§', 'ПРИКІНЦЕВІ', 'Прикінцеві', 'ПЕРЕХІДНІ', 'Перехідні'
        ]):
            if '{Параграф' not in clean_p:
                matches.append((anchor, clean_p))

    raw_tree = {
        'title': 'Господарський процесуальний кодекс України',
        'kind': 'code',
        'anchor': '',
        'children': []
    }

    current_section = None
    current_subsection = None
    current_chapter = None

    for anchor, raw in matches:
        kind = get_kind(raw)
        title = format_title(raw)
        node = {'title': title, 'kind': kind, 'anchor': anchor, 'children': []}
        
        if kind == 'section' or kind == 'final':
            raw_tree['children'].append(node)
            current_section = node
            current_subsection = None
            current_chapter = None
        elif kind == 'subsection':
            target = current_section if current_section else raw_tree
            target['children'].append(node)
            current_subsection = node
            current_chapter = None
        elif kind == 'chapter':
            if current_subsection:
                current_subsection['children'].append(node)
            elif current_section:
                current_section['children'].append(node)
            else:
                raw_tree['children'].append(node)
            current_chapter = node
        elif kind == 'paragraph':
            current_chapter['children'].append(node)

    return raw_tree

def convert_to_classifier_node(raw_node, code_prefix, level, base_url, code_title):
    title = raw_node['title']
    anchor = raw_node.get('anchor', '')
    direct_url = f'{base_url}#{anchor}' if anchor else base_url
    search_q = f'{code_title} {title}'
    
    node = {
        'code': code_prefix,
        'level': level,
        'name': title,
        'clean_name': title,
        'cross_references': [],
        'branch_url': make_search_url(search_q),
        'direct_url': direct_url,
        'total_docs_count': 0,
        'direct_docs_count': 0,
        'children': []
    }
    
    for i, child_raw in enumerate(raw_node.get('children', [])):
        child_code = f'{code_prefix} {(i + 1) * 10}'
        child_node = convert_to_classifier_node(child_raw, child_code, level + 1, base_url, code_title)
        node['children'].append(child_node)
        
    return node

def flatten_tree(nodes, parent_code="", parent_path_codes="", parent_path_names=""):
    flat = []
    for node in nodes:
        code = node["code"]
        name = node["clean_name"]
        
        path_codes = f"{parent_path_codes} / {code}" if parent_path_codes else code
        path_names = f"{parent_path_names} / {name}" if parent_path_names else name
        
        children = node.get("children", [])
        has_children = len(children) > 0
        children_count = len(children)
        
        flat_item = {
            "code": code,
            "level": node["level"],
            "name": node["name"],
            "clean_name": name,
            "parent_code": parent_code,
            "path_codes": path_codes,
            "path_names": path_names,
            "cross_references": node.get("cross_references", []),
            "branch_url": node.get("branch_url", ""),
            "direct_url": node.get("direct_url", ""),
            "total_docs_count": node.get("total_docs_count", 0),
            "direct_docs_count": node.get("direct_docs_count", 0),
            "has_children": has_children,
            "children_count": children_count
        }
        flat.append(flat_item)
        
        if has_children:
            flat.extend(flatten_tree(children, code, path_codes, path_names))
            
    return flat

def update_all():
    print("[*] Парсинг структури Цивільного кодексу України...")
    raw_cc_tree = extract_civil_code_tree()
    cc_node = convert_to_classifier_node(raw_cc_tree, "30 10", 2, BASE_CC_URL, "Цивільний кодекс України")
    
    print("[*] Парсинг структури Цивільного процесуального кодексу України...")
    raw_cpc_tree = extract_cpc_tree()
    cpc_node = convert_to_classifier_node(raw_cpc_tree, "30 20", 2, BASE_CPC_URL, "Цивільний процесуальний кодекс України")

    print("[*] Парсинг структури Кодексу України з процедур банкрутства...")
    raw_bankr_tree = extract_bankruptcy_tree()
    bankr_node = convert_to_classifier_node(raw_bankr_tree, "30 30", 2, BASE_BANKRUPTCY_URL, "Кодекс України з процедур банкрутства")

    print("[*] Парсинг структури Господарського процесуального кодексу України...")
    raw_gpc_tree = extract_gpc_tree()
    gpc_node = convert_to_classifier_node(raw_gpc_tree, "30 40", 2, BASE_GPC_URL, "Господарський процесуальний кодекс України")

    # 1. Оновлення classifier.json
    json_path = DATA_DIR / "classifier.json"
    print(f"[*] Завантаження {json_path}...")
    with open(json_path, "r", encoding="utf-8") as f:
        classifier_tree = json.load(f)

    cat_30 = None
    for cat in classifier_tree:
        if cat["code"] == "30":
            cat_30 = cat
            break

    if not cat_30:
        raise ValueError("Категорію 30 не знайдено в classifier.json")

    print(f"[+] Оновлення назви категорії 30: '{cat_30['clean_name']}' -> 'Цивільне і господарське право'")
    cat_30["name"] = "Цивільне і господарське право"
    cat_30["clean_name"] = "Цивільне і господарське право"
    cat_30["direct_url"] = BASE_CC_URL
    cat_30["branch_url"] = make_search_url("цивільне господарське право кодекс банкрутство процес")
    cat_30["children"] = [cc_node, cpc_node, bankr_node, gpc_node]

    print(f"[*] Збереження {json_path}...")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(classifier_tree, f, ensure_ascii=False, indent=2)

    # 2. Побудова flat списку
    print("[*] Генерація classifier_flat.json...")
    flat_all = flatten_tree(classifier_tree)
    
    flat_path = DATA_DIR / "classifier_flat.json"
    with open(flat_path, "w", encoding="utf-8") as f:
        json.dump(flat_all, f, ensure_ascii=False, indent=2)

    # 3. Оновлення SQLite бази
    sqlite_path = DATA_DIR / "classifier.sqlite"
    print(f"[*] Оновлення SQLite: {sqlite_path}...")
    conn = sqlite3.connect(sqlite_path)
    cur = conn.cursor()

    cur.execute("DELETE FROM categories")
    cur.execute("DELETE FROM categories_fts")

    for item in flat_all:
        cur.execute("""
            INSERT INTO categories (
                code, level, name, clean_name, parent_code,
                path_codes, path_names, cross_references,
                branch_url, direct_url,
                total_docs_count, direct_docs_count,
                has_children, children_count, semantic_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item["code"],
            item["level"],
            item["name"],
            item["clean_name"],
            item["parent_code"],
            item["path_codes"],
            item["path_names"],
            json.dumps(item["cross_references"], ensure_ascii=False),
            item["branch_url"],
            item["direct_url"],
            item["total_docs_count"],
            item["direct_docs_count"],
            1 if item["has_children"] else 0,
            item["children_count"],
            f"{item['clean_name']}. Шлях: {item['path_names']}. Код: {item['code']}."
        ))

        cur.execute("""
            INSERT INTO categories_fts (code, clean_name, path_names, semantic_text)
            VALUES (?, ?, ?, ?)
        """, (
            item["code"],
            item["clean_name"],
            item["path_names"],
            f"{item['clean_name']} {item['path_names']} {item['code']}"
        ))

    conn.commit()
    conn.close()

    # 4. CSV
    csv_path = DATA_DIR / "classifier.csv"
    print(f"[*] Збереження {csv_path}...")
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Код", "Рівень", "Назва", "Очищена назва", "Батьківський код",
            "Ієрархічний код", "Ієрархічний шлях", "Всього актів", "Прямих актів",
            "URL гілки", "URL прямий"
        ])
        for it in flat_all:
            writer.writerow([
                it["code"], it["level"], it["name"], it["clean_name"], it["parent_code"],
                it["path_codes"], it["path_names"], it["total_docs_count"], it["direct_docs_count"],
                it["branch_url"], it["direct_url"]
            ])

    # 5. Markdown
    md_path = DATA_DIR / "classifier.md"
    print(f"[*] Збереження {md_path}...")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Єдиний класифікатор правових актів України\n\n")
        f.write(f"- **Всього рубрик**: {len(flat_all):,}\n")
        f.write(f"- **Дата оновлення**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## Дерево класифікатора\n\n")
        for it in flat_all:
            indent = "  " * (it["level"] - 1)
            url = it["direct_url"] or it["branch_url"] or "#"
            f.write(f"{indent}- **`{it['code']}`** [{it['clean_name']}]({url})\n")

    print(f"\n[SUCCESS] Успішно оновлено категорію 30 'Цивільне законодавство' (30 10: ЦК, 30 20: ЦПК, 30 30: КУзПБ, 30 40: ГПК). Всього {len(flat_all)} рубрик у класифікаторі!")

if __name__ == "__main__":
    update_all()
