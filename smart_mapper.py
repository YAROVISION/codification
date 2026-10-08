"""
Модуль інтелектуального мапінгу сегментів судової практики (smart_mapper.py).
Впроваджує багаторівневий семантичний аналіз:
1. Визначення юрисдикції та контексту дайджесту (КАС, КГС, КЦС, ККС, ВП ВС, ЄСПЛ, СЄС, ВККС, ВРП).
2. Запобігання конфліктам юрисдикцій (Hard Constraints: КАС ніколи не потрапляє в господарський/кримінальний процес і навпаки).
3. Фільтрація загальних юридичних стоп-слів для точного фокусу FTS5 на правових інститутах.
4. Точний витяг номера остаточної постанови/ухвали Верховного Суду.
5. Пропуск та очищення службових файлів (00_Preamble.md, зміст).
6. Семантичне ранжування кандидатів з генерацією детального правового обґрунтування (LLM Reasoning).
"""

import os
import re
import sys
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = "data/classifier.sqlite"
DOCS_DIR = "documents/segments"

# Загальнопроцесуальні стоп-слова, які не несуть галузевої специфіки
LEGAL_STOPWORDS = {
    'суд', 'суду', 'судом', 'суді', 'судів', 'судова', 'судове', 'судові', 'судового', 'судових',
    'справа', 'справи', 'справі', 'справу', 'справах',
    'верховний', 'верховного', 'верховному', 'верховним', 'касаційний', 'касаційного',
    'позивач', 'позивача', 'позивачем', 'відповідач', 'відповідача', 'відповідачем',
    'скарга', 'скарги', 'скаргу', 'скаргою', 'касаційна', 'касаційну', 'апеляційна', 'апеляційну',
    'рішення', 'рішенням', 'рішенні', 'постанова', 'постановою', 'постанові', 'ухвала', 'ухвалою', 'ухвалі',
    'заява', 'заяви', 'заяву', 'заявою', 'провадження', 'провадженням', 'провадженні',
    'частина', 'частини', 'частиною', 'стаття', 'статті', 'статтею', 'пункт', 'пункту', 'пунктом',
    'кодекс', 'кодексу', 'закон', 'закону', 'законом', 'україни',
    'також', 'цього', 'цьому', 'який', 'яка', 'яке', 'які', 'яких', 'яким', 'якою',
    'щодо', 'встановлено', 'зазначено', 'відповідно', 'зокрема', 'може', 'бути', 'було', 'висновку',
    'особа', 'особи', 'особою', 'осіб', 'права', 'правах', 'прав', 'порядку', 'розгляду'
}


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def detect_digest_context(folder_name: str, preamble_text: str = "") -> Dict[str, Any]:
    """
    Визначає юрисдикцію суду, тип кодексу та дозволені/заборонені гілки класифікатора.
    """
    fn = folder_name.lower()
    pt = preamble_text.lower()
    
    context = {
        "court": "ВС",
        "is_pure_procedural": False,
        "default_procedural_code": None,
        "forbidden_branches": [],
        "preferred_branches": [],
        "digest_name": folder_name
    }
    
    # 1. Європейський суд з прав людини (ЄСПЛ)
    if "espl" in fn or "yespl" in fn or "єспл" in pt:
        context["court"] = "ЄСПЛ"
        context["preferred_branches"].extend(["10 40", "140 10"])
        context["forbidden_branches"].extend(["270 10", "270 20", "270 30", "270 50", "80", "150"])
        return context

    # 2. Суд Європейського Союзу (CJEU / СЄС)
    if "ses" in fn or "сєс" in fn:
        context["court"] = "СЄС"
        context["preferred_branches"].extend(["140 10", "140270"])
        return context

    # 3. Вища рада правосуддя / ВККС
    if "vkks" in fn or "вккс" in fn:
        context["court"] = "ВККС"
        context["preferred_branches"].extend(["280 40 20", "280 20"])
        return context
    if "vrp" in fn or "врп" in fn:
        context["court"] = "ВРП"
        context["preferred_branches"].extend(["280 20", "280 40 20"])
        return context

    # 4. Прокуратура
    if "prokyror" in fn or "прокурор" in pt:
        context["court"] = "Органи прокуратури"
        context["preferred_branches"].extend(["280 60", "50130 40"])

    # 5. Адміністративне судочинство (КАС / КУпАП)
    if "kas" in fn or "кас" in fn or "адміністративн" in pt:
        context["court"] = "КАС ВС"
        context["preferred_branches"].extend(["240 20", "240 10", "240"])
        context["forbidden_branches"].extend(["270 10", "270 20", "270 30", "250", "260"])
        if "daidzhest_kas_ukrainy" in fn or "20-річчя" in pt or "кодекс адміністративного судочинства" in pt:
            context["is_pure_procedural"] = True
            context["default_procedural_code"] = "240 20"

    # 6. Господарське судочинство (КГС)
    elif "kgs" in fn or "кгс" in fn or "гпк" in fn or "voen_stan_kgs" in fn or "господарськ" in pt:
        context["court"] = "КГС ВС"
        context["preferred_branches"].extend(["270 30", "150", "150190"])
        context["forbidden_branches"].extend(["270 10", "270 20", "270 50", "250", "260"])
        if "gpk" in fn or "господарський процесуальний кодекс" in pt or "analiz_vidmov" in fn:
            context["is_pure_procedural"] = True
            context["default_procedural_code"] = "270 30"

    # 7. Цивільне судочинство (КЦС)
    elif "kcs" in fn or "кцс" in fn or "цпк" in fn or "цивільн" in pt:
        context["court"] = "КЦС ВС"
        context["preferred_branches"].extend(["270 20", "30", "70", "50"])
        context["forbidden_branches"].extend(["270 10", "270 30", "270 50", "250", "260"])
        if "cpk" in fn or "цивільний процесуальний кодекс" in pt:
            context["is_pure_procedural"] = True
            context["default_procedural_code"] = "270 20"

    # 8. Кримінальне судочинство (ККС)
    elif "kks" in fn or "ккс" in fn or "кпк" in fn or "кримінальн" in pt:
        context["court"] = "ККС ВС"
        context["preferred_branches"].extend(["270 10", "250", "260"])
        context["forbidden_branches"].extend(["270 20", "270 30", "270 50", "80", "150", "20 50", "70"])

    # 9. Велика Палата ВС
    elif "vp" in fn or "велика палата" in pt:
        context["court"] = "ВП ВС"

    # 10. Тематичні спеціалізації (матеріальне право)
    if "bankrupt" in fn or "банкрут" in fn:
        context["preferred_branches"].append("150190")
    if "opodatk" in fn or "podat" in fn or "подат" in fn or "rro" in fn:
        context["preferred_branches"].extend(["20 50", "20 50 40"])
    if "zemel" in fn or "зем" in fn or "servitut" in fn:
        context["preferred_branches"].extend(["40 80", "40 30"])
    if "derzh_sluzhb" in fn or "derzh_slyzhb" in fn:
        context["preferred_branches"].extend(["10140", "50130 40"])
    if "chernobyl" in fn or "чорнобиль" in fn:
        context["preferred_branches"].append("210 20")
    if "spadsuna" in fn or "спадщин" in fn:
        context["preferred_branches"].append("30 70")
    if "korporat" in fn:
        context["preferred_branches"].extend(["150100", "270 30 10"])
    if "intvlasn" in fn or "intelekt" in fn or "designs" in fn:
        context["preferred_branches"].extend(["150 90", "30 50"])
    if "gromadyanstvo" in fn:
        context["preferred_branches"].append("10 40 10")
    if "strokiv_admin" in fn:
        context["is_pure_procedural"] = True
        context["default_procedural_code"] = "270 50"

    return context


