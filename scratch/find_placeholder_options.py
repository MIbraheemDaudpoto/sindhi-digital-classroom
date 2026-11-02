import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('data/sdc_platform.db')
print('In questions table:')
for r in conn.execute("SELECT id, lesson_id, status, text_sindhi, options_json FROM questions WHERE options_json LIKE '%ٻيو آپشن%'").fetchall():
    print(r)

print('\nIn quiz_sessions table:')
for r in conn.execute("SELECT id, user_id, class_level, subject, mode, questions_snapshot_json FROM quiz_sessions WHERE questions_snapshot_json LIKE '%ٻيو آپشن%'").fetchall():
    print(r[:5])
