#!/usr/bin/env python3
"""
Скрипт додавання нової кореневої категорії 180 'Підприємництво'
та підкатегорії 180 10 'Закон України «Про обов’язкове страхування цивільно-правової відповідальності власників наземних транспортних засобів»'
(Закон № 3720-IX, https://zakon.rada.gov.ua/laws/show/3720-20#Text)
із повною структурою 6 розділів та конкретизацією до 54 статей включно.

Оновлює всі 5 форматів класифікатора:
1. data/classifier.json
2. data/classifier_flat.json
3. data/classifier.sqlite (categories та categories_fts)
4. data/classifier.csv
5. data/classifier.md
А також запускає sync_classifier_counts.py для оновлення лічильників.
"""

import sys
import json
import csv
import re
import sqlite3
import urllib.parse
from datetime import datetime
from pathlib import Path

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

LAW_URL = "https://zakon.rada.gov.ua/laws/show/3720-20#Text"
BRANCH_URL = "https://zakon.rada.gov.ua/laws/show/3720-20"
ROOT_SEARCH_URL = "https://zakon.rada.gov.ua/laws/find/a?text=%D0%BF%D1%96%D0%B4%D0%BF%D1%80%D0%B8%D1%94%D0%BC%D0%BD%D0%B8%D1%86%D1%82%D0%B2%D0%BE&mode=all&cat=1&search=1"

