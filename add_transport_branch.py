#!/usr/bin/env python3
"""
Скрипт додавання нової кореневої категорії 200 'Транспорт, логістика'
та підкатегорії 200 10 'Кодекс торговельного мореплавства України' (КТМУ)
(Закон № 176/95-ВР, https://zakon.rada.gov.ua/laws/show/176/95-%D0%B2%D1%80#Text)
із конкретизацією до 11 розділів, 35 глав та 350 статей включно.

Оновлює всі 5 форматів класифікатора:
1. data/classifier.json
2. data/classifier_flat.json
3. data/classifier.sqlite (таблиці categories та categories_fts)
4. data/classifier.csv
5. data/classifier.md
А також запускає sync_classifier_counts.py для оновлення лічильників.
"""

import sys
import json
import csv
import re
import sqlite3
import subprocess
import urllib.parse
from datetime import datetime
from pathlib import Path

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SCRATCH_DIR = BASE_DIR / "scratch"

KTMU_STRU_MD = SCRATCH_DIR / "ktmu_stru.md"

KTMU_BASE_URL = "https://zakon.rada.gov.ua/laws/show/176/95-%D0%B2%D1%80"
TRANSPORT_SEARCH_URL = "https://zakon.rada.gov.ua/laws/find/a?text=%D1%82%D1%80%D0%B0%D0%BD%D1%81%D0%BF%D0%BE%D1%80%D1%82&mode=all&cat=1&search=1"


def smart_title(s: str) -> str:
    s = s.strip()
    parts = s.split('.')
    new_parts = []
    for p in parts:
        p_str = p.strip()
        if not p_str:
            continue
        p_str = p_str[0].upper() + p_str[1:].lower()
        new_parts.append(p_str)
    res = '. '.join(new_parts)
    replacements = {
        'україни': 'України',
        'україні': 'Україні',
        'україна': 'Україна',
        'автономної республіки крим': 'Автономної Республіки Крим',
        'автономна республіка крим': 'Автономна Республіка Крим',
        'єс': 'ЄС',
    }
    for k, v in replacements.items():
        res = re.sub(r'\b' + re.escape(k) + r'\b', v, res, flags=re.IGNORECASE)
    return res


def format_section_title(text: str) -> str:
    text = ' '.join(text.split()).strip()
    m = re.match(r'^(РОЗДІЛ|Розділ)\s+([IVXLCDM]+)[\.\s]*(.*)$', text, re.IGNORECASE)
    if m:
        num = m.group(2).upper()
        name = m.group(3).strip()
        if not name:
            return f'Розділ {num}'
        if name.startswith('{'):
            return f'Розділ {num}. {name}'
        return f'Розділ {num}. {smart_title(name)}'
    return smart_title(text)


def format_chapter_title(text: str) -> str:
    text = ' '.join(text.split()).strip()
    m = re.match(r'^(ГЛАВА|Глава)\s+([\d\-]+)[\.\s]*(.*)$', text, re.IGNORECASE)
    if m:
        num = m.group(2)
        name = m.group(3).strip()
        if name.startswith('{'):
            return f'Глава {num}. {name}'
        return f'Глава {num}. {smart_title(name)}'
    return smart_title(text)


def format_article_title(text: str) -> str:
    text = ' '.join(text.split()).strip()
    m = re.match(r'^(Стаття|СТАТТЯ)\s+([\d\-]+)[\.\s]*(.*)$', text, re.IGNORECASE)
    if m:
        num = m.group(2)
        name = m.group(3).strip()
        name = name.lstrip('.- ')
        return f'Стаття {num}. {name}'
    return text


def make_search_url(query: str) -> str:
    encoded = urllib.parse.quote(query)
    return f"https://zakon.rada.gov.ua/laws/main/find?find_text={encoded}"


def parse_ktmu_structure():
    with open(KTMU_STRU_MD, 'r', encoding='utf-8') as f:
        text = f.read()

    pattern = re.compile(r'\[(.*?)\]\((https://zakon\.rada\.gov\.ua/laws/show/176/95-[^\)]+)\)')
    matches = pattern.findall(text)
    items = []
    for label, url in matches:
        if any(label.startswith(x) for x in ['Розділ', 'РОЗДІЛ', 'Глава', 'ГЛАВА', 'Стаття', 'СТАТТЯ']):
            items.append((label.strip(), url.strip()))

    # Беремо рівно перші 396 унікальних елементів (першу половину файлу)
    items = items[:396]

    sections = []
    cur_sec = None
    cur_chap = None

    for label, url in items:
        if label.startswith('РОЗДІЛ') or label.startswith('Розділ'):
            title = format_section_title(label)
            cur_sec = {
                'title': title,
                'url': url,
                'chapters': [],
                'direct_articles': []
            }
            sections.append(cur_sec)
            cur_chap = None
        elif label.startswith('ГЛАВА') or label.startswith('Глава'):
            title = format_chapter_title(label)
            cur_chap = {
                'title': title,
                'url': url,
                'articles': []
            }
            if cur_sec is not None:
                cur_sec['chapters'].append(cur_chap)
        elif label.startswith('СТАТТЯ') or label.startswith('Стаття'):
            title = format_article_title(label)
            art_obj = {
                'title': title,
                'url': url
            }
            if cur_chap is not None:
                cur_chap['articles'].append(art_obj)
            elif cur_sec is not None:
                cur_sec['direct_articles'].append(art_obj)

    return sections


