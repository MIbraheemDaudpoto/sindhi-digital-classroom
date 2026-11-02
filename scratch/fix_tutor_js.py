import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('static/js/tutor.js', 'r', encoding='utf-8') as f:
    text = f.read()

bad_str = "stageEl.textContent = ✍️ تصديق ٿيل جواب تيار ٿي رهيو آهي ( سيڪنڊ)...;"
good_str = "stageEl.textContent = `✍️ تصديق ٿيل جواب تيار ٿي رهيو آهي (${elapsedSec} سيڪنڊ)...`;"

if bad_str in text:
    text = text.replace(bad_str, good_str)
    with open('static/js/tutor.js', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Successfully replaced bad_str in tutor.js")
else:
    print("bad_str NOT found, let's locate line 313")
    lines = text.splitlines()
    print("Line 312:", repr(lines[311]))
    print("Line 313:", repr(lines[312]))
    print("Line 314:", repr(lines[313]))
    lines[312] = "        stageEl.textContent = `✍️ تصديق ٿيل جواب تيار ٿي رهيو آهي (${elapsedSec} سيڪنڊ)...`;"
    with open('static/js/tutor.js', 'w', encoding='utf-8') as f:
        f.write("\n".join(lines) + "\n")
    print("Replaced line 313 by index!")