LAW_STRUCTURE = [
    {
        "sec_code_suffix": "10",
        "title": "Розділ I. Загальні положення",
        "articles": [
            ("Стаття 1", "Визначення термінів"),
            ("Стаття 2", "Законодавство про обов’язкове страхування цивільно-правової відповідальності"),
            ("Стаття 3", "Учасники ринку обов’язкового страхування цивільно-правової відповідальності"),
            ("Стаття 4", "Предмет та об’єкт договору обов’язкового страхування цивільно-правової відповідальності"),
            ("Стаття 5", "Страховий випадок"),
        ]
    },
    {
        "sec_code_suffix": "20",
        "title": "Розділ II. Укладення договорів обов’язкового страхування цивільно-правової відповідальності",
        "articles": [
            ("Стаття 6", "Види договорів обов’язкового страхування цивільно-правової відповідальності"),
            ("Стаття 7", "Обов’язковість страхування цивільно-правової відповідальності"),
            ("Стаття 8", "Єдина централізована база даних щодо обов’язкового страхування цивільно-правової відповідальності"),
            ("Стаття 9", "Перевірка наявності договорів обов’язкового страхування цивільно-правової відповідальності"),
            ("Стаття 10", "Право вибору страховика"),
            ("Стаття 11", "Укладення та строк дії договору обов’язкового страхування цивільно-правової відповідальності"),
            ("Стаття 12", "Визначення розміру страхової премії"),
            ("Стаття 13", "Особливості визначення розміру страхової премії для окремих категорій фізичних осіб"),
            ("Стаття 14", "Страхова сума"),
            ("Стаття 15", "Дострокове припинення договору обов’язкового страхування цивільно-правової відповідальності"),
            ("Стаття 16", "Чинність договору обов’язкового страхування цивільно-правової відповідальності у разі зміни власника забезпеченого транспортного засобу"),
            ("Стаття 17", "Інформаційна взаємодія"),
        ]
    },
    {
        "sec_code_suffix": "30",
        "title": "Розділ III. Порядок здійснення страхової (регламентної) виплати на території України",
        "articles": [
            ("Стаття 18", "Здійснення страхової (регламентної) виплати"),
            ("Стаття 19", "Пряме врегулювання страхового випадку"),
            ("Стаття 20", "Страхова (регламентна) виплата у разі заподіяння шкоди життю та здоров’ю потерпілої фізичної особи"),
            ("Стаття 21", "Страхова (регламентна) виплата у зв’язку з лікуванням потерпілої фізичної особи"),
            ("Стаття 22", "Страхова (регламентна) виплата у зв’язку з тимчасовою втратою працездатності потерпілою фізичною особою"),
            ("Стаття 23", "Страхова (регламентна) виплата у зв’язку із стійкою втратою чи зменшенням професійної або загальної працездатності потерпілої фізичної особи"),
            ("Стаття 24", "Визначення розміру моральної шкоди, заподіяної потерпілій фізичній особі"),
            ("Стаття 25", "Страхова (регламентна) виплата у зв’язку із смертю потерпілої фізичної особи"),
            ("Стаття 26", "Страхова (регламентна) виплата у разі заподіяння шкоди майну потерпілої особи"),
            ("Стаття 27", "Страхова (регламентна) виплата у разі пошкодження транспортного засобу"),
            ("Стаття 28", "Страхова (регламентна) виплата у разі знищення транспортного засобу"),
            ("Стаття 29", "Страхова (регламентна) виплата у разі пошкодження чи знищення іншого майна, ніж транспортний засіб"),
            ("Стаття 30", "Випадки, у яких страхова (регламентна) виплата не здійснюється"),
            ("Стаття 31", "Дії у разі настання дорожньо-транспортної пригоди"),
            ("Стаття 32", "Заява про страхову (регламентну) виплату та її розгляд страховиком (МТСБУ)"),
            ("Стаття 33", "Сприяння страховику (МТСБУ) у визначенні (з’ясуванні) причин, обставин та наслідків дорожньо-транспортної пригоди"),
            ("Стаття 34", "Повідомлення заявника про прийняте рішення за заявою про страхову (регламентну) виплату та порядок здійснення такої виплати"),
            ("Стаття 35", "Компенсація страховиком витрат особи, цивільно-правова відповідальність якої застрахована"),
            ("Стаття 36", "Правові наслідки порушення умов договору страхування та вимог цього Закону"),
            ("Стаття 37", "Право зворотної вимоги страховика (МТСБУ) до особи, відповідальної за заподіяння шкоди"),
            ("Стаття 38", "Право звернення до суду"),
            ("Стаття 39", "Здійснення страхової (регламентної) виплати у разі виникнення спору між страховиком та МТСБУ"),
        ]
    },
    {
        "sec_code_suffix": "40",
        "title": "Розділ IV. Моторне (транспортне) страхове бюро України",
        "articles": [
            ("Стаття 40", "Моторне (транспортне) страхове бюро України"),
            ("Стаття 41", "Основні завдання та функції МТСБУ"),
            ("Стаття 42", "Централізовані страхові резервні фонди МТСБУ"),
            ("Стаття 43", "Регламентні виплати з централізованих страхових резервних фондів МТСБУ"),
            ("Стаття 44", "Фінансове забезпечення діяльності МТСБУ"),
            ("Стаття 45", "Органи управління та контролю МТСБУ"),
            ("Стаття 46", "Загальні вимоги до системи управління МТСБУ"),
            ("Стаття 47", "Загальні збори членів МТСБУ"),
            ("Стаття 48", "Рада МТСБУ із загальних питань та рада МТСБУ з міжнародних питань"),
            ("Стаття 49", "Правління МТСБУ"),
            ("Стаття 50", "Звітність та зовнішній аудит МТСБУ"),
            ("Стаття 51", "Повноваження Національного банку України у сфері державного регулювання та нагляду за діяльністю МТСБУ"),
        ]
    },
    {
        "sec_code_suffix": "50",
        "title": "Розділ V. Вимоги до страховиків та членство в МТСБУ",
        "articles": [
            ("Стаття 52", "Умови здійснення обов’язкового страхування цивільно-правової відповідальності"),
            ("Стаття 53", "Умови і порядок набуття членства в МТСБУ"),
            ("Стаття 54", "Припинення членства в МТСБУ"),
        ]
    },
    {
        "sec_code_suffix": "60",
        "title": "Розділ VI. Прикінцеві та перехідні положення",
        "articles": []
    }
]


