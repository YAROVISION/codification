"""
Єдиний класифікатор правових актів України (рубрикатор ВРУ)
Скрипт парсингу, валідації та експорту класифікатора у формати:
- JSON (ієрархічне дерево + плоский список)
- CSV (з підтримкою UTF-8-SIG для Excel)
- SQLite (з підтримкою FTS5 повнотекстового пошуку, зв'язків та семантичних полів)
- Markdown (структурований звіт та інтерактивне дерево з посиланнями)
"""

import os
import sys
import re
import json
import csv
import sqlite3
import httpx
from bs4 import BeautifulSoup
from collections import Counter
from datetime import datetime

# Гарантуємо UTF-8 для виводу в консоль
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "https://zakon.rada.gov.ua/laws/main/klas"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)

RAW_HTML_CACHE = os.path.join(DATA_DIR, "klas_source.html")


def fetch_html(force_download: bool = False) -> str:
    """Завантажує HTML зі сайту Ради або бере з локального кешу."""
    if not force_download and os.path.exists(RAW_HTML_CACHE):
        print(f"[*] Використовуємо кешований HTML: {RAW_HTML_CACHE}")
        with open(RAW_HTML_CACHE, 'r', encoding='utf-8') as f:
            return f.read()

    print(f"[*] Завантажуємо сторінку класифікатора: {BASE_URL}...")
    response = httpx.get(BASE_URL, headers=HEADERS, timeout=45.0)
    response.raise_for_status()

    # zakon.rada.gov.ua надсилає байти у UTF-8
    content_text = response.content.decode('utf-8', errors='replace')
    
    with open(RAW_HTML_CACHE, 'w', encoding='utf-8') as f:
        f.write(content_text)
    print(f"[+] Сторінку збережено до кешу ({len(content_text):,} символів)")
    return content_text


def parse_classifier(html: str) -> list[dict]:
    """Парсить усі категорії класифікатора, витягує метадані, зв'язки та статистику."""
    soup = BeautifulSoup(html, 'html.parser')
    
    raw_items = []
    
    # Знаходимо всі <li> з тегом <code>
    for li in soup.find_all('li'):
        code_tag = li.find('code')
        if not code_tag:
            continue
        
        code = code_tag.get_text(strip=True)
        if not code:
            continue
            
        # Рівень визначається кількістю символів '·' у span (або відсутністю)
        span = li.find('span')
        span_text = span.get_text() if span else ''
        dots_count = span_text.count('·')
        level = dots_count + 1
        
        # Назва та основне посилання на категорію
        anchors = [a for a in li.find_all('a') if not a.find_parent('small')]
        name = ''
        branch_url = ''
        if anchors:
            name = anchors[0].get_text(strip=True)
            branch_url = anchors[0].get('href', '').strip()
        else:
            # Для вузлів з 0 документів без <a> тегу (клас text-muted)
            li_copy = BeautifulSoup(str(li), 'html.parser').find('li')
            for tag_to_remove in ['code', 'span', 'small']:
                for t in li_copy.find_all(tag_to_remove):
                    t.decompose()
            name = li_copy.get_text(strip=True).lstrip('—').strip()

        # Лічильники документів у тезі <small>
        small = li.find('small')
        small_text = small.get_text(strip=True) if small else ''
        
        total_docs_count = 0
        direct_docs_count = 0
        direct_url = ''
        
        if small:
            direct_a = small.find('a')
            if direct_a:
                direct_url = direct_a.get('href', '').strip()
                
            m = re.match(r'^(\d+)(?:/(\d+))?$', small_text)
            if m:
                total_docs_count = int(m.group(1))
                if m.group(2) is not None:
                    direct_docs_count = int(m.group(2))
                else:
                    direct_docs_count = total_docs_count
                    if not direct_url and branch_url:
                        direct_url = branch_url

        # Пошук перехресних посилань типу "(див. 20 20)"
        cross_refs = re.findall(r'\(див\.\s*([^)]+)\)', name)
        clean_name = re.sub(r'\s*\(див\.[^)]+\)', '', name).strip()
        
        raw_items.append({
            'code': code,
            'level': level,
            'name': name,
            'clean_name': clean_name,
            'cross_references': [r.strip() for r in cross_refs],
            'branch_url': branch_url,
            'direct_url': direct_url,
            'total_docs_count': total_docs_count,
            'direct_docs_count': direct_docs_count,
        })
        
    print(f"[+] Знайдено {len(raw_items)} елементів класифікатора")

    # Відновлення дерева та побудова ієрархічних шляхів через стек
    stack = []
    items_by_code = {}
    
    for it in raw_items:
        while stack and stack[-1]['level'] >= it['level']:
            stack.pop()
            
        if stack:
            parent = stack[-1]
            it['parent_code'] = parent['code']
            it['path_codes'] = [s['code'] for s in stack] + [it['code']]
            it['path_names'] = [s['clean_name'] for s in stack] + [it['clean_name']]
        else:
            it['parent_code'] = None
            it['path_codes'] = [it['code']]
            it['path_names'] = [it['clean_name']]
            
        it['has_children'] = False
        it['children_count'] = 0
        it['direct_children'] = []
        
        items_by_code[it['code']] = it
        stack.append(it)

    # Підрахунок дочірніх елементів
    for it in raw_items:
        p_code = it['parent_code']
        if p_code and p_code in items_by_code:
            parent = items_by_code[p_code]
            parent['has_children'] = True
            parent['children_count'] += 1
            parent['direct_children'].append(it['code'])

    # Формування семантичного опису для векторних моделей / ембеддінгів
    for it in raw_items:
        path_str = " > ".join(it['path_names'])
        it['semantic_text'] = (
            f"Категорія: {it['clean_name']}. "
            f"Ієрархічний шлях: {path_str}. "
            f"Код класифікатора: {it['code']} (Рівень {it['level']}). "
            f"Кількість документів: {it['total_docs_count']}."
        )

    return raw_items


