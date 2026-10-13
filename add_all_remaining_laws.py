#!/usr/bin/env python3
"""
Скрипт додавання підкатегорій для 7 законів органів влади та судоустрою:
- 170 30: Закон України «Про Національну гвардію України»
- 170 40: Закон України «Про державну охорону органів державної влади України та посадових осіб»
- 170 50: Закон України «Про Державну прикордонну службу України»
- 170 60: Закон України «Про контррозвідувальну діяльність»
- 170 70: Закон України «Про розвідку»
- 170 80: Закон України «Про судоустрій і статус суддів»
- 170 90: Закон України «Про статус суддів»

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
from datetime import datetime
from pathlib import Path

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

LAWS_CONFIG = [
    {
        "code": "170 30",
        "name": "Закон України «Про Національну гвардію України»",
        "clean_name": "Про Національну гвардію України",
        "url": "https://zakon.rada.gov.ua/laws/show/876-18",
        "path": Path("/Users/kostantinkrivula/.gemini/antigravity-ide/brain/2b9c4831-2d3a-47dc-ba1d-3373c18cd0b4/.system_generated/steps/518/content.md"),
        "sec_type": "rozdil",
    },
    {
        "code": "170 40",
        "name": "Закон України «Про державну охорону органів державної влади України та посадових осіб»",
        "clean_name": "Про державну охорону органів державної влади України та посадових осіб",
        "url": "https://zakon.rada.gov.ua/laws/show/160/98-%D0%B2%D1%80",
        "path": Path("/Users/kostantinkrivula/.gemini/antigravity-ide/brain/2b9c4831-2d3a-47dc-ba1d-3373c18cd0b4/.system_generated/steps/558/content.md"),
        "sec_type": "rozdil",
    },
    {
        "code": "170 50",
        "name": "Закон України «Про Державну прикордонну службу України»",
        "clean_name": "Про Державну прикордонну службу України",
        "url": "https://zakon.rada.gov.ua/laws/show/661-15",
        "path": Path("/Users/kostantinkrivula/.gemini/antigravity-ide/brain/2b9c4831-2d3a-47dc-ba1d-3373c18cd0b4/.system_generated/steps/524/content.md"),
        "sec_type": "rozdil",
    },
    {
        "code": "170 60",
        "name": "Закон України «Про контррозвідувальну діяльність»",
        "clean_name": "Про контррозвідувальну діяльність",
        "url": "https://zakon.rada.gov.ua/laws/show/374-15",
        "path": Path("/Users/kostantinkrivula/.gemini/antigravity-ide/brain/2b9c4831-2d3a-47dc-ba1d-3373c18cd0b4/.system_generated/steps/526/content.md"),
        "sec_type": "direct",
    },
    {
        "code": "170 70",
        "name": "Закон України «Про розвідку»",
        "clean_name": "Про розвідку",
        "url": "https://zakon.rada.gov.ua/laws/show/912-20",
        "path": Path("/Users/kostantinkrivula/.gemini/antigravity-ide/brain/2b9c4831-2d3a-47dc-ba1d-3373c18cd0b4/.system_generated/steps/560/content.md"),
        "sec_type": "rozdil",
    },
    {
        "code": "170 80",
        "name": "Закон України «Про судоустрій і статус суддів»",
        "clean_name": "Про судоустрій і статус суддів",
        "url": "https://zakon.rada.gov.ua/laws/show/1402-19",
        "path": Path("/Users/kostantinkrivula/.gemini/antigravity-ide/brain/2b9c4831-2d3a-47dc-ba1d-3373c18cd0b4/.system_generated/steps/528/content.md"),
        "sec_type": "rozdil",
    },
    {
        "code": "170 90",
        "name": "Закон України «Про статус суддів»",
        "clean_name": "Про статус суддів",
        "url": "https://zakon.rada.gov.ua/laws/show/2862-12",
        "path": Path("/Users/kostantinkrivula/.gemini/antigravity-ide/brain/2b9c4831-2d3a-47dc-ba1d-3373c18cd0b4/.system_generated/steps/530/content.md"),
        "sec_type": "glava",
    },
]

def clean_text_line(line: str) -> str:
    s = re.sub(r"^https?://[^\s]+\s+", "", line).strip()
    s = re.sub(r"\{.*?\}", "", s).strip()
    s = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", s).strip()
    return s

def format_title_casing(title: str) -> str:
    """Форматує назву розділу/глави, щоб вона була в нормальному регістрі (перше слово з великої, або стандартний стиль)."""
    t = title.strip()
    if t.startswith("."):
        t = t[1:].strip()
    if t.isupper() and len(t) > 3:
        return t.capitalize()
    return t

def parse_law_file(config: dict):
    path = config["path"]
    if not path.exists():
        raise FileNotFoundError(f"Файл не знайдено: {path}")

    text = path.read_text(encoding="utf-8")
    lines = [clean_text_line(l) for l in text.splitlines()]

    sec_type = config["sec_type"]

    sections = []
    current_section = None
    direct_articles = []

    for line in lines:
        if not line:
            continue

        if sec_type in ("rozdil", "glava"):
            sec_pattern = r"^(Розділ\s+[IVXLCDM]+)\.?\s*(.*)$" if sec_type == "rozdil" else r"^(Глава\s+[IVXLCDM\d]+)\.?\s*(.*)$"
            m_r = re.match(sec_pattern, line, re.IGNORECASE)
            if m_r and not m_r.group(2).startswith("["):
                r_num = m_r.group(1).strip()
                # нормалізуємо назву номера (Розділ I / Глава I)
                parts = r_num.split()
                r_num = f"{parts[0].capitalize()} {parts[1].upper()}" if len(parts) > 1 else r_num.capitalize()
                raw_t = m_r.group(2).strip()
                clean_t = format_title_casing(raw_t)

                current_section = {
                    "num": r_num,
                    "title": f"{r_num}. {clean_t}" if clean_t else r_num,
                    "articles": []
                }
                sections.append(current_section)
                continue

        m_a = re.match(r"^(Стаття\s+\d+(?:-\d+)?)\.?\s*(.*)$", line, re.IGNORECASE)
        if m_a:
            a_num = m_a.group(1).strip()
            # Нормалізуємо до вигляду "Стаття 1", "Стаття 111-1"
            a_parts = a_num.split()
            a_num = f"Стаття {a_parts[1]}" if len(a_parts) > 1 else a_num
            a_t = m_a.group(2).strip()
            if a_t.startswith("."):
                a_t = a_t[1:].strip()
            if not a_t:
                a_title = a_num
            else:
                a_title = f"{a_num}. {a_t}"

            art_item = {"num": a_num, "title": a_title}

            if sec_type == "direct":
                if not any(a["num"] == a_num for a in direct_articles):
                    direct_articles.append(art_item)
            else:
                if current_section is not None:
                    if not any(a["num"] == a_num for a in current_section["articles"]):
                        current_section["articles"].append(art_item)
                else:
                    if not any(a["num"] == a_num for a in direct_articles):
                        direct_articles.append(art_item)

    return sections, direct_articles

def build_law_node(config: dict, sections: list, direct_articles: list) -> dict:
    code = config["code"]
    name = config["name"]
    clean_name = config["clean_name"]
    url = config["url"]

    sub_node = {
        "code": code,
        "name": name,
        "clean_name": clean_name,
        "level": 2,
        "parent_code": "170",
        "direct_url": f"{url}#Text",
        "branch_url": url,
        "total_docs_count": 0,
        "direct_docs_count": 0,
        "cross_references": [],
        "children": []
    }

    if config["sec_type"] == "direct":
        # Статті безпосередньо під законом (level 3)
        art_idx = 10
        for art in direct_articles:
            art_code = f"{code} {art_idx}"
            art_node = {
                "code": art_code,
                "name": art["title"],
                "clean_name": art["title"],
                "level": 3,
                "parent_code": code,
                "direct_url": "",
                "branch_url": "",
                "total_docs_count": 0,
                "direct_docs_count": 0,
                "cross_references": [],
                "children": []
            }
            sub_node["children"].append(art_node)
            art_idx += 10
    else:
        sec_idx = 10
        for sec in sections:
            sec_code = f"{code} {sec_idx}"
            sec_node = {
                "code": sec_code,
                "name": sec["title"],
                "clean_name": sec["title"],
                "level": 3,
                "parent_code": code,
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

    return sub_node

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

def run():
    print("[*] Початок обробки 7 законів...")
    new_nodes = []
    for cfg in LAWS_CONFIG:
        secs, direct = parse_law_file(cfg)
        tot = sum(len(s["articles"]) for s in secs) + len(direct)
        print(f"  -> {cfg['code']} {cfg['clean_name']}: {len(secs)} розділів/глав, {tot} статей")
        node = build_law_node(cfg, secs, direct)
        new_nodes.append(node)

    # 1. Завантажуємо classifier.json
    json_path = DATA_DIR / "classifier.json"
    print(f"[*] Оновлення {json_path}...")
    with open(json_path, "r", encoding="utf-8") as f:
        classifier_tree = json.load(f)

    root_170 = None
    for n in classifier_tree:
        if n["code"] == "170":
            root_170 = n
            break

    if not root_170:
        raise ValueError("Категорію 170 'Органи влади' не знайдено!")

    new_codes = {cfg["code"] for cfg in LAWS_CONFIG}
    root_170["children"] = [c for c in root_170.get("children", []) if c["code"] not in new_codes]
    root_170["children"].extend(new_nodes)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(classifier_tree, f, ensure_ascii=False, indent=2)

    # 2. classifier_flat.json
    print("[*] Генерація classifier_flat.json...")
    flat_all = flatten_tree(classifier_tree)
    flat_path = DATA_DIR / "classifier_flat.json"
    with open(flat_path, "w", encoding="utf-8") as f:
        json.dump(flat_all, f, ensure_ascii=False, indent=2)

    # 3. SQLite
    sqlite_path = DATA_DIR / "classifier.sqlite"
    print(f"[*] Оновлення SQLite {sqlite_path}...")
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

    print(f"\n[SUCCESS] Успішно додано всі 7 законів! Загальна кількість рубрик у класифікаторі: {len(flat_all)}")

if __name__ == "__main__":
    run()
