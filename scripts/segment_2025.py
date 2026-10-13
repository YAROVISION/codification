#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
segment_2025.py
Повна нормалізація та сегментація річного огляду ККС ВС за 2025 рік:
documents/markdown/Oglyad_KKS_2025/Oglyad_KKS_2025.md
згідно з brain/conventions.md та .agents/skills/segment-paragraphs/SKILL.md.
"""

import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MD_PATH = BASE_DIR / "documents" / "markdown" / "Oglyad_KKS_2025" / "Oglyad_KKS_2025.md"


def clean_spaces(text: str) -> str:
    """Замінює переноси рядків і подвійні пробіли на один пробіл."""
    return re.sub(r'\s+', ' ', text).strip()


def normalize_court_links(text: str) -> str:
    """Нормалізує складні/подвійні посилання на ЄДРСР до єдиного стандарту <https://reyestr.court.gov.ua/Review/...>."""
    def repl_double(m):
        inner = m.group(1).strip()
        url = m.group(2).strip()
        inner_clean = re.sub(r'https?://reyestr\.court\.gov\.ua/Review/\d+', '', inner).strip()
        inner_clean = re.sub(r'\s+', ' ', inner_clean).strip()
        if inner_clean:
            return f"{inner_clean} <{url}>"
        else:
            return f"<{url}>"

    # 1. [провадження ... url](url)
    text = re.sub(r'\[([^\]]*?https?://reyestr\.court\.gov\.ua/Review/\d+[^\]]*?)\]\((https?://reyestr\.court\.gov\.ua/Review/\d+)\)', repl_double, text)
    # 2. [url](url)
    text = re.sub(r'\[(https?://reyestr\.court\.gov\.ua/Review/\d+)\]\(\1\)', r'<\1>', text)
    # 3. [провадження ...](url)
    text = re.sub(r'\[([^\]]+)\]\((https?://reyestr\.court\.gov\.ua/Review/\d+)\)', r'\1 <\2>', text)
    # 4. url без кутових дужок
    text = re.sub(r'(?<!<)(https?://reyestr\.court\.gov\.ua/Review/\d+)(?!>)', r'<\1>', text)
    # 5. подвійні кутові дужки
    text = re.sub(r'<<+(https?://reyestr\.court\.gov\.ua/Review/\d+)>+>', r'<\1>', text)
    return text


