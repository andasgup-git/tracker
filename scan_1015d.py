#!/usr/bin/env python3
import imaplib, email, json, re, signal, os, glob
from email.header import decode_header, make_header
from datetime import datetime, timedelta

signal.signal(signal.SIGALRM, lambda s, f: (_ for _ in ()).throw(TimeoutError('imap timeout')))

STATE = '/home/aniru/mailscan_state.json'
OUT = '/home/aniru/tracker/mscan1015d_new.json'

MAILBOXES = {
    'PERSONAL': ('aniruddha.dg1@gmail.com', 'dkkmgbmoemquaqlb'),
    'ADITED': ('aniruddha@aditedmotionpictures.com', 'zita ucxa gkrl yrru'),
    'APARNA': ('apu.dg1@gmail.com', 'yheu ovwl fcva aqzj'),
}
FOLDERS = ['INBOX', '[Gmail]/Sent Mail']
_EXCL = ('mscan1015_new.json', 'mscan1015b_new.json', 'mscan1015c_new.json', 'mscan1015d_new.json')

NOISE = ['no-reply', 'noreply', 'do-not-reply', 'donotreply', 'linkedin', 'indeed', 'imdb',
         'cinemark.com', 'emails.cinemark', 'nytimes', 'fox.com', 'bankbazaar',
         'onlinesbi', 'sbi.co', 'utimf', 'easemytrip', 'stage32', 'screendaily',
         'screenglobal', 'authoritymagazine', 'groupon', 'temu', 'mailer', 'newsletter',
         'notifications@', 'no_reply', 'bounce', 'mailchimp', 'substack', 'medium.com',
         'quora', 'glassdoor', 'ziprecruiter', 'facebookmail', 'instagram', 'pinterest',
         'twitter', 'x.com', 'amazon.com', 'spotify', 'netflix', 'hulu', 'roku',
         'calendar-notification', 'marketing', 'promo', 'deals', 'news@',
         'updates@', 'community@', 'member@', 'survey', 'feedback',
         'invoice+', 'alerts@', 'support@', 'gmail.com/calendar', 'e-news@', 'beehiiv',
         '4imprint', 'em.wsj.com', 'emails.hbr', 'costco', 'bevmo', 'audienhearing',
         'chase@mcmap', 'uber.com', 'classdojo', 'informeddelivery', 'usps', 'sofi',
         'bayclubs', 'jjshouse', 'subway', 'bigotires', 'sutterhealth', 'tajhotels',
         'circusroadfilms', 'shared1', 'indiaabroad', 'craftsuprint', 'nhusd.k12',
         'hometalk', 'worddaily', 'word daily', 'moechoice', 'marriott', 'prospectus_mbox',
         'investordelivery', 'my_merrill', 'otter.ai', 'updates.otter', 'adobe.com',
         'plaid.com', 'fidelity.com', 'bankofamerica', 'userinterviews', 'remitly',
         'adityabirlasunlife', 'recommend', 'webinar', 'nextdoor']


def dh(v):
    try:
        return str(make_header(decode_header(v or '')))
    except Exception:
        return v or ''


def get_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/plain' and 'attachment' not in str(part.get('Content-Disposition') or ''):
                try:
                    return part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', 'replace')
                except Exception:
                    pass
        for part in msg.walk():
            if part.get_content_type() == 'text/html':
                try:
                    h = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', 'replace')
                    h = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', h, flags=re.S | re.I)
                    return re.sub('<[^>]+>', ' ', h)
                except Exception:
                    pass
        return ''
    try:
        return msg.get_payload(decode=True).decode(msg.get_content_charset() or 'utf-8', 'replace')
    except Exception:
        return ''


def is_noise(frm):
    f = (frm or '').lower()
    return any(n in f for n in NOISE)


seen = set()
st = json.load(open(STATE))
for name in ('PERSONAL', 'ADITED', 'APARNA', 'SEEN', 'PERSONAL_RECENT_SEEN', 'ADITED_RECENT_SEEN', 'APARNA_RECENT_SEEN'):
    for x in st.get(name, []):
        if isinstance(x, str):
            seen.add(x)
for f in glob.glob('/home/aniru/tracker/mscan*.json') + glob.glob('/home/aniru/.mailscan*.json') + glob.glob('/home/aniru/mscan*.json'):
    if f.endswith(_EXCL):
        continue
    try:
        d = json.load(open(f))
    except Exception:
        continue
    if isinstance(d, list):
        d = {'results': d}
    if not isinstance(d, dict):
        continue
    for x in d.get('newseen', []):
        seen.add(x)
    for r in d.get('results', []):
        if not isinstance(r, dict):
            continue
        if r.get('uid'):
            seen.add('%s|%s|%s' % (r.get('mailbox'), r.get('folder'), r['uid']))
            seen.add('%s|%s' % (r.get('folder'), r['uid']))
            if r.get('msgid'):
                seen.add('%s|%s|%s' % (r.get('mailbox'), r.get('folder'), r['msgid']))
                seen.add('%s|%s' % (r.get('folder'), r['msgid']))