def extract_case_number(text: str) -> str:
    """
    Точне вилучення номера остаточної постанови/ухвали Верховного Суду.
    Шукає реквізити судового акта, а не проміжні справи першої інстанції.
    """
    # 1. Постанова/ухвала з номером справи або провадження (через перенесення рядків)
    pattern = re.compile(
        r'(?:Постанова|Ухвала|Рішення)[\s\S]{1,350}?(?:справ[іа]|провадженн[іі])\s+№\s*([\d\/\w\-]+)',
        re.IGNORECASE
    )
    matches = pattern.findall(text)
    if matches:
        return f"№ {matches[-1].strip()}"

    # 2. Номер справи безпосередньо перед посиланням на reyestr.court.gov.ua
    m_reg = re.search(r'справ[іа]\s+№\s*([\d\/\w\-]+)[\s\S]{0,100}?reyestr\.court\.gov\.ua', text, re.IGNORECASE)
    if m_reg:
        return f"№ {m_reg.group(1).strip()}"

    # 3. Загальний пошук у кінці документа (останні 500 символів)
    tail = text[-500:]
    m_tail = re.search(r'справ[іа]\s+№\s*([\d\/\w\-]+)', tail, re.IGNORECASE)
    if m_tail:
        return f"№ {m_tail.group(1).strip()}"

    # 4. Якщо в тексті є будь-яка справа
    m_any = re.search(r'справ[іа]\s+№\s*([\d\/\w\-]+)', text, re.IGNORECASE)
    if m_any:
        return f"№ {m_any.group(1).strip()}"

    return "Не вказана"


