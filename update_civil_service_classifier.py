#!/usr/bin/env python3
"""
Скрипт оновлення категорії 110:
'Нагороди і почесні звання' -> 'Органи влади'
Створення підкатегорії 110 10 'Закон України «Про державну службу»'
зі структурою чинного Закону України від 10.12.2015 № 889-VIII (Розділи та Глави).
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

LAW_BASE_URL = "https://zakon.rada.gov.ua/laws/show/889-19"
LAW_TITLE = "Закон України «Про державну службу»"

def make_search_url(query: str) -> str:
    params = {
        "text": query,
        "mode": "all",
        "cat": "1",
        "search": "1"
    }
    return f"https://zakon.rada.gov.ua/laws/find/a?{urllib.parse.urlencode(params)}"

def build_civil_service_tree():
    """
    Побудова структури Закону України «Про державну службу» № 889-VIII
    (11 Розділів, Глави в Розділах IV та VIII).
    """
    sections = [
        {
            "code_suffix": "10",
            "title": "Розділ I. Загальні положення",
            "children": []
        },
        {
            "code_suffix": "20",
            "title": "Розділ II. Правовий статус державного службовця",
            "children": []
        },
        {
            "code_suffix": "30",
            "title": "Розділ III. Управління державною службою",
            "children": []
        },
        {
            "code_suffix": "40",
            "title": "Розділ IV. Вступ на державну службу",
            "children": [
                {
                    "code_suffix": "10",
                    "title": "Глава 1. Загальні умови вступу на державну службу"
                },
                {
                    "code_suffix": "20",
                    "title": "Глава 2. Порядок проведення конкурсу на зайняття посад державної служби"
                },
                {
                    "code_suffix": "30",
                    "title": "Глава 3. Призначення на посаду державної служби"
                }
            ]
        },
        {
            "code_suffix": "50",
            "title": "Розділ V. Службова кар'єра",
            "children": []
        },
        {
            "code_suffix": "60",
            "title": "Розділ VI. Оплата праці, заохочення і соціальні гарантії",
            "children": []
        },
        {
            "code_suffix": "70",
            "title": "Розділ VII. Робочий час і час відпочинку державного службовця. Відпустки",
            "children": []
        },
        {
            "code_suffix": "80",
            "title": "Розділ VIII. Дисциплінарна та матеріальна відповідальність державних службовців",
            "children": [
                {
                    "code_suffix": "10",
                    "title": "Глава 1. Службова дисципліна"
                },
                {
                    "code_suffix": "20",
                    "title": "Глава 2. Засади дисциплінарної відповідальності"
                },
                {
                    "code_suffix": "30",
                    "title": "Глава 3. Матеріальна відповідальність державних службовців"
                }
            ]
        },
        {
            "code_suffix": "90",
            "title": "Розділ IX. Припинення державної служби",
            "children": []
        },
        {
            "code_suffix": "100",
            "title": "Розділ X. Особливості проходження державної служби в окремих державних органах. Патронатна служба",
            "children": []
        },
        {
            "code_suffix": "110",
            "title": "Розділ XI. Прикінцеві та перехідні положення",
            "children": []
        }
    ]

    root_code = "110 10"
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

    print(f"[+] Перейменування категорії 110: '{cat_110['clean_name']}' -> 'Органи влади'")
    cat_110["name"] = "Органи влади"
    cat_110["clean_name"] = "Органи влади"

    print("[+] Створення структури Закону України «Про державну службу»...")
    civil_service_node = build_civil_service_tree()
    cat_110["children"] = [civil_service_node]

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

    # Оновлення mapped_segments, якщо старі коди видалено
    valid_codes = set(it["code"] for it in flat_all)
    cur.execute("SELECT id, category_code FROM mapped_segments WHERE category_code LIKE '110%'")
    for seg_id, code in cur.fetchall():
        if code not in valid_codes:
            cur.execute("UPDATE mapped_segments SET category_code = '110 10' WHERE id = ?", (seg_id,))

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

    print(f"\n[SUCCESS] Успішно оновлено категорію 110 'Органи влади' та створено структуру Закону 'Про державну службу'. Всього {len(flat_all)} рубрик у класифікаторі!")

if __name__ == "__main__":
    update_all()
