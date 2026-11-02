import sqlite3

con = sqlite3.connect('data/sdc_platform.db')
con.row_factory = sqlite3.Row
rows = con.execute('SELECT * FROM progress').fetchall()
print(f'Total progress rows: {len(rows)}')
for r in rows:
    print(dict(r))
con.close()

