#!/usr/bin/env python3
"""
Скрипт перенесення існуючих взаємозв'язків у таблиці mapped_segments
з рівнів глав та параграфів безпосередньо на конкретні статті КК та КПК України.
"""

import sys
import re
import json
import sqlite3
from pathlib import Path

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "classifier.sqlite"

# Імпортуємо мапінг з classify_segments
sys.path.insert(0, str(BASE_DIR))
from classify_segments import (
    map_criminal_code_article,
    map_criminal_proc_code_article,
    map_civil_code_article,
    ARTICLE_MAP
)

def extract_article_number(text: str, code_abbr: str) -> str:
    """Витягує номер статті з тексту обґрунтування або сегмента."""
    # 1. Прямий патерн ст. X КК/КПК
    pat = rf'ст(?:атт[іеяю]|\.)?\s*(\d+(?:[-–]\d+)?)\s*{code_abbr}'
    m = re.search(pat, text, re.IGNORECASE)
    if m:
        return m.group(1).replace('–', '-').strip()
    
    # 2. Патерн без назви кодексу, якщо вже шукаємо в цільовому контексті
    pat2 = r'ст(?:атт[іеяю]|\.)?\s*(\d+(?:[-–]\d+)?)'
    m2 = re.search(pat2, text, re.IGNORECASE)
    if m2:
        return m2.group(1).replace('–', '-').strip()
        
    return ""

def main():
    print(f"[*] Підключення до бази {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Завантажуємо кеш категорій
    cat_cache = {}
    for row in cur.execute("SELECT code, clean_name, path_names FROM categories"):
        cat_cache[row[0]] = (row[1], row[2])

    print(f"[*] Завантажено {len(cat_cache)} рубрик класифікатора в кеш.")

    cur.execute("SELECT id, category_code, original_category, llm_reasoning, file_path, teza, full_text FROM mapped_segments")
    rows = cur.fetchall()
    print(f"[*] Всього записів у mapped_segments: {len(rows)}")

    updated_count = 0
    kk_updated = 0
    kpk_updated = 0
    ck_updated = 0
    skipped_count = 0
    unmatched = []

    stats_articles = {}

    for row in rows:
        seg_id, old_cat_code, orig_cat, reasoning, file_path, teza, full_text = row
        reasoning = str(reasoning or "")
        teza = str(teza or "")
        full_text = str(full_text or "")
        file_path_str = str(file_path or "")

        target_code = None
        target_art = None
        code_type = None

        if old_cat_code.startswith("130 10"):
            code_type = "КК"
            target_art = extract_article_number(reasoning, "КК")
            if not target_art or target_art not in ARTICLE_MAP.get("КК", {}):
                target_art = extract_article_number(teza, "КК")
            if not target_art or target_art not in ARTICLE_MAP.get("КК", {}):
                target_art = extract_article_number(full_text[:600], "КК")
            if not target_art or target_art not in ARTICLE_MAP.get("КК", {}):
                target_art = extract_article_number(reasoning, "")

            if target_art:
                target_code = map_criminal_code_article(target_art, full_text[:400])

        elif old_cat_code.startswith("140 10"):
            code_type = "КПК"
            target_art = extract_article_number(reasoning, "КПК")
            if not target_art or target_art not in ARTICLE_MAP.get("КПК", {}):
                target_art = extract_article_number(teza, "КПК")
            if not target_art or target_art not in ARTICLE_MAP.get("КПК", {}):
                target_art = extract_article_number(full_text[:600], "КПК")
            if not target_art or target_art not in ARTICLE_MAP.get("КПК", {}):
                target_art = extract_article_number(reasoning, "")

            if target_art:
                target_code = map_criminal_proc_code_article(target_art, full_text[:400])

        elif old_cat_code.startswith("20 10"):
            code_type = "ЦК"
            target_art = extract_article_number(reasoning, "ЦК")
            if not target_art or target_art not in ARTICLE_MAP.get("ЦК", {}):
                target_art = extract_article_number(teza, "ЦК")
            if not target_art or target_art not in ARTICLE_MAP.get("ЦК", {}):
                target_art = extract_article_number(full_text[:600], "ЦК")
            if not target_art or target_art not in ARTICLE_MAP.get("ЦК", {}):
                target_art = extract_article_number(reasoning, "")

            if target_art:
                target_code = map_civil_code_article(target_art, full_text[:400])

        if target_code and target_code != old_cat_code:
            # Оновлюємо назву та шлях з класифікатора
            if target_code in cat_cache:
                new_clean_name, new_path_names = cat_cache[target_code]
                
                # Оновлюємо reasoning
                new_reasoning = reasoning
                if f"[{old_cat_code}]" in new_reasoning:
                    new_reasoning = re.sub(r'Рубрика: \[.*?\] .*?(\.|$)', f'Рубрика: [{target_code}] {new_path_names}.', new_reasoning)
                elif "Рубрика:" in new_reasoning:
                    new_reasoning = re.sub(r'Рубрика: .*?(\.|$)', f'Рубрика: [{target_code}] {new_path_names}.', new_reasoning)
                else:
                    new_reasoning = f"{new_reasoning}. Рубрика: [{target_code}] {new_path_names}."

                cur.execute("""
                    UPDATE mapped_segments
                    SET category_code = ?,
                        original_category = ?,
                        llm_reasoning = ?
                    WHERE id = ?
                """, (target_code, new_clean_name, new_reasoning, seg_id))

                updated_count += 1
                if code_type == "КК":
                    kk_updated += 1
                elif code_type == "КПК":
                    kpk_updated += 1
                elif code_type == "ЦК":
                    ck_updated += 1

                art_key = f"{code_type} ст. {target_art}"
                stats_articles[art_key] = stats_articles.get(art_key, 0) + 1
            else:
                skipped_count += 1
        else:
            skipped_count += 1
            if code_type in ("КК", "КПК", "ЦК") and len(old_cat_code.split()) < 5:
                unmatched.append((seg_id, code_type, file_path_str, reasoning[:80]))

    conn.commit()
    conn.close()

    print(f"\n[РЕЗУЛЬТАТИ МІГРАЦІЇ ЗВ'ЯЗКІВ ДО СТАТЕЙ]")
    print(f"- Всього оновлено сегментів на конкретні статті: {updated_count}")
    print(f"  * Кримінальний кодекс України (КК): {kk_updated}")
    print(f"  * Кримінальний процесуальний кодекс України (КПК): {kpk_updated}")
    print(f"  * Цивільний кодекс України (ЦК): {ck_updated}")
    print(f"- Залишилося без змін (інші галузі або вже були на рівні статті): {skipped_count}")

    if unmatched:
        print(f"\n[УВАГА] Не вдалося точно зіставити {len(unmatched)} сегментів:")
        for it in unmatched[:10]:
            print(f"  ID {it[0]} ({it[1]}): {it[2]} -> {it[3]}")

    print(f"\n[ТОП-20 СТАТЕЙ ЗА КІЛЬКІСТЮ СУДОВИХ ПОЗИЦІЙ]")
    top_arts = sorted(stats_articles.items(), key=lambda x: x[1], reverse=True)[:20]
    for art, count in top_arts:
        print(f"  {art}: {count} позицій")

if __name__ == "__main__":
    main()
