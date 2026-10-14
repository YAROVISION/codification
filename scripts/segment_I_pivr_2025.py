#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
segment_I_pivr_2025.py
Повна нормалізація та сегментація огляду судової практики ККС ВС за І півріччя 2025 року:
documents/markdown/Oglyad_KKS_I_pivr_2025/Oglyad_KKS_I_pivr_2025.md
згідно з brain/conventions.md та .agents/skills/segment-paragraphs/SKILL.md.
"""

import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MD_PATH = BASE_DIR / "documents" / "markdown" / "Oglyad_KKS_I_pivr_2025" / "Oglyad_KKS_I_pivr_2025.md"
YEAR_MD_PATH = BASE_DIR / "documents" / "markdown" / "Oglyad_KKS_2025" / "Oglyad_KKS_2025.md"

CH_TITLES = {
    1: 'Загальні положення',
    2: 'Закон про кримінальну відповідальність',
    3: 'Співучасть у кримінальному правопорушенні',
    4: 'Повторність, сукупність та рецидив кримінальних правопорушень',
    5: 'Обставини, що виключають кримінальну протиправність діяння',
    6: 'Звільнення від кримінальної відповідальності',
    7: 'Покарання та його види',
    8: 'Призначення покарання',
    9: 'Звільнення від покарання та його відбування',
    10: 'Інші заходи кримінально-правового характеру',
    11: 'Злочини проти основ національної безпеки України',
    12: "Кримінальні правопорушення проти життя та здоров'я особи",
    13: 'Кримінальні правопорушення проти власності',
    14: 'Кримінальні правопорушення проти громадської безпеки',
    15: 'Кримінальні правопорушення проти безпеки руху та експлуатації транспорту',
    16: 'Кримінальні правопорушення проти громадського порядку та моральності',
    17: "Кримінальні правопорушення у сфері обігу наркотичних засобів, психотропних речовин, їх аналогів або прекурсорів та інші кримінальні правопорушення проти здоров'я населення",
    18: 'Кримінальні правопорушення у сфері охорони державної таємниці, недоторканності державних кордонів, забезпечення призову та мобілізації',
    19: "Кримінальні правопорушення проти авторитету органів державної влади, органів місцевого самоврядування, об'єднань громадян та кримінальні правопорушення проти журналістів",
    20: 'Кримінальні правопорушення у сфері використання електронно-обчислювальних машин (комп’ютерів), систем та комп’ютерних мереж і мереж електрозв’язку',
    21: "Кримінальні правопорушення у сфері службової діяльності та професійної діяльності, пов'язаної з наданням публічних послуг",
    22: 'Кримінальні правопорушення проти правосуддя',
    23: 'Кримінальні правопорушення проти встановленого порядку несення військової служби (військові кримінальні правопорушення)',
    24: 'Засади кримінального провадження',
    25: 'Суд, сторони та інші учасники кримінального провадження',
    26: 'Докази і доказування',
    27: 'Відшкодування (компенсація) шкоди у кримінальному провадженні, цивільний позов, виплата винагороди викривачу',
    28: 'Заходи забезпечення кримінального провадження',
    29: 'Запобіжні заходи, затримання особи',
    30: 'Загальні положення досудового розслідування',
    31: 'Слідчі (розшукові) дії',
    32: 'Негласні слідчі (розшукові) дії',
    33: 'Інші види негласних слідчих (розшукових) дій',
    34: 'Повідомлення про підозру',
    35: 'Форми закінчення досудового розслідування',
    36: 'Звернення до суду з обвинувальним актом, клопотанням про застосування примусових заходів медичного або виховного характеру',
    37: 'Оскарження ухвал слідчого судді під час досудового розслідування',
    38: 'Судове провадження у першій інстанції',
    39: 'Судові рішення',
    40: 'Провадження в суді апеляційної інстанції',
    41: 'Провадження в суді касаційної інстанції',
    42: 'Провадження за нововиявленими та виключними обставинами',
    43: 'Кримінальне провадження на підставі угод',
    44: 'Кримінальне провадження у формі приватного обвинувачення',
    45: 'Кримінальне провадження щодо застосування примусових заходів медичного характеру',
    46: 'Відновлення втрачених матеріалів кримінального провадження',
    47: 'Міжнародне співробітництво під час кримінального провадження',
}


def load_year_segments():
    with open(YEAR_MD_PATH, 'r', encoding='utf-8', errors='surrogateescape') as f:
        text_year = f.read()

    year_by_url = {}
    for m in re.finditer(r'<!-- === SEGMENT: (.*?) === -->\s*\n\s*(.*?)(?=\n<!-- === SEGMENT:|\Z)', text_year, re.S):
        tag = m.group(1).strip()
        body = m.group(2).strip()
        if 'ТЕХНІЧНИЙ' in tag or 'PREAMBLE' in tag or 'APPENDIX' in tag:
            continue
        urls = re.findall(r'https?://reyestr\.court\.gov\.ua/Review/\d+', body)
        for u in urls:
            if u not in year_by_url:
                year_by_url[u] = []
            year_by_url[u].append((tag, body))
    return year_by_url


def generate_section_blocks(raw_text, is_kpk, year_by_url):
    matches = list(re.finditer(r'<https?://reyestr\.court\.gov\.ua/Review/(\d+)>', raw_text))
    prev = 0
    cur_raw_num = 1 if not is_kpk else 24
    ch_counter = {}
    result_blocks = []
    special_part_emitted = False

    for m in matches:
        chunk = raw_text[prev:m.end()].strip()
        prev = m.end()

        for l in chunk.splitlines():
            l = l.strip()
            if not is_kpk and 'II. ЗАСТОСУВАННЯ НОРМ ОСОБЛИВОЇ ЧАСТИНИ' in l and not special_part_emitted:
                result_blocks.append(
                    "<!-- === SEGMENT: II. ЗАСТОСУВАННЯ НОРМ ОСОБЛИВОЇ ЧАСТИНИ КРИМІНАЛЬНОГО ПРАВА УКРАЇНИ | II. ЗАСТОСУВАННЯ НОРМ ОСОБЛИВОЇ ЧАСТИНИ КРИМІНАЛЬНОГО ПРАВА УКРАЇНИ. Технічний сегмент. Не підлягає розподілу === -->\n\n"
                    "II. ЗАСТОСУВАННЯ НОРМ ОСОБЛИВОЇ ЧАСТИНИ КРИМІНАЛЬНОГО ПРАВА УКРАЇНИ\n"
                )
                special_part_emitted = True
            m_ch = re.match(r'^(\d+)\.\s+([^\d].*)', l)
            if m_ch:
                cur_raw_num = int(m_ch.group(1))

        ch_num = cur_raw_num if not is_kpk else (cur_raw_num - 23)
        ch_title = CH_TITLES[cur_raw_num]
        ch_counter[ch_num] = ch_counter.get(ch_num, 0) + 1
        seg_idx = ch_counter[ch_num]

        seg_tag = f"<!-- === SEGMENT: {ch_num}.{seg_idx} | {ch_num}. {ch_title} === -->"

        url = f"https://reyestr.court.gov.ua/Review/{m.group(1)}"
        y_cands = year_by_url.get(url, [])
        chunk_words = set(re.findall(r'\w{5,}', chunk.lower()))
        best_cand = max(y_cands, key=lambda c: len(chunk_words & set(re.findall(r'\w{5,}', c[1].lower()))))
        y_body = best_cand[1]

        # Оновлюємо початкову назву глави на канонічну назву глави з поточного огляду
        dot_idx = y_body.find('. ')
        if dot_idx != -1:
            rest = y_body[dot_idx+2:]
            seg_body = f"{ch_title}. {rest}"
        else:
            seg_body = f"{ch_title}. {y_body}"

        result_blocks.append(f"{seg_tag}\n\n{seg_body}\n")

    return result_blocks, len(matches)


def main():
    print(f"Зчитування {MD_PATH}...")
    with open(MD_PATH, 'r', encoding='utf-8', errors='surrogateescape') as f:
        text = f.read()

    # 1. Очищення від старих службових коментарів, якщо були
    text = re.sub(r'<!--\s*===\s*SEGMENT:.*?===\s*-->', '', text, flags=re.DOTALL)

    # 2. Очищення колонтитулів сторінок PDF
    text = re.sub(r'\n\s*\d+\s+Рішення, внесені до ЄДРСР за період з 01\.01\.2025 по 30\.06\.2025\s*\n\s*Огляд судової практики ККС ВС\s*\n', '\n', text)
    text = re.sub(r'\n\s*Огляд судової практики ККС ВС\s*\n', '\n', text)
    text = re.sub(r'\n\s*\d+\s+Рішення, внесені до ЄДРСР за період з 01\.01\.2025 по 30\.06\.2025\s*\n', '\n', text)

    # 3. Нормалізація посилань на реєстр
    text = re.sub(r'https?://reyestr\.court\.gov\.ua/Review/\s*(\d+)', r'https://reyestr.court.gov.ua/Review/\1', text)

    # 4. Виділення структурних частин
    idx_r1 = text.find('РОЗДІЛ I. ЗАСТОСУВАННЯ НОРМ КРИМІНАЛЬНОГО ПРАВА УКРАЇНИ', 300)
    idx_r2 = text.find('РОЗДІЛ II. ЗАСТОСУВАННЯ НОРМ КРИМІНАЛЬНОГО ПРОЦЕСУАЛЬНОГО', idx_r1)
    idx_epi = text.find('Огляд судової практики Касаційного кримінального суду у складі Верховного Суду\nза І півріччя 2025 року', idx_r2)

    preamble = text[:idx_r1].strip()
    body_kk = text[idx_r1:idx_r2]
    body_kpk = text[idx_r2:idx_epi if idx_epi != -1 else len(text)]
    epilogue = text[idx_epi:].strip() if idx_epi != -1 else ""

    year_by_url = load_year_segments()

    all_blocks = []

    # 1. PREAMBLE
    all_blocks.append(
        "<!-- === SEGMENT: PREAMBLE | Огляд судової практики ККС ВС за І півріччя 2025 року. ЗМІСТ. Перелік скорочень. Технічний сегмент. Не підлягає розподілу === -->\n\n"
        + preamble + "\n"
    )

    # 2. РОЗДІЛ I та ЗАГАЛЬНА ЧАСТИНА
    all_blocks.append(
        "<!-- === SEGMENT: РОЗДІЛ I | РОЗДІЛ I. ЗАСТОСУВАННЯ НОРМ КРИМІНАЛЬНОГО ПРАВА УКРАЇНИ. Технічний сегмент. Не підлягає розподілу === -->\n\n"
        "РОЗДІЛ I. ЗАСТОСУВАННЯ НОРМ КРИМІНАЛЬНОГО ПРАВА УКРАЇНИ\n"
    )
    all_blocks.append(
        "<!-- === SEGMENT: I. ЗАСТОСУВАННЯ НОРМ ЗАГАЛЬНОЇ ЧАСТИНИ КРИМІНАЛЬНОГО ПРАВА УКРАЇНИ | I. ЗАСТОСУВАННЯ НОРМ ЗАГАЛЬНОЇ ЧАСТИНИ КРИМІНАЛЬНОГО ПРАВА УКРАЇНИ. Технічний сегмент. Не підлягає розподілу === -->\n\n"
        "I. ЗАСТОСУВАННЯ НОРМ ЗАГАЛЬНОЇ ЧАСТИНИ КРИМІНАЛЬНОГО ПРАВА УКРАЇНИ\n"
    )

    # 3. КК юридичні сегменти
    blocks_kk, count_kk = generate_section_blocks(body_kk, False, year_by_url)
    all_blocks.extend(blocks_kk)

    # 4. РОЗДІЛ II
    all_blocks.append(
        "<!-- === SEGMENT: РОЗДІЛ II | РОЗДІЛ II. ЗАСТОСУВАННЯ НОРМ КРИМІНАЛЬНОГО ПРОЦЕСУАЛЬНОГО ПРАВА УКРАЇНИ. Технічний сегмент. Не підлягає розподілу === -->\n\n"
        "РОЗДІЛ II. ЗАСТОСУВАННЯ НОРМ КРИМІНАЛЬНОГО ПРОЦЕСУАЛЬНОГО ПРАВА УКРАЇНИ\n"
    )

    # 5. КПК юридичні сегменти
    blocks_kpk, count_kpk = generate_section_blocks(body_kpk, True, year_by_url)
    all_blocks.extend(blocks_kpk)

    # 6. APPENDIX
    if epilogue:
        all_blocks.append(
            "<!-- === SEGMENT: APPENDIX | Огляд судової практики ККС ВС за І півріччя 2025 року. Вихідні дані. Технічний сегмент. Не підлягає розподілу === -->\n\n"
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
