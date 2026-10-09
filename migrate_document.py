#!/usr/bin/env python3
"""
Скрипт міграції нормалізованих оглядів судової практики:
1. Очищення старих сегментів у папці documents/segments/<doc_name>/.
2. Очищення попередніх зв'язків у таблиці mapped_segments бази data/classifier.sqlite.
3. Розбиття файлу documents/markdown/<doc_name>/<doc_name>.md на окремі файли сегментів у documents/segments/<doc_name>/.
4. Автоматичний мапінг юридичних сегментів до класифікації через smart_mapper (із виключенням технічних сегментів).
"""

import sys
import os
import re
import shutil
import argparse
from pathlib import Path

# Fix stdout encoding for Ukrainian on Windows/mac/Linux
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from smart_mapper import process_folder, get_db_connection


def split_and_migrate_document(md_file_path: str, dry_run: bool = False) -> dict:
    md_path = Path(md_file_path)
    if not md_path.exists():
        raise FileNotFoundError(f"Файл не знайдено: {md_path}")

    doc_name = md_path.parent.name
    segments_dir = Path("documents/segments") / doc_name

    print(f"=== Початок міграції для {doc_name} ===")
    print(f"Вихідний файл: {md_path}")
    print(f"Цільова папка сегментів: {segments_dir}")

    # 1. Видалення старих файлів сегментів
    if segments_dir.exists():
        old_count = len(list(segments_dir.glob("*.md")))
        if not dry_run:
            shutil.rmtree(segments_dir)
        print(f"🗑 Видалено {old_count} попередніх файлів сегментів у {segments_dir}.")

    if not dry_run:
        segments_dir.mkdir(parents=True, exist_ok=True)

    # 2. Видалення попередніх зв'язків з БД
    conn = get_db_connection()
    cur = conn.cursor()
    if not dry_run:
        cur.execute("DELETE FROM mapped_segments WHERE file_path LIKE ?", (f"%{doc_name}%",))
        deleted_mappings = cur.rowcount
        conn.commit()
        print(f"🗑 Видалено {deleted_mappings} попередніх записів із mapped_segments у БД.")
    else:
        cur.execute("SELECT count(*) FROM mapped_segments WHERE file_path LIKE ?", (f"%{doc_name}%",))
        print(f"[DRY-RUN] Було б видалено {cur.fetchone()[0]} записів з БД.")

    # 3. Читання markdown
    content = md_path.read_text(encoding="utf-8", errors="surrogateescape")

    # 4. Розбиття на сегменти за мітками <!-- === SEGMENT: ... === -->
    parts = re.split(r"(<!-- === SEGMENT: [^>]+ === -->)", content)
    raw_segments = []
    for i in range(1, len(parts), 2):
        tag = parts[i]
        body = parts[i + 1] if i + 1 < len(parts) else ""
        raw_segments.append((tag, body))

    print(f"📄 Знайдено {len(raw_segments)} сегментів у вихідному файлі.")

    # 5. Визначення імен файлів та генерація
    file_mapping = []
    current_rozdil = None
    kk_chapter_idx = 0
    kpk_chapter_idx = 0
    general_chapter_idx = 0
    last_chapter_title = None

    is_kks = "kks" in doc_name.lower() or "oglad_kks" in doc_name.lower()

    for tag, body in raw_segments:
        full_text = (tag + body).strip() + "\n"
        tag_match = re.search(r"<!-- === SEGMENT: (.*?) === -->", tag)
        tag_content = tag_match.group(1).strip() if tag_match else ""

        # Технічні сегменти
        norm_tag = tag_content.replace('І', 'I').replace('і', 'i').replace('’', "'")
        if "PREAMBLE" in norm_tag.upper():
            file_mapping.append(("00_Preamble.md", full_text, True))
            continue
        if "APPENDIX" in norm_tag.upper():
            file_mapping.append(("99_Appendix.md", full_text, True))
            continue
        if "ОБ'ЄДНАН" in norm_tag.upper() and "Технічний" in tag_content:
            if re.search(r"РОЗДІЛ\s+II\b|\bII\.", norm_tag):
                current_rozdil = "ROZDIL_OP_II"
                file_mapping.append(("02_Rozdil_II.md", full_text, True))
            else:
                current_rozdil = "ROZDIL_OP_I"
                file_mapping.append(("01_Rozdil_I.md", full_text, True))
            continue
        if re.search(r"РОЗДІЛ\s+I\b", norm_tag) and "Технічний" in tag_content:
            if "КРИМІНАЛЬНОГО ПРАВА" in norm_tag.upper():
                current_rozdil = "ROZDIL_KK"
            else:
                current_rozdil = "ROZDIL_OP_I"
            file_mapping.append(("01_Rozdil_I.md", full_text, True))
            continue
        if re.search(r"РОЗДІЛ\s+II\b", norm_tag) and "Технічний" in tag_content:
            if "КРИМІНАЛЬНОГО ПРОЦЕСУАЛЬНОГО" in norm_tag.upper():
                current_rozdil = "ROZDIL_KPK"
            elif "КРИМІНАЛЬНОГО ПРАВА" in norm_tag.upper():
                current_rozdil = "ROZDIL_KK"
            else:
                current_rozdil = "ROZDIL_OP_II"
            file_mapping.append(("02_Rozdil_II.md", full_text, True))
            continue
        if re.search(r"РОЗДІЛ\s+III\b", norm_tag) and "Технічний" in tag_content:
            if "КРИМІНАЛЬНОГО ПРОЦЕСУАЛЬНОГО" in norm_tag.upper():
                current_rozdil = "ROZDIL_KPK"
            else:
                current_rozdil = "ROZDIL_KK"
            file_mapping.append(("03_Rozdil_III.md", full_text, True))
            continue
        if "ЗАГАЛЬНОЇ ЧАСТИНИ" in norm_tag.upper() and "Технічний" in tag_content:
            current_rozdil = "ROZDIL_KK"
            file_mapping.append(("01_Zahalna_chastyna.md", full_text, True))
            continue
        if "ОСОБЛИВОЇ ЧАСТИНИ" in norm_tag.upper() and "Технічний" in tag_content:
            current_rozdil = "ROZDIL_KK"
            file_mapping.append(("03_Osoblyva_chastyna.md", full_text, True))
            continue
        if re.search(r"РОЗДІЛ\s+IV\b", norm_tag) and "Технічний" in tag_content:
            current_rozdil = "ROZDIL_KPK"
            file_mapping.append(("04_Rozdil_IV.md", full_text, True))
            continue
        if "ДОСУДОВЕ РОЗСЛІДУВАННЯ" in norm_tag.upper() and "Технічний" in tag_content:
            current_rozdil = "ROZDIL_KPK"
            file_mapping.append(("04_Dosudove.md", full_text, True))
            continue
        if "ПЕРЕГЛЯДУ" in norm_tag.upper() and "Технічний" in tag_content:
            current_rozdil = "ROZDIL_KPK"
            file_mapping.append(("04_Perehlyad.md", full_text, True))
            continue
        if "ПЕРШІЙ ІНСТАНЦІЇ" in norm_tag.upper() and "Технічний" in tag_content:
            current_rozdil = "ROZDIL_KPK"
            file_mapping.append(("04_Persha_instantsiya.md", full_text, True))
            continue
        if "МІЖНАРОДНЕ" in tag_content.upper() and "Технічний" in tag_content:
            current_rozdil = "ROZDIL_KPK"
            file_mapping.append(("04_Mizhnarodne.md", full_text, True))
            continue
        if "ЗАГАЛЬНІ ПОЛОЖЕННЯ" in tag_content.upper() and "Технічний" in tag_content:
            if "КПК" in tag_content.upper() or current_rozdil in ("ROZDIL_KPK", "ROZDIL_IV"):
                current_rozdil = "ROZDIL_KPK"
            file_mapping.append((f"tech_{len(file_mapping):02d}.md", full_text, True))
            continue
        if "ЗАХОДИ ЗАБЕЗПЕЧЕННЯ" in tag_content.upper() and "Технічний" in tag_content:
            current_rozdil = "ROZDIL_KPK"
            file_mapping.append((f"tech_{len(file_mapping):02d}.md", full_text, True))
            continue
        if "ОСОБЛИВІ ПОРЯДКИ" in tag_content.upper() and "Технічний" in tag_content:
            current_rozdil = "ROZDIL_KPK"
            file_mapping.append(("05_Osoblyvi_poryadky.md", full_text, True))
            continue
        if "Технічний" in tag_content or "Не підлягає розподілу" in tag_content:
            tech_fname = f"tech_{len(file_mapping):02d}.md"
            file_mapping.append((tech_fname, full_text, True))
            continue

        # Змістовні (юридичні) сегменти
        num_part = tag_content.split("|")[0].strip()
        title_part = tag_content.split("|")[1].strip() if "|" in tag_content else ""

        if is_kks:
            if current_rozdil == "ROZDIL_OP_I":
                fname = f"OP_01.{num_part.split('.')[-1]}_segment.md"
            elif current_rozdil == "ROZDIL_OP_II":
                fname = f"OP_02.{num_part.split('.')[-1]}_segment.md"
            elif current_rozdil in ("ROZDIL_KK", "ROZDIL_III", "ROZDIL_III_OSOB"):
                if title_part != last_chapter_title:
                    kk_chapter_idx += 1
                    last_chapter_title = title_part
                seg_num = num_part.split(".")[-1]
                fname = f"KK_{kk_chapter_idx:02d}.{seg_num}_segment.md"
            elif current_rozdil in ("ROZDIL_KPK", "ROZDIL_IV", "ROZDIL_IV_DOSUDOVE", "ROZDIL_IV_PEREHLYAD", "ROZDIL_IV_PERSHA"):
                if title_part != last_chapter_title:
                    kpk_chapter_idx += 1
                    last_chapter_title = title_part
                seg_num = num_part.split(".")[-1]
                fname = f"KPK_{kpk_chapter_idx:02d}.{seg_num}_segment.md"
            else:
                fname = f"{num_part}_segment.md"
            file_mapping.append((fname, full_text, False))
        else:
            if title_part != last_chapter_title:
                general_chapter_idx += 1
                last_chapter_title = title_part
            seg_num = num_part.split(".")[-1] if "." in num_part else num_part
            fname = f"{general_chapter_idx:02d}.{seg_num}_segment.md"
            file_mapping.append((fname, full_text, False))

    # Запис файлів
    if not dry_run:
        for fname, text, is_tech in file_mapping:
            dest = segments_dir / fname
            dest.write_text(text, encoding="utf-8", errors="surrogateescape")
        print(f"💾 Записано {len(file_mapping)} файлів сегментів у {segments_dir}.")

    tech_count = sum(1 for _, _, is_t in file_mapping if is_t)
    legal_count = sum(1 for _, _, is_t in file_mapping if not is_t)
    print(f"📊 Співвідношення: {legal_count} юридичних сегментів, {tech_count} технічних сегментів.")

    # 6. Запуск мапінгу до класифікації
    if not dry_run:
        print("🔗 Встановлення взаємозв'язків із класифікацією (smart_mapper)...")
        res = process_folder(segments_dir)
        print(f"✅ Результати мапінгу: оброблено={res['processed']}, замаплено={res['mapped']}")

        cur.execute("SELECT count(*) FROM mapped_segments WHERE file_path LIKE ?", (f"%{doc_name}%",))
        active_db_count = cur.fetchone()[0]
        print(f"🎯 Всього активних зв'язків у базі classifier.sqlite для {doc_name}: {active_db_count}")

        # 7. Генерація correlation HTML сторінки
        try:
            from build_correlation_pages import build_page_for_document
            corr_file = build_page_for_document(doc_name, conn)
            print(f"🌐 Створено інтерактивну correlation сторінку: {corr_file}")
        except Exception as e:
            print(f"⚠️ Не вдалося згенерувати correlation сторінку: {e}")
    else:
        active_db_count = 0

    conn.close()
    return {
        "doc_name": doc_name,
        "total_files": len(file_mapping),
        "legal_segments": legal_count,
        "tech_segments": tech_count,
        "mapped_count": active_db_count
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Міграція сегментів огляду судової практики та встановлення зв'язків з класифікацією")
    parser.add_argument("path", type=str, help="Шлях до файлу огляду documents/markdown/<doc_name>/<doc_name>.md")
    parser.add_argument("--dry-run", action="store_true", help="Режим симуляції")
    args = parser.parse_args()

    split_and_migrate_document(args.path, dry_run=args.dry_run)
