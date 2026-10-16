import json
from datetime import datetime

STATE = '/home/aniru/mailscan_state.json'
SCAN = '/home/aniru/tracker/mscan1015d_new.json'

ts = datetime.now().strftime('%Y-%m-%d %H:%M PT')

st = json.load(open(STATE))
before = {k: len(st.get(k, [])) for k in ['PERSONAL', 'ADITED', 'APARNA', 'SEEN']}
added = {}
scan = json.load(open(SCAN))
entries = list(scan.get('newseen', []))
for entry in entries:
    parts = entry.split('|')
    if len(parts) != 3:
        continue
    mb, folder, mid = parts
    lst = st.setdefault(mb, [])
    if entry not in lst:
        lst.append(entry)
        added[mb] = added.get(mb, 0) + 1
    gen = folder + '|' + mid
    sl = st.setdefault('SEEN', [])
    if gen not in sl:
        sl.append(gen)
        added['SEEN'] = added.get('SEEN', 0) + 1
    rs = st.setdefault(mb + '_RECENT_SEEN', [])
    if entry not in rs:
        rs.append(entry)

findings = (
    "Scan 1015d (Oct 15 2026 ~23:02 PT, SINCE 13-Oct; third run of the day after 1015 "
    "13:51 PT and 1015c 21:58 PT). PERSONAL INBOX window 293 (372852-372881); PERSONAL Sent 0; "
    "ADITED INBOX 37 (23698-23742); ADITED Sent 1 (1030, self-send). 4 NEW non-noise items, NONE "
    "needing a reply: PERSONAL 372880 Vi postpaid bill intimation (ebill.kol@vodafoneidea.com, "
    "automated 'ignore if already paid'); PERSONAL 372881 Capital One VentureOne 'Purchase "
    "declined: Your virtual card is deactivated' - VMO*VIMEO.COM charge declined on virtual card "
    "...8348, acct ...0372 (actionable FINANCE alert, no reply possible -> tracker t224); ADITED "
    "23740 Vimeo 'Your Starter plan receipt' (FYI); ADITED 23742 Vimeo 'Your video is ready! "
    "What's next?' (notification). No real sender asking a question -> NO reply draft prepared. "
    "APARNA app-password login STILL FAILS (AUTHENTICATIONFAILED, 47th+ consecutive) - unscanned."
)

st['last_scan_1015d'] = ts
st['last_scan_1015d_run'] = 'scan_1015d (SINCE 13-Oct, last-30 window)'
st['last_scan_1015d_findings'] = findings
st['last_scan_1015d_result'] = 'NO_ACTIONABLE_NEW'
st['aparna_status'] = (
    'LOGIN_FAILED [AUTHENTICATIONFAILED] apu.dg1@gmail.com as of %s (scan_1015d, late-evening). '
    'App password in cron task (yheu ovwl fcva aqzj) rejected. Mailbox UNSCANNED (47th+ consecutive). '
    'Needs a NEW app password.' % ts
)

json.dump(st, open(STATE, 'w'), indent=1)
after = {k: len(st.get(k, [])) for k in before}
print('STATE before', before)
print('STATE after ', after)
print('STATE added ', added)
