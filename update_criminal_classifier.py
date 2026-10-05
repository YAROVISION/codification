"""
Оновлення категорії 250 'Кримінальне законодавство' на нову структуру:
1. Кримінальний кодекс України (Загальна та Особлива частини за розділами)
2. Кримінальний процесуальний кодекс України (за розділами)

Генерація точних прямих посилань на zakon.rada.gov.ua та пошукових URL для ВРУ.
Оновлення всіх форматів даних:
- data/classifier.json
- data/classifier_flat.json
- data/classifier.sqlite (categories, categories_fts)
- data/classifier.csv
- data/classifier.md
"""

import os
import sys
import json
import csv
import sqlite3
import urllib.parse
from datetime import datetime

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

def make_search_url(query: str) -> str:
    encoded = urllib.parse.quote(query)
    return f"https://zakon.rada.gov.ua/laws/main/find?find_text={encoded}"

def build_criminal_tree():
    # 250 10: Кримінальний кодекс України
    kk_gen_sections = [
        ("250 10 10 10", "Розділ I. Загальні положення", "https://zakon.rada.gov.ua/laws/show/2341-14#n10", "Кримінальний кодекс загальні положення"),
        ("250 10 10 20", "Розділ II. Закон про кримінальну відповідальність", "https://zakon.rada.gov.ua/laws/show/2341-14#n21", "закон про кримінальну відповідальність чинність"),
        ("250 10 10 30", "Розділ III. Кримінальне правопорушення, його види та стадії", "https://zakon.rada.gov.ua/laws/show/2341-14#n49", "кримінальне правопорушення стадії готування замах"),
        ("250 10 10 40", "Розділ IV. Особа, яка підлягає кримінальній відповідальності (суб’єкт кримінального правопорушення)", "https://zakon.rada.gov.ua/laws/show/2341-14#n79", "суб'єкт кримінального правопорушення неосудність"),
        ("250 10 10 50", "Розділ V. Вина та її форми", "https://zakon.rada.gov.ua/laws/show/2341-14#n98", "вина умисел необережність кримінальний"),
        ("250 10 10 60", "Розділ VI. Співучасть у кримінальному правопорушенні", "https://zakon.rada.gov.ua/laws/show/2341-14#n108", "співучасть організатор виконавець пособник"),
        ("250 10 10 70", "Розділ VII. Повторність, сукупність та рецидив кримінальних правопорушень", "https://zakon.rada.gov.ua/laws/show/2341-14#n125", "повторність сукупність рецидив"),
        ("250 10 10 80", "Розділ VIII. Обставини, що виключають кримінальну протиправність діяння", "https://zakon.rada.gov.ua/laws/show/2341-14#n142", "необхідна оборона крайня необхідність затримання"),
        ("250 10 10 90", "Розділ IX. Звільнення від кримінальної відповідальності", "https://zakon.rada.gov.ua/laws/show/2341-14#n187", "звільнення від кримінальної відповідальності давність"),
        ("250 10 10 100", "Розділ X. Покарання та його види", "https://zakon.rada.gov.ua/laws/show/2341-14#n211", "покарання види штраф позбавлення волі"),
        ("250 10 10 110", "Розділ XI. Призначення покарання", "https://zakon.rada.gov.ua/laws/show/2341-14#n302", "призначення покарання пом'якшуючі обтяжуючі"),
        ("250 10 10 120", "Розділ XII. Звільнення від покарання та його відбування", "https://zakon.rada.gov.ua/laws/show/2341-14#n341", "звільнення від покарання іспитовий строк умовно-дострокове"),
        ("250 10 10 130", "Розділ XIII. Судимість", "https://zakon.rada.gov.ua/laws/show/2341-14#n389", "судимість погашення зняття"),
        ("250 10 10 140", "Розділ XIV. Інші заходи кримінально-правового характеру", "https://zakon.rada.gov.ua/laws/show/2341-14#n407", "примусові заходи медичного характеру спецконфіскація"),
        ("250 10 10 150", "Розділ XIV-1. Заходи кримінально-правового характеру щодо юридичних осіб", "https://zakon.rada.gov.ua/laws/show/2341-14#n431", "заходи щодо юридичних осіб кримінальний кодекс"),
        ("250 10 10 160", "Розділ XV. Особливості кримінальної відповідальності та покарання неповнолітніх", "https://zakon.rada.gov.ua/laws/show/2341-14#n452", "відповідальність покарання неповнолітніх кримінальний"),
        ("250 10 10 170", "Розділ XVI. Прикінцеві та перехідні положення", "https://zakon.rada.gov.ua/laws/show/2341-14#n503", "кримінальний кодекс прикінцеві перехідні положення")
    ]

    kk_spec_sections = [
        ("250 10 20 10", "Розділ I. Кримінальні правопорушення проти основ національної безпеки України", "https://zakon.rada.gov.ua/laws/show/2341-14#n516", "державна зрада диверсія колабораційна діяльність"),
        ("250 10 20 20", "Розділ II. Кримінальні правопорушення проти життя та здоров'я особи", "https://zakon.rada.gov.ua/laws/show/2341-14#n558", "вбивство тілесні ушкодження ненадання допомоги"),
        ("250 10 20 30", "Розділ III. Кримінальні правопорушення проти волі, честі та гідності особи", "https://zakon.rada.gov.ua/laws/show/2341-14#n678", "незаконне позбавлення волі викрадення торгівля людьми"),
        ("250 10 20 40", "Розділ IV. Кримінальні правопорушення проти статевої свободи та статевої недоторканості особи", "https://zakon.rada.gov.ua/laws/show/2341-14#n705", "зґвалтування сексуальне насильство розбещення"),
        ("250 10 20 50", "Розділ V. Кримінальні правопорушення проти виборчих, трудових та інших особистих прав і свобод людини і громадянина", "https://zakon.rada.gov.ua/laws/show/2341-14#n736", "порушення виборчих прав порушення трудових прав недоторканність житла"),
        ("250 10 20 60", "Розділ VI. Кримінальні правопорушення проти власності", "https://zakon.rada.gov.ua/laws/show/2341-14#n826", "крадіжка грабіж розбій вимагання шахрайство привласнення"),
        ("250 10 20 70", "Розділ VII. Кримінальні правопорушення у сфері господарської діяльності", "https://zakon.rada.gov.ua/laws/show/2341-14#n883", "легалізація доходів ухилення від сплати податків контрабанда"),
        ("250 10 20 80", "Розділ VIII. Кримінальні правопорушення проти довкілля", "https://zakon.rada.gov.ua/laws/show/2341-14#n1049", "забруднення довкілля незаконна порубка лісу браконьєрство"),
        ("250 10 20 90", "Розділ IX. Кримінальні правопорушення проти громадської безпеки", "https://zakon.rada.gov.ua/laws/show/2341-14#n1134", "терористичний акт створення злочинної організації зброя"),
        ("250 10 20 100", "Розділ X. Кримінальні правопорушення проти безпеки виробництва", "https://zakon.rada.gov.ua/laws/show/2341-14#n1215", "порушення правил безпеки на вибухонебезпечних виробництві"),
        ("250 10 20 110", "Розділ XI. Кримінальні правопорушення проти безпеки руху та експлуатації транспорту", "https://zakon.rada.gov.ua/laws/show/2341-14#n1236", "дтп керування у стані сп'яніння порушення правил руху"),
        ("250 10 20 120", "Розділ XII. Кримінальні правопорушення проти громадського порядку та моральності", "https://zakon.rada.gov.ua/laws/show/2341-14#n1303", "хуліганство наруга порнографія жорстоке поводження"),
        ("250 10 20 130", "Розділ XIII. Кримінальні правопорушення у сфері обігу наркотичних засобів, психотропних речовин, їх аналогів або прекурсорів та інші кримінальні правопорушення проти здоров'я населення", "https://zakon.rada.gov.ua/laws/show/2341-14#n1356", "наркотичні засоби збут зберігання психотропні отруйні речовини"),
        ("250 10 20 140", "Розділ XIV. Кримінальні правопорушення у сфері охорони державної таємниці, недоторканності державних кордонів, забезпечення призову та мобілізації", "https://zakon.rada.gov.ua/laws/show/2341-14#n1457", "державна таємниця ухилення від мобілізації призову кордон"),
        ("250 10 20 150", "Розділ XV. Кримінальні правопорушення проти авторитету органів державної влади, органів місцевого самоврядування, об'єднань громадян та кримінальні правопорушення проти журналістів", "https://zakon.rada.gov.ua/laws/show/2341-14#n1500", "опір працівникові правоохоронного органу журналіст підроблення документів"),
        ("250 10 20 160", "Розділ XVI. Кримінальні правопорушення у сфері використання електронно-обчислювальних машин (комп'ютерів), систем та комп'ютерних мереж і мереж електрозв'язку", "https://zakon.rada.gov.ua/laws/show/2341-14#n1576", "несанкціоноване втручання шкідливі програми кіберзлочини"),
        ("250 10 20 170", "Розділ XVII. Кримінальні правопорушення у сфері службової діяльності та професійної діяльності, пов'язаної з наданням публічних послуг", "https://zakon.rada.gov.ua/laws/show/2341-14#n1597", "зловживання владою неправомірна вигода хабарництво службова недбалість"),
        ("250 10 20 180", "Розділ XVIII. Кримінальні правопорушення проти правосуддя", "https://zakon.rada.gov.ua/laws/show/2341-14#n1653", "неправосудне рішення завідомо неправдиві показання невиконання судового рішення"),
        ("250 10 20 190", "Розділ XIX. Кримінальні правопорушення проти встановленого порядку несення військової служби (військові кримінальні правопорушення)", "https://zakon.rada.gov.ua/laws/show/2341-14#n1746", "непокора самовільне залишення частини сзч дезертирство мародерство"),
        ("250 10 20 200", "Розділ XX. Кримінальні правопорушення проти миру, безпеки людства та міжнародного правопорядку", "https://zakon.rada.gov.ua/laws/show/2341-14#n1879", "агресія воєнні злочини екоцид найманство геноцид")
    ]

    # 250 20: Кримінальний процесуальний кодекс України
    kpk_sections = [
        ("250 20 10", "Розділ I. Загальні положення", "https://zakon.rada.gov.ua/laws/show/4651-17#n11", "кримінальний процесуальний кодекс засади мова докази"),
        ("250 20 20", "Розділ II. Заходи забезпечення кримінального провадження", "https://zakon.rada.gov.ua/laws/show/4651-17#n578", "запобіжні заходи тримання під вартою арешт майна застава тимчасовий доступ"),
        ("250 20 30", "Розділ III. Досудове розслідування", "https://zakon.rada.gov.ua/laws/show/4651-17#n1077", "досудове розслідування єрдр підозра обшук нсрд слідчі дії"),
        ("250 20 40", "Розділ IV. Судове провадження у першій інстанції", "https://zakon.rada.gov.ua/laws/show/4651-17#n1753", "підготовче судове засідання судовий розгляд вирок"),
        ("250 20 50", "Розділ V. Судове провадження з перегляду судових рішень", "https://zakon.rada.gov.ua/laws/show/4651-17#n2169", "апеляційне касаційне провадження нововиявлені обставини верховний суд"),
        ("250 20 60", "Розділ VI. Особливі порядки кримінального провадження", "https://zakon.rada.gov.ua/laws/show/4651-17#n2652", "угоди про визнання винуватості примирення щодо неповнолітніх медичні заходи in absentia"),
        ("250 20 70", "Розділ VII. Виконання судових рішень", "https://zakon.rada.gov.ua/laws/show/4651-17#n2976", "набрання вироком законної сили виконання судове рішення"),
        ("250 20 80", "Розділ VIII. Міжнародне співробітництво під час кримінального провадження", "https://zakon.rada.gov.ua/laws/show/4651-17#n3041", "екстрадиція міжнародна правова допомога перейняття кримінального переслідування"),
        ("250 20 90", "Розділ IX-1. Особливий режим досудового розслідування, судового розгляду в умовах воєнного стану", "https://zakon.rada.gov.ua/laws/show/4651-17#n3464", "особливий режим воєнний стан стаття 615 кпк"),
        ("250 20 100", "Розділ X. Прикінцеві положення", "https://zakon.rada.gov.ua/laws/show/4651-17#n3487", "кпк прикінцеві положення введення в дію"),
        ("250 20 110", "Розділ XI. Перехідні положення", "https://zakon.rada.gov.ua/laws/show/4651-17#n3507", "кпк перехідні положення")
    ]

    def build_node(code, name, direct_url, search_query, level, children=None):
        return {
            "code": code,
            "level": level,
            "name": name,
            "clean_name": name,
            "cross_references": [],
            "branch_url": make_search_url(search_query),
            "direct_url": direct_url,
            "total_docs_count": 0,
            "direct_docs_count": 0,
            "children": children or []
        }

    # Побудова гілки КК України
    kk_gen_children = [
        build_node(c, n, d, q, 4) for c, n, d, q in kk_gen_sections
    ]
    kk_spec_children = [
        build_node(c, n, d, q, 4) for c, n, d, q in kk_spec_sections
    ]

    kk_gen_node = build_node(
        "250 10 10",
        "Загальна частина",
        "https://zakon.rada.gov.ua/laws/show/2341-14#n9",
        "Кримінальний кодекс України Загальна частина",
        3,
        kk_gen_children
    )

    kk_spec_node = build_node(
        "250 10 20",
        "Особлива частина",
        "https://zakon.rada.gov.ua/laws/show/2341-14#n515",
        "Кримінальний кодекс України Особлива частина",
        3,
        kk_spec_children
    )

    kk_root = build_node(
        "250 10",
        "Кримінальний кодекс України",
        "https://zakon.rada.gov.ua/laws/show/2341-14",
        "Кримінальний кодекс України",
        2,
        [kk_gen_node, kk_spec_node]
    )

    # Побудова гілки КПК України
    kpk_children = [
        build_node(c, n, d, q, 3) for c, n, d, q in kpk_sections
    ]

    kpk_root = build_node(
        "250 20",
        "Кримінальний процесуальний кодекс України",
        "https://zakon.rada.gov.ua/laws/show/4651-17",
        "Кримінальний процесуальний кодекс України",
        2,
        kpk_children
    )

    # Головний вузол 250
    node_250 = build_node(
        "250",
        "Кримінальне законодавство",
        "https://zakon.rada.gov.ua/laws/show/2341-14",
        "кримінальне законодавство кодекс кримінальний процес",
        1,
        [kk_root, kpk_root]
    )

    return node_250

