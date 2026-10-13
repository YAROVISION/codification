#!/usr/bin/env python3
"""
Скрипт перерахунку та синхронізації кількості співпадінь (судової практики та ін.)
у дереві класифікатора законодавства для всіх 5 форматів:
1. data/classifier.json
2. data/classifier_flat.json
3. data/classifier.sqlite (таблиця categories)
4. data/classifier.csv
5. data/classifier.md
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
DB_PATH = DATA_DIR / "classifier.sqlite"
JSON_TREE_PATH = DATA_DIR / "classifier.json"
FLAT_JSON_PATH = DATA_DIR / "classifier_flat.json"
CSV_PATH = DATA_DIR / "classifier.csv"
MD_PATH = DATA_DIR / "classifier.md"


def compute_and_sync_counts():
    print("[*] Підключення до бази даних...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Рахуємо прямі співпадіння з mapped_segments
    cur.execute("SELECT category_code, COUNT(*) FROM mapped_segments GROUP BY category_code")
    direct_counts = dict(cur.fetchall())
    total_matches = sum(direct_counts.values())
    print(f"    Знайдено {len(direct_counts)} категорій із прямими співпадіннями (всього {total_matches} зв'язків).")

    # 2. Завантажуємо classifier.json
    if not JSON_TREE_PATH.exists():
        raise FileNotFoundError(f"{JSON_TREE_PATH} не знайдено!")

    with open(JSON_TREE_PATH, "r", encoding="utf-8") as f:
        tree = json.load(f)

    # 3. Рекурсивне обчислення total_docs_count (direct + сума дітей)
    counts_map = {}  # code -> (direct, total)

    def process_node(node):
        code = node["code"]
        direct = direct_counts.get(code, 0)
        node["direct_docs_count"] = direct

        children = node.get("children", [])
        children_sum = 0
        if children:
            for child in children:
                children_sum += process_node(child)
        
        total = direct + children_sum
        node["total_docs_count"] = total
        counts_map[code] = (direct, total)
        return total

    for root_node in tree:
        process_node(root_node)

    root_total = sum(counts_map[r["code"]][1] for r in tree)
    print(f"    Сумарна кількість співпадінь по коренях 1-го рівня: {root_total}")

    # 4. Зберігаємо оновлений classifier.json
    print(f"[*] Збереження {JSON_TREE_PATH}...")
    with open(JSON_TREE_PATH, "w", encoding="utf-8") as f:
        json.dump(tree, f, ensure_ascii=False, indent=2)

    # 5. Оновлюємо classifier_flat.json
    def flatten_tree(nodes, parent_code="", parent_path_codes="", parent_path_names=""):
        flat = []
        for node in nodes:
            code = node["code"]
            name = node["clean_name"]
            path_codes = f"{parent_path_codes} / {code}" if parent_path_codes else code
            path_names = f"{parent_path_names} / {name}" if parent_path_names else name
            children = node.get("children", [])
            has_children = len(children) > 0

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
                "children_count": len(children)
            }
            flat.append(flat_item)
            if has_children:
                flat.extend(flatten_tree(children, code, path_codes, path_names))
        return flat

    print(f"[*] Оновлення {FLAT_JSON_PATH}...")
    flat_all = flatten_tree(tree)
    with open(FLAT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(flat_all, f, ensure_ascii=False, indent=2)

    # 6. Оновлюємо SQLite categories
    print(f"[*] Оновлення таблиці categories в {DB_PATH}...")
    for item in flat_all:
        cur.execute("""
            UPDATE categories
            SET direct_docs_count = ?, total_docs_count = ?
            WHERE code = ?
        """, (item["direct_docs_count"], item["total_docs_count"], item["code"]))

    conn.commit()
    conn.close()

    # 7. Оновлюємо CSV
    print(f"[*] Збереження {CSV_PATH}...")
    with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Код", "Рівень", "Назва", "Очищена назва", "Батьківський код",
            "Ієрархічний код", "Ієрархічний шлях", "Всього співпадінь", "Прямих співпадінь",
            "URL гілки", "URL прямий"
        ])
        for it in flat_all:
            writer.writerow([
                it["code"], it["level"], it["name"], it["clean_name"], it["parent_code"],
                it["path_codes"], it["path_names"], it["total_docs_count"], it["direct_docs_count"],
                it["branch_url"], it["direct_url"]
            ])

    # 8. Оновлюємо Markdown
    print(f"[*] Збереження {MD_PATH}...")
    with open(MD_PATH, "w", encoding="utf-8") as f:
        f.write("# Єдиний класифікатор правових актів України\n\n")
        f.write(f"- **Всього рубрик**: {len(flat_all):,}\n")
        f.write(f"- **Всього зафіксованих співпадінь**: {total_matches:,}\n")
        f.write(f"- **Дата оновлення**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## Дерево класифікатора\n\n")
        for it in flat_all:
            indent = "  " * (it["level"] - 1)
            url = it["direct_url"] or it["branch_url"] or "#"
            cnt_badge = f" `[{it['total_docs_count']}]`" if it["total_docs_count"] > 0 else ""
            f.write(f"{indent}- **`{it['code']}`** [{it['clean_name']}]({url}){cnt_badge}\n")

    print(f"\n[SUCCESS] Успішно синхронізовано кількість співпадінь для всіх {len(flat_all)} категорій!")


if __name__ == "__main__":
    compute_and_sync_counts()
