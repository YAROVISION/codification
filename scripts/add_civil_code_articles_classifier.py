#!/usr/bin/env python3
"""
Скрипт деталізації дерева класифікації правових актів України:
додавання статей Цивільного кодексу України (ЦК, 20 10) до конкретних статей включно.

Джерело:
- data/sources/ck_435-15.md

Синхронізує всі 5 форматів:
- data/classifier.json
- data/classifier_flat.json
- data/classifier.sqlite (categories, categories_fts)
- data/classifier.csv
- data/classifier.md
А також оновлює data/article_to_category_map.json ключем "ЦК".
"""

import os
import re
import sys
import json
import csv
import sqlite3
from datetime import datetime
from pathlib import Path

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

CK_URL = "https://zakon.rada.gov.ua/laws/show/435-15#Text"

def norm_roman(s: str) -> str:
    """Нормалізує змішані кириличні/латинські римські цифри."""
    table = str.maketrans('ІіХхСсМмВв', 'IiXxCcMmVv')
    return s.translate(table).upper()

def clean_art_title(raw_title: str) -> str:
    """Очищує назву статті від приміток, дат, номерів законів та квадратних дужок."""
    title = re.sub(r'\{[^\}]+\}', '', raw_title)
    title = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', title)
    title = ' '.join(title.split())
    title = title.strip(' .;:')
    if not title:
        title = "[Виключено / втратила чинність]"
    return title