def flatten_tree(nodes, parent_code=None, path_codes=None, path_names=None):
    flat = []
    for node in nodes:
        cur_path_codes = (path_codes or []) + [node["code"]]
        cur_path_names = (path_names or []) + [node["clean_name"]]
        
        item = {
            "code": node["code"],
            "level": node["level"],
            "name": node["name"],
            "clean_name": node["clean_name"],
            "parent_code": parent_code,
            "path_codes": " / ".join(cur_path_codes),
            "path_names": " / ".join(cur_path_names),
            "cross_references": node.get("cross_references", []),
            "branch_url": node.get("branch_url", ""),
            "direct_url": node.get("direct_url", ""),
            "total_docs_count": node.get("total_docs_count", 0),
            "direct_docs_count": node.get("direct_docs_count", 0),
            "has_children": len(node.get("children", [])) > 0,
            "children_count": len(node.get("children", []))
        }
        flat.append(item)
        if node.get("children"):
            flat.extend(flatten_tree(node["children"], node["code"], cur_path_codes, cur_path_names))
    return flat

def update_all():
    print("[*] Читаємо наявний classifier.json...")
    json_path = os.path.join(DATA_DIR, "classifier.json")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    tree = data.get("tree", [])
    
    # Знаходимо і замінюємо вузол 250
    new_250 = build_criminal_tree()
    
    found = False
    for i, root_node in enumerate(tree):
        if root_node.get("code") == "250":
            tree[i] = new_250
            found = True
            break
            
    if not found:
        tree.append(new_250)

    # Оновлюємо метадані
    flat_all = flatten_tree(tree)
    data["metadata"]["total_categories"] = len(flat_all)
    data["metadata"]["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"[+] Збереження classifier.json (всього рубрик: {len(flat_all)})...")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # classifier_flat.json
    flat_path = os.path.join(DATA_DIR, "classifier_flat.json")
    print(f"[+] Збереження classifier_flat.json...")
    with open(flat_path, "w", encoding="utf-8") as f:
        json.dump(flat_all, f, ensure_ascii=False, indent=2)

    # SQLite
    sqlite_path = os.path.join(DATA_DIR, "classifier.sqlite")
    print(f"[+] Оновлення SQLite бази: {sqlite_path}...")
    conn = sqlite3.connect(sqlite_path)
    cur = conn.cursor()

    cur.execute("DELETE FROM categories")
    cur.execute("DELETE FROM categories_fts")

    for item in flat_all:
        cur.execute("""
            INSERT INTO categories (
                code, level, name, clean_name, parent_code,
                path_codes, path_names, cross_references,
                branch_url, direct_url,
                total_docs_count, direct_docs_count,
                has_children, children_count, semantic_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item["code"],
            item["level"],
            item["name"],
            item["clean_name"],
            item["parent_code"],
            item["path_codes"],
            item["path_names"],
            json.dumps(item["cross_references"], ensure_ascii=False),
            item["branch_url"],
            item["direct_url"],
            item["total_docs_count"],
            item["direct_docs_count"],
            1 if item["has_children"] else 0,
            item["children_count"],
            f"{item['clean_name']}. Шлях: {item['path_names']}. Код: {item['code']}."
        ))

        # FTS5 index
        cur.execute("""
            INSERT INTO categories_fts (code, clean_name, path_names, semantic_text)
            VALUES (?, ?, ?, ?)
        """, (
            item["code"],
            item["clean_name"],
            item["path_names"],
            f"{item['clean_name']} {item['path_names']} {item['code']}"
        ))

    conn.commit()
    conn.close()

    # CSV
    csv_path = os.path.join(DATA_DIR, "classifier.csv")
    print(f"[+] Збереження classifier.csv...")
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Код", "Рівень", "Назва", "Очищена назва", "Батьківський код",
            "Ієрархічний код", "Ієрархічний шлях", "Всього актів", "Прямих актів",
            "URL гілки", "URL прямий"
        ])
        for it in flat_all:
            writer.writerow([
                it["code"], it["level"], it["name"], it["clean_name"], it["parent_code"],
                it["path_codes"], it["path_names"], it["total_docs_count"], it["direct_docs_count"],
                it["branch_url"], it["direct_url"]
            ])

    # Markdown
    md_path = os.path.join(DATA_DIR, "classifier.md")
    print(f"[+] Збереження classifier.md...")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Єдиний класифікатор правових актів України\n\n")
        f.write(f"- **Всього рубрик**: {len(flat_all):,}\n")
        f.write(f"- **Дата оновлення**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## Дерево класифікатора\n\n")
        for it in flat_all:
            indent = "  " * (it["level"] - 1)
            url = it["direct_url"] or it["branch_url"] or "#"
            f.write(f"{indent}- **`{it['code']}`** [{it['clean_name']}]({url})\n")

    print("[SUCCESS] Усі дані успішно синхронізовано та оновлено!")

if __name__ == "__main__":
    update_all()
