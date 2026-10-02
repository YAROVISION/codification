import sys
import sqlite3

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('data/classifier.sqlite')
c = conn.cursor()

print("=== 1. Перевірка службових файлів (преамбул) у базі ===")
c.execute("SELECT COUNT(*) FROM mapped_segments WHERE file_path LIKE '%preamble%' OR file_path LIKE '%zmist%'")
print("Залишок преамбул у mapped_segments:", c.fetchone()[0])

print("\n=== 2. Перевірка конфліктів юрисдикцій процесу ===")
queries = {
    "КАС у кримінальному, цивільному або господарському процесі": """
        SELECT COUNT(*) FROM mapped_segments 
        WHERE (file_path LIKE '%kas%' OR file_path LIKE '%кас%') 
          AND (category_code LIKE '270 10%' OR category_code LIKE '270 20%' OR category_code LIKE '270 30%')
    """,
    "КГС у кримінальному, цивільному або адмін. процесі": """
        SELECT COUNT(*) FROM mapped_segments 
        WHERE (file_path LIKE '%kgs%' OR file_path LIKE '%кгс%') 
          AND (category_code LIKE '270 10%' OR category_code LIKE '270 20%' OR category_code LIKE '270 50%')
    """,
    "КЦС у кримінальному, господарському або адмін. процесі": """
        SELECT COUNT(*) FROM mapped_segments 
        WHERE (file_path LIKE '%kcs%' OR file_path LIKE '%кцс%') 
          AND (category_code LIKE '270 10%' OR category_code LIKE '270 30%' OR category_code LIKE '270 50%')
    """,
    "ККС у цивільному, господарському або адмін. процесі чи житлі": """
        SELECT COUNT(*) FROM mapped_segments 
        WHERE (file_path LIKE '%kks%' OR file_path LIKE '%ккс%') 
          AND (category_code LIKE '270 20%' OR category_code LIKE '270 30%' OR category_code LIKE '270 50%' OR category_code LIKE '80%')
    """
}

for name, q in queries.items():
    c.execute(q)
    print(f"  {name}: {c.fetchone()[0]} (було: десятки/сотні помилок)")

print("\n=== 3. Загальна кількість якісно розмічених сегментів ===")
c.execute("SELECT COUNT(*) FROM mapped_segments")
total = c.fetchone()[0]
print(f"Всього сегментів у базі: {total}")

print("\n=== 4. Топ-10 категорій за кількістю розмічених сегментів ===")
c.execute("""
    SELECT m.category_code, c.clean_name, COUNT(*) as cnt
    FROM mapped_segments m
    LEFT JOIN categories c ON c.code = m.category_code
    GROUP BY m.category_code
    ORDER BY cnt DESC
    LIMIT 10
""")
for r in c.fetchall():
    print(f"  {r[0]}: {r[1]} -> {r[2]} сегментів")
