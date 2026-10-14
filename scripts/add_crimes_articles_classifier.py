#!/usr/bin/env python3
"""
Скрипт деталізації дерева класифікації правових актів України:
додавання статей Кримінального кодексу України (КК, 130 10) та
Кримінального процесуального кодексу України (КПК, 140 10) до конкретних статей включно.

Джерела:
- data/sources/kk_2341-14.md
- data/sources/kpk_4651-17.md

Синхронізує всі 5 форматів:
- data/classifier.json
- data/classifier_flat.json
- data/classifier.sqlite (categories, categories_fts)
- data/classifier.csv
- data/classifier.md
А також зберігає data/article_to_category_map.json для швидкого мапінгу в classify_segments.py.
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

KK_URL = "https://zakon.rada.gov.ua/laws/show/2341-14#Text"
KPK_URL = "https://zakon.rada.gov.ua/laws/show/4651-17#Text"

def norm_roman(s: str) -> str:
    """Нормалізує змішані кириличні/латинські римські цифри."""
    table = str.maketrans('ІіХхСсМмВв', 'IiXxCcMmVv')
    return s.translate(table).upper()

def clean_art_title(raw_title: str) -> str:
    """Очищує назву статті від приміток, дат, номерів законів та квадратних дужок."""
    # Прибираємо {Стаття...} або {Назва...}
    title = re.sub(r'\{[^\}]+\}', '', raw_title)
    # Прибираємо markdown посилання [Текст](url)
    title = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', title)
    title = ' '.join(title.split())
    title = title.strip(' .;:')
    if not title:
        title = "[Виключено / втратила чинність]"
    return title

def parse_kk_articles():
    """Парсить усі статті КК та прив'язує їх до розділів Загальної та Особливої частини."""
    src_file = DATA_DIR / "sources" / "kk_2341-14.md"
    with open(src_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    current_part = None
    current_sec = None
    articles_by_sec = {} # (part_name, sec_num) -> list of (art_num, title)

    for line in lines:
        l = re.sub(r'^https://[^\s]+\s*', '', line).strip()
        if not l:
            continue
        
        m_part = re.match(r'^(ЗАГАЛЬНА ЧАСТИНА|ОСОБЛИВА ЧАСТИНА)', l, re.I)
        if m_part:
            current_part = 'ZAHALNA' if 'ЗАГАЛЬНА' in m_part.group(1).upper() else 'OSOBLIVA'
            current_sec = None
            continue
            
        m_sec = re.match(r'^Розділ\s+([IVXLCDMІіХх]+(?:\-[0-9]+)?)\.?\s*(.*)', l, re.I)
        if m_sec:
            current_sec = norm_roman(m_sec.group(1))
            continue
            
        m_art = re.match(r'^Стаття\s+(\d+[\-\w]*)\.\s*(.*)', l)
        if m_art:
            art_num = m_art.group(1)
            raw_title = m_art.group(2)
            title = clean_art_title(raw_title)
            
            sec_key = current_sec
            if current_part == 'ZAHALNA' and sec_key == 'XIII-1':
                # ст. 91-1: якщо немає XIII-1, відносимо до XIII
                sec_key = 'XIII'
                
            key = (current_part, sec_key)
            if key not in articles_by_sec:
                articles_by_sec[key] = []
            articles_by_sec[key].append((art_num, title))

    return articles_by_sec

def parse_kpk_articles(kpk_map):
    """Парсить усі статті КПК та прив'язує їх до кінцевих вузлів (глав, параграфів, розділів)."""
    src_file = DATA_DIR / "sources" / "kpk_4651-17.md"
    with open(src_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    current_sec = None
    current_chap = None
    current_par = None
    articles_by_node = {} # parent_code -> list of (art_num, title)

    for line in lines:
        l = re.sub(r'^https://[^\s]+\s*', '', line).strip()
        if not l:
            continue
            
        m_sec = re.match(r'^Розділ\s+([IVXLCDMІіХх]+(?:\-[0-9]+)?)\.?\s*(.*)', l, re.I)
        if m_sec:
            current_sec = norm_roman(m_sec.group(1))
            current_chap = None
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
            
            parent_code = kpk_map.get((current_sec, current_chap, current_par))
            if not parent_code:
                parent_code = kpk_map.get((current_sec, current_chap, None))
            if not parent_code:
                parent_code = kpk_map.get((current_sec, None, None))
                
            if not parent_code:
                raise ValueError(f"Не знайдено батьківський вузол для статті {art_num} КПК ({current_sec}, {current_chap}, {current_par})")
                
            if parent_code not in articles_by_node:
                articles_by_node[parent_code] = []
            articles_by_node[parent_code].append((art_num, title))

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

    # 1. Знаходимо кореневі вузли 130 та 140
    root_130 = next((r for r in classifier_tree if r["code"] == "130"), None)
    root_140 = next((r for r in classifier_tree if r["code"] == "140"), None)

    if not root_130 or not root_140:
        raise ValueError("Не знайдено категорії 130 або 140 в класифікаторі!")

    node_130_10 = next((ch for ch in root_130.get("children", []) if ch["code"] == "130 10"), None)
    node_140_10 = next((ch for ch in root_140.get("children", []) if ch["code"] == "140 10"), None)

    if not node_130_10 or not node_140_10:
        raise ValueError("Не знайдено підкатегорії 130 10 (КК) або 140 10 (КПК)!")

    # Мапа розділів КК
    kk_sec_map = {}
    for part in node_130_10.get("children", []):
        part_key = 'ZAHALNA' if 'Загальна' in part['name'] else 'OSOBLIVA'
        for sec in part.get("children", []):
            m = re.search(r'Розділ\s+([IVXLCDMІіХх]+(?:\-[0-9]+)?)', sec['name'])
            sec_num = norm_roman(m.group(1)) if m else None
            kk_sec_map[(part_key, sec_num)] = sec

    # Мапа кінцевих вузлів КПК
    kpk_leaf_map = {}
    kpk_code_to_node = {}

    for sec in node_140_10.get("children", []):
        sec_m = re.search(r'Розділ\s+([IVXLCDMІіХх]+(?:\-[0-9]+)?)', sec['name'])
        sec_key = norm_roman(sec_m.group(1)) if sec_m else None
        
        if not sec.get("children"):
            kpk_leaf_map[(sec_key, None, None)] = sec["code"]
            kpk_code_to_node[sec["code"]] = sec
            
        for chap in sec.get("children", []):
            chap_m = re.search(r'Глава\s+(\d+(?:\-[0-9]+)?)', chap['name'])
            chap_key = chap_m.group(1) if chap_m else None
            
            if not chap.get("children"):
                kpk_leaf_map[(sec_key, chap_key, None)] = chap["code"]
                kpk_code_to_node[chap["code"]] = chap
                
            for par in chap.get("children", []):
                par_m = re.search(r'§\s*(\d+)', par['name'])
                par_key = par_m.group(1) if par_m else None
                kpk_leaf_map[(sec_key, chap_key, par_key)] = par["code"]
                kpk_code_to_node[par["code"]] = par

    print(f"[*] Завантажено розділів КК: {len(kk_sec_map)}, кінцевих вузлів КПК: {len(kpk_leaf_map)}")

    # 2. Парсимо статті КК та КПК
    kk_articles_by_sec = parse_kk_articles()
    kpk_articles_by_node = parse_kpk_articles(kpk_leaf_map)

    article_map = {"КК": {}, "КПК": {}}

    # 3. Додаємо статті КК
    total_kk_added = 0
    for key, sec_node in kk_sec_map.items():
        arts = kk_articles_by_sec.get(key, [])
        sec_code = sec_node["code"]
        sec_level = sec_node["level"]
        
        new_children = []
        for i, (art_num, title) in enumerate(arts, 1):
            step = i * 10
            art_code = f"{sec_code} {step}"
            full_title = f"Стаття {art_num}. {title}"
            
            art_node = {
                "code": art_code,
                "level": sec_level + 1,
                "name": full_title,
                "clean_name": full_title,
                "parent_code": sec_code,
                "cross_references": [],
                "branch_url": KK_URL,
                "direct_url": KK_URL,
                "total_docs_count": 0,
                "direct_docs_count": 0,
                "children": []
            }
            new_children.append(art_node)
            article_map["КК"][art_num] = art_code
            total_kk_added += 1

        sec_node["children"] = new_children
        sec_node["has_children"] = len(new_children) > 0
        sec_node["children_count"] = len(new_children)

    # 4. Додаємо статті КПК
    total_kpk_added = 0
    for parent_code, arts in kpk_articles_by_node.items():
        parent_node = kpk_code_to_node[parent_code]
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
                "branch_url": KPK_URL,
                "direct_url": KPK_URL,
                "total_docs_count": 0,
                "direct_docs_count": 0,
                "children": []
            }
            new_children.append(art_node)
            article_map["КПК"][art_num] = art_code
            total_kpk_added += 1

        parent_node["children"] = new_children
        parent_node["has_children"] = len(new_children) > 0
        parent_node["children_count"] = len(new_children)

    print(f"[+] Додано {total_kk_added} статей до Кримінального кодексу України (130 10)")
    print(f"[+] Додано {total_kpk_added} статей до Кримінального процесуального кодексу України (140 10)")
    print(f"[+] Всього нових статей: {total_kk_added + total_kpk_added}")

    # 5. Збереження article_to_category_map.json
    map_path = DATA_DIR / "article_to_category_map.json"
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
