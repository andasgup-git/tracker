import json
from datetime import datetime

P = '/home/aniru/tracker/tasks.json'
d = json.load(open(P))
tasks = d['tasks']
ids = {t.get('id') for t in tasks}

ts = 'Oct 15 2026 (~23:02 PT, mailbox scan 1015d, cron)'

new = []

t224 = {
    "id": "t224",
    "track": "finance",
    "title": "Vimeo Starter plan payment declined - Capital One virtual card ...8348 deactivated",
    "status": "pending",
    "priority": "medium",
    "due": None,
    "notes": (
        "Oct 15 2026 (%s): Capital One VentureOne alert 'Purchase declined: Your virtual card is "
        "deactivated' (PERSONAL INBOX UID 372881, Fri 16 Oct 2026 05:24 UTC) - the VMO*VIMEO.COM "
        "charge on virtual card ...8348 (account ...0372) was declined because that virtual card has "
        "been deactivated. Same window the ADITED mailbox received two Vimeo notices: 'Your Starter "
        "plan receipt' (ADITED INBOX UID 23740, Fri 16 Oct 01:29 EDT) and 'Your video is ready! "
        "What's next?' (ADITED INBOX UID 23742, Fri 16 Oct 01:46 EDT) - so the ADITED Video/Vimeo "
        "Starter plan is the relevant account. ACTION: sign in to Capital One and either reactivate/"
        "create a new virtual card, or add a working payment method to the Vimeo (ADITED) Starter "
        "plan, then re-run the declined purchase so the plan does not lapse. No email reply possible "
        "(notification@capitalone.com is a no-reply sender)."
    ) % ts,
}
new.append(t224)

for t in new:
    if t['id'] not in ids:
        tasks.append(t)
        print('added', t['id'])

json.dump(d, open(P, 'w'), indent=1)
print('total tasks', len(tasks))
