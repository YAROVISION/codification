#!/usr/bin/env python3
"""
Скрипт інтелектуальної класифікації та встановлення взаємозв'язків між сегментами судової практики
(documents/segments/<doc_name>/) та деревом класифікатора законодавства (data/classifier.sqlite).

Правила аналізу:
1. Зчитування перших 4 речень сегмента (ігноруючи технічні файли: 00_Preamble.md, заголовки частин).
2. Виявлення статті Закону (ст. 50 КК, стаття 50 КК, ст 50 КК, ч. 2 ст. 307 КК тощо).
3. Визначення кодексу за абревіатурою (КК, КПК, ЦК, КУпАП, КАС/КАСУ, ГПК, ЦПК, КУзПБ, КЗпП, СК, ЖК, МК, ПК, БК, КВК).
4. Визначення розділу та підрозділу за номером статті або назвою розділу/підрозділу з перших 4 речень / заголовку сегмента.
5. Запис взаємозв'язку до таблиці `mapped_segments` бази `data/classifier.sqlite`.
"""

import os
import re
import sys
import glob
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "classifier.sqlite"

# Словник скорочень кодексів та відповідних кореневих кодів у класифікаторі
CODE_ABBR_MAP = {
    'КК': ('130 10', 'Кримінальний кодекс України', '130'),
    'КПК': ('140 10', 'Кримінальний процесуальний кодекс України', '140'),
    'ЦК': ('20 10', 'Цивільний кодекс України', '20'),
    'ЦПК': ('30 10', 'Цивільний процесуальний кодекс України', '30'),
    'ГПК': ('40 10', 'Господарський процесуальний кодекс України', '40'),
    'КУЗПБ': ('50 10', 'Кодекс України з процедур банкрутства', '50'),
    'КЗПП': ('60 10', 'Кодекс законів про працю України', '60'),
    'СК': ('70 10', 'Сімейний кодекс України', '70'),
    'ЖК': ('80 20', 'Житловий кодекс України', '80'),
    'МК': ('90 10', 'Митний кодекс України', '90'),
    'ПК': ('100 10', 'Податковий кодекс України', '100'),
    'ПКУ': ('100 10', 'Податковий кодекс України', '100'),
    'КУПАП': ('110 10', 'Кодекс України про адміністративні правопорушення', '110'),
    'КАС': ('120 10', 'Кодекс адміністративного судочинства України', '120'),
    'КАСУ': ('120 10', 'Кодекс адміністративного судочинства України', '120'),
    'КВК': ('150 10', 'Кримінально-виконавчий кодекс України', '150'),
    'БК': ('10 10', 'Бюджетний кодекс України', '10'),
}

# Мапінг повних назв кодексів до їхніх скорочень
FULL_CODE_NAME_MAP = {
    'КРИМІНАЛЬНИЙ ПРОЦЕСУАЛЬНИЙ КОДЕКС УКРАЇНИ': 'КПК',
    'КРИМІНАЛЬНОГО ПРОЦЕСУАЛЬНОГО КОДЕКСУ УКРАЇНИ': 'КПК',
    'КРИМІНАЛЬНИЙ КОДЕКС УКРАЇНИ': 'КК',
    'КРИМІНАЛЬНОГО КОДЕКСУ УКРАЇНИ': 'КК',
    'ЦИВІЛЬНИЙ КОДЕКС УКРАЇНИ': 'ЦК',
    'ЦИВІЛЬНОГО КОДЕКСУ УКРАЇНИ': 'ЦК',
    'ЦИВІЛЬНИЙ ПРОЦЕСУАЛЬНИЙ КОДЕКС УКРАЇНИ': 'ЦПК',
    'ЦИВІЛЬНОГО ПРОЦЕСУАЛЬНОГО КОДЕКСУ УКРАЇНИ': 'ЦПК',
    'ГОСПОДАРСЬКИЙ ПРОЦЕСУАЛЬНИЙ КОДЕКС УКРАЇНИ': 'ГПК',
    'ГОСПОДАРСЬКОГО ПРОЦЕСУАЛЬНОГО КОДЕКСУ УКРАЇНИ': 'ГПК',
    'КОДЕКС АДМІНІСТРАТИВНОГО СУДОЧИНСТВА УКРАЇНИ': 'КАС',
    'КОДЕКСУ АДМІНІСТРАТИВНОГО СУДОЧИНСТВА УКРАЇНИ': 'КАС',
    'КОДЕКС УКРАЇНИ ПРО АДМІНІСТРАТИВНІ ПРАВОПОРУШЕННЯ': 'КУПАП',
}

# Регулярний вираз для пошуку статті та кодексу (підтримує п. 10 ч. 1 ст. 309 КПК, ст. 50 КК, стаття 111-1 КК)
ARTICLE_PATTERN = re.compile(
    r'(?:(?:п(?:ункт(?:ом|у|а)?)?\.?\s*\d+\s*)?(?:ч(?:астин(?:ою|і|а)?)?\.?\s*\d+\s*)?(?:ст(?:атт[іеяю]|[\.\s])?|стаття)\s*(\d+(?:[-–]\d+)?))\s*([А-Яа-яЄІЇA-Za-z]+)',
    re.IGNORECASE
)

