# Проєкт

## Мета
Побудувати семантичну базу правових актів і судової практики України:
1. Класифікатор правових актів ВРУ (zakon.rada.gov.ua/laws/main/klas): 1043 вузли, 4 рівні. Готові дані й веб-інтерфейс (див. [README](../README.md)).
2. Огляди судової практики Верховного Суду (ККС, КЦС, КГС, КАС, ЄСПЛ, ВП тощо) розбиваються на сегменти й мапляться до рубрик класифікатора (див. [MAPPING_PLAN](../MAPPING_PLAN.md)).

## Пайплайн оглядів
`documents/pdfs/*.pdf` → `documents/markdown/<Назва>/<Назва>.md` → `documents/segments/<Назва>/` (сегменти) → мапінг до категорій.

## Сегмент
Один абзац судової позиції + посилання на постанову. Формат і правила: [conventions.md](conventions.md).

## Ключові файли
- `parse_classifier.py`, `semantic_db.py`, `server.py`, `smart_mapper.py`, `verify_results.py`
- `data/classifier.sqlite`: БД класифікатора з FTS5
- `documents/markdown/Oglyad_KKS_2024/Oglyad_KKS_2024.md`: огляд ККС ВС 2024, зараз у ручній нормалізації

## Поточний фокус
Нормалізація `Oglyad_KKS_2024.md`: «один абзац = один сегмент» (розділи 4–8 оброблено, див. [progress.md](progress.md)).