def process_section(raw_section_text: str, is_kpk: bool):
    """
    Обробляє розділ огляду (КК або КПК):
    1. Розбиває на чанки рішень за посиланнями на реєстр.
    2. Розпізнає глави і підрозділи (включаючи дворядкові назви).
    3. Формує нормалізовані сегменти: один абзац = один рядок = один сегмент.
    """
    matches = list(re.finditer(r'<https?://reyestr\.court\.gov\.ua/Review/\d+>', raw_section_text))

    prev_end = 0
    chunks = []
    for m in matches:
        chunks.append(raw_section_text[prev_end:m.end()].strip())
        prev_end = m.end()

    current_ch_num = 1
    current_ch_title = "Загальні положення" if not is_kpk else "Засади кримінального провадження"
    current_sub_num = "1.1"
    current_sub_title = "Підстава кримінальної відповідальності" if not is_kpk else "Повага до людської гідності"

    ch_counter = {}
    result_blocks = []
    special_part_emitted = False

    for ch in chunks:
        lines = [l.strip() for l in ch.splitlines() if l.strip()]
        pos_lines = []

        i = 0
        while i < len(lines):
            l = lines[i]

            # Перевірка на Особливу частину КК
            if not is_kpk and "II. ЗАСТОСУВАННЯ НОРМ ОСОБЛИВОЇ ЧАСТИНИ" in l:
                if not special_part_emitted:
                    result_blocks.append(
                        "<!-- === SEGMENT: II. ЗАСТОСУВАННЯ НОРМ ОСОБЛИВОЇ ЧАСТИНИ КРИМІНАЛЬНОГО ПРАВА УКРАЇНИ | II. ЗАСТОСУВАННЯ НОРМ ОСОБЛИВОЇ ЧАСТИНИ КРИМІНАЛЬНОГО ПРАВА УКРАЇНИ. Технічний сегмент. Не підлягає розподілу === -->\n\n"
                        "II. ЗАСТОСУВАННЯ НОРМ ОСОБЛИВОЇ ЧАСТИНИ КРИМІНАЛЬНОГО ПРАВА УКРАЇНИ\n"
                    )
                    special_part_emitted = True
                i += 1
                continue

            if "РОЗДІЛ I" in l or "ЗАГАЛЬНОЇ ЧАСТИНИ" in l or "РОЗДІЛ II" in l:
                i += 1
                continue

            m_sub = re.match(r'^(\d+\.\d+)\.\s*(.*)', l)
            m_ch = re.match(r'^(\d+)\.\s*([^\d].*)', l)

            if m_sub:
                current_sub_num = m_sub.group(1)
                sub_title = m_sub.group(2).strip()
                # Перевірка на продовження назви підрозділу на наступному рядку
                if i + 1 < len(lines):
                    next_l = lines[i + 1]
                    if not re.match(r'^\d+\.', next_l) and not re.match(r'^\d+\.\d+\.', next_l) and not next_l.endswith('.') and len(next_l) < 85:
                        sub_title = f"{sub_title} {next_l}".strip()
                        i += 1
                current_sub_title = sub_title
                i += 1
                continue
            elif m_ch:
                raw_num = int(m_ch.group(1))
                current_ch_num = raw_num
                ch_title = m_ch.group(2).strip()
                # Перевірка на продовження назви глави на наступному рядку
                if i + 1 < len(lines):
                    next_l = lines[i + 1]
                    if not re.match(r'^\d+\.', next_l) and not re.match(r'^\d+\.\d+\.', next_l) and not next_l.endswith('.') and len(next_l) < 85:
                        ch_title = f"{ch_title} {next_l}".strip()
                        i += 1
                current_ch_title = ch_title
                i += 1
                continue
            else:
                pos_lines.append(l)
                i += 1

        # Текст позиції
        pos = clean_spaces(" ".join(pos_lines))

        # Очищення від номерів на початку
        pos = re.sub(r'^\d+\.\d+\.\s*', '', pos)
        pos = re.sub(r'^\d+\.\s*', '', pos)

        ch_counter[current_ch_num] = ch_counter.get(current_ch_num, 0) + 1
        seg_idx = ch_counter[current_ch_num]

        seg_tag = f"<!-- === SEGMENT: {current_ch_num}.{seg_idx} | {current_ch_num}. {current_ch_title} === -->"

        clean_ch_name = re.sub(r'^\d+\.\s*', '', current_ch_title).strip()
        clean_sub_name = re.sub(r'^\d+\.\d+\.\s*', '', current_sub_title).strip()

        # Формування єдиного рядка сегмента
        seg_line = f"{clean_ch_name}. {clean_sub_name}. {pos}"
        result_blocks.append(f"{seg_tag}\n\n{seg_line}\n")

    return result_blocks, len(chunks)