def build_nested_tree(flat_items: list[dict]) -> list[dict]:
    """Будує рекурсивне ієрархічне дерево для JSON."""
    items_copy = {}
    for it in flat_items:
        node = {
            'code': it['code'],
            'name': it['name'],
            'clean_name': it['clean_name'],
            'level': it['level'],
            'parent_code': it['parent_code'],
            'path': " / ".join(it['path_names']),
            'total_docs_count': it['total_docs_count'],
            'direct_docs_count': it['direct_docs_count'],
            'branch_url': it['branch_url'],
            'direct_url': it['direct_url'],
            'cross_references': it['cross_references'],
            'children': []
        }
        items_copy[it['code']] = node

    roots = []
    for it in flat_items:
        code = it['code']
        parent_code = it['parent_code']
        node = items_copy[code]
        if parent_code and parent_code in items_copy:
            items_copy[parent_code]['children'].append(node)
        else:
            roots.append(node)
            
    return roots


def export_json(flat_items: list[dict], nested_tree: list[dict]):
    """Експорт у nested JSON та flat JSON."""
    nested_path = os.path.join(DATA_DIR, "classifier.json")
    flat_path = os.path.join(DATA_DIR, "classifier_flat.json")

    # Зберігаємо компактний nested tree
    with open(nested_path, 'w', encoding='utf-8') as f:
        json.dump({
            'metadata': {
                'title': 'Єдиний класифікатор правових актів України (Юридична класифікація ВРУ)',
                'source': BASE_URL,
                'scraped_at': datetime.now().isoformat(),
                'total_categories': len(flat_items),
                'total_root_branches': len(nested_tree),
            },
            'tree': nested_tree
        }, f, ensure_ascii=False, indent=2)

    # Зберігаємо плоский список з повними метаданими
    with open(flat_path, 'w', encoding='utf-8') as f:
        json.dump({
            'metadata': {
                'title': 'Юридична класифікація ВРУ (Плоска структура)',
                'scraped_at': datetime.now().isoformat(),
                'total_categories': len(flat_items),
            },
            'items': flat_items
        }, f, ensure_ascii=False, indent=2)

    print(f"[+] JSON експортовано:")
    print(f"    - Дерево: {nested_path} ({os.path.getsize(nested_path):,} байт)")
    print(f"    - Плоский: {flat_path} ({os.path.getsize(flat_path):,} байт)")


