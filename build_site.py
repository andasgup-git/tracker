#!/usr/bin/env python3
"""Regenerate the tracker website from tasks.json -> index.html.
Run after every task update. Usage: python3 build_site.py"""
import json, os, datetime

BASE = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(BASE, 'tasks.json'), encoding='utf-8') as f:
    data = json.load(f)

with open(os.path.join(BASE, 'index_template.html'), encoding='utf-8') as f:
    template = f.read()

# Inject JSON safely
json_str = json.dumps(data, ensure_ascii=False, indent=1)
html = template.replace('__DATA_JSON__', json_str)

out = os.path.join(BASE, 'index.html')
with open(out, 'w', encoding='utf-8') as f:
    f.write(html)

# Summary
total = len(data['tasks'])
open_t = sum(1 for t in data['tasks'] if t['status'] != 'done')
high = sum(1 for t in data['tasks'] if t['status'] != 'done' and t['priority'] == 'high')
print(f"index.html regenerated: {total} tasks, {open_t} open, {high} high priority @ {datetime.datetime.now():%Y-%m-%d %H:%M}")
