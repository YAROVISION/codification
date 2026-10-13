#!/usr/bin/env python3
"""
Скрипт додавання нової кореневої категорії 170 'Органи влади'
та підкатегорії 170 10 'Закон України «Про Національну поліцію»'
із повною структурою розділів та конкретизацією до окремих статей включно.

Оновлює всі 5 форматів класифікатора:
1. data/classifier.json
2. data/classifier_flat.json
3. data/classifier.sqlite (categories та categories_fts)
4. data/classifier.csv
5. data/classifier.md
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

LAW_URL = "https://zakon.rada.gov.ua/laws/show/580-19#Text"
RAW_CONTENT_PATH = Path("/Users/kostantinkrivula/.gemini/antigravity-ide/brain/2b9c4831-2d3a-47dc-ba1d-3373c18cd0b4/.system_generated/steps/303/content.md")

ROZDIL_CANONICAL = [
    ("Розділ I", "Загальні положення"),
    ("Розділ II", "Принципи діяльності поліції"),
    ("Розділ III", "Система поліції та статус поліцейських"),
    ("Розділ IV", "Повноваження поліції"),
    ("Розділ V", "Поліцейські заходи"),
    ("Розділ VI", "Добір на посаду поліцейського"),
    ("Розділ VII", "Загальні засади проходження служби в поліції"),
    ("Розділ VIII", "Громадський контроль поліції"),
    ("Розділ IX", "Соціальний захист поліцейських"),
    ("Розділ X", "Фінансове та матеріально-технічне забезпечення поліції"),
    ("Розділ XI", "Прикінцеві та перехідні положення")
]

def make_search_url(query: str) -> str:
    params = {
        "text": query,
        "mode": "all",
        "cat": "1",
        "search": "1"
    }
    return f"https://zakon.rada.gov.ua/laws/find/a?{urllib.parse.urlencode(params)}"

def parse_law_structure():
    """Парсить усі розділи та статті Закону «Про Національну поліцію» із збереженого тексту."""
    if not RAW_CONTENT_PATH.exists():
        raise FileNotFoundError(f"Файл з текстом закону не знайдено: {RAW_CONTENT_PATH}")

    content = RAW_CONTENT_PATH.read_text(encoding="utf-8")
    lines = content.splitlines()[340:]

    sections = []
    current_section = None

    for line in lines:
        clean = re.sub(r"^https?://[^\s]+\s+", "", line).strip()
        
        m_r = re.match(r"^(Розділ\s+[IVXLCDM]+)\s+(.+)$", clean)
        if m_r:
            r_num = m_r.group(1).strip()
            canonical_title = None
            for rn, rt in ROZDIL_CANONICAL:
                if rn.lower() == r_num.lower():
                    canonical_title = rt
                    break
            if not canonical_title:
                canonical_title = m_r.group(2).strip().capitalize()

            current_section = {
                "title": f"{r_num}. {canonical_title}",
                "articles": []
            }
            sections.append(current_section)
            continue

        m_a = re.match(r"^(Стаття\s+\d+(?:-\d+)?)\.\s*(.+)$", clean)
        if m_a and current_section is not None:
            a_num = m_a.group(1).strip()
            a_title = m_a.group(2).strip()
            a_title = re.sub(r"\{.*?\}", "", a_title).strip()
            a_title = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", a_title).strip()
            
            if not any(art["num"] == a_num for art in current_section["articles"]):
                current_section["articles"].append({
                    "num": a_num,
                    "title": f"{a_num}. {a_title}"
                })

    return sections

def build_police_tree(sections):
    """Будує ієрархічне дерево для гілки 170 'Органи влади'."""
    sub_node = {
        "code": "170 10",
        "name": "Закон України «Про Національну поліцію»",
        "clean_name": "Про Національну поліцію",
        "level": 2,
        "parent_code": "170",
        "direct_url": LAW_URL,
        "branch_url": "https://zakon.rada.gov.ua/laws/show/580-19",
        "total_docs_count": 0,
        "direct_docs_count": 0,
        "cross_references": [],
        "children": []
    }

    sec_idx = 10
    for sec in sections:
        sec_code = f"170 10 {sec_idx}"
        sec_node = {
            "code": sec_code,
            "name": sec["title"],
            "clean_name": sec["title"],
            "level": 3,
            "parent_code": "170 10",
            "direct_url": "",
            "branch_url": "",
            "total_docs_count": 0,
            "direct_docs_count": 0,
            "cross_references": [],
            "children": []
        }

        art_idx = 10
        for art in sec["articles"]:
            art_code = f"{sec_code} {art_idx}"
            art_node = {
                "code": art_code,
                "name": art["title"],
                "clean_name": art["title"],
                "level": 4,
                "parent_code": sec_code,
                "direct_url": "",
                "branch_url": "",
                "total_docs_count": 0,
                "direct_docs_count": 0,
                "cross_references": [],
                "children": []
            }
            sec_node["children"].append(art_node)
            art_idx += 10

        sub_node["children"].append(sec_node)
        sec_idx += 10

    root_node = {
        "code": "170",
        "name": "Органи влади",
        "clean_name": "Органи влади",
        "level": 1,
        "parent_code": "",
        "direct_url": LAW_URL,
        "branch_url": make_search_url("органи влади поліція закон"),
        "total_docs_count": 0,
        "direct_docs_count": 0,
        "cross_references": [],
        "children": [sub_node]
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
    print("[*] Парсинг структури Закону України «Про Національну поліцію»...")
    sections = parse_law_structure()
    total_arts = sum(len(s["articles"]) for s in sections)
    print(f"    Знайдено {len(sections)} розділів та {total_arts} статей.")

    root_node = build_police_tree(sections)

    # 1. Оновлення classifier.json
    json_path = DATA_DIR / "classifier.json"
    print(f"[*] Оновлення {json_path}...")
    with open(json_path, "r", encoding="utf-8") as f:
        classifier_tree = json.load(f)

    # Видаляємо стару гілку 170, якщо була
    classifier_tree = [node for node in classifier_tree if node["code"] != "170"]
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

    print(f"\n[SUCCESS] Успішно створено категорію 170 'Органи влади' з підкатегорією 170 10 'Про Національну поліцію' ({len(sections)} розділів, {total_arts} статей). Всього {len(flat_all)} рубрик у класифікаторі!")

if __name__ == "__main__":
    update_all()
