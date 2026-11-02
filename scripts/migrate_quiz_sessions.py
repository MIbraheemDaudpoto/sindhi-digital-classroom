import sqlite3

def migrate():
    con = sqlite3.connect('data/sdc_platform.db')
    con.execute('''
    CREATE TABLE IF NOT EXISTS quiz_sessions (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        class_level INTEGER NOT NULL,
        subject TEXT NOT NULL,
        lesson_ids_json TEXT NOT NULL,
        mode TEXT DEFAULT 'practice',
        difficulty TEXT DEFAULT 'MEDIUM',
        total_questions INTEGER NOT NULL,
        questions_snapshot_json TEXT NOT NULL,
        provider_used TEXT NOT NULL,
        is_live_ai INTEGER DEFAULT 0,
        status TEXT DEFAULT 'IN_PROGRESS',
        score REAL DEFAULT NULL,
        max_score REAL DEFAULT NULL,
        percentage REAL DEFAULT NULL,
        answers_json TEXT DEFAULT '{}',
        created_at TEXT NOT NULL,
        submitted_at TEXT DEFAULT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    ''')
    con.execute('CREATE INDEX IF NOT EXISTS idx_quiz_sessions_user ON quiz_sessions(user_id, status);')
    con.execute('CREATE INDEX IF NOT EXISTS idx_quiz_sessions_created ON quiz_sessions(created_at);')
    con.commit()
    tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    print('quiz_sessions created successfully:', 'quiz_sessions' in tables)
    con.close()

if __name__ == '__main__':
    migrate()