def build_transport_tree():
    sections = parse_ktmu_structure()

    ktmu_code = "200 10"
    code_title = "Кодекс торговельного мореплавства України"

    code_node = {
        "code": ktmu_code,
        "level": 2,
        "name": code_title,
        "clean_name": code_title,
        "parent_code": "200",
        "branch_url": KTMU_BASE_URL,
        "direct_url": f"{KTMU_BASE_URL}#Text",
        "total_docs_count": 0,
        "direct_docs_count": 0,
        "cross_references": [],
        "children": []
    }

    for s_idx, sec in enumerate(sections):
        sec_code = f"{ktmu_code} {(s_idx + 1) * 10}"
        sec_node = {
            "code": sec_code,
            "level": 3,
            "name": sec["title"],
            "clean_name": sec["title"],
            "parent_code": ktmu_code,
            "branch_url": make_search_url(f"{code_title} {sec['title']}"),
            "direct_url": sec["url"],
            "total_docs_count": 0,
            "direct_docs_count": 0,
            "cross_references": [],
            "children": []
        }

        # If section has chapters
        if sec["chapters"]:
            for c_idx, chap in enumerate(sec["chapters"]):
                chap_code = f"{sec_code} {(c_idx + 1) * 10}"
                chap_node = {
                    "code": chap_code,
                    "level": 4,
                    "name": chap["title"],
                    "clean_name": chap["title"],
                    "parent_code": sec_code,
                    "branch_url": make_search_url(f"{code_title} {chap['title']}"),
                    "direct_url": chap["url"],
                    "total_docs_count": 0,
                    "direct_docs_count": 0,
                    "cross_references": [],
                    "children": []
                }

                for a_idx, art in enumerate(chap["articles"]):
                    art_code = f"{chap_code} {(a_idx + 1) * 10}"
                    art_node = {
                        "code": art_code,
                        "level": 5,
                        "name": art["title"],
                        "clean_name": art["title"],
                        "parent_code": chap_code,
                        "branch_url": make_search_url(f"{code_title} {art['title']}"),
                        "direct_url": art["url"],
                        "total_docs_count": 0,
                        "direct_docs_count": 0,
                        "cross_references": [],
                        "children": []
                    }
                    chap_node["children"].append(art_node)

                sec_node["children"].append(chap_node)

        elif sec["direct_articles"]:
            for a_idx, art in enumerate(sec["direct_articles"]):
                art_code = f"{sec_code} {(a_idx + 1) * 10}"
                art_node = {
                    "code": art_code,
                    "level": 4,
                    "name": art["title"],
                    "clean_name": art["title"],
                    "parent_code": sec_code,
                    "branch_url": make_search_url(f"{code_title} {art['title']}"),
                    "direct_url": art["url"],
                    "total_docs_count": 0,
                    "direct_docs_count": 0,
                    "cross_references": [],
                    "children": []
                }
                sec_node["children"].append(art_node)

        code_node["children"].append(sec_node)

    root_node = {
        "code": "200",
        "level": 1,
        "name": "Транспорт, логістика",
        "clean_name": "Транспорт, логістика",
        "parent_code": "",
        "branch_url": TRANSPORT_SEARCH_URL,
        "direct_url": "",
        "total_docs_count": 0,
        "direct_docs_count": 0,
        "cross_references": [],
        "children": [code_node]
    }

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
    print("[*] Побудова дерева '200 Транспорт, логістика' (Кодекс торговельного мореплавства України)...")
    trans_root = build_transport_tree()

    # 1. Оновлення data/classifier.json
    json_path = DATA_DIR / "classifier.json"
    print(f"[*] Оновлення {json_path}...")
    with open(json_path, "r", encoding="utf-8") as f:
        classifier_tree = json.load(f)

    classifier_tree = [node for node in classifier_tree if node["code"] != "200"]
    classifier_tree.append(trans_root)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(classifier_tree, f, ensure_ascii=False, indent=2)

    # 2. Розгортання у плоский список
    print("[*] Генерація classifier_flat.json...")
    flat_all = flatten_tree(classifier_tree)

    flat_json_path = DATA_DIR / "classifier_flat.json"
    with open(flat_json_path, "w", encoding="utf-8") as f:
        json.dump(flat_all, f, ensure_ascii=False, indent=2)

    # 3. SQLite
    sqlite_path = DATA_DIR / "classifier.sqlite"
    print(f"[*] Оновлення SQLite бази {sqlite_path}...")
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

    trans_flat = [it for it in flat_all if it["code"].startswith("200")]
    print(f"\n[SUCCESS] Успішно додано категорію 200 'Транспорт, логістика' ({len(trans_flat)} рубрик). Всього {len(flat_all)} рубрик у класифікаторі!")

    # 6. Синхронізація лічильників
    print("\n[*] Запуск sync_classifier_counts.py...")
    subprocess.run([sys.executable, str(BASE_DIR / "sync_classifier_counts.py")], check=True)


if __name__ == "__main__":
    update_all()
