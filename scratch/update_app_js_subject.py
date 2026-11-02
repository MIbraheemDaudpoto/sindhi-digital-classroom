import re

file_path = "static/js/app.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update handleIntegratedSearch to include subject_id
old_search_block = """  try {
    let url = `/api/sdc/search?q=${encodeURIComponent(query)}`;
    if (intSelectedChapter) url += `&chapter_id=${intSelectedChapter}`;
    const res = await fetch(url);
    if (res.ok) {
      const data = await res.json();
      renderIntSearchResults(data.chunks || []);
    }

    // Also trigger Grounded RAG Ask
    await handleIntRAGAsk(query);
  }"""

new_search_block = """  try {
    const curSub = (window.activeCourse && window.activeCourse.subject) || 
                   (window.currentLesson && window.currentLesson.course_id && window.currentLesson.course_id.includes('math') ? 'math' : null) ||
                   (window.currentLesson && window.currentLesson.course_id && window.currentLesson.course_id.includes('sci') ? 'science' : null);

    let url = `/api/sdc/search?q=${encodeURIComponent(query)}`;
    if (intSelectedChapter) url += `&chapter_id=${intSelectedChapter}`;
    if (curSub) url += `&subject_id=${encodeURIComponent(curSub)}`;
    const res = await fetch(url);
    if (res.ok) {
      const data = await res.json();
      renderIntSearchResults(data.chunks || []);
    }

    // Also trigger Grounded RAG Ask
    await handleIntRAGAsk(query);
  }"""

old_search_block_crlf = old_search_block.replace("\n", "\r\n")
new_search_block_crlf = new_search_block.replace("\n", "\r\n")

if old_search_block_crlf in content:
    content = content.replace(old_search_block_crlf, new_search_block_crlf, 1)
    print("Replaced handleIntegratedSearch block")
elif old_search_block in content:
    content = content.replace(old_search_block, new_search_block, 1)
    print("Replaced handleIntegratedSearch block (LF)")
else:
    print("Could not find handleIntegratedSearch block!")

# 2. Update handleIntRAGAsk payload
old_ask_block = """    const res = await fetch('/api/sdc/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: query, chapter_id: intSelectedChapter })
    });"""

new_ask_block = """    const curSub = (window.activeCourse && window.activeCourse.subject) || 
                   (window.currentLesson && window.currentLesson.course_id && window.currentLesson.course_id.includes('math') ? 'math' : null) ||
                   (window.currentLesson && window.currentLesson.course_id && window.currentLesson.course_id.includes('sci') ? 'science' : null);

    const payload = { query: query, chapter_id: intSelectedChapter };
    if (curSub) payload.subject_id = curSub;

    const res = await fetch('/api/sdc/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });"""

old_ask_block_crlf = old_ask_block.replace("\n", "\r\n")
new_ask_block_crlf = new_ask_block.replace("\n", "\r\n")

if old_ask_block_crlf in content:
    content = content.replace(old_ask_block_crlf, new_ask_block_crlf, 1)
    print("Replaced handleIntRAGAsk block")
elif old_ask_block in content:
    content = content.replace(old_ask_block, new_ask_block, 1)
    print("Replaced handleIntRAGAsk block (LF)")
else:
    print("Could not find handleIntRAGAsk block!")

# 3. Update loadIntegratedGlossary url
old_gloss_block = """  let url = '/api/sdc/glossary?limit=205';
  if (intSelectedChapter) url += `&chapter_id=${intSelectedChapter}`;
  if (letter) url += `&letter=${encodeURIComponent(letter)}`;"""

new_gloss_block = """  const curSub = (window.activeCourse && window.activeCourse.subject) || 
                 (window.currentLesson && window.currentLesson.course_id && window.currentLesson.course_id.includes('math') ? 'math' : null) ||
                 (window.currentLesson && window.currentLesson.course_id && window.currentLesson.course_id.includes('sci') ? 'science' : null);

  let url = '/api/sdc/glossary?limit=205';
  if (intSelectedChapter) url += `&chapter_id=${intSelectedChapter}`;
  if (curSub) url += `&subject_id=${encodeURIComponent(curSub)}`;
  if (letter) url += `&letter=${encodeURIComponent(letter)}`;"""

old_gloss_block_crlf = old_gloss_block.replace("\n", "\r\n")
new_gloss_block_crlf = new_gloss_block.replace("\n", "\r\n")

if old_gloss_block_crlf in content:
    content = content.replace(old_gloss_block_crlf, new_gloss_block_crlf, 1)
    print("Replaced loadIntegratedGlossary block")
elif old_gloss_block in content:
    content = content.replace(old_gloss_block, new_gloss_block, 1)
    print("Replaced loadIntegratedGlossary block (LF)")
else:
    print("Could not find loadIntegratedGlossary block!")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Finished updating app.js")

