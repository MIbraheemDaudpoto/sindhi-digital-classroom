import sys, os
sys.path.insert(0, ".")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from src.services.sdc_rag_db import get_db_connection
conn = get_db_connection()
r = conn.execute("SELECT * FROM sdc_glossary WHERE term_en LIKE ?", ('%lever%',)).fetchone()
print("Term EN:", r['term_en'])
print("Term SD:", r['term_sd'])
print("Def SD:", r['definition_sd'])
print("Citation:", r['citation_formatted'])
