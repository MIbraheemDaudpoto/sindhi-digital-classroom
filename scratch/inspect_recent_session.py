import sys, sqlite3, json
sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('data/sdc_platform.db')
r = conn.execute("SELECT questions_snapshot_json FROM quiz_sessions WHERE id='qz-sess-bca261405b5d'").fetchone()
if r:
    qs = json.loads(r[0])
    print(f"Total questions in session: {len(qs)}")
    for i, q in enumerate(qs):
        print(f"\nQ{i+1}: {q['text_sindhi']}")
        print(f"  Options: {q['options']}")
        print(f"  Correct: {q['correct_answer_index']}")
