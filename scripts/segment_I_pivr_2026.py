#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
segment_I_pivr_2026.py
Повна нормалізація та сегментація огляду судової практики ККС ВС за І півріччя 2026 року:
documents/markdown/Oglyad_KKS_I_pivr_2026/Oglyad_KKS_I_pivr_2026.md
згідно з brain/conventions.md та .agents/skills/segment-paragraphs/SKILL.md.
"""

import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MD_PATH = BASE_DIR / "documents" / "markdown" / "Oglyad_KKS_I_pivr_2026" / "Oglyad_KKS_I_pivr_2026.md"


def parse_toc(toc_str):
    lines = []
    for l in toc_str.splitlines():
        l_s = l.strip()
        if not l_s:
            continue
        if re.match(r'^(?:РОЗДІЛ|[I|V|X]+\.|\d+\.)', l_s):
            lines.append(l_s)
        else:
            if lines:
                lines[-1] += ' ' + l_s
            else:
                lines.append(l_s)

    chapters = {}
    subchapters = {}
    for line in lines:
        m_ch = re.match(r'^(\d+)\.\s+(.*?)(?:\s*\.{3,}|\s+\d+$)', line)
        if m_ch and not re.match(r'^\d+\.\d+\.', line):
            num = int(m_ch.group(1))
            title = re.sub(r'\s*\.{3,}.*$', '', m_ch.group(2)).strip()
            chapters[num] = title
            continue
        m_sub = re.match(r'^(\d+\.\d+)\.\s+(.*?)(?:\s*\.{3,}|\s+\d+$)', line)
        if m_sub:
            code = m_sub.group(1)
            title = re.sub(r'\s*\.{3,}.*$', '', m_sub.group(2)).strip()
            subchapters[code] = title
    return chapters, subchapters


def parse_positions(body, is_kpk, chapters_map, subchapters_map):
    matches = list(re.finditer(r'<https?://reyestr\.court\.gov\.ua/Review/(\d+)>', body))
    prev = 0
    cur_ch = 1 if not is_kpk else 27
    cur_sub_code = None
    cur_sub_title = None
    results = []
    ch_counters = {}
    special_part_emitted = False

    for i, m in enumerate(matches):
        chunk = body[prev:m.end()].strip()
        prev = m.end()

        # Для КК перевіряємо, чи перейшли до Особливої частини
        emit_special_part = False
        if not is_kpk and 'II. ЗАСТОСУВАННЯ НОРМ ОСОБЛИВОЇ ЧАСТИНИ' in chunk and not special_part_emitted:
            emit_special_part = True
            special_part_emitted = True

        lines = [l.strip() for l in chunk.splitlines() if l.strip()]
        text_lines = []

        j = 0
        while j < len(lines):
            line = lines[j]
            # Пропускаємо технічні заголовки
            if any(k in line for k in ['РОЗДІЛ I', 'РОЗДІЛ II', 'I. ЗАСТОСУВАННЯ НОРМ', 'II. ЗАСТОСУВАННЯ НОРМ']):
                j += 1
                continue

            # Заголовок глави: наприклад "1. Закон..." або "27. Засади..."
            m_ch = re.match(r'^(\d+)\.\s+(.*)', line)
            if m_ch and not re.match(r'^\d+\.\d+\.', line):
                cur_ch = int(m_ch.group(1))
                j += 1
                while j < len(lines) and not re.match(r'^\d+\.', lines[j]) and not any(k in lines[j] for k in ['РОЗДІЛ', 'I.', 'II.']):
                    if lines[j].lower() in chapters_map.get(cur_ch, '').lower():
                        j += 1
                    else:
                        break
                continue

            # Заголовок підрозділу (статті): наприклад "1.1. Законодавство..."
            m_sub = re.match(r'^(\d+\.\d+)\.\s+(.*)', line)
            if m_sub:
                cur_sub_code = m_sub.group(1)
                sub_acc = m_sub.group(2)
                j += 1
                while j < len(lines) and not re.search(r'\(ст\.\s*[\d\-]+[^\)]*\)', sub_acc):
                    sub_acc += ' ' + lines[j]
                    j += 1
                cur_sub_title = subchapters_map.get(cur_sub_code, sub_acc)
                continue

            text_lines.append(line)
            j += 1

        pos_text = ' '.join(' '.join(text_lines).split())
        sub_title_clean = re.sub(r'^\d+\.\d+\.\s*', '', cur_sub_title or '').strip()
        ch_title_clean = chapters_map.get(cur_ch, '').strip()

        if not is_kpk:
            eff_ch_num = cur_ch
        else:
            eff_ch_num = cur_ch - 26

        ch_counters[eff_ch_num] = ch_counters.get(eff_ch_num, 0) + 1
        seg_idx = ch_counters[eff_ch_num]

        seg_tag = f"<!-- === SEGMENT: {eff_ch_num}.{seg_idx} | {eff_ch_num}. {ch_title_clean} === -->"

        prefix_ch = ch_title_clean if ch_title_clean.endswith('.') else (ch_title_clean + '.')
        prefix_sub = (sub_title_clean if sub_title_clean.endswith('.') else (sub_title_clean + '.')) if sub_title_clean else ''

        if prefix_sub:
            full_seg = f"{prefix_ch} {prefix_sub} {pos_text}"
        else:
            full_seg = f"{prefix_ch} {pos_text}"

        results.append({
            'eff_ch': eff_ch_num,
            'seg_idx': seg_idx,
            'tag': seg_tag,
            'body': full_seg,
            'emit_special_part': emit_special_part
        })

    return results


def main():
    print(f"Зчитування {MD_PATH}...")
    with open(MD_PATH, 'r', encoding='utf-8', errors='surrogateescape') as f:
        raw_text = f.read()

    # 1. Очищення від старих службових коментарів, якщо були
    text = re.sub(r'<!--\s*===\s*SEGMENT:.*?===\s*-->', '', raw_text, flags=re.DOTALL)

    # 2. Очищення колонтитулів сторінок PDF
    text = re.sub(r'\n\s*\d+\s*\n\s*Огляд судової практики ККС ВС\s*\n', '\n', text)
    text = re.sub(r'\n\s*Огляд судової практики ККС ВС\s*\n', '\n', text)

    # 3. Нормалізація пробілів у посиланнях на реєстр (якщо були розриви)
    text = re.sub(r'https?://reyestr\.court\.gov\.ua/Review/\s*(\d+)', r'https://reyestr.court.gov.ua/Review/\1', text)

    # 4. Виділення структурних частин
    idx_r1 = text.find('РОЗДІЛ I. ЗАСТОСУВАННЯ НОРМ КРИМІНАЛЬНОГО ПРАВА УКРАЇНИ', 300)
    idx_r2 = text.find('РОЗДІЛ II. ЗАСТОСУВАННЯ НОРМ КРИМІНАЛЬНОГО ПРОЦЕСУАЛЬНОГО', idx_r1)
    idx_epi = text.find('Огляд судової практики Касаційного кримінального суду у складі Верховного Суду\nза І півріччя 2026 року', idx_r2)

    preamble = text[:idx_r1].strip()
    body_kk = text[idx_r1:idx_r2]
    body_kpk = text[idx_r2:idx_epi if idx_epi != -1 else len(text)]
    epilogue = text[idx_epi:].strip() if idx_epi != -1 else ""

    # 5. Парсинг змісту КК та КПК
    idx_toc_r2 = preamble.find('РОЗДІЛ II. ЗАСТОСУВАННЯ НОРМ КРИМІНАЛЬНОГО ПРОЦЕСУАЛЬНОГО')
    toc_kk = preamble[preamble.find('ЗМІСТ'):idx_toc_r2]
    toc_kpk = preamble[idx_toc_r2:preamble.find('ПЕРЕЛІК СКОРОЧЕНЬ')]

    ch_kk, sub_kk = parse_toc(toc_kk)
    ch_kpk, sub_kpk = parse_toc(toc_kpk)

    # 6. Парсинг позицій КК та КПК
    positions_kk = parse_positions(body_kk, False, ch_kk, sub_kk)
    positions_kpk = parse_positions(body_kpk, True, ch_kpk, sub_kpk)

    all_blocks = []

    # 7. Збирання нормалізованого файлу
    # PREAMBLE
    all_blocks.append(
        "<!-- === SEGMENT: PREAMBLE | Огляд судової практики ККС ВС за І півріччя 2026 року. ЗМІСТ. Перелік скорочень. Технічний сегмент. Не підлягає розподілу === -->\n\n"
        + preamble + "\n"
    )

    # РОЗДІЛ I та ЗАГАЛЬНА ЧАСТИНА
    all_blocks.append(
        "<!-- === SEGMENT: РОЗДІЛ I | РОЗДІЛ I. ЗАСТОСУВАННЯ НОРМ КРИМІНАЛЬНОГО ПРАВА УКРАЇНИ. Технічний сегмент. Не підлягає розподілу === -->\n\n"
        "РОЗДІЛ I. ЗАСТОСУВАННЯ НОРМ КРИМІНАЛЬНОГО ПРАВА УКРАЇНИ\n"
    )
    all_blocks.append(
        "<!-- === SEGMENT: I. ЗАСТОСУВАННЯ НОРМ ЗАГАЛЬНОЇ ЧАСТИНИ КРИМІНАЛЬНОГО ПРАВА УКРАЇНИ | I. ЗАСТОСУВАННЯ НОРМ ЗАГАЛЬНОЇ ЧАСТИНИ КРИМІНАЛЬНОГО ПРАВА УКРАЇНИ. Технічний сегмент. Не підлягає розподілу === -->\n\n"
        "I. ЗАСТОСУВАННЯ НОРМ ЗАГАЛЬНОЇ ЧАСТИНИ КРИМІНАЛЬНОГО ПРАВА УКРАЇНИ\n"
    )

    # КК сегменти (з вставкою технічного сегмента Особливої частини перед 11-ю главою)
    for p in positions_kk:
        if p['emit_special_part']:
            all_blocks.append(
                "<!-- === SEGMENT: II. ЗАСТОСУВАННЯ НОРМ ОСОБЛИВОЇ ЧАСТИНИ КРИМІНАЛЬНОГО ПРАВА УКРАЇНИ | II. ЗАСТОСУВАННЯ НОРМ ОСОБЛИВОЇ ЧАСТИНИ КРИМІНАЛЬНОГО ПРАВА УКРАЇНИ. Технічний сегмент. Не підлягає розподілу === -->\n\n"
                "II. ЗАСТОСУВАННЯ НОРМ ОСОБЛИВОЇ ЧАСТИНИ КРИМІНАЛЬНОГО ПРАВА УКРАЇНИ\n"
            )
        all_blocks.append(f"{p['tag']}\n\n{p['body']}\n")

    # РОЗДІЛ II
    all_blocks.append(
        "<!-- === SEGMENT: РОЗДІЛ II | РОЗДІЛ II. ЗАСТОСУВАННЯ НОРМ КРИМІНАЛЬНОГО ПРОЦЕСУАЛЬНОГО ПРАВА УКРАЇНИ. Технічний сегмент. Не підлягає розподілу === -->\n\n"
        "РОЗДІЛ II. ЗАСТОСУВАННЯ НОРМ КРИМІНАЛЬНОГО ПРОЦЕСУАЛЬНОГО ПРАВА УКРАЇНИ\n"
    )

    # КПК сегменти
    for p in positions_kpk:
        all_blocks.append(f"{p['tag']}\n\n{p['body']}\n")

    # APPENDIX
    if epilogue:
        all_blocks.append(
            "<!-- === SEGMENT: APPENDIX | Огляд судової практики ККС ВС за І півріччя 2026 року. Вихідні дані. Технічний сегмент. Не підлягає розподілу === -->\n\n"
            + epilogue + "\n"
        )

    final_text = "\n".join(all_blocks)
    total_legal = len(positions_kk) + len(positions_kpk)
    print(f"Згенеровано: КК сегментів = {len(positions_kk)}, КПК сегментів = {len(positions_kpk)}, Всього юридичних = {total_legal}")

    with open(MD_PATH, 'w', encoding='utf-8', errors='surrogateescape', newline='') as f:
        f.write(final_text)

    print(f"✅ Успішно збережено нормалізований файл: {MD_PATH}")


if __name__ == "__main__":
    main()
