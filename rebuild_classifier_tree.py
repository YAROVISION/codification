#!/usr/bin/env python3
"""
Скрипт повної перебудови дерева класифікації на нову структуру з 15 галузей права:
 10 Бюджетне право - Бюджетний кодекс України
 20 Цивільне право - Цивільний кодекс України
 30 Цивільний процес - Цивільний процесуальний кодекс України
 40 Господарський процес - Господарський процесуальний кодекс України
 50 Банкрутство - Кодекс України з процедур банкрутства
 60 Трудове право - Кодекс законів про працю України
 70 Сімейне право - Сімейний кодекс України
 80 Житлове право - Закон України «Про основні засади житлової політики» та Житловий кодекс України
 90 Митне право - Митний кодекс України
 100 Податкове право - Податковий кодекс України
 110 Адміністративне право - Кодекс України про адміністративні правопорушення
 120 Адміністративне судочинство - Кодекс адміністративного судочинства України
 130 Кримінальне право - Кримінальний кодекс України
 140 Кримінальний процес - Кримінальний процесуальний кодекс України
 150 Кримінально-виконавче право - Кримінально-виконавчий кодекс України

Оновлює всі 5 форматів класифікатора:
 - data/classifier.json
 - data/classifier_flat.json
 - data/classifier.sqlite (categories, categories_fts)
 - data/classifier.csv
 - data/classifier.md
"""

import os
import sys
import copy
import json
import csv
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

CONFIG = [
    ('10', 'Бюджетне право', [('20 10', '10 10')]),
    ('20', 'Цивільне право', [('30 10', '20 10')]),
    ('30', 'Цивільний процес', [('30 20', '30 10')]),
    ('40', 'Господарський процес', [('30 40', '40 10')]),
    ('50', 'Банкрутство', [('30 30', '50 10')]),
    ('60', 'Трудове право', [('50 10', '60 10')]),
    ('70', 'Сімейне право', [('70 10', '70 10')]),
    ('80', 'Житлове право', [('80 10', '80 10'), ('80 20', '80 20')]),
    ('90', 'Митне право', [('140 10', '90 10')]),
    ('100', 'Податкове право', [('150 10', '100 10')]),
    ('110', 'Адміністративне право', [('240 10', '110 10')]),
    ('120', 'Адміністративне судочинство', [('240 20', '120 10')]),
    ('130', 'Кримінальне право', [('250 10', '130 10')]),
    ('140', 'Кримінальний процес', [('250 20', '140 10')]),
    ('150', 'Кримінально-виконавче право', [('260 10', '150 10')]),
]


def find_subtree(old_tree, code):
    for root in old_tree:
        if root.get('code') == code:
            return copy.deepcopy(root)
        for ch in root.get('children', []):
            if ch.get('code') == code:
                return copy.deepcopy(ch)
            for sub_ch in ch.get('children', []):
                if sub_ch.get('code') == code:
                    return copy.deepcopy(sub_ch)
    return None


def renumber_node(node, old_pfx, new_pfx, parent_code):
    if node['code'] == old_pfx:
        node['code'] = new_pfx
    elif node['code'].startswith(old_pfx + ' '):
        suffix = node['code'][len(old_pfx):]
        node['code'] = new_pfx + suffix
    node['parent_code'] = parent_code
    
    for child in node.get('children', []):
        renumber_node(child, old_pfx, new_pfx, node['code'])


def flatten_tree(nodes, parent_code='', parent_path_codes='', parent_path_names=''):
    flat = []
    for node in nodes:
        code = node['code']
        name = node['clean_name']
        
        path_codes = f"{parent_path_codes} / {code}" if parent_path_codes else code
        path_names = f"{parent_path_names} / {name}" if parent_path_names else name
        
        children = node.get('children', [])
        has_children = len(children) > 0
        children_count = len(children)
        
        node['path_codes'] = path_codes
        node['path_names'] = path_names
        node['has_children'] = has_children
        node['children_count'] = children_count
        node['semantic_text'] = f"{name}. Шлях: {path_names}. Код: {code}."
        
        flat_item = {
            'code': code,
            'level': node['level'],
            'name': node['name'],
            'clean_name': name,
            'parent_code': parent_code,
            'path_codes': path_codes,
            'path_names': path_names,
            'cross_references': node.get('cross_references', []),
            'branch_url': node.get('branch_url', ''),
            'direct_url': node.get('direct_url', ''),
            'total_docs_count': node.get('total_docs_count', 0),
            'direct_docs_count': node.get('direct_docs_count', 0),
            'has_children': has_children,
            'children_count': children_count
        }
        flat.append(flat_item)
        if has_children:
            flat.extend(flatten_tree(children, code, path_codes, path_names))
    return flat


