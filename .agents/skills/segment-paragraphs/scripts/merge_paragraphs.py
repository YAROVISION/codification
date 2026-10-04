#!/usr/bin/env python3
"""Злиття блоку (абзац + посилання на постанову) в один рядок у markdown-файлі огляду.

Файл може містити некоректні UTF-8 байти, тому читаємо/пишемо з
errors='surrogateescape' і newline='' (байти і закінчення рядків не змінюються).

Використання:
  merge_paragraphs.py FILE --anchor "Початок першого рядка абзацу" \
      [--prefix "Розділ. Підрозділ. "] [--new-segment "5.2 | 5. Назва розділу"] [--dry-run]

Блок починається з першого рядка, що починається з --anchor, і закінчується
першим наступним рядком, який містить 'reyestr.court.gov.ua'.
Усі непорожні рядки блоку зливаються в один через пробіл.
--prefix додається на початок абзацу (заголовки через крапку).
--new-segment вставляє перед абзацом мітку <!-- === SEGMENT: ... === --> і порожній рядок.
"""
import argparse
import sys

CITATION_MARK = "reyestr.court.gov.ua"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--anchor", required=True, help="початок першого рядка блоку")
    ap.add_argument("--prefix", default="", help="префікс (заголовки через крапку)")
    ap.add_argument("--new-segment", default="", help='напр. "5.2 | 5. Повідомлення"')
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    text = open(a.file, encoding="utf-8", errors="surrogateescape", newline="").read()
    lines = text.split("\n")

    starts = [k for k, l in enumerate(lines) if l.startswith(a.anchor)]
    if not starts:
        print("ПОМИЛКА: anchor не знайдено", file=sys.stderr)
        return 1
    if len(starts) > 1:
        print(f"ПОПЕРЕДЖЕННЯ: anchor знайдено {len(starts)} разів, беру перший (рядок {starts[0]+1})")
    s = starts[0]
    e = next((k for k in range(s, len(lines)) if CITATION_MARK in lines[k]), None)
    if e is None or e - s > 40:
        print("ПОМИЛКА: не знайдено посилання reyestr у межах 40 рядків", file=sys.stderr)
        return 1

    merged = a.prefix + " ".join(l.strip() for l in lines[s : e + 1] if l.strip())
    repl = [merged]
    if a.new_segment:
        repl = [f"<!-- === SEGMENT: {a.new_segment} === -->", "", merged]

    print(f"Рядки {s+1}-{e+1} -> {len(repl)} рядків")
    print(merged[:200])
    if a.dry_run:
        return 0
    lines[s : e + 1] = repl
    open(a.file, "w", encoding="utf-8", errors="surrogateescape", newline="").write("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