def export_csv(flat_items: list[dict]):
    """Експорт у CSV (UTF-8 з BOM для коректного відкриття у Excel)."""
    csv_path = os.path.join(DATA_DIR, "classifier.csv")
    fieldnames = [
        'code',
        'level',
        'parent_code',
        'name',
        'clean_name',
        'has_children',
        'children_count',
        'total_docs_count',
        'direct_docs_count',
        'branch_url',
        'direct_url',
        'path_codes',
        'path_names',
        'cross_references',
        'semantic_text'
    ]

    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for it in flat_items:
            row = {
                'code': it['code'],
                'level': it['level'],
                'parent_code': it['parent_code'] or '',
                'name': it['name'],
                'clean_name': it['clean_name'],
                'has_children': 1 if it['has_children'] else 0,
                'children_count': it['children_count'],
                'total_docs_count': it['total_docs_count'],
                'direct_docs_count': it['direct_docs_count'],
                'branch_url': it['branch_url'],
                'direct_url': it['direct_url'],
                'path_codes': " / ".join(it['path_codes']),
                'path_names': " / ".join(it['path_names']),
                'cross_references': "; ".join(it['cross_references']),
                'semantic_text': it['semantic_text']
            }
            writer.writerow(row)

    print(f"[+] CSV експортовано: {csv_path} ({os.path.getsize(csv_path):,} байт)")