CASE_NUM_PATTERN = re.compile(
    r'(?:справ[іае]\s*(?:№\s*)?|№\s*)([0-9]{3,4}/[0-9]+/[0-9]{2}(?:-[а-я0-9]+)?)',
    re.IGNORECASE
)

REYESTR_URL_PATTERN = re.compile(
    r'https?://(?:reyestr\.court\.gov\.ua/Review/|court\.gov\.ua/)\d+',
    re.IGNORECASE
)


def get_first_sentences(text: str, n: int = 4) -> str:
    """Витягує перші N речень із тексту сегмента, очищеного від HTML-коментарів."""
    clean = re.sub(r'<!--.*?-->', '', text).strip()
    # Якщо є кілька абзаців, беремо початок
    sentences = re.split(r'(?<=[.!?])\s+', clean)
    return ' '.join(sentences[:n])


def parse_article_number(art_str: str) -> float:
    """Перетворює статтю '111-1' на число для порівняння (111.1)."""
    clean_art = art_str.replace('–', '-').strip()
    if '-' in clean_art:
        parts = clean_art.split('-')
        try:
            return float(parts[0]) + float(parts[1]) / 100.0
        except ValueError:
            return float(parts[0])
    try:
        return float(clean_art)
    except ValueError:
        return 0.0


def map_criminal_code_article(art_num: float, text_snippet: str) -> str:
    """Визначає точну рубрику КК (130 10 ...) за номером статті."""
    # Загальна частина (ст. 1 - 108)
    if art_num < 109:
        if art_num <= 4:
            return "130 10 10 10"   # Розділ I. Загальні положення
        elif art_num <= 10:
            return "130 10 10 20"   # Розділ II. Закон про кримінальну відповідальність
        elif art_num <= 17:
            return "130 10 10 30"   # Розділ III. Кримінальне правопорушення
        elif art_num <= 22:
            return "130 10 10 40"   # Розділ IV. Особа, яка підлягає кримінальній відповідальності
        elif art_num <= 25:
            return "130 10 10 50"   # Розділ V. Вина та її форми
        elif art_num <= 31:
            return "130 10 10 60"   # Розділ VI. Співучасть
        elif art_num <= 35:
            return "130 10 10 70"   # Розділ VII. Повторність, сукупність, рецидив
        elif art_num <= 43.99:
            return "130 10 10 80"   # Розділ VIII. Обставини, що виключають протиправність
        elif art_num <= 49.99:
            return "130 10 10 90"   # Розділ IX. Звільнення від кримінальної відповідальності
        elif art_num <= 64.99:
            return "130 10 10 100"  # Розділ X. Покарання та його види
        elif art_num <= 73.99:
            return "130 10 10 110"  # Розділ XI. Призначення покарання
        elif art_num <= 87.99:
            return "130 10 10 120"  # Розділ XII. Звільнення від покарання
        elif art_num <= 91.99:
            return "130 10 10 130"  # Розділ XIII. Судимість
        elif art_num <= 96.0:
            return "130 10 10 140"  # Розділ XIV. Примусові заходи медичного характеру
        elif art_num <= 96.2:
            return "130 10 10 150"  # Розділ XIV-1. Спеціальна конфіскація
        elif art_num <= 96.10:
            return "130 10 10 160"  # Розділ XIV-2. Заходи щодо юросіб
        else:
            return "130 10 10 170"  # Розділ XV. Неповнолітні
    
    # Особлива частина (ст. 109 - 447)
    if art_num <= 114.99:
        return "130 10 20 10"       # Розділ I. Проти основ нацбезпеки
    elif art_num <= 145.99:
        return "130 10 20 20"       # Розділ II. Проти життя та здоров'я
    elif art_num <= 151.99:
        return "130 10 20 30"       # Розділ III. Проти волі, честі, гідності
    elif art_num <= 156.99:
        return "130 10 20 40"       # Розділ IV. Проти статевої свободи
    elif art_num <= 184.99:
        return "130 10 20 50"       # Розділ V. Проти виборчих, трудових прав
    elif art_num <= 198.99:
        return "130 10 20 60"       # Розділ VI. Проти власності
    elif art_num <= 235.99:
        return "130 10 20 70"       # Розділ VII. У сфері госпдіяльності
    elif art_num <= 254.99:
        return "130 10 20 80"       # Розділ VIII. Проти довкілля
    elif art_num <= 270.99:
        return "130 10 20 90"       # Розділ IX. Проти громадської безпеки
    elif art_num <= 275.99:
        return "130 10 20 100"      # Розділ X. Проти безпеки виробництва
    elif art_num <= 292.99:
        return "130 10 20 110"      # Розділ XI. Проти безпеки руху та транспорту
    elif art_num <= 304.99:
        return "130 10 20 120"      # Розділ XII. Проти громадського порядку та моральності
    elif art_num <= 327.99:
        return "130 10 20 130"      # Розділ XIII. У сфері обігу наркотиків
    elif art_num <= 341.99:
        return "130 10 20 140"      # Розділ XIV. Охорона держтаємниці, кордонів, призов
    elif art_num <= 360.99:
        return "130 10 20 150"      # Розділ XV. Проти авторитету влади
    elif art_num <= 363.99:
        return "130 10 20 160"      # Розділ XVI. Комп'ютерні злочини
    elif art_num <= 370.99:
        return "130 10 20 170"      # Розділ XVII. Службові злочини, корупція
    elif art_num <= 400.99:
        return "130 10 20 180"      # Розділ XVIII. Проти правосуддя
    elif art_num <= 435.99:
        return "130 10 20 190"      # Розділ XIX. Військові злочини
    else:
        return "130 10 20 200"      # Розділ XX. Проти миру, безпеки людства


