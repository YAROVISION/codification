#!/usr/bin/env python3
"""
Скрипт додавання підкатегорії 180 30 'Закон України «Про адвокатуру та адвокатську діяльність»'
до категорії 180 'Підприємництво'.
Структура за Законом України № 5076-VI:
- Розділи I - X
- Статті 1 - 61 із конкретизацією до статей включно.
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

ADVOCACY_URL = "https://zakon.rada.gov.ua/laws/show/5076-17#Text"
ADVOCACY_NAME = "Закон України «Про адвокатуру та адвокатську діяльність»"
ADVOCACY_CLEAN_NAME = "Про адвокатуру та адвокатську діяльність"

def build_advocacy_tree():
    """
    Побудова структури Закону України «Про адвокатуру та адвокатську діяльність» (№ 5076-VI).
    """
    sections = [
        {
            "suffix": "10",
            "title": "Розділ I. Загальні положення",
            "articles": [
                ("10", "Стаття 1. Визначення основних термінів"),
                ("20", "Стаття 2. Адвокатура України"),
                ("30", "Стаття 3. Правова основа діяльності адвокатури України"),
                ("40", "Стаття 4. Принципи та засади здійснення адвокатської діяльності"),
                ("50", "Стаття 5. Адвокатура і держава"),
            ]
        },
        {
            "suffix": "20",
            "title": "Розділ II. Набуття права на заняття адвокатською діяльністю. Організаційні форми адвокатської діяльності",
            "articles": [
                ("10", "Стаття 6. Адвокат"),
                ("20", "Стаття 7. Вимоги щодо несумісності"),
                ("30", "Стаття 8. Допуск до складення кваліфікаційного іспиту"),
                ("40", "Стаття 9. Кваліфікаційний іспит"),
                ("50", "Стаття 10. Стажист адвоката. Стажування"),
                ("60", "Стаття 11. Присяга адвоката України"),
                ("70", "Стаття 12. Свідоцтво про право на заняття адвокатською діяльністю, посвідчення адвоката України"),
                ("80", "Стаття 13. Здійснення адвокатської діяльності адвокатом індивідуально"),
                ("90", "Стаття 14. Адвокатське бюро"),
                ("100", "Стаття 15. Адвокатське об’єднання"),
                ("110", "Стаття 16. Помічник адвоката"),
                ("120", "Стаття 17. Єдиний реєстр адвокатів України"),
                ("130", "Стаття 18. Об’єднання адвокатів"),
            ]
        },
        {
            "suffix": "30",
            "title": "Розділ III. Види адвокатської діяльності. Права і обов’язки адвоката. Гарантії адвокатської діяльності",
            "articles": [
                ("10", "Стаття 19. Види адвокатської діяльності"),
                ("20", "Стаття 20. Професійні права адвоката"),
                ("30", "Стаття 21. Професійні обов’язки адвоката"),
                ("40", "Стаття 22. Адвокатська таємниця"),
                ("50", "Стаття 23. Гарантії адвокатської діяльності"),
                ("60", "Стаття 24. Адвокатський запит"),
                ("70", "Стаття 25. Надання адвокатом безоплатної правничої допомоги"),
            ]
        },
        {
            "suffix": "40",
            "title": "Розділ IV. Договір про надання правничої допомоги",
            "articles": [
                ("10", "Стаття 26. Підстави для здійснення адвокатської діяльності"),
                ("20", "Стаття 27. Форма та зміст договору про надання правничої допомоги"),
                ("30", "Стаття 28. Підстави для відмови в укладенні договору про надання правничої допомоги"),
                ("40", "Стаття 29. Припинення, розірвання договору про надання правничої допомоги"),
                ("50", "Стаття 30. Гонорар"),
            ]
        },
        {
            "suffix": "50",
            "title": "Розділ V. Зупинення та припинення права на заняття адвокатською діяльністю",
            "articles": [
                ("10", "Стаття 31. Зупинення права на заняття адвокатською діяльністю"),
                ("20", "Стаття 32. Припинення права на заняття адвокатською діяльністю"),
            ]
        },
        {
            "suffix": "60",
            "title": "Розділ VI. Дисциплінарна відповідальність адвоката",
            "articles": [
                ("10", "Стаття 33. Загальні умови дисциплінарної відповідальності адвоката"),
                ("20", "Стаття 34. Підстави для притягнення адвоката до дисциплінарної відповідальності"),
                ("30", "Стаття 35. Види дисциплінарних стягнень, строк застосування дисциплінарних стягнень"),
                ("40", "Стаття 36. Ініціювання питання про дисциплінарну відповідальність адвоката"),
                ("50", "Стаття 37. Стадії дисциплінарного провадження"),
                ("60", "Стаття 38. Перевірка відомостей про дисциплінарний проступок адвоката"),
                ("70", "Стаття 39. Порушення дисциплінарної справи"),
                ("80", "Стаття 40. Розгляд дисциплінарної справи"),
                ("90", "Стаття 41. Прийняття рішення у дисциплінарній справі"),
                ("100", "Стаття 42. Оскарження рішення у дисциплінарній справі"),
            ]
        },
        {
            "suffix": "70",
            "title": "Розділ VII. Адвокатське самоврядування",
            "articles": [
                ("10", "Стаття 43. Засади адвокатського самоврядування"),
                ("20", "Стаття 44. Завдання адвокатського самоврядування"),
                ("30", "Стаття 45. Національна асоціація адвокатів України"),
                ("40", "Стаття 46. Організаційні форми адвокатського самоврядування"),
                ("50", "Стаття 47. Конференція адвокатів регіону"),
                ("60", "Стаття 48. Рада адвокатів регіону"),
                ("70", "Стаття 49. Голова ради адвокатів регіону"),
                ("80", "Стаття 50. Кваліфікаційно-дисциплінарна комісія адвокатури"),
                ("90", "Стаття 51. Ревізійна комісія адвокатів регіону"),
                ("100", "Стаття 52. Вища кваліфікаційно-дисциплінарна комісія адвокатури"),
                ("110", "Стаття 53. Вища ревізійна комісія адвокатури"),
                ("120", "Стаття 54. З’їзд адвокатів України"),
                ("130", "Стаття 55. Рада адвокатів України"),
                ("140", "Стаття 56. Голова Ради адвокатів України"),
                ("150", "Стаття 57. Обов’язковість рішень органів адвокатського самоврядування"),
                ("160", "Стаття 58. Фінансове забезпечення органів адвокатського самоврядування"),
            ]
        },
        {
            "suffix": "80",
            "title": "Розділ VIII. Здійснення в Україні адвокатської діяльності адвокатом іноземної держави. Особливості статусу адвоката іноземної держави",
            "articles": [
                ("10", "Стаття 59. Набуття адвокатом іноземної держави права на заняття адвокатською діяльністю в Україні. Особливості статусу адвоката іноземної держави"),
                ("20", "Стаття 60. Відповідальність адвоката іноземної держави"),
                ("30", "Стаття 61. Відносини адвоката іноземної держави з органами адвокатського самоврядування"),
            ]
        },
        {
            "suffix": "90",
            "title": "Розділ IX. Прикінцеві положення",
            "articles": []
        },
        {
            "suffix": "100",
            "title": "Розділ X. Перехідні положення",
            "articles": []
        }
    ]

    root_code = "180 30"
    root_node = {
        "code": root_code,
        "level": 2,
        "name": ADVOCACY_NAME,
        "clean_name": ADVOCACY_CLEAN_NAME,
        "cross_references": [],
        "branch_url": ADVOCACY_URL,
        "direct_url": ADVOCACY_URL,
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
            "branch_url": ADVOCACY_URL,
            "direct_url": ADVOCACY_URL,
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
                "branch_url": "",
                "direct_url": "",
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

    cat_180 = None
    for cat in classifier_tree:
        if cat["code"] == "180":
            cat_180 = cat
            break

    if not cat_180:
        raise ValueError("Категорію 180 'Підприємництво' не знайдено в classifier.json")

    print("[+] Створення структури 'Закон України «Про адвокатуру та адвокатську діяльність»' (180 30)...")
    advocacy_node = build_advocacy_tree()

    # Оновлення або додавання 180 30 до children категорії 180
    existing_children = [c for c in cat_180.get("children", []) if c["code"] != "180 30"]
    existing_children.append(advocacy_node)
    # Сортуємо children категорії 180 за кодом
    existing_children.sort(key=lambda x: [int(p) for p in x["code"].split()])
    cat_180["children"] = existing_children

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

    adv_count = sum(1 for it in flat_all if it["code"].startswith("180 30"))
    print(f"\n[SUCCESS] Успішно додано підкатегорію 180 30 'Закон України «Про адвокатуру та адвокатську діяльність»' ({adv_count} рубрик).")
    print(f"Всього {len(flat_all)} рубрик у класифікаторі!")

if __name__ == "__main__":
    update_all()
