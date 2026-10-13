#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт нормалізації та сегментації огляду:
documents/markdown/Oglyad_KKS_domashnye_nasylstvo(2019-2025)/Oglyad_KKS_domashnye_nasylstvo(2019-2025).md

Правила (brain/conventions.md):
1. Один абзац = один сегмент.
2. Абзац записаний одним рядком (позиція + посилання на постанову).
3. Заголовки/підзаголовки розділу додаються на початок абзацу через «. ».
4. Порожні рядки та артефакти номерів сторінок PDF прибираються.
5. Редагування з errors='surrogateescape', newline=''.
"""

import os
import re
import sys
from pathlib import Path

SRC_PATH = Path("documents/markdown/Oglyad_KKS_domashnye_nasylstvo(2019-2025)/Oglyad_KKS_domashnye_nasylstvo(2019-2025).md")

KNOWN_REMOVE_HEADERS = [
    'РОЗДІЛ І. ЗАСТОСУВАННЯ НОРМ КРИМІНАЛЬНОГО ПРАВА УКРАЇНИ',
    'РОЗДІЛ ІІ. ЗАСТОСУВАННЯ НОРМ КРИМІНАЛЬНОГО ПРОЦЕСУАЛЬНОГО ПРАВА УКРАЇНИ',
    'РОЗДІЛ ІІ. ЗАСТОСУВАННЯ НОРМ КРИМІНАЛЬНОГО ПРОЦЕСУАЛЬНОГО ПРАВА',
    'УКРАЇНИ',
    'І. ЗАГАЛЬНІ ПОЛОЖЕННЯ',
    'ІІ. ДОСУДОВЕ РОЗСЛІДУВАННЯ',
    'ІІІ. СУДОВЕ ПРОВАДЖЕННЯ',
]

SEC_DEFINITIONS = [
    (1, r'1\.\s+Підстава кримінальної відповідальності\. Принцип юридичної\s+відповідальності non bis in idem',
     'Підстава кримінальної відповідальності. Принцип юридичної відповідальності non bis in idem'),
    (2, r'2\.\s+Ознака «систематичність» у домашньому насильстві',
     'Ознака «систематичність» у домашньому насильстві'),
    (3, r'3\.\s+Потерпілі від домашнього насильства',
     'Потерпілі від домашнього насильства'),
    (4, r'4\.\s+Співвідношення поняття «злочин, пов\'язаний із домашнім насильством»\s+із поняттям «домашнє насильство»',
     'Співвідношення поняття «злочин, пов\'язаний із домашнім насильством» із поняттям «домашнє насильство»'),
    (5, r'5\.\s+Призначення покарання та звільнення від його відбування',
     'Призначення покарання та звільнення від його відбування'),
    (6, r'6\.\s+Обмежувальні заходи, які застосовуються до осіб за вчинення домашнього\s+насильства\. Порушення обмежувальних приписів',
     'Обмежувальні заходи, які застосовуються до осіб за вчинення домашнього насильства. Порушення обмежувальних приписів'),
    (7, r'7\.\s+Докази і доказування',
     'Докази і доказування'),
    (8, r'8\.\s+Форми закінчення досудового розслідування\. Закриття кримінального\s+провадження',
     'Форми закінчення досудового розслідування. Закриття кримінального провадження'),
    (9, r'9\.\s+Звернення до суду з обвинувальним актом',
     'Звернення до суду з обвинувальним актом'),
    (10, r'10\.\s+Складання досудової доповіді',
     'Складання досудової доповіді'),
    (11, r'11\.\s+Провадження в суді апеляційної інстанції\. Відмова у відкритті провадження',
     'Провадження в суді апеляційної інстанції. Відмова у відкритті провадження'),
    (12, r'12\.\s+Кримінальне провадження на підставі угод\. Загальний порядок судового\s+провадження на підставі угоди',
     'Кримінальне провадження на підставі угод. Загальний порядок судового провадження на підставі угоди'),
    (13, r'13\.\s+Кримінальне провадження у формі приватного обвинувачення',
     'Кримінальне провадження у формі приватного обвинувачення'),
]

def clean_lines(raw_text: str, sec_title: str, matched_hdr: str) -> str:
    """Видаляє заголовкові рядки та колонтитули і об'єднує текст у суцільний рядок."""
    # Очищуємо від номерів сторінок та колонтитулів
    t = re.sub(r'\n\s*\d+\s*\n\s*Огляд судової практики ККС ВС\s*\n', '\n', raw_text)
    # Прибираємо старі мітки сегментів, якщо трапляються
    t = re.sub(r'<!-- === SEGMENT:.*?=== -->', '', t)
    t = re.sub(r'###\s+.*', '', t)
    
    lines = [l.strip() for l in t.strip().splitlines() if l.strip()]
    cleaned = []
    for l in lines:
        if l in KNOWN_REMOVE_HEADERS:
            continue
        if l == sec_title or l in sec_title:
            continue
        if l == matched_hdr or l in matched_hdr:
            continue
        cleaned.append(l)

    one_line = ' '.join(cleaned)
    one_line = re.sub(r'\s+', ' ', one_line).strip()
    
    # Виправляємо URL рішень
    # Якщо рішення 1 (без номера рев'ю)
    if '755/4894/22' in one_line and 'https://reyestr.court.gov.ua/' in one_line:
        one_line = re.sub(r'<https?://reyestr\.court\.gov\.ua/?>', '<https://reyestr.court.gov.ua/Review/118225366>', one_line)
        one_line = re.sub(r'https?://reyestr\.court\.gov\.ua/?(?!\S)', '<https://reyestr.court.gov.ua/Review/118225366>', one_line)

    # Нормалізація посилань до <https://reyestr.court.gov.ua/Review/\1>
    one_line = re.sub(r'<https?://reyestr\.court\.gov\.ua/[Rr]eview/(\d+)>', r'https://reyestr.court.gov.ua/Review/\1', one_line)
    one_line = re.sub(r'https?://reyestr\.court\.gov\.ua/[Rr]eview/(\d+)', r'<https://reyestr.court.gov.ua/Review/\1>', one_line)
    
    return one_line

