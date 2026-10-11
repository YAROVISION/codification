#!/usr/bin/env python3
"""
Скрипт додавання підкатегорії 110 20 'Закон України «Про місцеве самоврядування в Україні»'
до категорії 110 'Органи влади'.
Структура за Законом України від 21.05.1997 № 280/97-ВР (Розділи та Глави).
"""

import sys
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

LAW_BASE_URL = "https://zakon.rada.gov.ua/laws/show/280/97-%D0%B2%D1%80"
LAW_TITLE = "Закон України «Про місцеве самоврядування в Україні»"

def make_search_url(query: str) -> str:
    params = {
        "text": query,
        "mode": "all",
        "cat": "1",
        "search": "1"
    }
    return f"https://zakon.rada.gov.ua/laws/find/a?{urllib.parse.urlencode(params)}"

def build_local_gov_tree():
    """
    Побудова структури Закону України «Про місцеве самоврядування в Україні» № 280/97-ВР
    (5 Розділів, 5 Глав у Розділі II).
    """
    sections = [
        {
            "code_suffix": "10",
            "title": "Розділ I. Загальні положення",
            "children": []
        },
        {
            "code_suffix": "20",
            "title": "Розділ II. Організаційно-правова основа місцевого самоврядування",
            "children": [
                {
                    "code_suffix": "10",
                    "title": "Глава 1. Повноваження сільських, селищних, міських рад"
                },
                {
                    "code_suffix": "20",
                    "title": "Глава 2. Повноваження виконавчих органів сільських, селищних, міських рад"
                },
                {
                    "code_suffix": "30",
                    "title": "Глава 3. Сільський, селищний, міський голова"
                },
                {
                    "code_suffix": "40",
                    "title": "Глава 4. Повноваження районних і обласних рад"
                },
                {
                    "code_suffix": "50",
                    "title": "Глава 5. Порядок формування, організація роботи органів та посадових осіб місцевого самоврядування"
                }
            ]
        },
        {
            "code_suffix": "30",
            "title": "Розділ III. Матеріальна і фінансова основа місцевого самоврядування",
            "children": []
        },
        {
            "code_suffix": "40",
            "title": "Розділ IV. Гарантії місцевого самоврядування. Відповідальність органів та посадових осіб місцевого самоврядування",
            "children": []
        },
        {
            "code_suffix": "50",
            "title": "Розділ V. Прикінцеві та перехідні положення",
            "children": []
        }
    ]

    root_code = "110 20"
    root_node = {
        "code": root_code,
        "level": 2,
        "name": LAW_TITLE,
        "clean_name": LAW_TITLE,
        "cross_references": [],
        "branch_url": make_search_url(LAW_TITLE),
        "direct_url": LAW_BASE_URL,
        "total_docs_count": 0,
        "direct_docs_count": 0,
        "children": []
    }

    for sec in sections:
        sec_code = f"{root_code} {sec['code_suffix']}"
        sec_title = sec["title"]
        sec_node = {
            "code": sec_code,
            "level": 3,
            "name": sec_title,
            "clean_name": sec_title,
            "cross_references": [],
            "branch_url": make_search_url(f"{LAW_TITLE} {sec_title}"),
            "direct_url": LAW_BASE_URL,
            "total_docs_count": 0,
            "direct_docs_count": 0,
            "children": []
        }

        for ch in sec.get("children", []):
            ch_code = f"{sec_code} {ch['code_suffix']}"
            ch_title = ch["title"]
            ch_node = {
                "code": ch_code,
                "level": 4,
                "name": ch_title,
                "clean_name": ch_title,
                "cross_references": [],
                "branch_url": make_search_url(f"{LAW_TITLE} {sec_title} {ch_title}"),
                "direct_url": LAW_BASE_URL,
                "total_docs_count": 0,
                "direct_docs_count": 0,
                "children": []
            }
            sec_node["children"].append(ch_node)

        root_node["children"].append(sec_node)

    return root_node

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
    json_path = DATA_DIR / "classifier.json"
    print(f"[*] Завантаження {json_path}...")
    with open(json_path, "r", encoding="utf-8") as f:
        classifier_tree = json.load(f)

    cat_110 = None
    for cat in classifier_tree:
        if cat["code"] == "110":
            cat_110 = cat
            break

    if not cat_110:
        raise ValueError("Категорію 110 не знайдено в classifier.json")

    print("[+] Створення структури Закону України «Про місцеве самоврядування в Україні» (110 20)...")
    local_gov_node = build_local_gov_tree()

    # Перевірка, чи вже існує 110 20, або додавання до children
    existing_children = [c for c in cat_110.get("children", []) if c["code"] != "110 20"]
    existing_children.append(local_gov_node)
    cat_110["children"] = existing_children

    # 1. Збереження classifier.json
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

    print(f"\n[SUCCESS] Успішно додано підкатегорію 110 20 'Закон України «Про місцеве самоврядування в Україні»'. Всього {len(flat_all)} рубрик у класифікаторі!")

if __name__ == "__main__":
    update_all()
