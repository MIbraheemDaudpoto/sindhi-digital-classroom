import sys
sys.path.insert(0, '.')
from src.services.sdc_rag_service import get_sdc_rag_service

svc = get_sdc_rag_service()
results = svc.search_chunks('سيٽ')
print('Direct search results count:', len(results))
for r in results[:3]:
    print('Chunk:', r.chunk_id, 'Subject:', r.subject_id, 'Chapter:', r.chapter_id, 'Topic:', r.topic)