def parse_segment_file(filepath: Path) -> Optional[Dict[str, Any]]:
    """
    Парсить окремий MD файл сегмента, структурує заголовок, тезу, фабулу та правовий висновок.
    """
    name_low = filepath.name.lower()
    if "preamble" in name_low or "zmist" in name_low or "table_of_contents" in name_low:
        return None

    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Помилка читання {filepath}: {e}")
        return None

    if "технічний сегмент" in text.lower() or "не підлягає розподілу" in text.lower():
        return None

    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not lines:
        return None

    info = {
        "file_path": str(filepath).replace("\\", "/"),
        "original_category": "",
        "teza": "",
        "summary": "",
        "circumstances": "",
        "reasoning": "",
        "case_number": extract_case_number(text),
        "full_text": text
    }

    # Витяг заголовка і тези
    header_idx = 0
    while header_idx < len(lines) and lines[header_idx].startswith("##"):
        header_idx += 1
    
    if header_idx < len(lines):
        info["original_category"] = lines[header_idx].lstrip("#").strip()
    
    if header_idx + 1 < len(lines):
        info["teza"] = lines[header_idx + 1].lstrip("#").strip()

    # Розділення на фабулу та правову позицію
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    
    reasoning_paras = []
    circumstances_paras = []
    
    is_reasoning_mode = False
    for p in paragraphs[1:]:
        clean_p = p.replace("\n", " ")
        if any(marker in clean_p.lower() for marker in [
            "оцінка суду", "позиція верховного суду", "правовий висновок", 
            "істотними обставинами є", "нововиявленими слід вважати",
            "верховний суд зазначив", "колегія суддів зазначає",
            "суд виходить з того", "суд дійшов висновку", "обґрунтування позиції"
        ]):
            is_reasoning_mode = True
            
        if is_reasoning_mode:
            reasoning_paras.append(clean_p)
        else:
            circumstances_paras.append(clean_p)

    if reasoning_paras:
        info["reasoning"] = " ".join(reasoning_paras)[:1500]
        info["circumstances"] = " ".join(circumstances_paras)[:800]
        info["summary"] = reasoning_paras[0][:600]
    else:
        info["summary"] = " ".join(lines[2:8])[:600]
        info["circumstances"] = " ".join(lines[2:12])[:800]

    return info


