#!/usr/bin/env python3
"""
Скрипт додавання підкатегорії Закон України «Про прикордонний контроль» 
до категорії 170 (Органи влади) у класифікаторі законодавства.
"""

import sys
import json
import sqlite3
from pathlib import Path

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "classifier.sqlite"
JSON_TREE_PATH = DATA_DIR / "classifier.json"
MAP_FILE = DATA_DIR / "article_to_category_map.json"

LAW_CODE = "170 120"
LAW_NAME = "Закон України «Про прикордонний контроль»"
LAW_CLEAN_NAME = "Про прикордонний контроль"
LAW_URL = "https://zakon.rada.gov.ua/laws/show/1710-17"
LAW_DIRECT_URL = "https://zakon.rada.gov.ua/laws/show/1710-17#Text"

SECTIONS = [
    {
        "code": "170 120 10",
        "name": "Розділ I. Загальні положення",
        "clean_name": "Розділ I. Загальні положення",
        "articles": [
            ("170 120 10 10", "Стаття 1. Визначення термінів", "1"),
            ("170 120 10 20", "Стаття 2. Організаційні засади здійснення прикордонного контролю", "2"),
            ("170 120 10 30", "Стаття 3. Правові засади здійснення прикордонного контролю", "3"),
            ("170 120 10 40", "Стаття 4. Принципи організації та здійснення прикордонного контролю", "4"),
            ("170 120 10 50", "Стаття 5. Місце здійснення прикордонного контролю", "5"),
        ]
    },
    {
        "code": "170 120 20",
        "name": "Розділ II. Процедури прикордонного контролю",
        "clean_name": "Розділ II. Процедури прикордонного контролю",
        "articles": [
            ("170 120 20 10", "Стаття 6. Загальні процедури прикордонного контролю", "6"),
            ("170 120 20 20", "Стаття 7. Прикордонний контроль осіб", "7"),
            ("170 120 20 30", "Стаття 7-1. Мова на державному кордоні України", "7-1"),
            ("170 120 20 40", "Стаття 8. Умови перетинання державного кордону іноземцями та особами без громадянства у разі в'їзду в Україну", "8"),
            ("170 120 20 50", "Стаття 9. Прикордонний контроль іноземців та осіб без громадянства під час в'їзду в Україну", "9"),
            ("170 120 20 60", "Стаття 10. Прикордонний контроль іноземців та осіб без громадянства під час виїзду з України", "10"),
            ("170 120 20 70", "Стаття 11. Спрощення прикордонного контролю", "11"),
            ("170 120 20 80", "Стаття 12. Відмітка про перетинання державного кордону", "12"),
            ("170 120 20 90", "Стаття 13. Перевірка дотримання правил і строку перебування іноземців та осіб без громадянства на території України", "13"),
            ("170 120 20 100", "Стаття 14. Порядок відмови у перетинанні державного кордону іноземцям, особам без громадянства та громадянам України", "14"),
        ]
    },
    {
        "code": "170 120 30",
        "name": "Розділ III. Особливості здійснення прикордонного контролю",
        "clean_name": "Розділ III. Особливості здійснення прикордонного контролю",
        "articles": [
            ("170 120 30 10", "Стаття 15. Прикордонний контроль у пунктах пропуску через державний кордон для автомобільного сполучення", "15"),
            ("170 120 30 20", "Стаття 16. Прикордонний контроль у пунктах пропуску через державний кордон для залізничного сполучення", "16"),
            ("170 120 30 30", "Стаття 17. Прикордонний контроль у пунктах пропуску через державний кордон для повітряного сполучення", "17"),
            ("170 120 30 40", "Стаття 18. Прикордонний контроль у пунктах пропуску через державний кордон для морського та річкового сполучення", "18"),
            ("170 120 30 50", "Стаття 19. Прикордонний контроль круїзних суден", "19"),
            ("170 120 30 60", "Стаття 20. Прикордонний контроль яхт", "20"),
            ("170 120 30 70", "Стаття 21. Прикордонний контроль риболовних суден", "21"),
            ("170 120 30 80", "Стаття 22. Прикордонний контроль поромів закордонного сполучення", "22"),
            ("170 120 30 90", "Стаття 23. Особливості прикордонного контролю окремих категорій осіб", "23"),
            ("170 120 30 100", "Стаття 24. Реєстрація паспортних документів іноземців та осіб без громадянства у пунктах пропуску через державний кордон", "24"),
        ]
    },
    {
        "code": "170 120 40",
        "name": "Розділ IV. Взаємодія та співпраця з питань здійснення прикордонного контролю",
        "clean_name": "Розділ IV. Взаємодія та співпраця з питань здійснення прикордонного контролю",
        "articles": [
            ("170 120 40 10", "Стаття 25. Взаємодія державних органів влади України під час здійснення пропуску осіб, транспортних засобів та вантажів у пунктах пропуску через державний кордон", "25"),
            ("170 120 40 20", "Стаття 26. Спільний прикордонний контроль із суміжними державами", "26"),
        ]
    },
    {
        "code": "170 120 50",
        "name": "Розділ V. Прикінцеві положення",
        "clean_name": "Розділ V. Прикінцеві положення",
        "articles": []
    }
]