def map_criminal_proc_code_article(art_num: float, text_snippet: str) -> str:
    """Визначає точну рубрику КПК (140 10 ...) за номером статті."""
    if art_num <= 6.99:
        return "140 10 10 10"       # Глава 1. Законодавство та сфера дії
    elif art_num <= 29.99:
        return "140 10 10 20"       # Глава 2. Засади кримінального провадження
    elif art_num <= 83.99:
        # Учасники (Глава 3, ст. 30 - 83)
        if art_num <= 39.99:
            return "140 10 10 30 10" # § 1. Суд і підсудність
        elif art_num <= 41.99:
            return "140 10 10 30 20" # § 2. Сторона обвинувачення (прокурор, слідчий)
        elif art_num <= 54.99:
            return "140 10 10 30 30" # § 3. Сторона захисту (підозрюваний, захисник)
        elif art_num <= 64.99:
            return "140 10 10 30 40" # § 4. Потерпілий
        elif art_num <= 74.99:
            return "140 10 10 30 50" # § 5. Інші учасники (свідок, експерт)
        else:
            return "140 10 10 30 60" # § 6. Відводи
    elif art_num <= 102.99:
        # Глава 4. Докази і доказування (ст. 84 - 102)
        if art_num <= 90.99:
            return "140 10 10 40 10" # § 1. Поняття доказів, належність та допустимість
        elif art_num <= 94.99:
            return "140 10 10 40 20" # § 2. Доказування
        elif art_num <= 97.99:
            return "140 10 10 40 30" # § 3. Показання
        elif art_num <= 100.99:
            return "140 10 10 40 40" # § 4. Речові докази і документи
        else:
            return "140 10 10 40 50" # § 5. Висновок експерта
    elif art_num <= 109.99:
        return "140 10 10 50"       # Глава 5. Фіксування
    elif art_num <= 112.99:
        return "140 10 10 60"       # Глава 6. Процесуальні рішення
    elif art_num <= 117.99:
        return "140 10 10 70"       # Глава 7. Процесуальні строки
    elif art_num <= 130.99:
        return "140 10 10 80"       # Глава 8. Процесуальні витрати
    elif art_num <= 132.99:
        return "140 10 20 10"       # Глава 9. Заходи забезпечення
    elif art_num <= 139.99:
        return "140 10 20 20"       # Глава 10. Виклик
    elif art_num <= 143.99:
        return "140 10 20 30"       # Глава 11. Привід
    elif art_num <= 147.99:
        return "140 10 20 40"       # Глава 12. Грошове стягнення
    elif art_num <= 153.99:
        return "140 10 20 50"       # Глава 13. Тимчасове обмеження
    elif art_num <= 158.99:
        return "140 10 20 60"       # Глава 14. Відсторонення від посади
    elif art_num <= 166.99:
        return "140 10 20 70"       # Глава 15. Тимчасовий доступ до речей
    elif art_num <= 169.99:
        return "140 10 20 80"       # Глава 16. Тимчасове вилучення майна
    elif art_num <= 175.99:
        return "140 10 20 90"       # Глава 17. Арешт майна
    elif art_num <= 213.99:
        return "140 10 20 100"      # Глава 18. Запобіжні заходи
    elif art_num <= 222.99:
        return "140 10 30 10"       # Глава 19. Досудове розслідування: загальні положення
    elif art_num <= 245.99:
        return "140 10 30 20"       # Глава 20. Слідчі (розшукові) дії
    elif art_num <= 275.99:
        return "140 10 30 30"       # Глава 21. НСРД
    elif art_num <= 279.99:
        return "140 10 30 40"       # Глава 22. Повідомлення про підозру
    elif art_num <= 282.99:
        return "140 10 30 50"       # Глава 23. Зупинення розслідування
    elif art_num <= 293.99:
        return "140 10 30 60"       # Глава 24. Закінчення розслідування
    elif art_num <= 297.99:
        return "140 10 30 70"       # Глава 24-1. Спеціальне досудове розслідування
    elif art_num <= 302.99:
        return "140 10 30 80"       # Глава 25. Кримінальні проступки
    elif art_num <= 313.99:
        return "140 10 30 90"       # Глава 26. Оскарження рішень під час розслідування
    elif art_num <= 317.99:
        return "140 10 40 10"       # Глава 27. Підготовче провадження
    elif art_num <= 368.99:
        return "140 10 40 20"       # Глава 28. Судовий розгляд
    elif art_num <= 380.99:
        return "140 10 40 30"       # Глава 29. Судові рішення
    elif art_num <= 391.99:
        return "140 10 40 40"       # Глава 30. Особливі порядки в суді 1-ї інстанції
    elif art_num <= 423.99:
        return "140 10 50 10"       # Глава 31. Апеляційне провадження
    elif art_num <= 443.99:
        return "140 10 50 20"       # Глава 32. Касаційне провадження
    elif art_num <= 458.99:
        return "140 10 50 30"       # Глава 33. Виключні обставини
    elif art_num <= 467.99:
        return "140 10 50 40"       # Глава 34. Нововиявлені обставини
    elif art_num <= 516.99:
        return "140 10 60"          # Розділ VI. Особливі порядки кримінального провадження
    elif art_num <= 531.99:
        return "140 10 70"          # Розділ VII. Відновлення втрачених матеріалів
    elif art_num <= 540.99:
        return "140 10 80"          # Розділ VIII. Виконання судових рішень
    elif art_num <= 614.99:
        return "140 10 90"          # Розділ IX. Міжнародне співробітництво
    else:
        return "140 10 100"         # Розділ IX-1. Воєнний стан