def build_entrepreneurship_tree():
    """Створює структуру категорії 180 та підкатегорії 180 10 зі всіма розділами та статтями."""
    sub_children = []

    for sec in LAW_STRUCTURE:
        sec_code = f"180 10 {sec['sec_code_suffix']}"
        sec_node = {
            "code": sec_code,
            "name": sec["title"],
            "clean_name": sec["title"],
            "level": 3,
            "parent_code": "180 10",
            "branch_url": "",
            "direct_url": "",
            "total_docs_count": 0,
            "direct_docs_count": 0,
            "cross_references": [],
            "children": []
        }

        art_idx = 10
        for a_num, a_title in sec["articles"]:
            art_code = f"{sec_code} {art_idx}"
            full_art_name = f"{a_num}. {a_title}"
            art_node = {
                "code": art_code,
                "name": full_art_name,
                "clean_name": full_art_name,
                "level": 4,
                "parent_code": sec_code,
                "branch_url": "",
                "direct_url": "",
                "total_docs_count": 0,
                "direct_docs_count": 0,
                "cross_references": [],
                "children": []
            }
            sec_node["children"].append(art_node)
            art_idx += 10

        sub_children.append(sec_node)

    law_node = {
        "code": "180 10",
        "name": "Закон України «Про обов’язкове страхування цивільно-правової відповідальності власників наземних транспортних засобів»",
        "clean_name": "Про обов’язкове страхування цивільно-правової відповідальності власників наземних транспортних засобів",
        "level": 2,
        "parent_code": "180",
        "branch_url": BRANCH_URL,
        "direct_url": LAW_URL,
        "total_docs_count": 0,
        "direct_docs_count": 0,
        "cross_references": [],
        "children": sub_children
    }

    root_node = {
        "code": "180",
        "name": "Підприємництво",
        "clean_name": "Підприємництво",
        "level": 1,
        "parent_code": "",
        "branch_url": ROOT_SEARCH_URL,
        "direct_url": LAW_URL,
        "total_docs_count": 0,
        "direct_docs_count": 0,
        "cross_references": [],
        "children": [law_node]
    }

    return root_node


def flatten_tree(nodes, parent_code="", parent_path_codes="", parent_path_names=""):
    """Рекурсивно розгортає дерево категорій у плоский список з обчисленням path_codes та path_names."""
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
    print("[*] Побудова структури категорії 180 'Підприємництво' та підкатегорії 180 10...")
    root_node = build_entrepreneurship_tree()
    total_arts = sum(len(s["articles"]) for s in LAW_STRUCTURE)
    print(f"    Створено 6 розділів та {total_arts} статей.")

    # 1. Оновлення classifier.json
    json_path = DATA_DIR / "classifier.json"
    print(f"[*] Оновлення {json_path}...")
    with open(json_path, "r", encoding="utf-8") as f:
        classifier_tree = json.load(f)

    # Видаляємо стару гілку 180, якщо вже була
    classifier_tree = [node for node in classifier_tree if node["code"] != "180"]
    classifier_tree.append(root_node)

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
            INSERT INTO categories_fts (code, name, clean_name, path_names, semantic_text)
            VALUES (?, ?, ?, ?, ?)
        """, (
            item["code"],
            item["name"],
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

    # 6. Синхронізація лічильників
    print("[*] Синхронізація лічильників співпадінь...")
    try:
        from sync_classifier_counts import compute_and_sync_counts
        compute_and_sync_counts()
    except Exception as e:
        print(f"⚠️ Помилка синхронізації лічильників: {e}")

    print(f"\n[SUCCESS] Успішно створено категорію 180 'Підприємництво' та підкатегорію 180 10 (6 розділів, {total_arts} статей). Всього {len(flat_all)} рубрик у класифікаторі!")


if __name__ == "__main__":
    update_all()