for x in list(seen):
    if '|' in x and x.split('|')[0] in FOLDERS:
        for nm in MAILBOXES:
            seen.add(nm + '|' + x)


def already(name, folder, uid, mid):
    cands = ['%s|%s|%s' % (name, folder, uid), '%s|%s' % (folder, uid)]
    if mid:
        cands += ['%s|%s|%s' % (name, folder, mid), '%s|%s' % (folder, mid)]
    return any(c in seen for c in cands)


since = (datetime.now() - timedelta(days=2)).strftime('%d-%b-%Y')
results = []
newseen = []
login_status = {}
uidvalidity = {}
window_counts = {}

for name, (user, pw) in MAILBOXES.items():
    M = None
    cands = [pw, pw.replace(' ', '').strip()]
    ok = False
    err = None
    for p in cands:
        if not p:
            continue
        try:
            signal.alarm(90)
            M = imaplib.IMAP4_SSL('imap.gmail.com', 993)
            M.login(user, p)
            signal.alarm(0)
            ok = True
            break
        except Exception as e:
            err = e
    if not ok:
        login_status[name] = 'LOGIN_FAILED %s' % err
        results.append({'mailbox': name, 'error': 'login: %s' % err})
        continue
    login_status[name] = 'OK'
    for folder in FOLDERS:
        try:
            signal.alarm(90)
            typ, _ = M.select('"%s"' % folder, readonly=True)
            if typ != 'OK':
                continue
            uv = M.untagged_responses.get('UIDVALIDITY')
            uidvalidity['%s|%s' % (name, folder)] = uv[0].decode() if uv else '?'
            typ, data = M.uid('SEARCH', None, '(SINCE "%s")' % since)
            allids = data[0].split() if data and data[0] else []
            window_counts['%s|%s' % (name, folder)] = (len(allids),
                                                       allids[0].decode() if allids else '-',
                                                       allids[-1].decode() if allids else '-')
            ids = allids[-30:]
            signal.alarm(0)
            for i in ids:
                iu = i.decode()
                try:
                    signal.alarm(60)
                    typ, d = M.uid('FETCH', i, '(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE TO MESSAGE-ID)])')
                    signal.alarm(0)
                    if typ != 'OK' or not d or not d[0]:
                        continue
                    msg = email.message_from_bytes(d[0][1])
                    frm = dh(msg.get('From'))
                    subj = dh(msg.get('Subject'))
                    date = msg.get('Date')
                    mid = (msg.get('Message-ID') or '').strip()
                    newseen.append('%s|%s|%s' % (name, folder, iu))
                    if mid:
                        newseen.append('%s|%s|%s' % (name, folder, mid))
                    isold = already(name, folder, iu, mid)
                    noise = is_noise(frm)
                    why = 'noise' if noise else ''
                    if folder == '[Gmail]/Sent Mail' and user.split('@')[0].lower() in frm.lower():
                        noise = True
                        why = 'self-send'
                    rec = {'mailbox': name, 'folder': folder, 'uid': iu, 'from': frm,
                           'subject': subj, 'date': date, 'msgid': mid,
                           'noise': noise, 'why': why, 'already_seen': isold}
                    if not noise and not isold:
                        try:
                            signal.alarm(60)
                            t2, dd = M.uid('FETCH', i, '(RFC822)')
                            signal.alarm(0)
                            if t2 == 'OK' and dd and dd[0]:
                                body = get_body(email.message_from_bytes(dd[0][1]))
                                rec['body'] = re.sub(r'\n{3,}', '\n\n', body)[:8000]
                        except Exception as e:
                            rec['bodyerr'] = str(e)
                    results.append(rec)
                except Exception as e:
                    results.append({'mailbox': name, 'folder': folder, 'uid': iu, 'error': str(e)})
        except Exception as e:
            results.append({'mailbox': name, 'folder': folder, 'error': str(e)})
    try:
        M.logout()
    except Exception:
        pass

json.dump({'since': since, 'results': results, 'newseen': newseen,
           'login_status': login_status, 'uidvalidity': uidvalidity,
           'window_counts': window_counts},
          open(OUT, 'w'), indent=1)
print('SINCE', since, '| scanned at', datetime.now())
print('LOGIN', login_status)
print('UIDVALIDITY', uidvalidity)
print('WINDOW_COUNTS', window_counts)
for r in results:
    if r.get('error'):
        print('ERR', r)
    else:
        if r.get('already_seen'):
            tag = 'OLD  '
        elif r.get('noise'):
            tag = 'NOISE'
        else:
            tag = 'NEW  '
        print('%s | %s | %s | %s | %s | %s | %s' % (tag, r['mailbox'], r['folder'], r['uid'],
                                               r['from'][:55], r['subject'][:75], r.get('date')))
print('TOTAL_CANDIDATES', len(results))
print('NEW_NONNOISE', sum(1 for r in results if r.get('uid') and not r.get('noise') and not r.get('already_seen')))
