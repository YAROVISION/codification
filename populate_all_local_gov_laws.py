#!/usr/bin/env python3
"""
Скрипт повного наповнення категорії 110 'Органи влади':
1. Додавання 11 підкатегорій (базових законів про органи влади та місцеве самоврядування)
2. Прикріплення списку direct_acts (із 12 законів з прямими посиланнями)
3. Вилучення пошукового URL з direct_url для 110 (щоб не відкривав пошук на ВРУ)
Оновлює:
- data/classifier.json
- data/classifier_flat.json
- data/classifier.sqlite
- data/classifier.csv
- data/classifier.md
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

DIRECT_ACTS_LIST = [
    {
        "title": "Закон України «Про місцеве самоврядування в Україні»",
        "number": "№ 280/97-ВР від 21.05.1997",
        "url": "https://zakon.rada.gov.ua/laws/show/280/97-%D0%B2%D1%80",
        "type": "Базовий профільний закон",
        "description": "Визначає систему, функції, повноваження та гарантії місцевого самоврядування в Україні, статус рад, голів та виконавчих органів."
    },
    {
        "title": "Закон України «Про державну службу»",
        "number": "№ 889-VIII від 10.12.2015",
        "url": "https://zakon.rada.gov.ua/laws/show/889-19",
        "type": "Публічна служба",
        "description": "Встановлює принципи, правові та організаційні засади забезпечення професійної державної служби в органах державної влади."
    },
    {
        "title": "Закон України «Про службу в органах місцевого самоврядування»",
        "number": "№ 2493-III від 07.06.2001",
        "url": "https://zakon.rada.gov.ua/laws/show/2493-14",
        "type": "Муніципальна служба",
        "description": "Регулює правовий статус посадових осіб місцевого самоврядування, порядок прийняття на службу, проходження та припинення служби."
    },
    {
        "title": "Закон України «Про службу в органах місцевого самоврядування» (нова редакція)",
        "number": "№ 3077-IX від 02.05.2023",
        "url": "https://zakon.rada.gov.ua/laws/show/3077-20",
        "type": "Реформа служби в ОМС",
        "description": "Системна реформа служби в ОМС на засадах відкритого конкурсу, нової грейдової системи оплати праці та політичної неупередженості."
    },
    {
        "title": "Закон України «Про статус депутатів місцевих рад»",
        "number": "№ 93-IV від 11.07.2002",
        "url": "https://zakon.rada.gov.ua/laws/show/93-15",
        "type": "Представницький мандат",
        "description": "Визначає статус, права, обов'язки, гарантії депутатської діяльності депутатів сільських, селищних, міських, районних і обласних рад."
    },
    {
        "title": "Закон України «Про органи самоорганізації населення»",
        "number": "№ 2625-III від 11.07.2001",
        "url": "https://zakon.rada.gov.ua/laws/show/2625-14",
        "type": "Громадське самоврядування",
        "description": "Порядок створення та діяльності будинкових, вуличних, квартальних комітетів, комітетів мікрорайонів і районів у містах."
    },
    {
        "title": "Закон України «Про співробітництво територіальних громад»",
        "number": "№ 1508-VII від 17.06.2014",
        "url": "https://zakon.rada.gov.ua/laws/show/1508-18",
        "type": "Міжмуніципальне співробітництво",
        "description": "Організаційно-правові засади реалізації спільних проєктів, співфінансування установ та делегування повноважень між громадами."
    },
    {
        "title": "Закон України «Про добровільне об'єднання територіальних громад»",
        "number": "№ 157-VIII від 05.02.2015",
        "url": "https://zakon.rada.gov.ua/laws/show/157-19",
        "type": "Децентралізація",
        "description": "Регулює відносини добровільного об'єднання територіальних громад сіл, селищ, міст у спроможні територіальні громади."
    },
    {
        "title": "Закон України «Про порядок вирішення окремих питань адміністративно-територіального устрою України»",
        "number": "№ 3285-IX від 28.07.2023",
        "url": "https://zakon.rada.gov.ua/laws/show/3285-20",
        "type": "Територіальний устрій",
        "description": "Порядок утворення, ліквідації, встановлення та зміни меж населених пунктів і районів, категоризація міст, селищ, сіл."
    },
    {
        "title": "Закон України «Про асоціації органів місцевого самоврядування»",
        "number": "№ 1275-VI від 16.04.2009",
        "url": "https://zakon.rada.gov.ua/laws/show/1275-17",
        "type": "Асоціації ОМС",
        "description": "Правові та організаційні засади створення і діяльності всеукраїнських та регіональних асоціацій органів місцевого самоврядування."
    },
    {
        "title": "Закон України «Про засади державної регіональної політики»",
        "number": "№ 156-VIII від 05.02.2015",
        "url": "https://zakon.rada.gov.ua/laws/show/156-19",
        "type": "Регіональний розвиток",
        "description": "Визначає принципи та механізми державної підтримки соціально-економічного розвитку регіонів і територіальних громад."
    },
    {
        "title": "Закон України «Про столицю України - місто-герой Київ»",
        "number": "№ 401-XIV від 15.01.1999",
        "url": "https://zakon.rada.gov.ua/laws/show/401-14",
        "type": "Спеціальний статус",
        "description": "Спеціальний закон, що визначає систему місцевого самоврядування та виконавчої влади у місті Києві."
    }
]

OTHER_LAWS_SUBCATS = [
    {
        "code": "110 30",
        "title": "Закон України «Про службу в органах місцевого самоврядування»",
        "direct_url": "https://zakon.rada.gov.ua/laws/show/2493-14"
    },
    {
        "code": "110 40",
        "title": "Закон України «Про статус депутатів місцевих рад»",
        "direct_url": "https://zakon.rada.gov.ua/laws/show/93-15"
    },
    {
        "code": "110 50",
        "title": "Закон України «Про органи самоорганізації населення»",
        "direct_url": "https://zakon.rada.gov.ua/laws/show/2625-14"
    },
    {
        "code": "110 60",
        "title": "Закон України «Про співробітництво територіальних громад»",
        "direct_url": "https://zakon.rada.gov.ua/laws/show/1508-18"
    },
    {
        "code": "110 70",
        "title": "Закон України «Про добровільне об'єднання територіальних громад»",
        "direct_url": "https://zakon.rada.gov.ua/laws/show/157-19"
    },
    {
        "code": "110 80",
        "title": "Закон України «Про порядок вирішення окремих питань адміністративно-територіального устрою України»",
        "direct_url": "https://zakon.rada.gov.ua/laws/show/3285-20"
    },
    {
        "code": "110 90",
        "title": "Закон України «Про асоціації органів місцевого самоврядування»",
        "direct_url": "https://zakon.rada.gov.ua/laws/show/1275-17"
    },
    {
        "code": "110 100",
        "title": "Закон України «Про засади державної регіональної політики»",
        "direct_url": "https://zakon.rada.gov.ua/laws/show/156-19"
    },
    {
        "code": "110 110",
        "title": "Закон України «Про столицю України - місто-герой Київ»",
        "direct_url": "https://zakon.rada.gov.ua/laws/show/401-14"
    }
]

def make_search_url(query: str) -> str:
    params = {
        "text": query,
        "mode": "all",
        "cat": "1",
        "search": "1"
    }
    return f"https://zakon.rada.gov.ua/laws/find/a?{urllib.parse.urlencode(params)}"

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
            "direct_acts": node.get("direct_acts", []),
            "branch_url": node.get("branch_url", ""),
            "direct_url": node.get("direct_url", ""),
            "total_docs_count": node.get("total_docs_count", 0),
            "direct_docs_count": node.get("direct_docs_count", len(node.get("direct_acts", []))),
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

    # Встановлюємо direct_acts та вимикаємо пошук
    cat_110["direct_acts"] = DIRECT_ACTS_LIST
    cat_110["direct_docs_count"] = len(DIRECT_ACTS_LIST)
    cat_110["direct_url"] = ""  # Не відкривати пошук
    cat_110["branch_url"] = "https://zakon.rada.gov.ua/laws/main/perv"  # Первинні акти ВРУ

    # Зберігаємо існуючі 110 10 та 110 20
    existing_children = cat_110.get("children", [])
    node_110_10 = next((c for c in existing_children if c["code"] == "110 10"), None)
    node_110_20 = next((c for c in existing_children if c["code"] == "110 20"), None)

    if node_110_10:
        node_110_10["direct_acts"] = [a for a in DIRECT_ACTS_LIST if "державну службу" in a["title"].lower()]
        node_110_10["direct_docs_count"] = len(node_110_10["direct_acts"])
        node_110_10["direct_url"] = "https://zakon.rada.gov.ua/laws/show/889-19"

    if node_110_20:
        node_110_20["direct_acts"] = DIRECT_ACTS_LIST
        node_110_20["direct_docs_count"] = len(DIRECT_ACTS_LIST)
        node_110_20["direct_url"] = "https://zakon.rada.gov.ua/laws/show/280/97-%D0%B2%D1%80"

    new_children = []
    if node_110_10:
        new_children.append(node_110_10)
    if node_110_20:
        new_children.append(node_110_20)

    # Додаємо інші підкатегорії законів
    for sub in OTHER_LAWS_SUBCATS:
        sub_code = sub["code"]
        sub_title = sub["title"]
        sub_url = sub["direct_url"]
        
        matching_acts = [a for a in DIRECT_ACTS_LIST if sub_title.lower() in a["title"].lower() or a["title"].lower() in sub_title.lower()]
        if not matching_acts:
            matching_acts = [{
                "title": sub_title,
                "number": "",
                "url": sub_url,
                "type": "Закон України",
                "description": f"Офіційний текст закону на порталі Верховної Ради України."
            }]

        sub_node = {
            "code": sub_code,
            "level": 2,
            "name": sub_title,
            "clean_name": sub_title,
            "cross_references": [],
            "direct_acts": matching_acts,
            "branch_url": make_search_url(sub_title),
            "direct_url": sub_url,
            "total_docs_count": 0,
            "direct_docs_count": len(matching_acts),
            "children": []
        }
        new_children.append(sub_node)

    cat_110["children"] = new_children

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
                direct_acts, branch_url, direct_url,
                total_docs_count, direct_docs_count,
                has_children, children_count, semantic_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item["code"],
            item["level"],
            item["name"],
            item["clean_name"],
            item["parent_code"],
            item["path_codes"],
            item["path_names"],
            json.dumps(item["cross_references"], ensure_ascii=False),
            json.dumps(item.get("direct_acts", []), ensure_ascii=False),
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

    print(f"\n[SUCCESS] Успішно наповнено категорію 110. Всього {len(flat_all)} рубрик у класифікаторі!")

if __name__ == "__main__":
    update_all()