def map_civil_code_article(art_num: float, text_snippet: str) -> str:
    """Визначає точну рубрику ЦК (20 10 ...) за номером статті."""
    # Книга перша. Загальні положення (ст. 1 - 268)
    if art_num <= 23.99:
        return "20 10 10 10"       # Розділ I. Основні положення
    elif art_num <= 176.99:
        # Розділ II. Особи
        if art_num <= 49.99:
            return "20 10 10 20 10 10"  # Глава 4. Загальні положення про фізособу
        elif art_num <= 54.99:
            return "20 10 10 20 10 20"  # Глава 5. ФОП
        elif art_num <= 79.99:
            return "20 10 10 20 10 30"  # Глава 6. Опіка та піклування
        elif art_num <= 112.99:
            return "20 10 10 20 20 10"  # Глава 7. Загальні положення про юрособу
        elif art_num <= 162.99:
            return "20 10 10 20 20 20"  # Глава 8. Підприємницькі товариства
        else:
            return "20 10 10 20 30"     # Підрозділ 3. Держава, громади
    elif art_num <= 200.99:
        # Розділ III. Об'єкти цивільних прав
        if art_num <= 178.99:
            return "20 10 10 30 10"     # Глава 12. Загальні положення про об'єкти
        elif art_num <= 193.99:
            return "20 10 10 30 20"     # Глава 13. Речі. Майно (ст. 183 ЦК)
        elif art_num <= 198.99:
            return "20 10 10 30 30"     # Глава 14. Цінні папери
        else:
            return "20 10 10 30 40"     # Глава 15. Нематеріальні блага
    elif art_num <= 250.99:
        return "20 10 10 40"            # Розділ IV. Правочини. Представництво
    elif art_num <= 268.99:
        return "20 10 10 50"            # Розділ V. Строки. Позовна давність
    elif art_num <= 315.99:
        return "20 10 20"               # Книга друга. Особисті немайнові права
    elif art_num <= 417.99:
        # Книга третя. Право власності та інші речові права
        if art_num <= 394.99:
            return "20 10 30 10"        # Розділ I. Право власності
        else:
            return "20 10 30 20"        # Розділ II. Речові права на чуже майно
    elif art_num <= 508.99:
        return "20 10 40"               # Книга четверта. Право інтелектуальної власності
    elif art_num <= 1215.99:
        return "20 10 50"               # Книга п'ята. Зобов'язальне право
    else:
        return "20 10 60"               # Книга шоста. Спадкове право


def match_category_by_name(conn: sqlite3.Connection, parent_prefix: str, text: str) -> Optional[str]:
    """Шукає найбільш відповідну категорію серед підкатегорій parent_prefix за входженням назви."""
    cur = conn.cursor()
    cur.execute(
        "SELECT code, clean_name FROM categories WHERE code LIKE ? AND code != ? ORDER BY length(code) DESC",
        (f"{parent_prefix}%", parent_prefix)
    )
    rows = cur.fetchall()
    text_lower = text.lower()
    for code, name in rows:
        name_clean = re.sub(r'^(?:Розділ|Глава|Книга|§)\s+[\w\d\.\-]+\s*[\.:]?\s*', '', name, flags=re.IGNORECASE).strip().lower()
        if len(name_clean) > 5 and name_clean in text_lower:
            return code
    return None


