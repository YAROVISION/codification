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
DOCS_PDFS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "documents", "pdfs")
DOCS_MARKDOWN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "documents", "markdown")
DOCS_SEGMENTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "documents", "segments")
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

        # PDF serving
        if path.startswith("/documents/pdfs/"):
            self.handle_pdf(path)
            return

        # API Endpoints
        if path == "/api/stats":
            self.send_json_response(self.handle_stats())
        elif path == "/api/digests":
            self.send_json_response(self.handle_digests())
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

    def do_HEAD(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path.startswith("/documents/pdfs/"):
            rel_path = urllib.parse.unquote(parsed.path.replace("/documents/pdfs/", "").lstrip("/"))
            file_path = os.path.normpath(os.path.join(DOCS_PDFS_DIR, rel_path))
            if file_path.startswith(DOCS_PDFS_DIR) and os.path.isfile(file_path):
                self.send_response(200)
                self.send_header("Content-Type", "application/pdf")
                self.send_header("Content-Length", str(os.path.getsize(file_path)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
                return
        super().do_HEAD()

    def handle_pdf(self, path):
        rel_path = urllib.parse.unquote(path.replace("/documents/pdfs/", "").lstrip("/"))
        file_path = os.path.normpath(os.path.join(DOCS_PDFS_DIR, rel_path))

        # Захист від directory traversal
        if not file_path.startswith(DOCS_PDFS_DIR) or not os.path.isfile(file_path):
            self.send_error(404, "PDF Not Found")
            return

        try:
            file_size = os.path.getsize(file_path)
            filename = os.path.basename(file_path)

            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Length", str(file_size))
            self.send_header("Content-Disposition", f'inline; filename="{urllib.parse.quote(filename)}"')
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()

            with open(file_path, "rb") as f:
                self.copyfile(f, self.wfile)
        except (ConnectionResetError, BrokenPipeError):
            pass
        except Exception as e:
            try:
                self.send_error(500, "Error streaming PDF")
            except Exception:
                pass

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
                    SELECT id, case_number, original_category, teza, summary, circumstances, reasoning, confidence_score, llm_reasoning, file_path, pdf_path
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

    def handle_digests(self):
        """Повертає список PDF дайджестів з перевіркою markdown, сегментів та категорій."""
        results = []
        if not os.path.exists(DOCS_PDFS_DIR):
            return results

        files = sorted([f for f in os.listdir(DOCS_PDFS_DIR) if f.lower().endswith(".pdf")])
        for idx, filename in enumerate(files, 1):
            name_no_ext = os.path.splitext(filename)[0]

            # Перевірка наявності у documents/markdown:
            # 1. Окремий файл name_no_ext.md
            # 2. Або папка name_no_ext з .md файлами всередині
            md_path_file = os.path.join(DOCS_MARKDOWN_DIR, f"{name_no_ext}.md")
            md_path_dir = os.path.join(DOCS_MARKDOWN_DIR, name_no_ext)
            has_markdown = False
            if os.path.isfile(md_path_file):
                has_markdown = True
            elif os.path.isdir(md_path_dir):
                md_inner = [mf for mf in os.listdir(md_path_dir) if mf.endswith(".md") and not mf.startswith(".")]
                has_markdown = len(md_inner) > 0

            # Перевірка наявності оброблених сегментів у documents/segments/name_no_ext
            seg_folder = os.path.join(DOCS_SEGMENTS_DIR, name_no_ext)
            segments_count = 0
            has_segments = False
            if os.path.isdir(seg_folder):
                seg_files = [sf for sf in os.listdir(seg_folder) if sf.endswith(".md") and not sf.startswith(".")]
                segments_count = len(seg_files)
                has_segments = segments_count > 0

            category = self.detect_category(filename)

            pdf_full_path = os.path.join(DOCS_PDFS_DIR, filename)
            pdf_size_bytes = os.path.getsize(pdf_full_path) if os.path.isfile(pdf_full_path) else 0

            results.append({
                "num": idx,
                "filename": filename,
                "url": f"/documents/pdfs/{urllib.parse.quote(filename)}",
                "size_bytes": pdf_size_bytes,
                "has_markdown": has_markdown,
                "has_segments": has_segments,
                "segments_count": segments_count,
                "category": category
            })
        return results

    @staticmethod
    def detect_category(filename):
        fn = filename.upper()
        if "KKS" in fn:
            return "ККС ВС (Кримінальна)"
        elif "KGS" in fn:
            return "КГС ВС (Господарська)"
        elif "KAS" in fn or "OHLIAD_KAS" in fn:
            return "КАС ВС (Адміністративна)"
        elif "KCS" in fn or "KC_S" in fn:
            return "КЦС ВС (Цивільна)"
        elif "VP" in fn or "VELYKA" in fn or "ZVED_DAIDZHEST_VP" in fn:
            return "Велика Палата ВС"
        elif "ESPL" in fn or "YESPL" in fn:
            return "Практика ЄСПЛ"
        elif "SES" in fn or "COMMUNITY_DESIGNS" in fn:
            return "Суд Європейського Союзу"
        elif "VRP" in fn:
            return "Вища рада правосуддя"
        elif "BANKRUPTCY" in fn:
            return "КГС ВС (Банкрутство)"
        elif "VS" in fn or "OGLYAD" in fn or "OHLIAD" in fn or "ZBIRNUK" in fn:
            return "Верховний Суд (Тематична)"
        else:
            return "Судова практика"


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
