import sqlite3, sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('data/sdc_platform.db')
conn.row_factory = sqlite3.Row

for ch in range(3, 13):
    chunks = conn.execute("SELECT topic_title_sd, topic_title_en, summary_sd, citation_formatted FROM sdc_chunks WHERE chapter_id = ? LIMIT 3", (ch,)).fetchall()
    gloss = conn.execute("SELECT term_sd, term_en, definition_sd FROM sdc_glossary WHERE chapter_id = ? LIMIT 3", (ch,)).fetchall()
    print(f"\n=== Science Chapter {ch} ===")
    for c in chunks:
        print(f"  Chunk: {c['topic_title_sd']} ({c['topic_title_en']})")
        print(f"    Summary: {c['summary_sd'][:120]}...")
    for g in gloss:
        print(f"  Glossary: {g['term_sd']} ({g['term_en']}) -> {g['definition_sd'][:80]}")

