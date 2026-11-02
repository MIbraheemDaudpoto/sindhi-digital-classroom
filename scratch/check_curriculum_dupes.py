import json, sqlite3, re
from collections import Counter

conn = sqlite3.connect('data/sdc_platform.db')

# 1. Math exercises
with open('data/stbb_math_6_complete.json', 'r', encoding='utf-8') as f:
    math_data = json.load(f)
exs = math_data.get('exercises', [])
math_q = [re.sub(r'\s+', ' ', e['question_sd']).strip() for e in exs]
c_math = Counter(math_q)
print("Math exercises duplicates:")
for q, c in c_math.items():
    if c > 1:
        print(f"  [{c}x] {q}")

# 2. Questions table
q_rows = conn.execute("SELECT text_sindhi FROM questions").fetchall()
q_texts = [re.sub(r'\s+', ' ', r[0]).strip() for r in q_rows]
c_q = Counter(q_texts)
print("\nQuestions table duplicates:")
for q, c in c_q.items():
    if c > 1:
        print(f"  [{c}x] {q}")

# 3. Glossary terms
g_rows = conn.execute("SELECT term_sd, definition_sd FROM sdc_glossary").fetchall()
g_defs = [re.sub(r'\s+', ' ', r[1]).strip() for r in g_rows if r[1]]
c_g = Counter(g_defs)
print("\nGlossary definitions duplicates:")
for q, c in c_g.items():
    if c > 1:
        print(f"  [{c}x] {q}")