def classify_segment(file_path: Path, conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """
    Аналізує файл сегмента та формує список зв'язків з класифікатором:
    1. Первинний зв'язок — на основі аналізу перших 4 речень (квінтесенція правової позиції).
    2. Доповнена класифікація — на основі дослідження решти тексту сегмента на наявність інших
       статей кодексів та законів. Встановлюються другий, третій і наступні зв'язки.
       Ці зв'язки доповнюють перший, не виключаючи його (конкуренція відсутня).
    """
    try:
        content = file_path.read_text(encoding='utf-8', errors='surrogateescape')
    except Exception as e:
        print(f"Помилка читання {file_path}: {e}")
        return []

    # Очищуємо коментарі SEGMENT
    clean_text = re.sub(r'<!--.*?-->', '', content).strip()
    first_4 = get_first_sentences(clean_text, 4)

    # Витяг номера справи
    case_num = "Не вказана"
    m_case = CASE_NUM_PATTERN.search(clean_text)
    if m_case:
        case_num = f"№ {m_case.group(1)}"

    # Витяг посилання на реєстр судових рішень (ЄДРСР)
    decision_url = ""
    m_url = REYESTR_URL_PATTERN.search(clean_text)
    if m_url:
        decision_url = m_url.group(0)

    # Визначення шляху до офіційного випуску журналу огляду (PDF)
    doc_folder_name = file_path.parent.name
    pdf_rel_candidate = f"documents/pdfs/{doc_folder_name}.pdf"
    pdf_path = pdf_rel_candidate if (BASE_DIR / pdf_rel_candidate).is_file() else ""

    # Витяг тези (перші 2-3 речення або абзац правової позиції)
    teza = first_4[:350]
    if len(first_4) > 350:
        teza = teza.rsplit(' ', 1)[0] + "..."

    rel_file_path = str(file_path.relative_to(BASE_DIR) if file_path.is_relative_to(BASE_DIR) else file_path)

    # 1. ПЕРВИННА КЛАСИФІКАЦІЯ (за першими 4 реченнями)
    matched_art_str = None
    matched_code_abbr = None
    matched_code_root = None
    matched_code_name = None

    # Перевірка наявності повної назви кодексу на початку або у перших 4 реченнях
    first_4_upper = first_4.upper()
    for full_name, abbr in FULL_CODE_NAME_MAP.items():
        if full_name in first_4_upper:
            m_full_art = re.search(r'(?:\bst\b|\bст\b|\bстатт[іеяю]\b|\bстаття\b)\.?\s*(\d+(?:[-–]\d+)?)', first_4, re.IGNORECASE)
            if m_full_art:
                matched_art_str = m_full_art.group(1)
                matched_code_abbr = abbr
                matched_code_root, matched_code_name, _ = CODE_ABBR_MAP[abbr]
                break

    if not matched_code_abbr:
        for m_art in ARTICLE_PATTERN.finditer(first_4):
            candidate_abbr = m_art.group(2).upper().strip()
            if candidate_abbr in CODE_ABBR_MAP:
                matched_art_str = m_art.group(1)
                matched_code_abbr = candidate_abbr
                matched_code_root, matched_code_name, _ = CODE_ABBR_MAP[candidate_abbr]
                break

    # Якщо в перших 4 реченнях не знайдено статті, шукаємо в межах перших 1200 символів
    if not matched_code_abbr:
        for m_wide in ARTICLE_PATTERN.finditer(clean_text[:1200]):
            candidate_abbr = m_wide.group(2).upper().strip()
            if candidate_abbr in CODE_ABBR_MAP:
                matched_art_str = m_wide.group(1)
                matched_code_abbr = candidate_abbr
                matched_code_root, matched_code_name, _ = CODE_ABBR_MAP[candidate_abbr]
                break

    # Якщо абревіатуру не виявлено безпосередньо біля статті, перевіряємо префікс або контекстні маркери
    if not matched_code_abbr:
        fn = file_path.stem.upper()
        text_lower = clean_text[:1000].lower()
        if fn.startswith("KPK_") or "слідч" in text_lower or "досудов" in text_lower or "єрдр" in text_lower or "нсрд" in text_lower:
            matched_code_abbr = "КПК"
            matched_code_root, matched_code_name, _ = CODE_ABBR_MAP["КПК"]
        elif fn.startswith("KK_"):
            matched_code_abbr = "КК"
            matched_code_root, matched_code_name, _ = CODE_ABBR_MAP["КК"]
        elif fn.startswith("OP_"):
            matched_code_abbr = "КПК" if ("слідч" in text_lower or "кпк" in text_lower) else "КК"
            matched_code_root, matched_code_name, _ = CODE_ABBR_MAP[matched_code_abbr]

    if matched_code_abbr and not matched_art_str:
        pattern = re.compile(rf'\b(?:ст(?:атт[іеяю]|\.)?|стаття)\s*(\d+(?:[-–]\d+)?)\s*{matched_code_abbr}\b', re.IGNORECASE)
        m_sec = pattern.search(clean_text[:2000])
        if m_sec:
            matched_art_str = m_sec.group(1)

    primary_cat_code = matched_code_root or "140 10"
    primary_confidence = 0.70
    primary_reasoning_parts = []

    if matched_code_abbr and matched_art_str:
        art_num = parse_article_number(matched_art_str)
        primary_reasoning_parts.append(f"Первинна норма: ст. {matched_art_str} {matched_code_abbr}")
        if matched_code_abbr == "КК":
            primary_cat_code = map_criminal_code_article(art_num, first_4)
            primary_confidence = 0.95
        elif matched_code_abbr == "КПК":
            primary_cat_code = map_criminal_proc_code_article(art_num, first_4)
            primary_confidence = 0.95
        elif matched_code_abbr == "ЦК":
            primary_cat_code = map_civil_code_article(art_num, first_4)
            primary_confidence = 0.95
        else:
            sub_code = match_category_by_name(conn, matched_code_root, first_4)
            if sub_code:
                primary_cat_code = sub_code
                primary_confidence = 0.90
            else:
                primary_cat_code = matched_code_root
                primary_confidence = 0.85
    elif matched_code_abbr:
        sub_code = match_category_by_name(conn, matched_code_root, first_4)
        if sub_code:
            primary_cat_code = sub_code
            primary_confidence = 0.85
            primary_reasoning_parts.append(f"Визначено за назвою розділу в {matched_code_abbr}")
        else:
            primary_cat_code = matched_code_root
            primary_confidence = 0.75
            primary_reasoning_parts.append(f"Прив'язано до кодексу {matched_code_abbr}")
    else:
        primary_reasoning_parts.append("Загальна прив'язка за контекстом сегмента")

    cur = conn.cursor()
    cur.execute("SELECT clean_name, path_names FROM categories WHERE code = ?", (primary_cat_code,))
    row = cur.fetchone()
    primary_name = row[0] if row else primary_cat_code
    primary_path = row[1] if row else primary_cat_code

    primary_llm_reasoning = f"{'; '.join(primary_reasoning_parts)}. Рубрика: [{primary_cat_code}] {primary_path}."

    results: List[Dict[str, Any]] = [{
        "category_code": primary_cat_code,
        "case_number": case_num,
        "original_category": primary_name,
        "teza": teza,
        "summary": first_4,
        "circumstances": "",
        "reasoning": "",
        "confidence_score": primary_confidence,
        "llm_reasoning": primary_llm_reasoning,
        "file_path": rel_file_path,
        "pdf_path": pdf_path,
        "decision_url": decision_url,
        "is_primary": True
    }]

    seen_categories = {primary_cat_code}

    # 2. ДОПОВНЕНА КЛАСИФІКАЦІЯ (дослідження всього тексту сегмента на наявність додаткових норм)
    for m_rest in ARTICLE_PATTERN.finditer(clean_text):
        abbr = m_rest.group(2).upper().strip()
        if abbr in CODE_ABBR_MAP:
            art_str = m_rest.group(1)
            if abbr == matched_code_abbr and art_str == matched_art_str:
                continue
            root_code, code_title, _ = CODE_ABBR_MAP[abbr]
            art_num = parse_article_number(art_str)
            
            aug_cat_code = root_code
            aug_confidence = 0.90
            
            if abbr == "КК":
                aug_cat_code = map_criminal_code_article(art_num, clean_text[:800])
            elif abbr == "КПК":
                aug_cat_code = map_criminal_proc_code_article(art_num, clean_text[:800])
            elif abbr == "ЦК":
                aug_cat_code = map_civil_code_article(art_num, clean_text[:800])
            else:
                sub = match_category_by_name(conn, root_code, clean_text[:800])
                aug_cat_code = sub if sub else root_code

            if aug_cat_code not in seen_categories:
                seen_categories.add(aug_cat_code)
                cur.execute("SELECT clean_name, path_names FROM categories WHERE code = ?", (aug_cat_code,))
                c_row = cur.fetchone()
                aug_name = c_row[0] if c_row else aug_cat_code
                aug_path = c_row[1] if c_row else aug_cat_code

                aug_reasoning = (
                    f"[ДОПОВНЕНА КЛАСИФІКАЦІЯ] Виявлено додаткову норму в тексті рішення: ст. {art_str} {abbr}. "
                    f"Доповнює первинний зв'язок без конкуренції. Рубрика: [{aug_cat_code}] {aug_path}."
                )

                results.append({
                    "category_code": aug_cat_code,
                    "case_number": case_num,
                    "original_category": aug_name,
                    "teza": teza,
                    "summary": first_4,
                    "circumstances": "",
                    "reasoning": "",
                    "confidence_score": aug_confidence,
                    "llm_reasoning": aug_reasoning,
                    "file_path": rel_file_path,
                    "pdf_path": pdf_path,
                    "decision_url": decision_url,
                    "is_primary": False
                })

    # 3. ВИЯВЛЕННЯ СТАТЕЙ ТА ЗАКОНІВ ПОЗА КЛАСИФІКАЦІЄЮ
    raw_found = []
    # Пошук законів України, конвенцій або Конституції зі статтею
    for m_law in re.finditer(
        r'(?:ст(?:атт[іеяю]|\.)?|стаття)\s*(\d+(?:[-–]\d+)?)\s*(?:Закону\s+(?:України\s+)?(?:[«"][^»"]+[»"]|[А-Яа-яЄІЇA-Za-z\s]{3,45}?(?=[,\.;\)\n\r]))|Конвенції|ЄКПЛ|Конституції\s+України)',
        clean_text, re.IGNORECASE
    ):
        raw_norm = re.sub(r'\s+', ' ', m_law.group(0).strip())
        if raw_norm not in raw_found:
            raw_found.append(raw_norm)

    # Очищуємо від неповних обрізків (якщо є варіант із назвою закону в лапках)
    final_norms = []
    for norm in raw_found:
        if norm.lower().endswith("закону") and any(norm.lower() in other.lower() and len(other) > len(norm) for other in raw_found):
            continue
        final_norms.append(norm)

    # Пошук абревіатур біля статей, яких немає в CODE_ABBR_MAP
    STOP_WORDS = {
        'УКРАЇНИ', 'СУДУ', 'РОКУ', 'ЧАСТИНИ', 'ПУНКТУ', 'СТАТТІ', 'ТА', 'АБО', 'ДО', 'НА',
        'ЗА', 'ВІД', 'ПРОВАДЖЕННЯ', 'СПРАВИ', 'ВКАЗАНОГО', 'ЦЬОГО', 'ВІДПОВІДНОГО', 'ІНШОГО',
        'ЗАЗНАЧЕНОГО', 'ПОРЯДКУ', 'ВИПАДКУ', 'МЕЖАХ', 'ВИМОГ', 'ПОЛОЖЕНЬ', 'ЗАКОНУ'
    }
    for m_art in ARTICLE_PATTERN.finditer(clean_text):
        cand = m_art.group(2).upper().strip()
        if len(cand) >= 2 and cand not in CODE_ABBR_MAP and cand not in STOP_WORDS:
            phrase = f"ст. {m_art.group(1)} {m_art.group(2)}"
            if phrase not in final_norms and not any(phrase in x for x in final_norms):
                final_norms.append(phrase)

    if results:
        results[0]["unclassified_norms"] = final_norms

    return results


def classify_folder(folder_path: Path) -> int:
    """
    Опрацьовує папку або окремий файл сегментів.
    Перед класифікацією перевіряє наявність існуючих взаємозв'язків у БД:
    - Якщо зв'язок існує: перевіряє його правильність за правилами скіла.
      При збігу — підтверджує валідність.
      При розбіжності чи застарілому коді — оновлює на правильну рубрику.
    - Виконує доповнену класифікацію (дослідження решти тексту) і зберігає
      усі додаткові норми як окремі зв'язки без конкуренції.
    """
    if not DB_PATH.exists():
        print(f"Помилка: Базу {DB_PATH} не знайдено!")
        return 0

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    if folder_path.is_file():
        files = [folder_path]
        doc_pattern = folder_path.parent.name
    else:
        files = sorted(list(folder_path.glob("*_segment.md")))
        doc_pattern = folder_path.name

    if not files:
        print(f"⚠️ Не знайдено файлів сегментів у {folder_path}")
        conn.close()
        return 0

    print(f"[*] Перевірка та класифікація {len(files)} сегментів для огляду: {doc_pattern}...")

    # Перевірка наявності попередніх зв'язків
    cur.execute("SELECT count(*) FROM mapped_segments WHERE file_path LIKE ?", (f"%{doc_pattern}%",))
    existing_total = cur.fetchone()[0]
    if existing_total > 0:
        print(f"ℹ️ У базі вже існує {existing_total} взаємозв'язків. Проводиться верифікація та доповнена класифікація...")
    else:
        print("ℹ️ Попередніх взаємозв'язків у базі не знайдено. Проводиться первинне встановлення та доповнена класифікація...")

    valid_count = 0
    updated_count = 0
    augmented_count = 0
    inserted_count = 0
    all_unclassified = []

    for f in files:
        # Пропускаємо технічні файли
        if "preamble" in f.name.lower() or "zmist" in f.name.lower():
            continue

        results = classify_segment(f, conn)
        if not results:
            continue

        # Збір норм поза класифікацією для інформування
        if "unclassified_norms" in results[0] and results[0]["unclassified_norms"]:
            for norm in results[0]["unclassified_norms"]:
                all_unclassified.append((f.name, results[0]["case_number"], norm))
                print(f"  ⚠️ [ПОЗА КЛАСИФІКАЦІЄЮ] {f.name}: виявлено \"{norm}\", якої немає в класифікаторі")

        rel_path = results[0]["file_path"]

        # Отримуємо всі існуючі зв'язки для цього сегмента
        cur.execute("SELECT id, category_code FROM mapped_segments WHERE file_path = ?", (rel_path,))
        existing_records = {row[1]: row[0] for row in cur.fetchall()}  # {category_code: id}

        # Категорії, які визначено в цьому прогоні
        computed_categories = {res["category_code"] for res in results}

        # 1. Опрацьовуємо первинний зв'язок
        primary_res = results[0]
        prim_cat = primary_res["category_code"]

        if prim_cat in existing_records:
            valid_count += 1
            cur.execute("""
                UPDATE mapped_segments
                SET case_number = ?, teza = ?, summary = ?,
                    confidence_score = ?, llm_reasoning = ?, pdf_path = ?, decision_url = ?
                WHERE id = ?
            """, (
                primary_res["case_number"], primary_res["teza"], primary_res["summary"],
                primary_res["confidence_score"], primary_res["llm_reasoning"], primary_res["pdf_path"], primary_res.get("decision_url", ""),
                existing_records[prim_cat]
            ))
        else:
            # Якщо для сегмента був старий запис з невідомою/застарілою категорією, оновлюємо його
            obsolete_ids = [eid for cat, eid in existing_records.items() if cat not in computed_categories]
            if obsolete_ids:
                reused_id = obsolete_ids[0]
                updated_count += 1
                print(f"  🔄 [ОНОВЛЕНО] {f.name}: первинний зв'язок оновлено на [{prim_cat}] {primary_res['original_category']}")
                cur.execute("""
                    UPDATE mapped_segments
                    SET category_code = ?, original_category = ?, case_number = ?,
                        teza = ?, summary = ?, circumstances = ?, reasoning = ?,
                        confidence_score = ?, llm_reasoning = ?, pdf_path = ?, decision_url = ?
                    WHERE id = ?
                """, (
                    primary_res["category_code"], primary_res["original_category"], primary_res["case_number"],
                    primary_res["teza"], primary_res["summary"], primary_res["circumstances"], primary_res["reasoning"],
                    primary_res["confidence_score"], primary_res["llm_reasoning"], primary_res["pdf_path"], primary_res.get("decision_url", ""),
                    reused_id
                ))
                # Видаляємо з переліку використаних
                existing_records = {k: v for k, v in existing_records.items() if v != reused_id}
            else:
                inserted_count += 1
                print(f"  ✨ [НОВИЙ ПЕРВИННИЙ] {f.name} -> [{prim_cat}] {primary_res['original_category']}")
                cur.execute("""
                    INSERT INTO mapped_segments (
                        category_code, case_number, original_category,
                        teza, summary, circumstances, reasoning,
                        confidence_score, llm_reasoning, file_path, pdf_path, decision_url
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    primary_res["category_code"], primary_res["case_number"], primary_res["original_category"],
                    primary_res["teza"], primary_res["summary"], primary_res["circumstances"], primary_res["reasoning"],
                    primary_res["confidence_score"], primary_res["llm_reasoning"], rel_path, primary_res["pdf_path"], primary_res.get("decision_url", "")
                ))

        # 2. Опрацьовуємо доповнені зв'язки (решта результатів)
        for aug_res in results[1:]:
            aug_cat = aug_res["category_code"]
            if aug_cat in existing_records:
                valid_count += 1
            else:
                augmented_count += 1
                print(f"  ➕ [ДОПОВНЕНО] {f.name} -> [{aug_cat}] {aug_res['original_category']}")
                cur.execute("""
                    INSERT INTO mapped_segments (
                        category_code, case_number, original_category,
                        teza, summary, circumstances, reasoning,
                        confidence_score, llm_reasoning, file_path, pdf_path, decision_url
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    aug_res["category_code"], aug_res["case_number"], aug_res["original_category"],
                    aug_res["teza"], aug_res["summary"], aug_res["circumstances"], aug_res["reasoning"],
                    aug_res["confidence_score"], aug_res["llm_reasoning"], rel_path, aug_res["pdf_path"], aug_res.get("decision_url", "")
                ))

    conn.commit()

    # Автоматичне оновлення HTML-сторінки кореляції для огляду
    try:
        from build_correlation_pages import build_page_for_document
        build_page_for_document(doc_pattern, conn)
    except Exception as e:
        print(f"⚠️ Не вдалося оновити correlation сторінку: {e}")

    conn.close()

    if all_unclassified:
        print(f"\n⚠️ ВИЯВЛЕНО СТАТТІ ТА ЗАКОНИ ПОЗА КЛАСИФІКАЦІЄЮ ({len(all_unclassified)}):")
        for fn, cnum, norm in all_unclassified:
            print(f"   • {fn} ({cnum}): {norm}")

    total_active = valid_count + updated_count + inserted_count + augmented_count
    print(f"\n📊 Підсумок перевірки для {doc_pattern}:")
    print(f"   - Підтверджено валідними: {valid_count}")
    print(f"   - Оновлено / виправлено: {updated_count}")
    print(f"   - Додано нових первинних зв'язків: {inserted_count}")
    print(f"   - Додано доповнених зв'язків: {augmented_count}")
    if all_unclassified:
        print(f"   - ⚠️ Виявлено норм поза класифікацією: {len(all_unclassified)}")
    print(f"   - Всього активних взаємозв'язків у базі: {total_active}")
    return total_active


def main():
    if len(sys.argv) > 1:
        target = Path(sys.argv[1])
    else:
        # За замовчуванням опрацьовуємо останній робочий огляд або всі
        target = BASE_DIR / "documents" / "segments" / "Oglyad_KKS_03_2026"
        if not target.exists():
            target = BASE_DIR / "documents" / "segments"

    if target.is_dir() and not list(target.glob("*_segment.md")):
        # Це коренева папка segments — опрацьовуємо всі підпапки
        subdirs = [p for p in target.iterdir() if p.is_dir()]
        print(f"[*] Знайдено {len(subdirs)} папок оглядів для класифікації.")
        total_classified = 0
        for s in subdirs:
            total_classified += classify_folder(s)
        print(f"\n🎉 Всього встановлено {total_classified} взаємозв'язків!")
    else:
        classify_folder(target)


if __name__ == "__main__":
    main()
