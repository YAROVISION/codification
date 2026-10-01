"""
Модуль для роботи із семантичною базою даних класифікатора законодавства України.
Надає API для:
- Навігації по ієрархічному дереву (батьки, діти, предки)
- Швидкого повнотекстового пошуку через FTS5
- Роботи із семантичними зв'язками (граф галузей права)
- Підготовки та збереження векторних ембеддінгів (для Semantic Search / RAG)
"""

import os
import json
import sqlite3
from typing import Optional, List, Dict, Any


DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "classifier.sqlite")


class SemanticClassifierDB:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"База даних не знайдена за шляхом: {db_path}. Спочатку запустіть parse_classifier.py")
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_roots(self) -> List[Dict[str, Any]]:
        """Отримати 28 головних галузей права (Рівень 1)."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM categories 
                WHERE level = 1 
                ORDER BY CAST(code AS INTEGER)
            """)
            return [dict(row) for row in cur.fetchall()]

    def get_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Знайти категорію за її точним кодом (наприклад, '10 10 10')."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM categories WHERE code = ?", (code,))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_children(self, parent_code: str) -> List[Dict[str, Any]]:
        """Отримати прямих нащадків заданої категорії."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM categories 
                WHERE parent_code = ? 
                ORDER BY id
            """, (parent_code,))
            return [dict(row) for row in cur.fetchall()]

    def get_ancestors(self, code: str) -> List[Dict[str, Any]]:
        """Отримати ланцюжок предків (від кореня до заданої категорії)."""
        cat = self.get_by_code(code)
        if not cat:
            return []
        
        path_codes = [c.strip() for c in cat['path_codes'].split('/')]
        ancestors = []
        for c in path_codes:
            node = self.get_by_code(c)
            if node:
                ancestors.append(node)
        return ancestors

    def get_subtree(self, root_code: str) -> List[Dict[str, Any]]:
        """Отримати всі підкатегорії будь-якої глибини для вказаного розділу."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            # Оскільки path_codes містить ланцюжок '10 / 10 10 / ...', шукаємо за префіксом
            cur.execute("""
                SELECT * FROM categories 
                WHERE code = ? OR path_codes LIKE ? 
                ORDER BY level, id
            """, (root_code, f"{root_code} / %"))
            return [dict(row) for row in cur.fetchall()]

    def search_fts(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Повнотекстовий пошук (FTS5) за назвами, шляхами та контекстом.
        Підтримує префікси (наприклад: 'подат*'), логічні оператори (AND, OR, NOT).
        """
        # Екранування або додавання зірочки, якщо одне слово
        clean_q = query.strip()
        if clean_q and not any(op in clean_q for op in ['*', 'AND', 'OR', 'NOT', '"']):
            tokens = clean_q.split()
            fts_query = " ".join(f'"{t}"*' for t in tokens)
        else:
            fts_query = clean_q

        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT 
                    c.id, c.code, c.level, c.name, c.clean_name,
                    c.path_names, c.total_docs_count, c.direct_docs_count,
                    c.branch_url, c.direct_url,
                    bm25(categories_fts) AS rank
                FROM categories_fts
                JOIN categories c ON c.code = categories_fts.code
                WHERE categories_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (fts_query, limit))
            return [dict(row) for row in cur.fetchall()]

    def get_semantic_relations(self, code: Optional[str] = None) -> List[Dict[str, Any]]:
        """Отримати семантичні зв'язки (перехресні посилання тощо)."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            if code:
                cur.execute("""
                    SELECT r.*, c.clean_name AS target_name 
                    FROM semantic_relations r
                    LEFT JOIN categories c ON c.code = r.target_code
                    WHERE r.source_code = ?
                """, (code,))
            else:
                cur.execute("""
                    SELECT r.*, 
                           src.clean_name AS source_name, 
                           dst.clean_name AS target_name 
                    FROM semantic_relations r
                    LEFT JOIN categories src ON src.code = r.source_code
                    LEFT JOIN categories dst ON dst.code = r.target_code
                """)
            return [dict(row) for row in cur.fetchall()]

    def get_corpus_for_embedding(self) -> List[Dict[str, Any]]:
        """
        Повертає структуровані текстові блоки для кожного вузла.
        Готово для передачі в embedding-моделі (SentenceTransformers, OpenAI, Gemini).
        """
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, code, level, clean_name, path_names, total_docs_count, semantic_text 
                FROM categories 
                ORDER BY id
            """)
            return [dict(row) for row in cur.fetchall()]

    def update_embedding(self, code: str, embedding_bytes: bytes):
        """Зберегти бінарний вектор ембеддінгу для категорії."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE categories SET embedding = ?, updated_at = CURRENT_TIMESTAMP WHERE code = ?", 
                        (embedding_bytes, code))
            conn.commit()

    def get_stats(self) -> Dict[str, Any]:
        """Загальна статистика класифікатора в базі даних."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM categories")
            total = cur.fetchone()[0]

            cur.execute("SELECT level, COUNT(*) FROM categories GROUP BY level")
            by_level = {row[0]: row[1] for row in cur.fetchall()}

            cur.execute("SELECT SUM(direct_docs_count) FROM categories")
            direct_docs = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM semantic_relations")
            relations = cur.fetchone()[0]

            return {
                'total_categories': total,
                'levels': by_level,
                'total_direct_docs': direct_docs,
                'semantic_relations': relations
            }


if __name__ == "__main__":
    db = SemanticClassifierDB()
    stats = db.get_stats()
    print("=== Статистика бази даних ===")
    print(f"Всього категорій: {stats['total_categories']}")
    print(f"Розподіл за рівнями: {stats['levels']}")
    print(f"Семантичних зв'язків: {stats['semantic_relations']}")

    print("\n=== Приклад вибірки: Топ 5 галузей права ===")
    for root in db.get_roots()[:5]:
        print(f"  [{root['code']}] {root['clean_name']} — актів у гілці: {root['total_docs_count']:,} (дочірніх: {root['children_count']})")

    print("\n=== Приклад FTS5 пошуку за словом 'кібербезпека' або 'інформаційн' ===")
    results = db.search_fts("інформаційн*", limit=5)
    for res in results:
        print(f"  [{res['code']}] {res['clean_name']}")
        print(f"      Шлях: {res['path_names']}")

    print("\n=== Приклад предків для коду '10 10 10' ===")
    ancestors = db.get_ancestors("10 10 10")
    for a in ancestors:
        print(f"  -> Рівень {a['level']}: [{a['code']}] {a['clean_name']}")
