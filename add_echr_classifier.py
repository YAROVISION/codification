#!/usr/bin/env python3
"""
Скрипт додавання підкатегорії 160 20 'Конвенція про захист прав людини і основоположних свобод'
до категорії 160 'Міжнародне право'.
Структура за Конвенцією про захист прав людини і основоположних свобод (995_004):
- Розділ I. Права і свободи (статті 1-18)
- Розділ II. Європейський суд з прав людини (статті 19-51)
- Розділ III. Інші положення (статті 52-59)
- Протоколи до Конвенції (Перший протокол, Протоколи № 4, 6, 7, 12, 13, 16)
із конкретизацією до статей включно.
"""

import sys
import json
import csv
import sqlite3
from datetime import datetime
from pathlib import Path

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

ECHR_URL = "https://zakon.rada.gov.ua/laws/show/995_004#Text"
ECHR_TITLE = "Конвенція про захист прав людини і основоположних свобод"

def build_echr_tree():
    """
    Побудова структури Конвенції про захист прав людини і основоположних свобод (№ 995_004).
    """
    sections = [
        {
            "suffix": "10",
            "title": "Розділ I. Права і свободи",
            "articles": [
                ("10", "Стаття 1. Зобов'язання поважати права людини"),
                ("20", "Стаття 2. Право на життя"),
                ("30", "Стаття 3. Заборона катування"),
                ("40", "Стаття 4. Заборона рабства і примусової праці"),
                ("50", "Стаття 5. Право на свободу та особисту недоторканність"),
                ("60", "Стаття 6. Право на справедливий суд"),
                ("70", "Стаття 7. Ніякого покарання без закону"),
                ("80", "Стаття 8. Право на повагу до приватного і сімейного життя"),
                ("90", "Стаття 9. Свобода думки, совісті і релігії"),
                ("100", "Стаття 10. Свобода вираження поглядів"),
                ("110", "Стаття 11. Свобода зібрань та об'єднань"),
                ("120", "Стаття 12. Право на шлюб"),
                ("130", "Стаття 13. Право на ефективний засіб юридичного захисту"),
                ("140", "Стаття 14. Заборона дискримінації"),
                ("150", "Стаття 15. Відступ від зобов'язань під час надзвичайної ситуації"),
                ("160", "Стаття 16. Обмеження політичної діяльності іноземців"),
                ("170", "Стаття 17. Заборона зловживання правами"),
                ("180", "Стаття 18. Межі застосування обмежень прав"),
            ]
        },
        {
            "suffix": "20",
            "title": "Розділ II. Європейський суд з прав людини",
            "articles": [
                ("10", "Стаття 19. Створення Суду"),
                ("20", "Стаття 20. Кількість суддів"),
                ("30", "Стаття 21. Посадові критерії"),
                ("40", "Стаття 22. Вибори суддів"),
                ("50", "Стаття 23. Строк повноважень і звільнення з посади"),
                ("60", "Стаття 24. Канцелярія, юридичні секретарі та доповідачі"),
                ("70", "Стаття 25. Пленарні засідання Суду"),
                ("80", "Стаття 26. Одноособовий склад Суду, комітети, палати та Велика палата"),
                ("90", "Стаття 27. Компетенція суддів, які засідають одноособово"),
                ("100", "Стаття 28. Компетенція комітетів"),
                ("110", "Стаття 29. Рішення палат щодо прийнятності та суті заяв"),
                ("120", "Стаття 30. Відмова від розгляду справи на користь Великої палати"),
                ("130", "Стаття 31. Повноваження Великої палати"),
                ("140", "Стаття 32. Юрисдикція Суду"),
                ("150", "Стаття 33. Міждержавні справи"),
                ("160", "Стаття 34. Індивідуальні заяви"),
                ("170", "Стаття 35. Умови прийнятності"),
                ("180", "Стаття 36. Участь третьої сторони"),
                ("190", "Стаття 37. Вилучення заяв з реєстру справ"),
                ("200", "Стаття 38. Розгляд справи"),
                ("210", "Стаття 39. Досягнення дружнього врегулювання"),
                ("220", "Стаття 40. Слухання у відкритому засіданні та доступ до документів"),
                ("230", "Стаття 41. Справедлива сатисфакція"),
                ("240", "Стаття 42. Рішення палат"),
                ("250", "Стаття 43. Передання справи на розгляд Великої палати"),
                ("260", "Стаття 44. Остаточні рішення у справі"),
                ("270", "Стаття 45. Умотивованість рішень у справі та ухвал"),
                ("280", "Стаття 46. Обов'язкова сила рішень та їх виконання"),
                ("290", "Стаття 47. Консультативні висновки"),
                ("300", "Стаття 48. Консультативна компетенція Суду"),
                ("310", "Стаття 49. Умотивованість консультативних висновків"),
                ("320", "Стаття 50. Витрати на забезпечення діяльності Суду"),
                ("330", "Стаття 51. Привілеї та імунітети суддів"),
            ]
        },
        {
            "suffix": "30",
            "title": "Розділ III. Інші положення",
            "articles": [
                ("10", "Стаття 52. Запити Генерального секретаря"),
                ("20", "Стаття 53. Гарантія визнаних прав людини"),
                ("30", "Стаття 54. Повноваження Комітету Міністрів"),
                ("40", "Стаття 55. Відмова від інших засобів урегулювання спорів"),
                ("50", "Стаття 56. Територіальне застосування"),
                ("60", "Стаття 57. Застереження"),
                ("70", "Стаття 58. Денонсація"),
                ("80", "Стаття 59. Підписання і ратифікація"),
            ]
        },
        {
            "suffix": "40",
            "title": "Перший протокол",
            "articles": [
                ("10", "Стаття 1. Захист права власності"),
                ("20", "Стаття 2. Право на освіту"),
                ("30", "Стаття 3. Право на вільні вибори"),
                ("40", "Стаття 4. Територіальне застосування"),
                ("50", "Стаття 5. Зв'язок з Конвенцією"),
                ("60", "Стаття 6. Підписання і ратифікація"),
            ]
        },
        {
            "suffix": "50",
            "title": "Протокол № 4",
            "articles": [
                ("10", "Стаття 1. Заборона позбавлення свободи за борги"),
                ("20", "Стаття 2. Свобода пересування"),
                ("30", "Стаття 3. Заборона вислання громадян"),
                ("40", "Стаття 4. Заборона колективного вислання іноземців"),
                ("50", "Стаття 5. Територіальне застосування"),
                ("60", "Стаття 6. Зв'язок з Конвенцією"),
            ]
        },
        {
            "suffix": "60",
            "title": "Протокол № 6 (щодо скасування смертної кари)",
            "articles": [
                ("10", "Стаття 1. Скасування смертної кари"),
                ("20", "Стаття 2. Смертна кара у воєнний час"),
                ("30", "Стаття 3. Заборона відступу від зобов'язань"),
                ("40", "Стаття 4. Заборона застережень"),
                ("50", "Стаття 5. Територіальне застосування"),
                ("60", "Стаття 6. Зв'язок з Конвенцією"),
            ]
        },
        {
            "suffix": "70",
            "title": "Протокол № 7",
            "articles": [
                ("10", "Стаття 1. Процедурні гарантії в разі вислання іноземців"),
                ("20", "Стаття 2. Право на апеляцію в кримінальних справах"),
                ("30", "Стаття 3. Відшкодування в разі судової помилки"),
                ("40", "Стаття 4. Право не бути судженим або покараним двічі"),
                ("50", "Стаття 5. Рівність прав чоловіків і жінок у шлюбі"),
                ("60", "Стаття 6. Територіальне застосування"),
                ("70", "Стаття 7. Зв'язок з Конвенцією"),
            ]
        },
        {
            "suffix": "80",
            "title": "Протокол № 12",
            "articles": [
                ("10", "Стаття 1. Загальна заборона дискримінації"),
                ("20", "Стаття 2. Територіальне застосування"),
                ("30", "Стаття 3. Зв'язок з Конвенцією"),
            ]
        },
        {
            "suffix": "90",
            "title": "Протокол № 13 (щодо скасування смертної кари за будь-яких обставин)",
            "articles": [
                ("10", "Стаття 1. Скасування смертної кари"),
                ("20", "Стаття 2. Заборона відступу від зобов'язань"),
                ("30", "Стаття 3. Заборона застережень"),
                ("40", "Стаття 4. Територіальне застосування"),
                ("50", "Стаття 5. Зв'язок з Конвенцією"),
            ]
        },
        {
            "suffix": "100",
            "title": "Протокол № 16",
            "articles": [
                ("10", "Стаття 1. Запити про надання консультативних висновків"),
                ("20", "Стаття 2. Прийняття запиту колегією Великої палати"),
                ("30", "Стаття 3. Надання консультативного висновку Великою палатою"),
                ("40", "Стаття 4. Участь третьої сторони"),
                ("50", "Стаття 5. Юридична сила консультативних висновків"),
            ]
        }
    ]

    root_code = "160 20"
    root_node = {
        "code": root_code,
        "level": 2,
        "name": ECHR_TITLE,
        "clean_name": ECHR_TITLE,
        "cross_references": [],
        "branch_url": ECHR_URL,
        "direct_url": ECHR_URL,
        "total_docs_count": 0,
        "direct_docs_count": 0,
        "children": []
    }

    for sec in sections:
        sec_code = f"{root_code} {sec['suffix']}"
        sec_title = sec["title"]
        sec_node = {
            "code": sec_code,
            "level": 3,
            "name": sec_title,
            "clean_name": sec_title,
            "cross_references": [],
            "branch_url": ECHR_URL,
            "direct_url": ECHR_URL,
            "total_docs_count": 0,
            "direct_docs_count": 0,
            "children": []
        }

        for art_suffix, art_title in sec["articles"]:
            art_code = f"{sec_code} {art_suffix}"
            art_node = {
                "code": art_code,
                "level": 4,
                "name": art_title,
                "clean_name": art_title,
                "cross_references": [],
                "branch_url": ECHR_URL,
                "direct_url": ECHR_URL,
                "total_docs_count": 0,
                "direct_docs_count": 0,
                "children": []
            }
            sec_node["children"].append(art_node)

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

    cat_160 = None
    for cat in classifier_tree:
        if cat["code"] == "160":
            cat_160 = cat
            break

    if not cat_160:
        raise ValueError("Категорію 160 'Міжнародне право' не знайдено в classifier.json")

    print("[+] Створення структури 'Конвенція про захист прав людини і основоположних свобод' (160 20)...")
    echr_node = build_echr_tree()

    # Оновлення або додавання 160 20 до children категорії 160
    existing_children = [c for c in cat_160.get("children", []) if c["code"] != "160 20"]
    existing_children.append(echr_node)
    # Сортуємо children категорії 160 за кодом
    existing_children.sort(key=lambda x: [int(p) for p in x["code"].split()])
    cat_160["children"] = existing_children

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

    echr_count = sum(1 for it in flat_all if it["code"].startswith("160 20"))
    print(f"\n[SUCCESS] Успішно додано підкатегорію 160 20 'Конвенція про захист прав людини і основоположних свобод' ({echr_count} рубрик).")
    print(f"Всього {len(flat_all)} рубрик у класифікаторі!")

if __name__ == "__main__":
    update_all()
