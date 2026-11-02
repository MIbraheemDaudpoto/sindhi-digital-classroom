# -*- coding: utf-8 -*-
with open("static/app.html", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace('<script src="/static/js/tutor.js"></script>', '<script src="/static/js/tutor.js?v=6"></script>')
text = text.replace('<script src="/static/js/quiz.js?v=5"></script>', '<script src="/static/js/quiz.js?v=6"></script>')
text = text.replace('<script src="/static/js/app.js"></script>', '<script src="/static/js/app.js?v=6"></script>')

with open("static/app.html", "w", encoding="utf-8", newline="\r\n") as f:
    f.write(text)
print("Updated static/app.html successfully!")

