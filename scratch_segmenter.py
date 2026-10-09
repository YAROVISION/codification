import re, sys

with open('documents/markdown/Oglyad_KKS_04_2026/Oglyad_KKS_04_2026.md', 'r', encoding='utf-8', errors='surrogateescape') as f:
    raw = f.read()

cleaned = re.sub(r'
\s*\d+\s*
\s*Огляд судової практики ККС ВС\s*
', '
', raw)
print('Cleaned length:', len(cleaned))
