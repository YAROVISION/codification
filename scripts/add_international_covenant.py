#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
add_international_covenant.py
Додає рубрику 'Міжнародне право' (160) та підрозділ
'Міжнародний пакт про громадянські і політичні права' (160 10)
з 6 частинами та 53 статтями до класифікатора в усіх 5 форматах:
1. data/classifier.json
2. data/classifier_flat.json
3. data/classifier.sqlite (categories, categories_fts)
4. data/classifier.csv
5. data/classifier.md
"""

import json
import sqlite3
import csv
import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

PARTS_AND_ARTICLES = [
    {
        "part_num": 10,
        "part_name": "Частина I",
        "articles": [
            (10, 1, "Право народів на самовизначення")
        ]
    },
    {
        "part_num": 20,
        "part_name": "Частина II",
        "articles": [
            (10, 2, "Забезпечення прав без дискримінації та правові засоби захисту"),
            (20, 3, "Рівні права чоловіків і жінок"),
            (30, 4, "Відступ від зобов'язань під час надзвичайного становища"),
            (40, 5, "Заборона зловживання правами та неприпустимість їх звуження")
        ]
    },
    {
        "part_num": 30,
        "part_name": "Частина III",
        "articles": [
            (10, 6, "Право на життя"),
            (20, 7, "Заборона катувань, нелюдського або такого, що принижує гідність, поводження чи покарання"),
            (30, 8, "Заборона рабства, підневільного стану та примусової праці"),
            (40, 9, "Право на свободу та особисту недоторканність"),
            (50, 10, "Гуманне поводження з особами, позбавленими волі"),
            (60, 11, "Заборона позбавлення волі за невиконання договірного зобов'язання"),
            (70, 12, "Свобода пересування та вибору місця проживання"),
            (80, 13, "Процедурні гарантії при висланні іноземців"),
            (90, 14, "Право на справедливий судовий розгляд та презумпція невинуватості"),
            (100, 15, "Заборона зворотної дії кримінального закону"),
            (110, 16, "Право на визнання правосуб'єктності"),
            (120, 17, "Захист від свавільного втручання в особисте і сімейне життя"),
            (130, 18, "Свобода думки, совісті та релігії"),
            (140, 19, "Свобода вираження поглядів та думок"),
            (150, 20, "Заборона пропаганди війни та розпалювання ворожнечі"),
            (160, 21, "Право на мирні збори"),
            (170, 22, "Свобода асоціацій та створення професійних спілок"),
            (180, 23, "Захист сім'ї та право на шлюб"),
            (190, 24, "Права дитини та захист її інтересів"),
            (200, 25, "Право на участь у веденні державних справ та виборчі права"),
            (210, 26, "Рівність перед законом і недискримінація"),
            (220, 27, "Права етнічних, релігійних та мовних меншин")
        ]
    },
    {
        "part_num": 40,
        "part_name": "Частина IV",
        "articles": [
            (10, 28, "Заснування Комітету з прав людини"),
            (20, 29, "Склад та вибори членів Комітету з прав людини"),
            (30, 30, "Порядок проведення виборів членів Комітету"),
            (40, 31, "Представництво держав у складі Комітету"),
            (50, 32, "Строк повноважень членів Комітету"),
            (60, 33, "Заповнення вакансій у разі припинення обов'язків члена Комітету"),
            (70, 34, "Процедура обрання на відкриті вакансії"),
            (80, 35, "Винагорода членам Комітету"),
            (90, 36, "Забезпечення діяльності Комітету секретаріатом ООН"),
            (100, 37, "Скликання засідань Комітету"),
            (110, 38, "Урочиста заява членів Комітету"),
            (120, 39, "Посадові особи та правила процедури Комітету"),
            (130, 40, "Доповіді держав-учасниць про здійснення прав"),
            (140, 41, "Розгляд Комітетом повідомлень про невиконання зобов'язань державою"),
            (150, 42, "Призначення Спеціальної погоджувальної комісії"),
            (160, 43, "Привілеї та імунітети членів Комітету та погоджувальної комісії"),
            (170, 44, "Співвідношення положень щодо врегулювання спорів з іншими процедурами"),
            (180, 45, "Щорічна доповідь Комітету Генеральній Асамблеї ООН")
        ]
    },
    {
        "part_num": 50,
        "part_name": "Частина V",
        "articles": [
            (10, 46, "Тлумачення положень щодо Статуту Організації Об'єднаних Націй"),
            (20, 47, "Невід'ємне право народів володіти та користуватися природними багатствами")
        ]
    },
    {
        "part_num": 60,
        "part_name": "Частина VI",
        "articles": [
            (10, 48, "Підписання, ратифікація та приєднання до Пакту"),
            (20, 49, "Набрання чинності Пактом"),
            (30, 50, "Поширення дії Пакту на всі частини федеративних держав"),
            (40, 51, "Порядок внесення поправок до Пакту"),
            (50, 52, "Повідомлення Генерального секретаря ООН"),
            (60, 53, "Автентичність текстів та зберігання примірників Пакту")
        ]
    }
]

def build_international_law_tree():
    root_code = "160"
    root_name = "Міжнародне право"
    covenant_code = "160 10"
    covenant_name = "Міжнародний пакт про громадянські і політичні права"
    covenant_url = "https://zakon.rada.gov.ua/laws/show/995_043#Text"

    covenant_children = []

    for part_info in PARTS_AND_ARTICLES:
        part_code = f"{covenant_code} {part_info['part_num']}"
        part_name = part_info["part_name"]
        part_path_codes = f"{root_code} / {covenant_code} / {part_code}"
        part_path_names = f"{root_name} / {covenant_name} / {part_name}"

        article_children = []
        for art_code_suffix, art_num, art_title in part_info["articles"]:
            art_code = f"{part_code} {art_code_suffix}"
            art_name = f"Стаття {art_num}. {art_title}"
            art_path_codes = f"{part_path_codes} / {art_code}"
            art_path_names = f"{part_path_names} / {art_name}"

            art_node = {
                "code": art_code,
                "level": 4,
                "name": art_name,
                "clean_name": art_name,
                "parent_code": part_code,
                "path_codes": art_path_codes,
                "path_names": art_path_names,
                "cross_references": [],
                "branch_url": "",
                "direct_url": "",
                "total_docs_count": 0,
                "direct_docs_count": 0,
                "has_children": False,
                "children_count": 0,
                "children": []
            }
            article_children.append(art_node)

        part_node = {
            "code": part_code,
            "level": 3,
            "name": part_name,
            "clean_name": part_name,
            "parent_code": covenant_code,
            "path_codes": part_path_codes,
            "path_names": part_path_names,
            "cross_references": [],
            "branch_url": "",
            "direct_url": "",
            "total_docs_count": 0,
            "direct_docs_count": 0,
            "has_children": True,
            "children_count": len(article_children),
            "children": article_children
        }
        covenant_children.append(part_node)

    covenant_node = {
        "code": covenant_code,
        "level": 2,
        "name": covenant_name,
        "clean_name": covenant_name,
        "parent_code": root_code,
        "path_codes": f"{root_code} / {covenant_code}",
        "path_names": f"{root_name} / {covenant_name}",
        "cross_references": [],
        "branch_url": covenant_url,
        "direct_url": covenant_url,
        "total_docs_count": 0,
        "direct_docs_count": 0,
        "has_children": True,
        "children_count": len(covenant_children),
        "children": covenant_children
    }

    root_node = {
        "code": root_code,
        "level": 1,
        "name": root_name,
        "clean_name": root_name,
        "parent_code": "",
        "path_codes": root_code,
        "path_names": root_name,
        "cross_references": [],
        "branch_url": covenant_url,
        "direct_url": covenant_url,
        "total_docs_count": 0,
        "direct_docs_count": 0,
        "has_children": True,
        "children_count": 1,
        "children": [covenant_node]
    }

    return root_node


def flatten_tree(nodes):
    flat = []
    def recurse(node):
        item = {k: v for k, v in node.items() if k != "children"}
        flat.append(item)
        for child in node.get("children", []):
            recurse(child)
    for n in nodes:
        recurse(n)
    return flat


def export_markdown(nodes):
    lines = ["# Класифікатор законодавства України\n"]
    flat = flatten_tree(nodes)
    lines.append(f"Всього категорій: {len(flat)}\n")

    def recurse(node):
        indent = "  " * (node["level"] - 1)
        lines.append(f"{indent}- **{node['code']}** {node['name']}")
        for child in node.get("children", []):
            recurse(child)

    for n in nodes:
        recurse(n)
    return "\n".join(lines) + "\n"


def export_csv(flat_nodes, filepath):
    headers = [
        "Код", "Рівень", "Назва", "Очищена назва", "Батьківський код",
        "Ієрархічний код", "Ієрархічний шлях", "Всього актів", "Прямих актів",
        "Має підкатегорії", "Кількість підкатегорій", "Посилання на гілку", "Пряме посилання"
    ]
    with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for item in flat_nodes:
            writer.writerow([
                item["code"],
                item["level"],
                item["name"],
                item["clean_name"],
                item["parent_code"],
                item["path_codes"],
                item["path_names"],
                item["total_docs_count"],
                item["direct_docs_count"],
                1 if item["has_children"] else 0,
                item["children_count"],
                item.get("branch_url", ""),
                item.get("direct_url", "")
            ])


def main():
    json_path = DATA_DIR / "classifier.json"
    with open(json_path, "r", encoding="utf-8") as f:
        classifier_tree = json.load(f)

    # Перевірка: чи вже є рубрика 160
    existing = [n for n in classifier_tree if n["code"] == "160"]
    if existing:
        print("Рубрика 160 вже існує. Замінюємо її оновленою гілкою...")
        classifier_tree = [n for n in classifier_tree if n["code"] != "160"]

    new_root = build_international_law_tree()
    classifier_tree.append(new_root)

    print(f"Збереження classifier.json... (галузей: {len(classifier_tree)})")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(classifier_tree, f, ensure_ascii=False, indent=2)

    flat_list = flatten_tree(classifier_tree)
    flat_path = DATA_DIR / "classifier_flat.json"
    print(f"Збереження classifier_flat.json... (всього категорій: {len(flat_list)})")
    with open(flat_path, "w", encoding="utf-8") as f:
        json.dump(flat_list, f, ensure_ascii=False, indent=2)

    csv_path = DATA_DIR / "classifier.csv"
    print("Збереження classifier.csv...")
    export_csv(flat_list, csv_path)

    md_path = DATA_DIR / "classifier.md"
    print("Збереження classifier.md...")
    md_content = export_markdown(classifier_tree)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    # Оновлення SQLite
    sqlite_path = DATA_DIR / "classifier.sqlite"
    print("Оновлення classifier.sqlite (categories, categories_fts)...")
    conn = sqlite3.connect(sqlite_path)
    cur = conn.cursor()

    # Отримуємо нові категорії для додавання
    new_flat = flatten_tree([new_root])
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Видаляємо з categories та fts старі записи 160 (якщо були)
    cur.execute("DELETE FROM categories WHERE code LIKE '160%'")
    cur.execute("DELETE FROM categories_fts WHERE code LIKE '160%'")

    for item in new_flat:
        sem_text = f"{item['name']}. Шлях: {item['path_names']}. Код: {item['code']}."
        cur.execute("""
            INSERT INTO categories (
                code, parent_code, level, name, clean_name, path_codes, path_names,
                has_children, children_count, total_docs_count, direct_docs_count,
                branch_url, direct_url, cross_references, semantic_text,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item["code"],
            item["parent_code"],
            item["level"],
            item["name"],
            item["clean_name"],
            item["path_codes"],
            item["path_names"],
            1 if item["has_children"] else 0,
            item["children_count"],
            item["total_docs_count"],
            item["direct_docs_count"],
            item.get("branch_url", ""),
            item.get("direct_url", ""),
            "[]",
            sem_text,
            now_str,
            now_str
        ))

        cur.execute("""
            INSERT INTO categories_fts (
                code, name, clean_name, path_names, semantic_text
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            item["code"],
            item["name"],
            item["clean_name"],
            item["path_names"],
            sem_text
        ))

    conn.commit()
    conn.close()
    print(f"Успішно додано {len(new_flat)} категорій до бази даних!")

if __name__ == "__main__":
    main()