def build_law_tree_node():
    law_node = {
        "code": LAW_CODE,
        "level": 2,
        "name": LAW_NAME,
        "clean_name": LAW_CLEAN_NAME,
        "parent_code": "170",
        "path_codes": f"170 / {LAW_CODE}",
        "path_names": f"Органи влади / {LAW_CLEAN_NAME}",
        "cross_references": [],
        "branch_url": LAW_URL,
        "direct_url": LAW_DIRECT_URL,
        "total_docs_count": 0,
        "direct_docs_count": 0,
        "has_children": True,
        "children_count": len(SECTIONS),
        "children": []
    }

    for sec in SECTIONS:
        sec_node = {
            "code": sec["code"],
            "level": 3,
            "name": sec["name"],
            "clean_name": sec["clean_name"],
            "parent_code": LAW_CODE,
            "path_codes": f"170 / {LAW_CODE} / {sec['code']}",
            "path_names": f"Органи влади / {LAW_CLEAN_NAME} / {sec['clean_name']}",
            "cross_references": [],
            "branch_url": "",
            "direct_url": "",
            "total_docs_count": 0,
            "direct_docs_count": 0,
            "has_children": len(sec["articles"]) > 0,
            "children_count": len(sec["articles"]),
            "children": []
        }

        for art_code, art_name, art_num in sec["articles"]:
            art_node = {
                "code": art_code,
                "level": 4,
                "name": art_name,
                "clean_name": art_name,
                "parent_code": sec["code"],
                "path_codes": f"170 / {LAW_CODE} / {sec['code']} / {art_code}",
                "path_names": f"Органи влади / {LAW_CLEAN_NAME} / {sec['clean_name']} / {art_name}",
                "cross_references": [],
                "branch_url": "",
                "direct_url": "",
                "total_docs_count": 0,
                "direct_docs_count": 0,
                "has_children": False,
                "children_count": 0,
                "children": []
            }
            sec_node["children"].append(art_node)

        law_node["children"].append(sec_node)

    return law_node


def main():
    print("[*] Додавання Закон України «Про прикордонний контроль» до класифікатора...")

    # 1. Оновлення classifier.json
    with open(JSON_TREE_PATH, "r", encoding="utf-8") as f:
        tree = json.load(f)

    node_170 = None
    for r in tree:
        if r["code"] == "170":
            node_170 = r
            break

    if not node_170:
        raise ValueError("Категорію 170 не знайдено в classifier.json!")

    # Перевіримо, чи вже є 170 120
    existing = [c for c in node_170.get("children", []) if c["code"] == LAW_CODE]
    if existing:
        print(f"[-] Категорія {LAW_CODE} вже існує в classifier.json, оновлюємо її...")
        node_170["children"] = [c for c in node_170["children"] if c["code"] != LAW_CODE]

    law_node = build_law_tree_node()
    node_170["children"].append(law_node)
    # Сортування дітей за числовим кодом
    def sort_key(x):
        parts = [int(p) if p.isdigit() else 0 for p in x["code"].split()]
        return parts

    node_170["children"].sort(key=sort_key)
    node_170["has_children"] = True
    node_170["children_count"] = len(node_170["children"])

    with open(JSON_TREE_PATH, "w", encoding="utf-8") as f:
        json.dump(tree, f, ensure_ascii=False, indent=2)
    print(f"[+] Оновлено {JSON_TREE_PATH}")

    # 2. Оновлення бази SQLite (таблиця categories)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Очищення старих записів для цієї гілки, якщо були
    cur.execute("DELETE FROM categories WHERE code LIKE '170 120%'")

    # Вставка всіх нових вузлів
    def insert_node(n):
        cur.execute("""
            INSERT OR REPLACE INTO categories (
                code, parent_code, level, name, clean_name, path_codes, path_names,
                has_children, children_count, total_docs_count, direct_docs_count,
                branch_url, direct_url, cross_references, semantic_text, description
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            n["code"], n["parent_code"], n["level"], n["name"], n["clean_name"],
            n["path_codes"], n["path_names"], 1 if n["has_children"] else 0,
            n["children_count"], n["total_docs_count"], n["direct_docs_count"],
            n.get("branch_url", ""), n.get("direct_url", ""), "[]",
            f"{n['name']} {n['clean_name']}", ""
        ))
        for ch in n.get("children", []):
            insert_node(ch)

    insert_node(law_node)

    # Оновлення кількості дітей для 170
    cur.execute("""
        UPDATE categories 
        SET has_children = 1, children_count = (SELECT count(*) FROM categories WHERE parent_code = '170')
        WHERE code = '170'
    """)

    conn.commit()
    conn.close()
    print(f"[+] Оновлено таблицю categories у {DB_PATH}")

    # 3. Оновлення article_to_category_map.json
    article_map = {}
    if MAP_FILE.exists():
        with open(MAP_FILE, "r", encoding="utf-8") as f:
            article_map = json.load(f)

    border_map = {}
    for sec in SECTIONS:
        for art_code, art_name, art_num in sec["articles"]:
            border_map[art_num] = art_code

    article_map["ПРИКОРДОННИЙ_КОНТРОЛЬ"] = border_map
    with open(MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(article_map, f, ensure_ascii=False, indent=2)
    print(f"[+] Додано {len(border_map)} статей до {MAP_FILE} під ключем 'ПРИКОРДОННИЙ_КОНТРОЛЬ'")


if __name__ == "__main__":
    main()