def main():
    if not SRC_PATH.exists():
        print(f"Помилка: файл {SRC_PATH} не знайдено.")
        sys.exit(1)

    with open(SRC_PATH, "r", encoding="utf-8", errors="surrogateescape", newline="") as f:
        text = f.read()

    # 1. Знаходження початку тіла
    pos_body = text.find('РОЗДІЛ І. ЗАСТОСУВАННЯ НОРМ КРИМІНАЛЬНОГО ПРАВА УКРАЇНИ', text.find('ПЕРЕЛІК СКОРОЧЕНЬ'))
    if pos_body == -1:
        raise ValueError("Не знайдено початок тіла огляду!")

    # 2. Знаходження закінчення тіла (початок APPENDIX)
    last_url = '<https://reyestr.court.gov.ua/Review/131097093>'
    pos_appendix = text.rfind(last_url)
    if pos_appendix == -1:
        last_url = 'https://reyestr.court.gov.ua/Review/131097093'
        pos_appendix = text.rfind(last_url)
    if pos_appendix == -1:
        raise ValueError("Не знайдено останнє судове рішення для виділення додатку!")
    pos_appendix += len(last_url)

    # 3. Виділення та очищення PREAMBLE
    preamble_raw = text[:pos_body].strip()
    preamble_raw = re.sub(r'\n\s*\d+\s*\n\s*Огляд судової практики ККС ВС\s*\n', '\n\n', preamble_raw)
    preamble_raw = re.sub(r'<!-- === SEGMENT:.*?=== -->', '', preamble_raw)
    preamble_raw = re.sub(r'\n{3,}', '\n\n', preamble_raw).strip()
    preamble_tag = "<!-- === SEGMENT: PREAMBLE | Огляд судової практики Верховного Суду у провадженнях про кримінальні правопорушення, пов’язані з домашнім насильством. ЗМІСТ. Перелік скорочень. Технічний сегмент. Не підлягає розподілу === -->"

    # 4. Виділення та очищення APPENDIX
    appendix_raw = text[pos_appendix:].strip()
    appendix_raw = re.sub(r'\n\s*\d+\s*\n\s*Огляд судової практики ККС ВС\s*\n', '\n\n', appendix_raw)
    appendix_raw = re.sub(r'<!-- === SEGMENT:.*?=== -->', '', appendix_raw)
    appendix_raw = re.sub(r'\n{3,}', '\n\n', appendix_raw).strip()
    appendix_tag = "<!-- === SEGMENT: APPENDIX | Огляд судової практики Верховного Суду у провадженнях про кримінальні правопорушення, пов’язані з домашнім насильством. Вихідні дані. Технічний сегмент. Не підлягає розподілу === -->"

    # 5. Знаходження меж розділів
    body_text = text[pos_body:pos_appendix]
    sec_spans = []
    for num, pat, title in SEC_DEFINITIONS:
        m = re.search(pat, body_text)
        if not m:
            raise ValueError(f"Розділ {num} не знайдено за патерном: {pat}")
        start = pos_body + m.start()
        sec_spans.append((num, title, start, m.group(0)))

    output_parts = [f"{preamble_tag}\n\n{preamble_raw}"]

    total_segments = 0
    for i in range(len(sec_spans)):
        num, title, start, matched_hdr = sec_spans[i]
        end = sec_spans[i+1][2] if i+1 < len(sec_spans) else pos_appendix
        sec_content = text[start + len(matched_hdr):end]

        # Розбиття на окремі справи за реквізитами судових рішень
        dec_pattern = r'((?:Постанов[аі]|Ухвал[аі])\s+.*?(?:https?://[^\s>]+|<https?://[^\s>]+>))'
        parts = re.split(dec_pattern, sec_content, flags=re.DOTALL)

        cases = []
        for p_idx in range(0, len(parts)-1, 2):
            t = parts[p_idx]
            d = parts[p_idx+1]
            cases.append(t + ' ' + d)

        print(f"Розділ {num:02d} ({title}): знайдено {len(cases)} справ(и).")

        for idx, case_raw in enumerate(cases):
            sub_num = idx + 1
            tag = f"<!-- === SEGMENT: {num}.{sub_num} | {num}. {title} === -->"
            cleaned_case = clean_lines(case_raw, title, matched_hdr)
            line = f"{title}. {cleaned_case}"
            output_parts.append(f"{tag}\n\n{line}")
            total_segments += 1

    output_parts.append(f"{appendix_tag}\n\n{appendix_raw}")

    final_content = "\n\n".join(output_parts) + "\n"

    with open(SRC_PATH, "w", encoding="utf-8", errors="surrogateescape", newline="") as f:
        f.write(final_content)

    print(f"\n[SUCCESS] Успішно сформовано {total_segments} змістовних сегментів + PREAMBLE + APPENDIX.")
    print(f"Файл збережено: {SRC_PATH}")

if __name__ == "__main__":
    main()
