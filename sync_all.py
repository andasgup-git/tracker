#!/usr/bin/env python3
"""Auto-sync: pull open GitHub issues -> tasks.json -> rebuild site -> push.
Run by cron every 30 min. Idempotent: only adds issues not already synced."""
import json, os, re, sys, subprocess, urllib.request, datetime

BASE = "/home/aniru/tracker"
TASKS = os.path.join(BASE, "tasks.json")
REPO = "andasgup-git/tracker"

def get_token():
    """Extract token from the git remote URL (never hardcoded in files)."""
    r = subprocess.run(["git", "-C", BASE, "remote", "get-url", "origin"],
                       capture_output=True, text=True)
    url = r.stdout.strip()
    m = re.search(r'https://([^:@]+):([^@]+)@', url)
    return m.group(2) if m else None

def fetch_open_issues(token):
    url = f"https://api.github.com/repos/{REPO}/issues?state=open&per_page=100"
    req = urllib.request.Request(url, headers={
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "hermes-tracker"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

TRACK_KEYWORDS = {
    "job": ["job", "work", "office", "google", "meeting", "aop", "team", "email"],
    "dc": ["devi", "chowdhurani", "zee", "festival", "film", "imdb", "dcp", "kdm", "release", "premiere", "distribution", "screen", "theatre", "theater", "booking", "nabc", "dc "],
    "studio": ["confluence", "studio", "adited", "basaff", "aparna", "hollywood", "pitch", "deck", "proposal"],
    "finance": ["tax", "lovleen", "bhatia", "swyft", "buffalo", "wyoming", "universal organic", "llc", "bank", "invoice", "1099", "irs", "delaware", "boi", "cpa", "zelle", "pay"],
    "home": ["home", "family", "ariana", "health", "doctor", "insurance", "fastrak", "toll", "house", "grocer", "miji", "therapy", "rceb", "school", "piano", "gym", "swim"],
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

def main():
    token = get_token()
    if not token:
        print("NO_TOKEN - remote URL has no credentials")
        return

    with open(TASKS, encoding='utf-8') as f:
        data = json.load(f)

    existing_ids = {t['id'] for t in data['tasks']}
    try:
        issues = fetch_open_issues(token)
    except Exception as e:
        print(f"FETCH_FAIL: {e}")
        return

    added = 0
    resolved = 0
    for issue in issues:
        if issue.get('pull_request'):  # skip PRs
            continue
        iid = f"t-issue-{issue['number']}"
        title = (issue.get('title') or '').strip()
        body = (issue.get('body') or '').strip()

        # ── RESOLVE handler: "resolve t01 ..." or "done t01 ..." marks a task done ──
        m_res = re.match(r'^(?:resolve|done|complete|finish)\s+(t-?[\w-]+)(?:\s+(.*))?$', title, re.I)
        if m_res:
            tid = m_res.group(1)
            found = False
            for t in data['tasks']:
                if t['id'] == tid:
                    t['status'] = 'done'
                    found = True
                    break
            if found:
                resolved += 1
                print(f"RESOLVED: {tid} -> done")
                try:
                    req = urllib.request.Request(
                        f"https://api.github.com/repos/{REPO}/issues/{issue['number']}",
                        data=json.dumps({"state": "closed"}).encode(),
                        headers={"Authorization": f"token {token}",
                                 "Accept": "application/vnd.github+json",
                                 "User-Agent": "hermes-tracker"},
                        method="PATCH")
                    with urllib.request.urlopen(req, timeout=30):
                        pass
                    print(f"CLOSED issue #{issue['number']}")
                except Exception as e:
                    print(f"CLOSE_FAIL #{issue['number']}: {e}")
            else:
                print(f"RESOLVE_MISS: task {tid} not found (issue #{issue['number']})")
            continue

        if iid in existing_ids:
            continue
        if not title:
            continue
        track, clean_title = detect_track(title, body)
        low_prio = (title + ' ' + body).lower()
        if re.search(r'\b(high|urgent|asap|important|today)\b', low_prio):
            priority = "high"
        elif re.search(r'\b(low|whenever|someday|optional)\b', low_prio):
            priority = "low"
        else:
            priority = "medium"
        due = None
        m = re.search(r'(?:due|by|deadline)[\s:]*(\d{4}-\d{2}-\d{2})', low_prio)
        if m:
            due = m.group(1)
        notes = re.sub(r'^(track|tag|priority|due)[\s:].*$', '', body, flags=re.I | re.M).strip()
        data['tasks'].append({
            "id": iid, "track": track, "title": clean_title,
            "status": "pending", "priority": priority, "due": due,
            "notes": notes or f"Added from issue #{issue['number']}."
        })
        existing_ids.add(iid)
        added += 1
        print(f"ADDED: [{track}] {clean_title} (p={priority}, due={due})")

    if added == 0 and resolved == 0:
        print(f"NO_NEW_TASKS ({datetime.datetime.now():%H:%M}) - {len(data['tasks'])} total")
        return

    with open(TASKS, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # rebuild site
    subprocess.run([sys.executable, os.path.join(BASE, "build_site.py")], check=True)

    # commit + push
    subprocess.run(["git", "-C", BASE, "pull", "--rebase", "origin", "main"],
                   capture_output=True, text=True)
    subprocess.run(["git", "-C", BASE, "add", "tasks.json", "index.html"], check=True)
    subprocess.run(["git", "-C", BASE, "commit", "-m", f"Auto-sync: {added} added, {resolved} resolved"],
                   capture_output=True, text=True)
    p = subprocess.run(["git", "-C", BASE, "push"], capture_output=True, text=True)
    print(f"PUSHED: {added} added, {resolved} resolved, {len(data['tasks'])} total")

if __name__ == "__main__":
    main()
