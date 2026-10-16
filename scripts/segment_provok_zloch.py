#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт сегментації файлу:
documents/markdown/Oglyad_KKS_provok_zloch/Oglyad_KKS_provok_zloch.md

Вимоги:
- "Один абзац — один сегмент", записаний строго одним рядком.
- Мітки: <!-- === SEGMENT: N.M | N. Назва розділу === -->
- Префікс на початку кожного абзацу: "Назва розділу. " (без цифри N.).
- Очищення колонтитулів сторінок (\d+\nОгляд судової практики ККС ВС).
- Збереження технічних сегментів PREAMBLE та APPENDIX.
- Збереження файлу з surrogateescape, newline=''.
"""

import re
import os

FILE_PATH = 'documents/markdown/Oglyad_KKS_provok_zloch/Oglyad_KKS_provok_zloch.md'

SECTIONS = [
    (1, 'Сутнісні ознаки провокації злочину в контексті практики ЄСПЛ та їх застосування національними судами',
     '1. Сутнісні ознаки провокації злочину в контексті практики ЄСПЛ та їх застосування'),
    (2, 'Поняття та критерії провокації злочину',
     '2. Поняття та критерії провокації злочину'),
    (3, 'Відмежування провокації злочину від допустимої поведінки правоохоронних органів',
     '3. Відмежування провокації злочину від допустимої поведінки'),
    (4, 'Ініціативність дій особи і їх оцінка в ході аналізу доводів про провокацію злочину',
     '4. Ініціативність дій особи і їх оцінка в ході аналізу доводів про провокацію злочину'),
    (5, 'Конфіденційне співробітництво і його відмінність від провокації злочину',
     '2. Конфіденційне співробітництво і його відмінність від провокації злочину'),
    (6, 'Оцінка доводів про провокацію злочину',
     '3. Оцінка доводів про провокацію злочину'),
    (7, 'Вимоги до процесуальних документів',
     '4. Вимоги до процесуальних документів'),
]

APPENDIX_MARKER = 'Огляд судової практики Касаційного кримінального суду у складі Верховного Суду\nщодо провокації злочину (актуальна практика).'

def clean_text(text: str) -> str:
    # Remove page footers / headers
    text = re.sub(r'\n\s*\d+\s*\n\s*Огляд судової практики ККС ВС[^\n]*', '\n', text)
    # Remove isolated page numbers
    text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
    return text

def normalize_segment_content(text: str, sec_title: str) -> str:
    # Clean footers
    text = clean_text(text)
    
    # Normalize whitespace inside
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\s*\n\s*', ' ', text)
    text = text.strip()
    
    # Normalize URL angle brackets
    # If https://reyestr.court.gov.ua/... is not in < >, wrap it
    text = re.sub(r'(?<!<)(https?://reyestr\.court\.gov\.ua/Review/\d+)(?!>)', r'<\1>', text)
    
    # Ensure space before <https://reyestr.court.gov.ua/
    text = re.sub(r'(?<=[^\s])(<https?://reyestr\.court\.gov\.ua/Review/\d+>)', r' \1', text)
    
    # Ensure space before dash if any
    text = re.sub(r'\s*–\s*<http', r' – <http', text)
    text = re.sub(r'\s*-\s*<http', r' - <http', text)
    
    # Prepend section title if not already present
    prefix = f"{sec_title}."
    if not text.startswith(prefix):
        # Check if it starts with section number or part of title
        # E.g. "1. Сутнісні ознаки..."
        # If text starts with title without prefix, just add prefix
        text = f"{sec_title}. {text}"
    
    # Final whitespace cleanup
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def main():
    with open(FILE_PATH, 'r', encoding='utf-8', errors='surrogateescape') as f:
        raw = f.read()

    appendix_pos = raw.find(APPENDIX_MARKER, 20000)
    if appendix_pos == -1:
        raise ValueError('Appendix marker not found!')

    positions = []
    for num, title, heading in SECTIONS:
        pos = raw.find(heading, 1200)
        if pos == -1:
            raise ValueError(f'Heading not found: {heading}')
        positions.append((num, title, pos))
    positions.append((8, 'APPENDIX', appendix_pos))

    # Preamble extraction
    preamble_raw = raw[:positions[0][2]].strip()
    preamble_clean = clean_text(preamble_raw).strip()
    
    # Appendix extraction
    appendix_raw = raw[appendix_pos:].strip()
    appendix_clean = clean_text(appendix_raw).strip()

    output_blocks = []

    # PREAMBLE Block
    output_blocks.append(
        "<!-- === SEGMENT: PREAMBLE | Огляд судової практики Касаційного кримінального суду у складі Верховного Суду "
        "щодо провокації злочину (актуальна практика). ЗМІСТ. ПЕРЕЛІК СКОРОЧЕНЬ. Технічний сегмент. Не підлягає розподілу === -->\n\n"
        f"{preamble_clean}\n"
    )

    total_segments = 0

    # Decision regex to find all decision endpoints in a section:
    # Either (Постанова|Ухвала) ... https?://reyestr.court.gov.ua/Review/\d+>?
    dec_pat = re.compile(
        r'(?:Постанова|Ухвала)[^\n]*\n(?:[^\n]*\n){0,3}?[^\n]*https?://reyestr\.court\.gov\.ua/Review/\d+>?'
    )

    for i in range(len(SECTIONS)):
        sec_num, title, start_p = positions[i]
        _, _, end_p = positions[i+1]
        sec_raw = raw[start_p:end_p]

        # In sec_raw, find the section heading and slice after it
        # The heading starts at the very beginning of sec_raw
        # Find where the first decision text begins
        matches = list(dec_pat.finditer(sec_raw))
        if not matches:
            raise ValueError(f'No decisions found in section {sec_num}!')

        # The text before the first decision ends at matches[0].end()
        # But we must skip the section heading line(s)
        # Let's see: we can match the heading by finding the newline(s)
        # Heading lines are at the start
        sec_body_start = 0
        # If sec_num == 1: heading is 2 lines
        if sec_num in (1, 3):
            # 2 lines heading
            lines = sec_raw.split('\n', 2)
            sec_body_start = len(lines[0]) + 1 + len(lines[1]) + 1
        else:
            # 1 line heading
            lines = sec_raw.split('\n', 1)
            sec_body_start = len(lines[0]) + 1

        curr_start = sec_body_start
        for seg_idx, match in enumerate(matches, 1):
            seg_end = match.end()
            raw_seg_text = sec_raw[curr_start:seg_end]
            curr_start = seg_end
            
            norm_text = normalize_segment_content(raw_seg_text, title)
            
            seg_tag = f"<!-- === SEGMENT: {sec_num}.{seg_idx} | {sec_num}. {title} === -->"
            output_blocks.append(f"{seg_tag}\n\n{norm_text}\n")
            total_segments += 1
            print(f"Sec {sec_num}.{seg_idx} ({title[:30]}...): length {len(norm_text)} chars")

    # APPENDIX Block
    output_blocks.append(
        "<!-- === SEGMENT: APPENDIX | Огляд судової практики Касаційного кримінального суду у складі Верховного Суду "
        "щодо провокації злочину (актуальна практика). Вихідні дані. Застереження. Технічний сегмент. Не підлягає розподілу === -->\n\n"
        f"{appendix_clean}\n"
    )

    final_content = "\n".join(output_blocks)

    with open(FILE_PATH, 'w', encoding='utf-8', errors='surrogateescape', newline='') as f:
        f.write(final_content)

    print(f"\nSuccessfully wrote normalized content to {FILE_PATH}")
    print(f"Total substantive segments created: {total_segments}")

if __name__ == '__main__':
    main()
