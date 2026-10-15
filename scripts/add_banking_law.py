#!/usr/bin/env python3
"""
Скрипт додавання підкатегорії Закон України «Про банки і банківську діяльність»
до категорії 180 (Підприємництво) у класифікаторі законодавства.
Створює повну ієрархію розділів (I–VII), глав (1–16) та статей (1–83) Закону № 2121-III.
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

LAW_CODE = "180 20"
LAW_NAME = "Закон України «Про банки і банківську діяльність»"
LAW_CLEAN_NAME = "Про банки і банківську діяльність"
LAW_URL = "https://zakon.rada.gov.ua/laws/show/2121-14"
LAW_DIRECT_URL = "https://zakon.rada.gov.ua/laws/show/2121-14#Text"

RAW_STRUCTURE = [
    {
        "num": "I",
        "title": "Розділ I. Загальні положення",
        "glavas": [
            {
                "num": "1",
                "title": "Глава 1. Загальні положення",
                "articles": [
                    ("1", "Предмет та мета Закону"),
                    ("2", "Визначення термінів"),
                    ("3", "Сфера застосування Закону"),
                    ("4", "Банківська система України"),
                    ("5", "Економічна незалежність банків"),
                    ("6", "Організаційно-правова форма банку"),
                    ("7", "Державні банки"),
                    ("7-1", "Особливості управління державними банками на період воєнного стану"),
                    ("8", "Кооперативні банки"),
                    ("8-1", "Особливості правового статусу банку фінансової інклюзії"),
                    ("9", "Банківські спілки та асоціації"),
                    ("13", "Законодавство про банківську діяльність"),
                ]
            }
        ],
        "direct_articles": []
    },
    {
        "num": "II",
        "title": "Розділ II. Створення, державна реєстрація, ліцензування діяльності та реорганізація банків",
        "glavas": [
            {
                "num": "2",
                "title": "Глава 2. Створення банків",
                "articles": [
                    ("14", "Учасники банків"),
                    ("15", "Найменування банку"),
                    ("16", "Статут банку"),
                    ("17", "Порядок створення та державної реєстрації банків"),
                    ("18", "Державний реєстр банків"),
                    ("19", "Банківська ліцензія"),
                    ("20", "Порядок видачі банківської ліцензії"),
                    ("22", "Підстави для відмови у видачі банківської ліцензії"),
                ]
            },
            {
                "num": "4",
                "title": "Глава 4. Відокремлені підрозділи банку",
                "articles": [
                    ("23", "Порядок відкриття відокремлених підрозділів банку на території України"),
                    ("24", "Порядок відкриття філій та представництв іноземних банків в Україні"),
                    ("25", "Порядок відкриття підрозділів українських банків за кордоном"),
                ]
            },
            {
                "num": "5",
                "title": "Глава 5. Реорганізація банку",
                "articles": [
                    ("26", "Способи реорганізації банку"),
                    ("27", "Умови реорганізації банку"),
                    ("28", "Порядок реорганізації банку"),
                    ("29", "Оскарження рішень щодо реорганізації"),
                ]
            }
        ],
        "direct_articles": []
    },
    {
        "num": "III",
        "title": "Розділ III. Капітал, управління, вимоги до діяльності банків",
        "glavas": [
            {
                "num": "6",
                "title": "Глава 6. Капітал, фонди та резерви банку",
                "articles": [
                    ("30", "Структура регулятивного капіталу банку"),
                    ("31", "Мінімальний розмір статутного капіталу"),
                    ("32", "Формування статутного капіталу банку"),
                    ("33", "Збільшення та зменшення статутного капіталу"),
                    ("34", "Формування резервів банку"),
                    ("35", "Покриття збитків банку"),
                    ("35-1", "Капітал банківської групи"),
                    ("36", "Придбання або збільшення істотної участі у банку"),
                    ("36-1", "Вимоги до структури власності банку"),
                    ("36-2", "Особливості набуття або збільшення істотної участі"),
                    ("36-3", "Наслідки порушення вимог щодо істотної участі"),
                ]
            },
            {
                "num": "7",
                "title": "Глава 7. Управління банком",
                "articles": [
                    ("37", "Органи управління та контролю банку"),
                    ("38", "Загальні збори учасників банку"),
                    ("39", "Рада банку"),
                    ("40", "Правління банку"),
                    ("41", "Вимоги до керівників банку"),
                    ("42", "Обов’язки керівників банку"),
                    ("43", "Відповідальність керівників банку"),
                    ("44", "Система внутрішнього контролю"),
                    ("45", "Підрозділ внутрішнього аудиту"),
                    ("46", "Система управління ризиками"),
                ]
            },
            {
                "num": "8",
                "title": "Глава 8. Вимоги до діяльності банку",
                "articles": [
                    ("47", "Види діяльності банку"),
                    ("48", "Обмеження щодо діяльності банків"),
                    ("49", "Кредитні операції банку"),
                    ("50", "Інвестиційна діяльність банків"),
                    ("51", "Розрахункові операції банків"),
                    ("52", "Операції банку з пов’язаними з банком особами"),
                    ("53", "Процентні ставки та комісійні винагороди банку"),
                    ("54", "Забезпечення безпеки банківської діяльності"),
                ]
            },
            {
                "num": "9",
                "title": "Глава 9. Відносини банку з клієнтами",
                "articles": [
                    ("55", "Регулювання відносин банку з клієнтом"),
                    ("56", "Право клієнта на інформацію"),
                    ("57", "Захист прав споживачів банківських послуг"),
                    ("58", "Відповідальність банку перед клієнтом"),
                    ("59", "Арешт та примусове списання коштів з рахунків клієнтів"),
                ]
            },
            {
                "num": "10",
                "title": "Глава 10. Банківська таємниця та конфіденційність інформації",
                "articles": [
                    ("60", "Банківська таємниця"),
                    ("61", "Зобов’язання щодо збереження банківської таємниці"),
                    ("62", "Порядок розкриття банками банківської таємниці"),
                    ("62-1", "Конфіденційність інформації (виключено)"),
                    ("62-2", "Особливості захисту банківської таємниці"),
                ]
            },
            {
                "num": "11",
                "title": "Глава 11. Запобігання та протидія легалізації доходів, одержаних злочинним шляхом",
                "articles": [
                    ("63", "Запобігання легалізації (відмиванню) доходів, одержаних злочинним шляхом, фінансуванню тероризму та розповсюдження зброї масового знищення"),
                ]
            }
        ],
        "direct_articles": []
    },
    {
        "num": "IV",
        "title": "Розділ IV. Регулювання банківської діяльності. Банківський нагляд",
        "glavas": [
            {
                "num": "12",
                "title": "Глава 12. Повноваження НБУ щодо регулювання діяльності та нагляду",
                "articles": [
                    ("66", "Форми регулювання банківської діяльності"),
                    ("67", "Мета, організація, підстави та обсяг нагляду"),
                    ("67-1", "Нагляд на консолідованій основі"),
                ]
            },
            {
                "num": "13",
                "title": "Глава 13. Бухгалтерський облік, звітність та аудит",
                "articles": [
                    ("68", "Загальні засади ведення бухгалтерського обліку і звітності в банках"),
                    ("69", "Звітність банків, банківських груп"),
                    ("70", "Аудиторська перевірка банку"),
                ]
            },
            {
                "num": "14",
                "title": "Глава 14. Інспекційні перевірки банків",
                "articles": [
                    ("71", "Інспекційні перевірки банків"),
                    ("72", "Перевірка осіб, які охоплюються наглядовою діяльністю Національного банку України"),
                ]
            },
            {
                "num": "14-1",
                "title": "Глава 14-1. Заходи впливу",
                "articles": [
                    ("73", "Заходи впливу"),
                    ("74", "Порядок застосування заходів впливу"),
                ]
            }
        ],
        "direct_articles": []
    },
    {
        "num": "V",
        "title": "Розділ V. Проблемний та неплатоспроможний банк. Ліквідація банку",
        "glavas": [
            {
                "num": "15",
                "title": "Глава 15. Критерії віднесення банку до проблемних та неплатоспроможних",
                "articles": [
                    ("75", "Віднесення банку до категорії проблемних"),
                    ("76", "Віднесення банку до категорії неплатоспроможних"),
                ]
            },
            {
                "num": "16",
                "title": "Глава 16. Ліквідація банку",
                "articles": [
                    ("77", "Відкликання банківської ліцензії та ліквідація банку"),
                    ("78", "Ліквідація банку з ініціативи власників"),
                ]
            }
        ],
        "direct_articles": []
    },
    {
        "num": "VI",
        "title": "Розділ VI. Оскарження рішень Національного банку України",
        "glavas": [],
        "direct_articles": [
            ("79", "Оскарження рішень, дій або бездіяльності Національного банку України"),
            ("79-1", "Особливості судового розгляду справ про оскарження рішень Національного банку України"),
        ]
    },
    {
        "num": "VII",
        "title": "Розділ VII. Прикінцеві положення",
        "glavas": [],
        "direct_articles": []
    }
]


def build_banking_tree():
    law_node = {
        "code": LAW_CODE,
        "level": 2,
        "name": LAW_NAME,
        "clean_name": LAW_CLEAN_NAME,
        "parent_code": "180",
        "path_codes": f"180 / {LAW_CODE}",
        "path_names": f"Підприємництво / {LAW_CLEAN_NAME}",
        "cross_references": [],
        "branch_url": LAW_URL,
        "direct_url": LAW_DIRECT_URL,
        "total_docs_count": 0,
        "direct_docs_count": 0,
        "has_children": True,
        "children_count": len(RAW_STRUCTURE),
        "children": []
    }

    art_map = {}

    for r_idx, r in enumerate(RAW_STRUCTURE, 1):
        r_code = f"{LAW_CODE} {r_idx * 10}"
        r_children = []

        if r["glavas"]:
            for g_idx, g in enumerate(r["glavas"], 1):
                g_code = f"{r_code} {g_idx * 10}"
                g_arts = []
                for a_idx, (art_num, art_title) in enumerate(g["articles"], 1):
                    a_code = f"{g_code} {a_idx * 10}"
                    art_full_name = f"Стаття {art_num}. {art_title}"
                    a_node = {
                        "code": a_code,
                        "level": 5,
                        "name": art_full_name,
                        "clean_name": art_full_name,
                        "parent_code": g_code,
                        "path_codes": f"180 / {LAW_CODE} / {r_code} / {g_code} / {a_code}",
                        "path_names": f"Підприємництво / {LAW_CLEAN_NAME} / {r['title']} / {g['title']} / {art_full_name}",
                        "cross_references": [],
                        "branch_url": "",
                        "direct_url": "",
                        "total_docs_count": 0,
                        "direct_docs_count": 0,
                        "has_children": False,
                        "children_count": 0,
                        "children": []
                    }
                    g_arts.append(a_node)
                    art_map[art_num] = a_code

                g_node = {
                    "code": g_code,
                    "level": 4,
                    "name": g["title"],
                    "clean_name": g["title"],
                    "parent_code": r_code,
                    "path_codes": f"180 / {LAW_CODE} / {r_code} / {g_code}",
                    "path_names": f"Підприємництво / {LAW_CLEAN_NAME} / {r['title']} / {g['title']}",
                    "cross_references": [],
                    "branch_url": "",
                    "direct_url": "",
                    "total_docs_count": 0,
                    "direct_docs_count": 0,
                    "has_children": len(g_arts) > 0,
                    "children_count": len(g_arts),
                    "children": g_arts
                }
                r_children.append(g_node)
        elif r["direct_articles"]:
            for a_idx, (art_num, art_title) in enumerate(r["direct_articles"], 1):
                a_code = f"{r_code} {a_idx * 10}"
                art_full_name = f"Стаття {art_num}. {art_title}"
                a_node = {
                    "code": a_code,
                    "level": 4,
                    "name": art_full_name,
                    "clean_name": art_full_name,
                    "parent_code": r_code,
                    "path_codes": f"180 / {LAW_CODE} / {r_code} / {a_code}",
                    "path_names": f"Підприємництво / {LAW_CLEAN_NAME} / {r['title']} / {art_full_name}",
                    "cross_references": [],
                    "branch_url": "",
                    "direct_url": "",
                    "total_docs_count": 0,
                    "direct_docs_count": 0,
                    "has_children": False,
                    "children_count": 0,
                    "children": []
                }
                r_children.append(a_node)
                art_map[art_num] = a_code

        r_node = {
            "code": r_code,
            "level": 3,
            "name": r["title"],
            "clean_name": r["title"],
            "parent_code": LAW_CODE,
            "path_codes": f"180 / {LAW_CODE} / {r_code}",
            "path_names": f"Підприємництво / {LAW_CLEAN_NAME} / {r['title']}",
            "cross_references": [],
            "branch_url": "",
            "direct_url": "",
            "total_docs_count": 0,
            "direct_docs_count": 0,
            "has_children": len(r_children) > 0,
            "children_count": len(r_children),
            "children": r_children
        }
        law_node["children"].append(r_node)

    return law_node, art_map


def main():
    print("[*] Додавання Закон України «Про банки і банківську діяльність» до класифікатора...")
    law_node, art_map = build_banking_tree()
    print(f"    Підготовлено: 7 розділів, 16 глав та {len(art_map)} конкретних статей.")

    # 1. Оновлення classifier.json
    with open(JSON_TREE_PATH, "r", encoding="utf-8") as f:
        tree = json.load(f)

    node_180 = None
    for r in tree:
        if r["code"] == "180":
            node_180 = r
            break

    if not node_180:
        raise ValueError("Категорію 180 не знайдено в classifier.json!")

    node_180["children"] = [c for c in node_180.get("children", []) if c["code"] != LAW_CODE]
    node_180["children"].append(law_node)

    def sort_key(x):
        parts = [int(p) if p.isdigit() else 0 for p in x["code"].split()]
        return parts

    node_180["children"].sort(key=sort_key)
    node_180["has_children"] = True
    node_180["children_count"] = len(node_180["children"])

    with open(JSON_TREE_PATH, "w", encoding="utf-8") as f:
        json.dump(tree, f, ensure_ascii=False, indent=2)
    print(f"[+] Оновлено {JSON_TREE_PATH}")

    # 2. Оновлення бази SQLite (таблиця categories)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("DELETE FROM categories WHERE code LIKE '180 20%'")

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
        SET has_children = 1, children_count = (SELECT count(*) FROM categories WHERE parent_code = '180')
        WHERE code = '180'
    """)

    conn.commit()
    conn.close()
    print(f"[+] Оновлено таблицю categories у {DB_PATH}")

    # 3. Оновлення article_to_category_map.json
    article_map = {}
    if MAP_FILE.exists():
        with open(MAP_FILE, "r", encoding="utf-8") as f:
            article_map = json.load(f)

    article_map["БАНКИ"] = art_map
    with open(MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(article_map, f, ensure_ascii=False, indent=2)
    print(f"[+] Додано {len(art_map)} статей до {MAP_FILE} під ключем 'БАНКИ'")


if __name__ == "__main__":
    main()