def main():
    print(f"Зчитування {MD_PATH}...")
    with open(MD_PATH, 'r', encoding='utf-8', errors='surrogateescape') as f:
        raw = f.read()

    # Очищення від старих сміттєвих коментарів і заголовків
    text = re.sub(r'<!--\s*===\s*SEGMENT:.*?===\s*-->', '', raw, flags=re.DOTALL)
    text = re.sub(r'^###\s+.*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n\s*\d+\s*\n\s*Огляд судової практики ККС ВС\s*\n', '\n', text)

    # Нормалізація посилань на судові рішення
    text = normalize_court_links(text)

    # Відокремлюємо ЗМІСТ / преамбулу
    marker_r1 = "РОЗДІЛ I. ЗАСТОСУВАННЯ НОРМ КРИМІНАЛЬНОГО ПРАВА УКРАЇНИ"
    idx_r1 = text.find(marker_r1, 300)
    if idx_r1 == -1:
        raise ValueError("Не знайдено РОЗДІЛ I!")

    preamble = text[:idx_r1].strip()
    body = text[idx_r1:]

    # Розділяємо body на Розділ I (КК) та Розділ II (КПК)
    marker_r2 = "РОЗДІЛ II. ЗАСТОСУВАННЯ НОРМ КРИМІНАЛЬНОГО ПРОЦЕСУАЛЬНОГО ПРАВА"
    idx_r2 = body.find(marker_r2)
    if idx_r2 == -1:
        raise ValueError("Не знайдено РОЗДІЛ II у тілі огляду!")

    body_kk = body[:idx_r2]
    body_kpk_full = body[idx_r2:]

    # Відокремлюємо післямову (вихідні дані) в кінці КПК
    epilogue = ""
    epilogue_marker = "Огляд судової практики Касаційного кримінального суду у складі Верховного Суду\nза 2025 рік / Упоряд."
    idx_epi = body_kpk_full.find(epilogue_marker)
    if idx_epi != -1:
        epilogue = body_kpk_full[idx_epi:].strip()
        body_kpk = body_kpk_full[:idx_epi]
    else:
        body_kpk = body_kpk_full

    all_blocks = []

    # 1. PREAMBLE
    all_blocks.append(
        "<!-- === SEGMENT: PREAMBLE | Огляд судової практики ККС ВС за 2025 рік. ЗМІСТ. Перелік скорочень. Технічний сегмент. Не підлягає розподілу === -->\n\n"
        + preamble + "\n"
    )

    # 2. РОЗДІЛ I та ЗАГАЛЬНА ЧАСТИНА (технічні сегменти)
    all_blocks.append(
        "<!-- === SEGMENT: РОЗДІЛ I | РОЗДІЛ I. ЗАСТОСУВАННЯ НОРМ КРИМІНАЛЬНОГО ПРАВА УКРАЇНИ. Технічний сегмент. Не підлягає розподілу === -->\n\n"
        "РОЗДІЛ I. ЗАСТОСУВАННЯ НОРМ КРИМІНАЛЬНОГО ПРАВА УКРАЇНИ\n"
    )
    all_blocks.append(
        "<!-- === SEGMENT: I. ЗАСТОСУВАННЯ НОРМ ЗАГАЛЬНОЇ ЧАСТИНИ КРИМІНАЛЬНОГО ПРАВА УКРАЇНИ | I. ЗАСТОСУВАННЯ НОРМ ЗАГАЛЬНОЇ ЧАСТИНИ КРИМІНАЛЬНОГО ПРАВА УКРАЇНИ. Технічний сегмент. Не підлягає розподілу === -->\n\n"
        "I. ЗАСТОСУВАННЯ НОРМ ЗАГАЛЬНОЇ ЧАСТИНИ КРИМІНАЛЬНОГО ПРАВА УКРАЇНИ\n"
    )

    # 3. КК юридичні сегменти
    blocks_kk, count_kk = process_section(body_kk, False)
    all_blocks.extend(blocks_kk)

    # 4. РОЗДІЛ II (технічний сегмент)
    all_blocks.append(
        "<!-- === SEGMENT: РОЗДІЛ II | РОЗДІЛ II. ЗАСТОСУВАННЯ НОРМ КРИМІНАЛЬНОГО ПРОЦЕСУАЛЬНОГО ПРАВА УКРАЇНИ. Технічний сегмент. Не підлягає розподілу === -->\n\n"
        "РОЗДІЛ II. ЗАСТОСУВАННЯ НОРМ КРИМІНАЛЬНОГО ПРОЦЕСУАЛЬНОГО ПРАВА УКРАЇНИ\n"
    )

    # 5. КПК юридичні сегменти
    blocks_kpk, count_kpk = process_section(body_kpk, True)
    all_blocks.extend(blocks_kpk)

    # 6. APPENDIX (вихідні дані / післямова)
    if epilogue:
        all_blocks.append(
            "<!-- === SEGMENT: APPENDIX | Огляд судової практики ККС ВС за 2025 рік. Вихідні дані. Технічний сегмент. Не підлягає розподілу === -->\n\n"
            + epilogue + "\n"
        )

    final_text = "\n".join(all_blocks)
    total_legal = count_kk + count_kpk
    print(f"Згенеровано: КК сегментів = {count_kk}, КПК сегментів = {count_kpk}, Всього юридичних = {total_legal}")

    with open(MD_PATH, 'w', encoding='utf-8', errors='surrogateescape', newline='') as f:
        f.write(final_text)

    print(f"✅ Успішно збережено нормалізований файл: {MD_PATH}")


if __name__ == "__main__":
    main()