def find_best_category(info: Dict[str, Any], context: Dict[str, Any], conn: sqlite3.Connection) -> Tuple[str, float, str]:
    """
    Семантично підбирає найкращу категорію з урахуванням юрисдикції, правил виключення та стоп-слів.
    """
    cur = conn.cursor()

    # 1. Якщо дайджест повністю присвячений конкретному процесуальному кодексу (наприклад, КАСУ або ГПК)
    if context.get("is_pure_procedural") and context.get("default_procedural_code"):
        code = context["default_procedural_code"]
        cur.execute("SELECT clean_name, path_names FROM categories WHERE code = ?", (code,))
        row = cur.fetchone()
        cat_name = row["clean_name"] if row else "Процесуальне судочинство"
        cat_path = row["path_names"] if row else cat_name
        reasoning = (
            f"Тематичний дайджест {context['court']}: правова позиція щодо застосування "
            f"процесуальних норм за рубрикою «{cat_name}» ({cat_path})."
        )
        return code, 1.0, reasoning

    # 2. Формуємо цільовий пошуковий текст без загальних стоп-слів
    search_seed = f"{info['original_category']} {info['teza']} {info['reasoning'][:300]}"
    clean_search = "".join(c if c.isalnum() or c.isspace() else " " for c in search_seed.lower())
    
    tokens = [t for t in clean_search.split() if len(t) > 3 and t not in LEGAL_STOPWORDS][:10]
    
    if not tokens:
        tokens = [t for t in "".join(c if c.isalnum() or c.isspace() else " " for c in info['summary'].lower()).split() if len(t) > 3 and t not in LEGAL_STOPWORDS][:8]

    if not tokens:
        fallback_code = context["preferred_branches"][0] if context["preferred_branches"] else "270"
        return fallback_code, 0.5, "Базовий мапінг за юрисдикцією суду (недостатньо ключових слів)"

    fts_query = " OR ".join(f'"{t}"*' for t in tokens)

    # Витягуємо топ-20 кандидатів через FTS5
    cur.execute("""
        SELECT c.code, c.clean_name, c.path_codes, c.path_names, bm25(categories_fts) AS rank
        FROM categories_fts
        JOIN categories c ON c.code = categories_fts.code
        WHERE categories_fts MATCH ?
        ORDER BY rank
        LIMIT 20
    """, (fts_query,))
    candidates = cur.fetchall()

    if not candidates:
        fallback_code = context["preferred_branches"][0] if context["preferred_branches"] else "270"
        return fallback_code, 0.5, "Мапінг за юрисдикцією: збігів за ключовими словами не знайдено"

    best_code = None
    best_score = -99999.0
    best_name = ""
    best_path = ""

    for cand in candidates:
        code = cand["code"]
        name = cand["clean_name"]
        path_codes = cand["path_codes"]
        path_names = cand["path_names"]
        rank = abs(cand["rank"])

        # Жорсткий фільтр: заборонені гілки юрисдикції
        is_forbidden = False
        for forb in context["forbidden_branches"]:
            if code == forb or code.startswith(forb + " ") or forb in path_codes:
                is_forbidden = True
                break
        if is_forbidden:
            continue

        # Базовий бал схожості
        score = 10.0 / (rank + 1.0)

        # Бонус за збіг з пріоритетною юрисдикцією / спеціалізацією дайджесту
        for pref in context["preferred_branches"]:
            if code == pref or code.startswith(pref + " ") or pref in path_codes:
                score += 6.0
                break

        # Штраф за занадто загальні вузли (рівень 1), якщо є специфічні
        if len(code.split()) == 1 and code in ["10", "20", "30", "150", "270", "280"]:
            score -= 4.0

        if score > best_score:
            best_score = score
            best_code = code
            best_name = name
            best_path = path_names

    if not best_code:
        # Якщо всі кандидати відсіялися фільтром юрисдикції — обираємо пріоритетну категорію суду
        best_code = context["preferred_branches"][0] if context["preferred_branches"] else candidates[0]["code"]
        cur.execute("SELECT clean_name, path_names FROM categories WHERE code = ?", (best_code,))
        fb_row = cur.fetchone()
        best_name = fb_row["clean_name"] if fb_row else "Загальна категорія"
        best_path = fb_row["path_names"] if fb_row else best_name
        confidence = 0.70
    else:
        confidence = min(0.98, max(0.65, 0.65 + best_score / 20.0))

    reasoning = (
        f"Семантичний мапінг з урахуванням юрисдикції {context['court']}. "
        f"Обрано рубрику «{best_name}» ({best_path})."
    )

    return best_code, round(confidence, 2), reasoning