def export_sqlite(flat_items: list[dict]):
    """Експорт у SQLite з індексами, FTS5 та підготовкою під семантичну БД."""
    db_path = os.path.join(DATA_DIR, "classifier.sqlite")
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.executescript("""
    -- Таблиця категорій класифікатора
    CREATE TABLE categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        parent_code TEXT,
        level INTEGER NOT NULL,
        name TEXT NOT NULL,
        clean_name TEXT NOT NULL,
        path_codes TEXT NOT NULL,
        path_names TEXT NOT NULL,
        has_children BOOLEAN NOT NULL DEFAULT 0,
        children_count INTEGER NOT NULL DEFAULT 0,
        total_docs_count INTEGER NOT NULL DEFAULT 0,
        direct_docs_count INTEGER NOT NULL DEFAULT 0,
        branch_url TEXT,
        direct_url TEXT,
        cross_references TEXT,
        semantic_text TEXT NOT NULL,
        description TEXT,
        embedding BLOB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (parent_code) REFERENCES categories(code)
    );

    CREATE INDEX idx_categories_code ON categories(code);
    CREATE INDEX idx_categories_parent ON categories(parent_code);
    CREATE INDEX idx_categories_level ON categories(level);
    CREATE INDEX idx_categories_name ON categories(clean_name);

    -- Повнотекстовий пошук (FTS5) за кодами, назвами та ієрархічними шляхами
    CREATE VIRTUAL TABLE categories_fts USING fts5(
        code,
        name,
        clean_name,
        path_names,
        semantic_text,
        tokenize='unicode61'
    );

    -- Семантичні зв'язки між галузями права (знаннєвий граф)
    CREATE TABLE semantic_relations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_code TEXT NOT NULL,
        relation_type TEXT NOT NULL, -- 'see_also', 'subsumes', 'cross_domain', 'regulates'
        target_code TEXT NOT NULL,
        weight REAL DEFAULT 1.0,
        notes TEXT,
        FOREIGN KEY (source_code) REFERENCES categories(code),
        FOREIGN KEY (target_code) REFERENCES categories(code)
    );

    -- Схема для збереження нормативних актів (під майбутнє розширення)
    CREATE TABLE documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_code TEXT NOT NULL,
        rada_id TEXT,
        doc_number TEXT,
        doc_type TEXT,
        title TEXT NOT NULL,
        adoption_date DATE,
        url TEXT,
        content_summary TEXT,
        embedding BLOB,
        FOREIGN KEY (category_code) REFERENCES categories(code)
    );

    -- Зручні представлення (Views)
    CREATE VIEW v_root_branches AS
    SELECT 
        code, 
        clean_name AS branch_name, 
        children_count, 
        total_docs_count, 
        direct_docs_count, 
        branch_url 
    FROM categories 
    WHERE level = 1 
    ORDER BY CAST(code AS INTEGER);

    CREATE VIEW v_stats AS
    SELECT 
        level,
        COUNT(*) AS categories_count,
        SUM(total_docs_count) AS total_docs,
        SUM(direct_docs_count) AS direct_docs
    FROM categories
    GROUP BY level;
    """)

    for it in flat_items:
        cur.execute("""
        INSERT INTO categories (
            code, parent_code, level, name, clean_name,
            path_codes, path_names, has_children, children_count,
            total_docs_count, direct_docs_count, branch_url, direct_url,
            cross_references, semantic_text
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            it['code'],
            it['parent_code'],
            it['level'],
            it['name'],
            it['clean_name'],
            " / ".join(it['path_codes']),
            " / ".join(it['path_names']),
            1 if it['has_children'] else 0,
            it['children_count'],
            it['total_docs_count'],
            it['direct_docs_count'],
            it['branch_url'],
            it['direct_url'],
            json.dumps(it['cross_references'], ensure_ascii=False),
            it['semantic_text']
        ))

        # Додаємо у FTS5 індекс
        cur.execute("""
        INSERT INTO categories_fts (
            code, name, clean_name, path_names, semantic_text
        ) VALUES (?, ?, ?, ?, ?)
        """, (
            it['code'],
            it['name'],
            it['clean_name'],
            " / ".join(it['path_names']),
            it['semantic_text']
        ))

        # Якщо є перехресні посилання (див. ...), заносимо у таблицю семантичних зв'язків
        for ref in it['cross_references']:
            cur.execute("""
            INSERT INTO semantic_relations (source_code, relation_type, target_code, notes)
            VALUES (?, 'see_also', ?, 'Офіційне перехресне посилання у рубрикаторі ВРУ')
            """, (it['code'], ref))

    conn.commit()
    conn.close()

    print(f"[+] SQLite експортовано: {db_path} ({os.path.getsize(db_path):,} байт)")


def export_markdown(flat_items: list[dict], nested_tree: list[dict]):
    """Експорт у красивий Markdown з переліком галузей, статистикою та повним деревом."""
    md_path = os.path.join(DATA_DIR, "classifier.md")
    
    total_cats = len(flat_items)
    level_counts = Counter(it['level'] for it in flat_items)
    total_docs_level1 = sum(root['total_docs_count'] for root in nested_tree)
    
    lines = []
    lines.append("# Єдиний класифікатор правових актів України (Юридична класифікація ВРУ)")
    lines.append("")
    lines.append("> Офіційний рубрикатор нормативно-правових актів порталу «Законодавство України» Верховної Ради України.")
    lines.append("> Джерело: [zakon.rada.gov.ua/laws/main/klas](https://zakon.rada.gov.ua/laws/main/klas)")
    lines.append(f"> Дата збору даних: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`")
    lines.append("")
    
    lines.append("## Загальна статистика класифікатора")
    lines.append("")
    lines.append("| Метрика | Значення | Опис |")
    lines.append("|---|---|---|")
    lines.append(f"| **Всього категорій** | `{total_cats:,}` | Всі вузли класифікатора (1-4 рівні) |")
    lines.append(f"| **Головних галузей (Рівень 1)** | `{level_counts[1]}` | Основні розділи системи права |")
    lines.append(f"| **Підрозділів (Рівень 2)** | `{level_counts[2]}` | Галузеві підгрупи актів |")
    lines.append(f"| **Рубрик (Рівень 3)** | `{level_counts[3]}` | Предметні рубрики законодавства |")
    lines.append(f"| **Детальних рубрик (Рівень 4)** | `{level_counts[4]}` | Спеціалізовані підтеми |")
    lines.append(f"| **Сумарна кількість документів у гілках** | `{total_docs_level1:,}` | Загальний обсяг облікованих актів |")
    lines.append("")
    
    lines.append("## Зміст головних галузей права (Рівень 1)")
    lines.append("")
    lines.append("| Код | Галузь права | Кількість підкатегорій | Всього актів у гілці | Прямих актів | Посилання |")
    lines.append("|---|---|:---:|:---:|:---:|---|")
    for root in nested_tree:
        direct_str = f"[{root['direct_docs_count']}]({root['direct_url']})" if root['direct_url'] else f"{root['direct_docs_count']}"
        branch_link = f"[{root['clean_name']}]({root['branch_url']})" if root['branch_url'] else root['clean_name']
        lines.append(f"| `{root['code']}` | {branch_link} | {len(root['children'])} | **{root['total_docs_count']:,}** | {direct_str} | [Всі акти]({root['branch_url']}) |")
    lines.append("")
    
    lines.append("---")
    lines.append("")
    lines.append("## Повне ієрархічне дерево класифікатора")
    lines.append("")

    def render_node(node: dict, indent: int):
        prefix = "  " * indent
        code_str = f"`{node['code']}`"
        
        # Посилання на назву
        if node['branch_url']:
            name_str = f"[{node['clean_name']}]({node['branch_url']})"
        else:
            name_str = f"**{node['clean_name']}**"

        # Лічильники
        counts_part = []
        if node['total_docs_count'] > 0:
            if node['children'] and node['direct_docs_count'] != node['total_docs_count']:
                if node['direct_url']:
                    counts_part.append(f"*(всього: **{node['total_docs_count']}**, прямих: [{node['direct_docs_count']}]({node['direct_url']}))*")
                else:
                    counts_part.append(f"*(всього: **{node['total_docs_count']}**, прямих: {node['direct_docs_count']})*")
            else:
                counts_part.append(f"*(актів: **{node['total_docs_count']}**)*")
        else:
            counts_part.append("*(0 актів)*")

        counts_str = " " + counts_part[0] if counts_part else ""
        
        # Перехресні посилання
        refs_str = ""
        if node['cross_references']:
            refs_str = f" *(див. {', '.join(node['cross_references'])})*"

        lines.append(f"{prefix}- {code_str} {name_str}{counts_str}{refs_str}")
        for child in node['children']:
            render_node(child, indent + 1)

    for root in nested_tree:
        lines.append(f"### `{root['code']}` {root['clean_name']} *(Всього актів: {root['total_docs_count']:,})*")
        lines.append("")
        render_node(root, 0)
        lines.append("")

    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))

    print(f"[+] Markdown експортовано: {md_path} ({os.path.getsize(md_path):,} байт)")


def main():
    print("=" * 65)
    print("Парсер та генератор бази даних класифікатора законодавства ВРУ")
    print("=" * 65)
    
    html = fetch_html()
    flat_items = parse_classifier(html)
    nested_tree = build_nested_tree(flat_items)

    print("\n--- Експорт файлів ---")
    export_json(flat_items, nested_tree)
    export_csv(flat_items)
    export_sqlite(flat_items)
    export_markdown(flat_items, nested_tree)

    print("\n" + "=" * 65)
    print("Усі формати успішно згенеровано у папку: data/")
    print("=" * 65)


if __name__ == "__main__":
    main()
