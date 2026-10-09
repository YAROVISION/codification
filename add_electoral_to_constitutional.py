#!/usr/bin/env python3
"""
Скрипт додавання Виборчого кодексу України (код 10 20) до категорії 10 'Конституційне право':
1. Парсинг офіційної структури Виборчого кодексу України (Закон № 396-IX).
2. Побудова структури: 4 Книги та 42 Розділи з конкретизацією до статей (не включаючи окремі статті).
3. Додавання підрозділу '10 20' до категорії '10' поруч із '10 10' (Конституція України).
4. Оновлення всіх 5 джерел даних:
   - data/classifier.json
   - data/classifier_flat.json
   - data/classifier.sqlite (таблиці categories та categories_fts)
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
ELECTORAL_PRINT_HTML = SCRATCH_DIR / "electoral_print.html"

BASE_ELECTORAL_URL = "https://zakon.rada.gov.ua/laws/show/396-20"

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
        'президента україни': 'Президента України',
        'президент україни': 'Президент України',
        'президентом україни': 'Президентом України',
        'верховна рада україни': 'Верховна Рада України',
        'верховної ради україни': 'Верховної Ради України',
        'народних депутатів україни': 'народних депутатів України',
        'народного депутата україни': 'народного депутата України',
    }
    for k, v in replacements.items():
        res = re.sub(r'\b' + re.escape(k) + r'\b', v, res, flags=re.IGNORECASE)
    return res

def format_title(text: str) -> str:
    text = text.strip()
    if 'ПРИКІНЦЕВІ' in text.upper() and 'ПЕРЕХІДНІ' in text.upper():
        m_roz = re.match(r'^(Розділ\s+[IVXLCDM]+)\.?\s*(.*)$', text, re.IGNORECASE)
        if m_roz:
            return f'{m_roz.group(1)}. Прикінцеві та перехідні положення'
        return 'Прикінцеві та перехідні положення'
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
    return smart_title(text)

def make_search_url(query: str) -> str:
    encoded = urllib.parse.quote(query)
    return f"https://zakon.rada.gov.ua/laws/main/find?find_text={encoded}"

def extract_electoral_code_tree():
    with open(ELECTORAL_PRINT_HTML, 'r', encoding='utf-8', errors='ignore') as f:
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
        if any(clean_p.startswith(k) for k in ['КНИГА', 'Книга', 'Розділ', 'РОЗДІЛ']):
            matches.append((anchor, clean_p))

    raw_tree = {
        'title': 'Виборчий кодекс України',
        'kind': 'code',
        'anchor': '',
        'children': []
    }

    current_book = None
    for anchor, raw in matches:
        title = format_title(raw)
        if raw.startswith('КНИГА') or raw.startswith('Книга'):
            book_node = {'title': title, 'kind': 'book', 'anchor': anchor, 'children': []}
            raw_tree['children'].append(book_node)
            current_book = book_node
        elif raw.startswith('Розділ') or raw.startswith('РОЗДІЛ'):
            section_node = {'title': title, 'kind': 'section', 'anchor': anchor, 'children': []}
            if current_book is not None:
                current_book['children'].append(section_node)
            else:
                raw_tree['children'].append(section_node)

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
    print("[*] Парсинг структури Виборчого кодексу України...")
    raw_electoral_tree = extract_electoral_code_tree()
    electoral_node = convert_to_classifier_node(
        raw_electoral_tree, "10 20", 2, BASE_ELECTORAL_URL, "Виборчий кодекс України"
    )

    # 1. Оновлення classifier.json
    json_path = DATA_DIR / "classifier.json"
    print(f"[*] Завантаження {json_path}...")
    with open(json_path, "r", encoding="utf-8") as f:
        classifier_tree = json.load(f)

    cat_10 = None
    for cat in classifier_tree:
        if cat["code"] == "10":
            cat_10 = cat
            break

    if not cat_10:
        raise ValueError("Категорію 10 не знайдено в classifier.json")

    # Зберігаємо існуючі діти крім попереднього 10 20 якщо був
    existing_children = [c for c in cat_10.get("children", []) if c["code"] != "10 20"]
    existing_children.append(electoral_node)
    
    # Сортування дітей за кодом
    def sort_code(c):
        return [int(x) if x.isdigit() else x for x in c["code"].split()]
    existing_children.sort(key=sort_code)
    
    cat_10["children"] = existing_children

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

    print(f"\n[SUCCESS] Успішно додано категорію 10 20 'Виборчий кодекс України' (4 книги, 42 розділи). Всього {len(flat_all)} рубрик у класифікаторі!")

if __name__ == "__main__":
    update_all()