def process_folder(folder_path: Path, dry_run: bool = False) -> Dict[str, int]:
    """
    Обробляє окрему папку дайджесту.
    """
    stats = {"processed": 0, "mapped": 0, "cleaned_preambles": 0}
    conn = get_db_connection()
    cur = conn.cursor()

    preamble_file = folder_path / "00_Preamble.md"
    preamble_text = ""
    if preamble_file.exists():
        try:
            preamble_text = preamble_file.read_text(encoding="utf-8")
        except Exception:
            pass

    context = detect_digest_context(folder_path.name, preamble_text)

    # Очищуємо помилково внесені преамбули та застереження (appendix)
    if not dry_run:
        cur.execute("DELETE FROM mapped_segments WHERE file_path LIKE ? OR file_path LIKE ?", 
                    (f"%{folder_path.name}/00_Preamble.md%", f"%{folder_path.name}/%appendix%"))
        stats["cleaned_preambles"] += cur.rowcount

    md_files = sorted([f for f in folder_path.glob("*.md") 
                       if "preamble" not in f.name.lower() 
                       and "zmist" not in f.name.lower()
                       and "appendix" not in f.name.lower()
                       and "dodatok" not in f.name.lower()])
    
    for f in md_files:
        info = parse_segment_file(f)
        if not info:
            continue

        cat_code, conf, reason = find_best_category(info, context, conn)

        pdf_rel = f"documents/pdfs/{folder_path.name}.pdf"

        if not dry_run:
            cur.execute("SELECT id FROM mapped_segments WHERE file_path = ?", (info["file_path"],))
            existing = cur.fetchone()
            if existing:
                cur.execute("""
                    UPDATE mapped_segments
                    SET category_code = ?,
                        case_number = ?,
                        original_category = ?,
                        teza = ?,
                        summary = ?,
                        circumstances = ?,
                        reasoning = ?,
                        confidence_score = ?,
                        llm_reasoning = ?,
                        pdf_path = ?
                    WHERE id = ?
                """, (
                    cat_code,
                    info["case_number"],
                    info["original_category"],
                    info["teza"],
                    info["summary"],
                    info["circumstances"],
                    info["reasoning"],
                    conf,
                    reason,
                    pdf_rel,
                    existing["id"]
                ))
            else:
                cur.execute("""
                    INSERT INTO mapped_segments 
                    (category_code, case_number, original_category, teza, summary, circumstances, reasoning, confidence_score, llm_reasoning, file_path, pdf_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    cat_code,
                    info["case_number"],
                    info["original_category"],
                    info["teza"],
                    info["summary"],
                    info["circumstances"],
                    info["reasoning"],
                    conf,
                    reason,
                    info["file_path"],
                    pdf_rel
                ))
            stats["mapped"] += 1
        stats["processed"] += 1

    if not dry_run:
        conn.commit()
    conn.close()

    return stats


def run_full_remapping(dry_run: bool = False):
    """
    Повний прохід по всіх 232 папках сегментів для виправлення всіх помилок мапінгу.
    """
    docs_dir = Path(DOCS_DIR)
    folders = sorted([d for d in docs_dir.iterdir() if d.is_dir()], key=lambda x: x.name)
    total_folders = len(folders)
    
    print(f"🚀 Запуск повного семантичного перемапінгу по всіх {total_folders} папках дайджестів...")
    if dry_run:
        print("⚠️ Режим симуляції (Dry-Run): зміни в БД вноситися не будуть.")

    total_processed = 0
    total_mapped = 0

    for idx, f in enumerate(folders, 1):
        res = process_folder(f, dry_run=dry_run)
        total_processed += res["processed"]
        total_mapped += res["mapped"]
        if idx % 10 == 0 or idx == total_folders:
            print(f"[{idx:3d}/{total_folders}] Оброблено папок | Сегментів: {total_processed} | Оновлено: {total_mapped}")

    print(f"\n🎉 Повний перемапінг успішно завершено!")
    print(f"Всього оброблено папок: {total_folders}")
    print(f"Всього перевірено та оновлено судових сегментів: {total_mapped}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Розумний мапінг судових сегментів до класифікатора")
    parser.add_argument("--folder", type=str, help="Назва конкретної папки в documents/segments")
    parser.add_argument("--all", action="store_true", help="Обробити всі папки в documents/segments")
    parser.add_argument("--clean-preambles", action="store_true", help="Видалити всі помилкові записи 00_Preamble.md з БД")
    parser.add_argument("--dry-run", action="store_true", help="Режим симуляції без запису в БД")
    args = parser.parse_args()

    if args.clean_preambles:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM mapped_segments WHERE file_path LIKE '%00_Preamble.md%' OR file_path LIKE '%preamble%'")
        count = cur.rowcount
        conn.commit()
        conn.close()
        print(f"🧹 Видалено {count} записів преамбул з усієї бази даних.")

    elif args.folder:
        target = Path(DOCS_DIR) / args.folder
        if not target.exists():
            print(f"❌ Папку {target} не знайдено!")
            sys.exit(1)
        res = process_folder(target, dry_run=args.dry_run)
        print(f"✅ Папка {args.folder}: оброблено {res['processed']}, оновлено {res['mapped']}")

    elif args.all:
        run_full_remapping(dry_run=args.dry_run)

    else:
        print("Вкажіть конкретну папку через --folder <name>, запустіть для всіх через --all, або очистіть преамбули через --clean-preambles.")
