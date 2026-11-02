import sqlite3
import json
import random
import re

conn = sqlite3.connect('data/sdc_platform.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Test generating 5 questions for Science Unit 1 (lesson-sci-6-1)
unit_num = 1
subj_filter = "science-6"

gloss_rows = cur.execute('SELECT * FROM sdc_glossary WHERE subject_id = ?', (subj_filter,)).fetchall()
all_gloss = [dict(r) for r in gloss_rows]
unit_gloss = [g for g in all_gloss if g.get('chapter_id') == unit_num]
other_gloss = [g for g in all_gloss if g.get('chapter_id') != unit_num]

chunk_rows = cur.execute('SELECT * FROM sdc_chunks WHERE subject_id = ?', (subj_filter,)).fetchall()
all_chunks = [dict(r) for r in chunk_rows]
unit_chunks = [c for c in all_chunks if c.get('chapter_id') == unit_num]
other_chunks = [c for c in all_chunks if c.get('chapter_id') != unit_num]

generated = []

# 1. Glossary questions
for g in unit_gloss[:3]:
    term = g['term_sd']
    defn = g['definition_sd']
    distractors = [x['term_sd'] for x in random.sample(other_gloss + [x for x in unit_gloss if x['id'] != g['id']], 3)]
    opts = [term] + distractors
    random.shuffle(opts)
    generated.append({
        'type': 'glossary_definition',
        'question': f"'{defn}' هيٺين مان ڪنهن جي تعريف آهي؟",
        'options': opts,
        'correct': term,
        'citation': g.get('citation_formatted', 'STBB Science Class 6')
    })

# 2. Chunk questions
for c in unit_chunks[:2]:
    topic = c['topic_title_sd']
    summary = c['summary_sd']
    sents = [s.strip() for s in re.split(r"[۔\.\n]+", summary) if len(s.strip()) > 15]
    if sents:
        correct_sent = sents[0]
        # Distractors from other chunks
        distractor_sents = []
        sampled_chunks = random.sample(other_chunks, 3)
        for sc in sampled_chunks:
            sc_sents = [s.strip() for s in re.split(r"[۔\.\n]+", sc['summary_sd']) if len(s.strip()) > 15]
            if sc_sents:
                distractor_sents.append(sc_sents[0])
            else:
                distractor_sents.append(f"هي عمل صرف {sc['topic_title_sd']} سان واسطو رکي ٿو۔")
        
        opts = [correct_sent] + distractor_sents[:3]
        random.shuffle(opts)
        generated.append({
            'type': 'topic_fact',
            'question': f"موضوع '{topic}' بابت درسي ڪتاب مطابق ڪهڙو بيان درست آهي؟",
            'options': opts,
            'correct': correct_sent,
            'citation': c.get('citation_formatted', 'STBB Science Class 6')
        })

with open('scratch/test_generated_mcqs.json', 'w', encoding='utf-8') as f:
    json.dump(generated, f, ensure_ascii=False, indent=2)

print(f"Generated {len(generated)} high quality questions!")
