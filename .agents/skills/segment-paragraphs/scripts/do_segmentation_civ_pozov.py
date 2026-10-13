#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт нормалізації та сегментації огляду:
documents/markdown/Oglyad_KKS_civ_pozov/Oglyad_KKS_civ_pozov.md

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

SRC_PATH = Path("documents/markdown/Oglyad_KKS_civ_pozov/Oglyad_KKS_civ_pozov.md")

KNOWN_HEADERS = {
    'I. ВИСНОВКИ ВЕЛИКОЇ ПАЛАТИ ВЕРХОВНОГО СУДУ',
    'II. СТОРОНИ ЦИВІЛЬНОГО ПОЗОВУ У КРИМІНАЛЬНОМУ ПРОВАДЖЕННІ',
    '1. Цивільний позивач',
    '2. Цивільний відповідач як суб’єкт відшкодування шкоди',
    '1) Відповідальність особи, діянням якої заподіяно шкоду',
    '2) Роботодавець обвинуваченого (засудженого) як суб’єкт, на якого покладається',
    'обов’язок з відшкодування шкоди',
    'III. ЗАСТОСУВАННЯ ПОЛОЖЕНЬ ЗАКОНОДАВСТВА ПРО СТРАХУВАННЯ ПІД ЧАС',
    'РОЗГЛЯДУ КРИМІНАЛЬНИХ ПРОВАДЖЕНЬ',
    'IV. СОЛІДАРНА ВІДПОВІДАЛЬНІСТЬ КІЛЬКОХ ОСІБ ЗА ШКОДУ, ЗАПОДІЯНУ',
    'КРИМІНАЛЬНИМ ПРАВОПОРУШЕННЯМ',
    'V. ВІДШКОДУВАННЯ ШКОДИ, ЗАПОДІЯНОЇ НЕОСУДНОЮ ОСОБОЮ',
    'VI. ВИРІШЕННЯ ЦИВІЛЬНОГО ПОЗОВУ ПРО ВІДШКОДУВАННЯ ОКРЕМИХ ВИДІВ',
    'ШКОДИ',
    '1. Шкода життю та здоров’ю (смерть, втрата працездатності, витрати на лікування',
    'тощо)',
    '2. Моральна шкода',
    '3. Упущена вигода',
    '4. Витрати на поховання',
    'VII. СПІВВІДНОШЕННЯ МАТЕРІАЛЬНОЇ ШКОДИ І СКЛАДУ КРИМІНАЛЬНОГО',
    'ПРАВОПОРУШЕННЯ',
    'VIII. ПРОЦЕСУАЛЬНІ ПИТАННЯ, ЯКІ ВИНИКАЮТЬ ПІД ЧАС РОЗГЛЯДУ ЦИВІЛЬНОГО',
    'ПОЗОВУ'
}

def clean_lines(raw_text: str) -> str:
    """Видаляє заголовкові рядки та об'єднує текст у суцільний рядок."""
    lines = [l.strip() for l in raw_text.strip().splitlines() if l.strip()]
    cleaned = [l for l in lines if l not in KNOWN_HEADERS]
    one_line = ' '.join(cleaned)
    one_line = re.sub(r'\s+', ' ', one_line).strip()
    # Нормалізація URL реєстру до єдиного формату <https://reyestr.court.gov.ua/Review/...>
    one_line = re.sub(r'<https?://reyestr\.court\.gov\.ua/[Rr]eview/(\d+)>', r'https://reyestr.court.gov.ua/Review/\1', one_line)
    one_line = re.sub(r'https?://reyestr\.court\.gov\.ua/[Rr]eview/(\d+)', r'<https://reyestr.court.gov.ua/Review/\1>', one_line)
    return one_line


