with open('static/app.html', 'r', encoding='utf-8') as f:
    html = f.read()

import re
panes = re.findall(r'id=["\'](pane-[^"\']+)["\']', html)
print('Panes found in static/app.html:', panes)

buttons = re.findall(r'data-tab=["\']([^"\']+)["\']', html)
print('Data-tabs found in static/app.html:', buttons)

