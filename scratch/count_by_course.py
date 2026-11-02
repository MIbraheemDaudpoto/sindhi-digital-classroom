import sqlite3
conn = sqlite3.connect('data/sdc_platform.db')
for r in conn.execute('SELECT c.id, c.subject, c.class_level, count(q.id) FROM courses c LEFT JOIN lessons l ON l.course_id = c.id LEFT JOIN questions q ON q.lesson_id = l.id AND q.status = "APPROVED" GROUP BY c.id').fetchall():
    print(r)

