#!/usr/bin/env python3
"""Sync a newly-opened GitHub issue into tasks.json, then rebuild the site.
Run inside GitHub Actions on issues:opened. Reads issue data from env."""
import json, os, re, datetime, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS = os.path.join(BASE, 'tasks.json')

title = os.environ.get('ISSUE_TITLE', '').strip()
body = os.environ.get('ISSUE_BODY', '').strip() or ''
issue_no = os.environ.get('ISSUE_NUMBER', '0')

if not title:
    print("No title — nothing to sync")
    sys.exit(0)

with open(TASKS, encoding='utf-8') as f:
    data = json.load(f)

# ── track detection: explicit prefix wins, else keyword match ──
TRACK_KEYWORDS = {
    "job": ["job", "work", "office", "google", "meeting", "aop", "team", "email"],
    "dc": ["devi", "chowdhurani", "dc ", "zee", "festival", "film", "imdb", "dcp", "kdm", "release", "premiere", "distribution", "screen", "theatre", "theater", "booking", "n abc", "nabc"],
    "studio": ["confluence", "studio", "adited", "basaff", "aparna", "hollywood", "pitch", "deck", "proposal", "basa f"],
    "finance": ["tax", "lovleen", "bhatia", "swyft", "buffalo", "wyoming", "universal organic", "llc", "bank", "invoice", "1099", "irs", "delaware", "boi", "cpa", "zelle", "pay"],
    "home": ["home", "family", "aparna", "ariana", "health", "doctor", "insurance", "fastrak", "toll", "house", "grocer", "miji", "therapy", "rceb", "school", "piano", "gym", "swim"],
    "miku": ["miku", "pet", "vet", "dog", "cat", "walk"],
}
PREFIX_RE = re.compile(r'^(?:\[([a-z]+)\]|\(([a-z]+)\)|track:?\s*([a-z]+))\s*[:.-]?\s*(.*)$', re.I)

def detect_track(t, b):
    m = PREFIX_RE.match(t)
    if m:
        for g in m.groups():
            if g and g.lower() in TRACK_KEYWORDS:
                return g.lower(), (m.group(4) or t)
    low = (t + ' ' + b).lower()
    best, score = "home", 0
    for track, kws in TRACK_KEYWORDS.items():
        s = sum(1 for k in kws if k in low)
        if s > score:
            best, score = track, s
    return best, t

track, clean_title = detect_track(title, body)

# ── priority: explicit keyword, else medium ──
low_prio = (title + ' ' + body).lower()
if re.search(r'\b(high|urgent|asap|important|today)\b', low_prio):
    priority = "high"
elif re.search(r'\b(low|whenever|someday|optional)\b', low_prio):
    priority = "low"
else:
    priority = "medium"

# ── due date: "due 2026-08-20" / "due:2026-08-20" / "by 2026-08-20" ──
due = None
m = re.search(r'(?:due|by|deadline)[\s:]*(\d{4}-\d{2}-\d{2})', low_prio)
if m:
    due = m.group(1)

# ── notes: body, stripped of instruction lines ──
notes = body.strip() if body else ''
notes = re.sub(r'^(track|tag|priority|due)[\s:].*$', '', notes, flags=re.I | re.M).strip()

new_task = {
    "id": f"t-issue-{issue_no}",
    "track": track,
    "title": clean_title,
    "status": "pending",
    "priority": priority,
    "due": due,
    "notes": notes or f"Added from issue #{issue_no}."
}
data['tasks'].append(new_task)

with open(TASKS, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Added: [{track}] {clean_title} (priority={priority}, due={due})")

# ── rebuild the site ──
sys.path.insert(0, BASE)
import importlib.util
spec = importlib.util.spec_from_file_location("build_site", os.path.join(BASE, "build_site.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