def main():
    if not SRC_PATH.exists():
        print(f"Помилка: файл {SRC_PATH} не знайдено.")
        sys.exit(1)

    with open(SRC_PATH, "r", encoding="utf-8", errors="surrogateescape", newline="") as f:
        orig_text = f.read()

    # 1. Очищення номерів сторінок та колонтитулів PDF
    cleaned = re.sub(r'\n\s*\d+\s*\n\s*Огляд судової практики Верховного Суду\s*\n', '\n', orig_text)

    # 2. Виділення PREAMBLE
    start_body = cleaned.find('I. ВИСНОВКИ ВЕЛИКОЇ ПАЛАТИ ВЕРХОВНОГО СУДУ\n', cleaned.find('ЦК Цивільний кодекс України'))
    preamble_raw = cleaned[:start_body].strip()

    # 3. Виділення APPENDIX
    last_url_str = '<https://reyestr.court.gov.ua/Review/134881235>'
    end_last_case_pos = cleaned.rfind(last_url_str)
    if end_last_case_pos == -1:
        # Fallback without brackets
        last_url_str = 'https://reyestr.court.gov.ua/Review/134881235'
        end_last_case_pos = cleaned.rfind(last_url_str)
    end_last_case = end_last_case_pos + len(last_url_str)
    appendix_raw = cleaned[end_last_case:].strip()

    # 4. Основне тіло
    body = cleaned[start_body:end_last_case]

    # Знаходження меж 8 основних розділів
    sec_patterns = [
        (1, r'I\.\s+ВИСНОВКИ ВЕЛИКОЇ ПАЛАТИ ВЕРХОВНОГО СУДУ'),
        (2, r'II\.\s+СТОРОНИ ЦИВІЛЬНОГО ПОЗОВУ У КРИМІНАЛЬНОМУ ПРОВАДЖЕННІ'),
        (3, r'III\.\s+ЗАСТОСУВАННЯ ПОЛОЖЕНЬ ЗАКОНОДАВСТВА ПРО СТРАХУВАННЯ'),
        (4, r'IV\.\s+СОЛІДАРНА ВІДПОВІДАЛЬНІСТЬ КІЛЬКОХ ОСІБ'),
        (5, r'V\.\s+ВІДШКОДУВАННЯ ШКОДИ, ЗАПОДІЯНОЇ НЕОСУДНОЮ ОСОБОЮ'),
        (6, r'VI\.\s+ВИРІШЕННЯ ЦИВІЛЬНОГО ПОЗОВУ ПРО ВІДШКОДУВАННЯ ОКРЕМИХ ВИДІВ'),
        (7, r'VII\.\s+СПІВВІДНОШЕННЯ МАТЕРІАЛЬНОЇ ШКОДИ І СКЛАДУ КРИМІНАЛЬНОГО'),
        (8, r'VIII\.\s+ПРОЦЕСУАЛЬНІ ПИТАННЯ, ЯКІ ВИНИКАЮТЬ ПІД ЧАС РОЗГЛЯДУ ЦИВІЛЬНОГО')
    ]

    splits = []
    for num, p in sec_patterns:
        m = re.search(p, body)
        splits.append(m.start())
    splits.append(len(body))

    url_pat = re.compile(r'(?:<https?://reyestr\.court\.gov\.ua/Review/\d+>|https?://reyestr\.court\.gov\.ua/Review/\d+)')

    def extract_positions(text):
        matches = list(url_pat.finditer(text))
        cases = []
        prev_end = 0
        i = 0
        while i < len(matches):
            m = matches[i]
            end_pos = m.end()
            # Включення блоку «Аналогічні правові позиції»
            while i + 1 < len(matches):
                next_m = matches[i+1]
                gap = text[end_pos:next_m.start()]
                if 'Аналогічн' in gap or (gap.strip().startswith('Постанова') and 'справі' in gap):
                    end_pos = next_m.end()
                    i += 1
                else:
                    break
            case_raw = text[prev_end:end_pos].strip()
            cases.append(case_raw)
            prev_end = end_pos
            i += 1
        return cases

    output_parts = []

    # PREAMBLE
    preamble_tag = "<!-- === SEGMENT: PREAMBLE | Огляд судової практики Верховного Суду щодо цивільного позову в кримінальному провадженні. ЗМІСТ. Перелік скорочень. Технічний сегмент. Не підлягає розподілу === -->"
    output_parts.append(f"{preamble_tag}\n\n{preamble_raw}")

    # РОЗДІЛ I
    c1 = extract_positions(body[splits[0]:splits[1]])
    for idx, c in enumerate(c1):
        tag = f"<!-- === SEGMENT: 1.{idx+1} | 1. Висновки Великої Палати Верховного Суду === -->"
        prefix = "Висновки Великої Палати Верховного Суду. "
        line = prefix + clean_lines(c)
        output_parts.append(f"{tag}\n\n{line}")

    # РОЗДІЛ II
    c2 = extract_positions(body[splits[1]:splits[2]])
    for idx, c in enumerate(c2):
        if idx < 6: # 2.1 to 2.6
            tag = f"<!-- === SEGMENT: 2.{idx+1} | 2. Сторони цивільного позову у кримінальному провадженні. Цивільний позивач === -->"
            prefix = "Сторони цивільного позову у кримінальному провадженні. Цивільний позивач. "
        elif idx < 8: # 2.7 to 2.8
            tag = f"<!-- === SEGMENT: 2.{idx+1} | 2. Сторони цивільного позову у кримінальному провадженні. Відповідальність особи, діянням якої заподіяно шкоду === -->"
            prefix = "Сторони цивільного позову у кримінальному провадженні. Цивільний відповідач як суб’єкт відшкодування шкоди. Відповідальність особи, діянням якої заподіяно шкоду. "
        else: # 2.9 to 2.19
            tag = f"<!-- === SEGMENT: 2.{idx+1} | 2. Сторони цивільного позову у кримінальному провадженні. Роботодавець обвинуваченого (засудженого) як суб’єкт відшкодування шкоди === -->"
            prefix = "Сторони цивільного позову у кримінальному провадженні. Цивільний відповідач як суб’єкт відшкодування шкоди. Роботодавець обвинуваченого (засудженого) як суб’єкт, на якого покладається обов’язок з відшкодування шкоди. "
        line = prefix + clean_lines(c)
        output_parts.append(f"{tag}\n\n{line}")

    # РОЗДІЛ III
    c3 = extract_positions(body[splits[2]:splits[3]])
    for idx, c in enumerate(c3):
        tag = f"<!-- === SEGMENT: 3.{idx+1} | 3. Застосування положень законодавства про страхування під час розгляду кримінальних проваджень === -->"
        prefix = "Застосування положень законодавства про страхування під час розгляду кримінальних проваджень. "
        line = prefix + clean_lines(c)
        output_parts.append(f"{tag}\n\n{line}")

    # РОЗДІЛ IV
    c4 = extract_positions(body[splits[3]:splits[4]])
    for idx, c in enumerate(c4):
        tag = f"<!-- === SEGMENT: 4.{idx+1} | 4. Солідарна відповідальність кількох осіб за шкоду, заподіяну кримінальним правопорушенням === -->"
        prefix = "Солідарна відповідальність кількох осіб за шкоду, заподіяну кримінальним правопорушенням. "
        line = prefix + clean_lines(c)
        output_parts.append(f"{tag}\n\n{line}")

    # РОЗДІЛ V
    c5 = extract_positions(body[splits[4]:splits[5]])
    for idx, c in enumerate(c5):
        tag = f"<!-- === SEGMENT: 5.{idx+1} | 5. Відшкодування шкоди, заподіяної неосудною особою === -->"
        prefix = "Відшкодування шкоди, заподіяної неосудною особою. "
        line = prefix + clean_lines(c)
        output_parts.append(f"{tag}\n\n{line}")

    # РОЗДІЛ VI
    c6 = extract_positions(body[splits[5]:splits[6]])
    for idx, c in enumerate(c6):
        if idx < 4: # 6.1 to 6.4
            tag = f"<!-- === SEGMENT: 6.{idx+1} | 6. Вирішення цивільного позову про відшкодування окремих видів шкоди. Шкода життю та здоров’ю === -->"
            prefix = "Вирішення цивільного позову про відшкодування окремих видів шкоди. Шкода життю та здоров’ю (смерть, втрата працездатності, витрати на лікування тощо). "
        elif idx < 8: # 6.5 to 6.8
            tag = f"<!-- === SEGMENT: 6.{idx+1} | 6. Вирішення цивільного позову про відшкодування окремих видів шкоди. Моральна шкода === -->"
            prefix = "Вирішення цивільного позову про відшкодування окремих видів шкоди. Моральна шкода. "
        elif idx < 10: # 6.9 to 6.10
            tag = f"<!-- === SEGMENT: 6.{idx+1} | 6. Вирішення цивільного позову про відшкодування окремих видів шкоди. Упущена вигода === -->"
            prefix = "Вирішення цивільного позову про відшкодування окремих видів шкоди. Упущена вигода. "
        else: # 6.11
            tag = f"<!-- === SEGMENT: 6.{idx+1} | 6. Вирішення цивільного позову про відшкодування окремих видів шкоди. Витрати на поховання === -->"
            prefix = "Вирішення цивільного позову про відшкодування окремих видів шкоди. Витрати на поховання. "
        line = prefix + clean_lines(c)
        output_parts.append(f"{tag}\n\n{line}")

    # РОЗДІЛ VII
    c7 = extract_positions(body[splits[6]:splits[7]])
    for idx, c in enumerate(c7):
        tag = f"<!-- === SEGMENT: 7.{idx+1} | 7. Співвідношення матеріальної шкоди і складу кримінального правопорушення === -->"
        prefix = "Співвідношення матеріальної шкоди і складу кримінального правопорушення. "
        line = prefix + clean_lines(c)
        output_parts.append(f"{tag}\n\n{line}")

    # РОЗДІЛ VIII
    c8 = extract_positions(body[splits[7]:splits[8]])
    for idx, c in enumerate(c8):
        tag = f"<!-- === SEGMENT: 8.{idx+1} | 8. Процесуальні питання, які виникають під час розгляду цивільного позову === -->"
        prefix = "Процесуальні питання, які виникають під час розгляду цивільного позову. "
        line = prefix + clean_lines(c)
        output_parts.append(f"{tag}\n\n{line}")

    # APPENDIX
    appendix_tag = "<!-- === SEGMENT: APPENDIX | Огляд судової практики Верховного Суду щодо цивільного позову в кримінальному провадженні. Вихідні дані. Технічний сегмент. Не підлягає розподілу === -->"
    output_parts.append(f"{appendix_tag}\n\n{appendix_raw}")

    final_text = "\n\n".join(output_parts) + "\n"

    # Запис у вихідний файл
    with open(SRC_PATH, "w", encoding="utf-8", errors="surrogateescape", newline="") as f:
        f.write(final_text)

    total_legal = len(output_parts) - 2
    print(f"✅ Успішно нормалізовано та сегментовано {SRC_PATH}")
    print(f"📊 Всього сегментів: {len(output_parts)} (1 PREAMBLE + {total_legal} правових позицій + 1 APPENDIX)")


if __name__ == "__main__":
    main()