def main():
    json_path = DATA_DIR / "classifier.json"
    backup_json_path = DATA_DIR / "classifier.json.bak_old_tree"
    sqlite_path = DATA_DIR / "classifier.sqlite"
    backup_sqlite_path = DATA_DIR / "classifier.sqlite.bak_old_tree"

    print("[*] 1. Створення резервних копій...")
    if json_path.exists():
        shutil.copy2(json_path, backup_json_path)
    if sqlite_path.exists():
        shutil.copy2(sqlite_path, backup_sqlite_path)
    print("    Резервні копії створено.")

    print("[*] 2. Завантаження чинного classifier.json...")
    with open(json_path, "r", encoding="utf-8") as f:
        old_tree = json.load(f)

    print("[*] 3. Побудова нової структури з 15 галузей...")
    new_roots = []
    for root_code, root_name, subs in CONFIG:
        children = []
        direct_url = ''
        branch_url = ''
        
        for old_c, new_c in subs:
            st = find_subtree(old_tree, old_c)
            if not st:
                raise ValueError(f"Піддерево {old_c} не знайдено!")
            renumber_node(st, old_c, new_c, root_code)
            children.append(st)
            if not direct_url and st.get('direct_url'):
                direct_url = st.get('direct_url')
            if not branch_url and st.get('branch_url'):
                branch_url = st.get('branch_url')

        root_node = {
            'code': root_code,
            'level': 1,
            'name': root_name,
            'clean_name': root_name,
            'parent_code': None,
            'path_codes': root_code,
            'path_names': root_name,
            'cross_references': [],
            'branch_url': branch_url,
            'direct_url': direct_url,
            'total_docs_count': 0,
            'direct_docs_count': 0,
            'has_children': True,
            'children_count': len(children),
            'semantic_text': f"{root_name}. Шлях: {root_name}. Код: {root_code}.",
            'children': children
        }
        new_roots.append(root_node)

    # 4. Обчислюємо flat та оновлюємо вузли
    print("[*] 4. Генерація плоского списку (classifier_flat.json)...")
    flat_all = flatten_tree(new_roots)

    # Збереження classifier.json
    print(f"[*] 5. Збереження {json_path}...")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(new_roots, f, ensure_ascii=False, indent=2)

    # Збереження classifier_flat.json
    flat_path = DATA_DIR / "classifier_flat.json"
    print(f"[*] 6. Збереження {flat_path}...")
    with open(flat_path, "w", encoding="utf-8") as f:
        json.dump(flat_all, f, ensure_ascii=False, indent=2)

    # Збереження в SQLite
    print(f"[*] 7. Оновлення SQLite ({sqlite_path})...")
    conn = sqlite3.connect(sqlite_path)
    cur = conn.cursor()

    cur.execute("DELETE FROM categories")
    cur.execute("DELETE FROM categories_fts")
    cur.execute("DELETE FROM semantic_relations")

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
    cur.execute("VACUUM")
    cur.execute("PRAGMA integrity_check")
    integrity = cur.fetchone()[0]
    conn.close()
    print(f"    SQLite оновлено. Перевірка цілісності: {integrity}")

    # Збереження CSV
    csv_path = DATA_DIR / "classifier.csv"
    print(f"[*] 8. Збереження {csv_path}...")
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

    # Збереження Markdown
    md_path = DATA_DIR / "classifier.md"
    print(f"[*] 9. Збереження {md_path}...")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Класифікатор правових актів України\n\n")
        f.write(f"- **Всього рубрик**: {len(flat_all):,}\n")
        f.write(f"- **Кореневих категорій**: {len(new_roots)}\n")
        f.write(f"- **Дата оновлення**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## Структура класифікатора (15 галузей права)\n\n")
        for it in flat_all:
            indent = "  " * (it["level"] - 1)
            url = it["direct_url"] or it["branch_url"] or "#"
            f.write(f"{indent}- **`{it['code']}`** [{it['clean_name']}]({url})\n")

    print("\n" + "=" * 60)
    print(f"🎉 ПЕРЕБУДОВА УСПІШНО ЗАВЕРШЕНА!")
    print(f"Всього кореневих категорій: {len(new_roots)}")
    print(f"Всього рубрик у новому класифікаторі: {len(flat_all)}")
    print("=" * 60)
    for r in new_roots:
        cnt = len([x for x in flat_all if x['code'] == r['code'] or x['code'].startswith(r['code'] + ' ')])
        print(f"  {r['code']:<4} {r['clean_name']:<35} ({cnt} рубрик)")


if __name__ == "__main__":
    main()
