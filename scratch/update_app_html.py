path = 'static/app.html'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

target = '''              <!-- Quick Topic Prompts Bar -->
              <div class="tutor-quick-prompts" style="display: flex; gap: 6px; overflow-x: auto; padding: 6px 0 8px; border-bottom: 1px solid var(--border-subtle); margin-bottom: 8px;">
                <button type="button" class="quick-prompt-pill" onclick="sdcTutor.askQuickPrompt('جيو گهرڙو ڇا آهي؟')">🔬 جيو گهرڙو</button>
                <button type="button" class="quick-prompt-pill" onclick="sdcTutor.askQuickPrompt('خوردبين جا مکيه حصا ڪهڙا آهن؟')">🔍 خوردبين</button>
                <button type="button" class="quick-prompt-pill" onclick="sdcTutor.askQuickPrompt('ٻوٽن ۾ فوٽوسنٿيسز جو عمل سمجهايو۔')">🌿 فوٽوسنٿيسز</button>
                <button type="button" class="quick-prompt-pill" onclick="sdcTutor.askQuickPrompt('اک جا مختلف حصا ڪهڙا آهن؟')">👁️ اک جا حصا</button>
                <button type="button" class="quick-prompt-pill" onclick="sdcTutor.askQuickPrompt('روشني جي رفتار ڇا آهي؟')">⚡ روشني جي رفتار</button>
              </div>

              <!-- Live Chat Message Stream -->
              <div id="tutor-chat-stream" class="chat-stream" role="log" aria-live="polite">
                <div class="chat-bubble tutor-bubble">
                  <div class="bubble-sender">🤖 سنڌي اي آءِ استاد (AI Tutor)</div>
                  <div>اسلام عليڪم! آءٌ اوهان جو سنڌي اي آءِ استاد آهيان. وڊيو ڏسندي يا پڙهندي سائنس بابت ڪوبه سوال هجي ته لکو يا مائڪ تي سنڌي ۾ ڳالهايو.</div>
                </div>
              </div>'''

replacement = '''              <!-- Quick Topic Prompts Bar -->
              <div class="tutor-quick-prompts" style="display: flex; gap: 6px; overflow-x: auto; padding: 6px 0 8px; border-bottom: 1px solid var(--border-subtle); margin-bottom: 8px;">
                <button type="button" class="quick-prompt-pill" onclick="sdcTutor.askQuickPrompt('جيو گهرڙو ڇا آهي؟')">🔬 جيو گهرڙو</button>
                <button type="button" class="quick-prompt-pill" onclick="sdcTutor.askQuickPrompt('سيٽ ڇا آهي ۽ ان جا رڪن ڪيئن لکبا آهن؟')">🔢 سيٽ ۽ رڪن</button>
                <button type="button" class="quick-prompt-pill" onclick="sdcTutor.askQuickPrompt('سڄا عدد ڇا آهن؟')">➕ سڄا عدد</button>
                <button type="button" class="quick-prompt-pill" onclick="sdcTutor.askQuickPrompt('ٻوٽن ۾ فوٽوسنٿيسز جو عمل سمجهايو۔')">🌿 فوٽوسنٿيسز</button>
                <button type="button" class="quick-prompt-pill" onclick="sdcTutor.askQuickPrompt('عمودي وچولي ليڪ ڪيئن ٺاهبي آهي؟')">📐 جاميٽري</button>
                <button type="button" class="quick-prompt-pill" onclick="sdcTutor.askQuickPrompt('خوردبين جا مکيه حصا ڪهڙا آهن؟')">🔍 خوردبين</button>
              </div>

              <!-- Live Chat Message Stream -->
              <div id="tutor-chat-stream" class="chat-stream" role="log" aria-live="polite">
                <div class="chat-bubble tutor-bubble">
                  <div class="bubble-sender">🤖 سنڌي اي آءِ استاد (AI Tutor)</div>
                  <div>اسلام عليڪم! آءٌ اوهان جو سنڌي اي آءِ استاد آهيان. وڊيو ڏسندي يا پڙهندي رياضي يا سائنس بابت ڪوبه سوال هجي ته لکو يا مائڪ تي سنڌي ۾ ڳالهايو. (آواز ٻڌڻ لاءِ هر جواب تي اسپيڪر بٽڻ دٻايو)</div>
                </div>
              </div>'''

norm_text = text.replace('\r\n', '\n')
norm_target = target.replace('\r\n', '\n')
norm_rep = replacement.replace('\r\n', '\n')

if norm_target in norm_text:
    new_text = norm_text.replace(norm_target, norm_rep)
    with open(path, 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(new_text.replace('\n', '\r\n'))
    print('Updated app.html successfully!')
else:
    print('Target not found in app.html')

