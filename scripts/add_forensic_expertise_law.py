#!/usr/bin/env python3
"""
Скрипт додавання підкатегорії Закон України «Про судову експертизу»
до категорії 170 (Органи влади) у класифікаторі законодавства.
Створює повну ієрархію розділів (I–IV) та статей (1–24) Закону № 4038-XII.
"""

import sys
import re
import json
import sqlite3
from pathlib import Path

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "classifier.sqlite"
JSON_TREE_PATH = DATA_DIR / "classifier.json"
MAP_FILE = DATA_DIR / "article_to_category_map.json"

LAW_CODE = "170 150"
LAW_NAME = "Закон України «Про судову експертизу»"
LAW_CLEAN_NAME = "Про судову експертизу"
LAW_URL = "https://zakon.rada.gov.ua/laws/show/4038-12"
LAW_DIRECT_URL = "https://zakon.rada.gov.ua/laws/show/4038-12#Text"

RAW_SECTIONS = [
    {
        "num": "I",
        "title": "Розділ I. Загальні положення",
        "articles": [
            ("1", "Поняття судової експертизи"),
            ("2", "Законодавство України про судову експертизу"),
            ("3", "Принципи судово-експертної діяльності"),
            ("4", "Гарантії незалежності судового експерта та правильності його висновку"),
            ("5", "Максимальне збереження об’єктів дослідження"),
            ("6", "Забезпечення умов праці судового експерта за місцезнаходженням об’єктів дослідження"),
            ("7", "Суб’єкти судово-експертної діяльності"),
            ("7-1", "Підстави проведення судової експертизи (обстеження і дослідження)"),
            ("8", "Науково-методичне та організаційно-управлінське забезпечення судово-експертної діяльності"),
            ("9", "Державний Реєстр атестованих судових експертів"),
        ]
    },
    {
        "num": "II",
        "title": "Розділ II. Судовий експерт",
        "articles": [
            ("10", "Особи, які можуть бути судовими експертами"),
            ("11", "Особи, які не можуть бути судовими експертами"),
            ("12", "Обов’язки судового експерта"),
            ("13", "Права судового експерта"),
            ("14", "Відповідальність судового експерта"),
        ]
    },
    {
        "num": "III",
        "title": "Розділ III. Фінансове та організаційне забезпечення судово-експертної діяльності",
        "articles": [
            ("15", "Фінансування судово-експертної діяльності"),
            ("16", "Атестація"),
            ("16-1", "Тимчасове зупинення та поновлення права на проведення судової експертизи"),
            ("16-2", "Припинення права на проведення судової експертизи"),
            ("17", "Експертно-кваліфікаційні комісії"),
            ("18", "Оплата праці та соціальний захист судових експертів"),
            ("18-1", "Щорічні та додаткові відпустки судових експертів"),
            ("19", "Охорона державних спеціалізованих установ, що проводять судові експертизи"),
            ("20", "Інформаційне забезпечення"),
            ("21", "Професійна підготовка судового експерта"),
        ]
    },
    {
        "num": "IV",
        "title": "Розділ IV. Міжнародне співробітництво в галузі судової експертизи",
        "articles": [
            ("22", "Проведення судової експертизи за дорученням відповідного органу чи особи іншої держави"),
            ("23", "Залучення фахівців з інших держав для спільного проведення судових експертиз"),
            ("24", "Міжнародне наукове співробітництво"),
        ]
    }
]


def build_sections_structure():
    sections = []
    for s_idx, sec in enumerate(RAW_SECTIONS, 1):
        sec_code = f"{LAW_CODE} {s_idx * 10}"
        sec_dict = {
            "code": sec_code,
            "name": sec["title"],
            "clean_name": sec["title"],
            "articles": []
        }
        for a_idx, (art_num, art_title) in enumerate(sec["articles"], 1):
            art_code = f"{sec_code} {a_idx * 10}"
            art_full_name = f"Стаття {art_num}. {art_title}"
            sec_dict["articles"].append((art_code, art_full_name, art_num))
        sections.append(sec_dict)
    return sections


def build_law_tree_node(sections):
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
        "children_count": len(sections),
        "children": []
    }

    for sec in sections:
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
    print("[*] Додавання Закон України «Про судову експертизу» до класифікатора...")
    sections = build_sections_structure()
    total_arts = sum(len(s["articles"]) for s in sections)
    print(f"    Підготовлено: 4 розділи та {total_arts} конкретних статей.")

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

    node_170["children"] = [c for c in node_170.get("children", []) if c["code"] != LAW_CODE]

    law_node = build_law_tree_node(sections)
    node_170["children"].append(law_node)

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

    cur.execute("DELETE FROM categories WHERE code LIKE '170 150%'")

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

    exp_map = {}
    for sec in sections:
        for art_code, art_name, art_num in sec["articles"]:
            exp_map[art_num] = art_code

    article_map["СУДОВА_ЕКСПЕРТИЗА"] = exp_map
    with open(MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(article_map, f, ensure_ascii=False, indent=2)
    print(f"[+] Додано {len(exp_map)} статей до {MAP_FILE} під ключем 'СУДОВА_ЕКСПЕРТИЗА'")


if __name__ == "__main__":
    main()
