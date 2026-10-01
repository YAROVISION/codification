import os
import re
import sqlite3
from pathlib import Path

DB_PATH = "data/classifier.sqlite"
DOCS_DIR = "documents/segments"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def extract_markdown_info(text):
    info = {
        "original_category": "",
        "teza": "",
        "summary": "",
        "reasoning": "",
        "case_number": "Не вказана"
    }
    
    # Витягуємо номер справи
    case_match = re.search(r"справ[іа]\s+№\s*([\d\/А-Яа-я\-]+)", text, re.IGNORECASE)
    if case_match:
        info["case_number"] = f"№ {case_match.group(1).strip()}"
        
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines:
        return info
        
    # Спрощена логіка: 
    # 1. Перший рядок (заголовок) -> original_category
    # 2. Другий абзац (підзаголовок або суть) -> teza
    # 3. Все інше -> summary
    
    info["original_category"] = lines[0].lstrip("#").strip()
    
    if len(lines) > 1:
        info["teza"] = lines[1].lstrip("#").strip()
        
    info["summary"] = " ".join(lines[2:10])[:500] + "..." # Беремо перші абзаци як короткий опис
    
    return info

def map_segments():
    print("🚀 Запуск автоматичного мапінгу MD сегментів через FTS5...")
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Видаляємо попередні результати (або не видаляємо, якщо хочемо залишити і JSON і MD)
    # cur.execute("DELETE FROM mapped_segments") 
    
    processed = 0
    mapped = 0
    
    md_files = list(Path(DOCS_DIR).rglob("*.md"))
    print(f"Знайдено {len(md_files)} MD файлів для обробки.\n")
    
    for filepath in md_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()
                
            info = extract_markdown_info(text)
            
            # Формуємо пошуковий запит
            search_text = f"{info['original_category']} {info['teza']} {info['summary']}"
            
            clean_search = "".join(c if c.isalnum() or c.isspace() else ' ' for c in search_text)
            tokens = [t for t in clean_search.split() if len(t) > 3][:15] # 15 ключових слів
            
            if not tokens:
                continue
                
            fts_query = " OR ".join(f'"{t}"*' for t in tokens)
            
            cur.execute("""
                SELECT c.code, bm25(categories_fts) AS rank, c.clean_name
                FROM categories_fts
                JOIN categories c ON c.code = categories_fts.code
                WHERE categories_fts MATCH ?
                ORDER BY rank
                LIMIT 1
            """, (fts_query,))
            
            match = cur.fetchone()
            
            if match:
                category_code = match["code"]
                score = min(0.99, abs(match["rank"]) / 15.0 + 0.5)
                
                cur.execute("""
                    INSERT INTO mapped_segments 
                    (category_code, case_number, original_category, teza, summary, circumstances, reasoning, confidence_score, llm_reasoning, file_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    category_code, 
                    info["case_number"], 
                    info["original_category"], 
                    info["teza"], 
                    info["summary"], 
                    "", 
                    "", 
                    score, 
                    f"Автоматичний мапінг з Markdown (FTS5 BM25). Знайдено збіг з рубрикою «{match['clean_name']}».", 
                    str(filepath)
                ))
                mapped += 1
                
            processed += 1
            if processed % 100 == 0:
                print(f"Оброблено: {processed}/{len(md_files)}")
                
        except Exception as e:
            print(f"Помилка в {filepath}: {e}")
            
    conn.commit()
    conn.close()
    
    print(f"\n✅ Мапінг завершено!")
    print(f"Всього оброблено MD файлів: {processed}")
    print(f"Успішно прив'язано до рубрик: {mapped}")

if __name__ == "__main__":
    map_segments()