def parse_ck_articles(node_map):
    """Парсить усі статті ЦК та прив'язує їх до кінцевих вузлів (глав, параграфів, прикінцевих положень)."""
    src_file = DATA_DIR / "sources" / "ck_435-15.md"
    with open(src_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    current_chap = None
    current_par = None
    is_final = False
    articles_by_node = {} # parent_code -> list of (art_num, title)

    for line in lines:
        l = re.sub(r'^https://[^\s]+\s*', '', line).strip()
        if not l:
            continue
            
        if re.search(r'Прикінцеві та перехідні положення', l, re.I):
            is_final = True
            current_chap = 'FINAL'
            current_par = None
            continue
            
        m_chap = re.match(r'^Глава\s+(\d+(?:\-[0-9]+)?)\.?\s*(.*)', l, re.I)
        if m_chap:
            current_chap = m_chap.group(1)
            current_par = None
            continue
            
        m_par = re.match(r'^(?:§|Параграф)\s*(\d+)\.?\s*(.*)', l, re.I)
        if m_par:
            current_par = m_par.group(1)
            continue
            
        m_art = re.match(r'^Стаття\s+(\d+[\-\w]*)\.\s*(.*)', l)
        if m_art:
            art_num = m_art.group(1)
            raw_title = m_art.group(2)
            title = clean_art_title(raw_title)
            
            target_code = node_map.get((current_chap, current_par))
            if not target_code:
                target_code = node_map.get((current_chap, None))
                
            if not target_code:
                raise ValueError(f"Не знайдено батьківський вузол для статті {art_num} ЦК ({current_chap}, {current_par})")
                
            if target_code not in articles_by_node:
                articles_by_node[target_code] = []
            articles_by_node[target_code].append((art_num, title))

    return articles_by_node

def flatten_tree(nodes, parent_code="", parent_path_codes="", parent_path_names=""):
    """Рекурсивне розгортання дерева категорій у плаский список."""
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

def main():
    json_path = DATA_DIR / "classifier.json"
    print(f"[*] Зчитування дерева з {json_path}...")
    with open(json_path, "r", encoding="utf-8") as f:
        classifier_tree = json.load(f)

    # 1. Знаходимо категорію 20 (Цивільне право) -> 20 10 (Цивільний кодекс України)
    root_20 = next((r for r in classifier_tree if r["code"] == "20"), None)
    if not root_20:
        raise ValueError("Не знайдено категорії 20 (Цивільне право) в класифікаторі!")

    node_20_10 = next((ch for ch in root_20.get("children", []) if ch["code"] == "20 10"), None)
    if not node_20_10:
        raise ValueError("Не знайдено підкатегорії 20 10 (Цивільний кодекс України)!")

    # 2. Будуємо мапу кінцевих вузлів ЦК: (chap_num, par_num) -> code
    node_map = {}
    code_to_node = {}

    def build_map(node, current_chap=None):
        name = node["name"]
        m_ch = re.search(r'Глава\s+(\d+(?:\-[0-9]+)?)', name)
        if m_ch:
            current_chap = m_ch.group(1)
            
        m_par = re.search(r'§\s*(\d+)', name)
        if m_par:
            par_num = m_par.group(1)
            node_map[(current_chap, par_num)] = node["code"]
            code_to_node[node["code"]] = node
            return

        children = node.get("children", [])
        if not children:
            if current_chap:
                node_map[(current_chap, None)] = node["code"]
                code_to_node[node["code"]] = node
            elif "Прикінцеві" in name:
                node_map[('FINAL', None)] = node["code"]
                code_to_node[node["code"]] = node
        else:
            for ch in children:
                build_map(ch, current_chap)

    build_map(node_20_10)
    print(f"[*] Знайдено {len(node_map)} кінцевих вузлів (глав/параграфів) у Цивільному кодексі України.")

    # 3. Парсимо всі статті ЦК
    articles_by_node = parse_ck_articles(node_map)

    # Завантажуємо наявну мапу статей
    map_path = DATA_DIR / "article_to_category_map.json"
    if map_path.exists():
        with open(map_path, "r", encoding="utf-8") as f:
            article_map = json.load(f)
    else:
        article_map = {}
    article_map["ЦК"] = {}

    # 4. Додаємо статті як дітей кінцевих вузлів
    total_ck_added = 0
    for parent_code, arts in articles_by_node.items():
        parent_node = code_to_node[parent_code]
        parent_level = parent_node["level"]

        new_children = []
        for i, (art_num, title) in enumerate(arts, 1):
            step = i * 10
            art_code = f"{parent_code} {step}"
            full_title = f"Стаття {art_num}. {title}"

            art_node = {
                "code": art_code,
                "level": parent_level + 1,
                "name": full_title,
                "clean_name": full_title,
                "parent_code": parent_code,
                "cross_references": [],
                "branch_url": CK_URL,
                "direct_url": CK_URL,
                "total_docs_count": 0,
                "direct_docs_count": 0,
                "children": []
            }
            new_children.append(art_node)
            article_map["ЦК"][art_num] = art_code
            total_ck_added += 1

        parent_node["children"] = new_children
        parent_node["has_children"] = len(new_children) > 0
        parent_node["children_count"] = len(new_children)

    print(f"[+] Додано {total_ck_added} статей до Цивільного кодексу України (20 10)")

    # 5. Збереження article_to_category_map.json
    print(f"[*] Збереження мапи статей: {map_path}...")
    with open(map_path, "w", encoding="utf-8") as f:
        json.dump(article_map, f, ensure_ascii=False, indent=2)

    # 6. Збереження classifier.json
    print(f"[*] Збереження {json_path}...")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(classifier_tree, f, ensure_ascii=False, indent=2)

    # 7. Генерація classifier_flat.json
    flat_path = DATA_DIR / "classifier_flat.json"
    print(f"[*] Генерація {flat_path}...")
    flat_all = flatten_tree(classifier_tree)
    with open(flat_path, "w", encoding="utf-8") as f:
        json.dump(flat_all, f, ensure_ascii=False, indent=2)

    # 8. Оновлення SQLite бази
    sqlite_path = DATA_DIR / "classifier.sqlite"
    print(f"[*] Оновлення SQLite бази: {sqlite_path}...")
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

    # 9. CSV
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

    # 10. Markdown
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

    print(f"\n[SUCCESS] Успішно оновлено всі 5 форматів класифікатора! Всього рубрик: {len(flat_all):,}")

if __name__ == "__main__":
    main()
