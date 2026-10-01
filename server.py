"""
Локальний веб-сервер для візуального інтерфейсу класифікатора законодавства.
Використовує тільки стандартну бібліотеку Python (http.server + sqlite3).
Забезпечує:
- Роздачу статичного веб-інтерфейсу (HTML, CSS, JS)
- REST API для дерева, пошуку FTS5 та навігації
"""

import os
import sys
import json
import sqlite3
import urllib.parse
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

PORT = 8080
PUBLIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public")
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DATA_DIR, "classifier.sqlite")
JSON_TREE_PATH = os.path.join(DATA_DIR, "classifier.json")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class ClassifierHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC_DIR, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # API Endpoints
        if path == "/api/stats":
            self.send_json_response(self.handle_stats())
        elif path == "/api/tree":
            self.send_json_response(self.handle_tree())
        elif path == "/api/roots":
            self.send_json_response(self.handle_roots())
        elif path == "/api/category":
            code = query.get("code", [""])[0]
            self.send_json_response(self.handle_category(code))
        elif path == "/api/children":
            code = query.get("code", [""])[0]
            self.send_json_response(self.handle_children(code))
        elif path == "/api/search":
            q = query.get("q", [""])[0]
            limit = int(query.get("limit", [30])[0])
            self.send_json_response(self.handle_search(q, limit))
        else:
            # Обслуговування статичних файлів з public/
            super().do_GET()

    def send_json_response(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def handle_stats(self):
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM categories")
            total = cur.fetchone()[0]

            cur.execute("SELECT level, COUNT(*) FROM categories GROUP BY level")
            by_level = {f"level_{row[0]}": row[1] for row in cur.fetchall()}

            cur.execute("SELECT SUM(direct_docs_count) FROM categories")
            direct_docs = cur.fetchone()[0]

            cur.execute("SELECT SUM(total_docs_count) FROM categories WHERE level = 1")
            total_docs = cur.fetchone()[0]

            return {
                "total_categories": total,
                "levels": by_level,
                "total_docs_registered": total_docs,
                "direct_docs_registered": direct_docs,
                "root_branches": by_level.get("level_1", 28)
            }

    def handle_tree(self):
        if os.path.exists(JSON_TREE_PATH):
            with open(JSON_TREE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"error": "classifier.json not found"}

    def handle_roots(self):
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT code, clean_name, children_count, total_docs_count, direct_docs_count, branch_url
                FROM categories
                WHERE level = 1
                ORDER BY CAST(code AS INTEGER)
            """)
            return [dict(r) for r in cur.fetchall()]

    def handle_category(self, code):
        if not code:
            return {"error": "Missing code"}
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM categories WHERE code = ?", (code,))
            row = cur.fetchone()
            if not row:
                return {"error": "Category not found"}
            cat = dict(row)

            # Отримуємо прямих дітей
            cur.execute("""
                SELECT code, clean_name, level, total_docs_count, direct_docs_count, has_children, children_count, branch_url, direct_url
                FROM categories WHERE parent_code = ? ORDER BY id
            """, (code,))
            cat["children"] = [dict(r) for r in cur.fetchall()]

            # Отримуємо предків
            ancestor_codes = [c.strip() for c in cat["path_codes"].split("/")]
            cat["ancestors"] = []
            for ac in ancestor_codes:
                cur.execute("SELECT code, clean_name, level FROM categories WHERE code = ?", (ac,))
                ar = cur.fetchone()
                if ar:
                    cat["ancestors"].append(dict(ar))

            # Перехресні зв'язки
            cur.execute("""
                SELECT r.*, c.clean_name AS target_name, c.branch_url AS target_url
                FROM semantic_relations r
                LEFT JOIN categories c ON c.code = r.target_code
                WHERE r.source_code = ?
            """, (code,))
            cat["relations"] = [dict(r) for r in cur.fetchall()]

            # Судова практика (Прикріплені сегменти)
            try:
                cur.execute("""
                    SELECT id, case_number, original_category, teza, summary, circumstances, reasoning, confidence_score, llm_reasoning, file_path
                    FROM mapped_segments
                    WHERE category_code = ?
                """, (code,))
                cat["segments"] = [dict(r) for r in cur.fetchall()]
            except sqlite3.OperationalError:
                cat["segments"] = []

            return cat

    def handle_children(self, parent_code):
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT code, clean_name, level, total_docs_count, direct_docs_count, has_children, children_count, branch_url, direct_url
                FROM categories WHERE parent_code = ? ORDER BY id
            """, (parent_code,))
            return [dict(r) for r in cur.fetchall()]

    def handle_search(self, q, limit=30):
        if not q or not q.strip():
            return []
        
        clean_q = q.strip()
        tokens = [t for t in clean_q.split() if t]
        if not any(ch in clean_q for ch in ['*', '"', 'AND', 'OR']):
            fts_query = " ".join(f'"{t}"*' for t in tokens)
        else:
            fts_query = clean_q

        with get_db_connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute("""
                    SELECT 
                        c.code, c.level, c.clean_name, c.path_names,
                        c.total_docs_count, c.direct_docs_count,
                        c.branch_url, c.direct_url,
                        bm25(categories_fts) AS rank
                    FROM categories_fts
                    JOIN categories c ON c.code = categories_fts.code
                    WHERE categories_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                """, (fts_query, limit))
                return [dict(r) for r in cur.fetchall()]
            except sqlite3.OperationalError:
                # Фоллбек на простий LIKE, якщо синтаксис запиту некоректний для FTS
                cur.execute("""
                    SELECT code, level, clean_name, path_names, total_docs_count, direct_docs_count, branch_url, direct_url
                    FROM categories
                    WHERE clean_name LIKE ? OR path_names LIKE ? OR code LIKE ?
                    LIMIT ?
                """, (f"%{clean_q}%", f"%{clean_q}%", f"%{clean_q}%", limit))
                return [dict(r) for r in cur.fetchall()]


def run_server(port=PORT):
    server = ThreadingHTTPServer(("127.0.0.1", port), ClassifierHandler)
    print(f"\n=======================================================")
    print(f"🚀 Веб-інтерфейс запущено: http://127.0.0.1:{port}")
    print(f"📁 Статичні файли: {PUBLIC_DIR}")
    print(f"Натисніть Ctrl+C для зупинки сервера")
    print(f"=======================================================\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nСервер зупинено.")


if __name__ == "__main__":
    run_server()
