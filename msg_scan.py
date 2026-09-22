#!/usr/bin/env python3
import imaplib, email, json, re, signal, os
from email.header import decode_header, make_header
from datetime import datetime, timedelta

signal.signal(signal.SIGALRM, lambda s, f: (_ for _ in ()).throw(TimeoutError('imap timeout')))

STATE = '/home/aniru/mailscan_state.json'
OUT = '/home/aniru/tracker/mscan_latest.json'

MAILBOXES = {
    'PERSONAL': ('aniruddha.dg1@gmail.com', os.environ.get('PW_PERSONAL', '')),
    'ADITED': ('aniruddha@aditedmotionpictures.com', os.environ.get('PW_ADITED', '')),
    'APARNA': ('apu.dg1@gmail.com', os.environ.get('PW_APARNA', '')),
}
PWS_ALT = {k: v for k, v in {
    'PERSONAL': os.environ.get('PW_PERSONAL_ALT', ''),
    'ADITED': os.environ.get('PW_ADITED_ALT', ''),
    'APARNA': os.environ.get('PW_APARNA_ALT', ''),
}.items()}
FOLDERS = ['INBOX', '[Gmail]/Sent Mail']

NOISE = ['no-reply', 'noreply', 'do-not-reply', 'donotreply', 'linkedin', 'indeed', 'imdb',
         'cinemark.com', 'emails.cinemark', 'nytimes', 'fox.com', 'bankbazaar',
         'onlinesbi', 'sbi.co', 'utimf', 'easemytrip', 'stage32', 'screendaily',
         'screenglobal', 'authoritymagazine', 'groupon', 'temu', 'mailer',
         'notifications@', 'no_reply', 'bounce', 'mailchimp', 'substack', 'medium.com',
         'quora', 'glassdoor', 'ziprecruiter', 'facebookmail', 'instagram', 'pinterest',
         'twitter', 'x.com', 'amazon.com', 'spotify', 'netflix', 'hulu', 'roku',
         'calendar-notification', 'notify', 'marketing', 'promo', 'deals',
         'survey', 'feedback', 'alerts@', 'variety.com', 'americanbanker',
         'tajhotels', 'singaporeair', 'tax.gov.ae', 'pdffiller', 'mercury.com',
         'apple.com', 'uber.com', 'costco', 'synchrony', 'wellsfargo', 'irctc',
         'icicisecurities', 'subway', 'adobe', 'microsoft.com', 'hcsnd', 'sparkpost',
         'ccsend', 'lstrk', 'xt.local', 'brevo', 'nfdcindia', 'zohocrm',
         'amazonses', 'cmail19', 'mlsend2', 'geopod-ismtpd', 'mail.gmail.com>',
         'ip-172-', 'ec2.internal', 'rts-solutions', 'dfw1s10mta', 'iad4s12mta',
         'ind1s0', 'las1s0', 'atl1s0', 'fra3s0', 'outlook.com',
         'hbr.org', 'bankofamerica', 'emcom.', 'plaid', 'craftsuprint',
         'seaworld', 'sesameplace', 'bayareanewsgroup', 'curryonwheels',
         'irctctourism', 'conference@conference', 'wise.com', 'ifza.com',
         'filmfreeway', 'eventbrite', 'chadis.com']

TRACK = {'[dc]': 'DC', '[studio]': 'studio', '[finance]': 'finance', '[home]': 'home',
         '[miku]': 'miku', '[job]': 'job'}


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


st = json.load(open(STATE))
seen = set()
for k, v in st.items():
    if isinstance(v, list):
        for x in v:
            if isinstance(x, str):
                seen.add(x)
for name in ('PERSONAL', 'ADITED', 'APARNA'):
    for x in st.get(name, []):
        if isinstance(x, str) and not x.startswith(name + '|'):
            seen.add(name + '|' + x)


def already(name, folder, uid, mid):
    if '%s|%s|%s' % (name, folder, uid) in seen:
        return True
    if '%s|%s' % (folder, uid) in seen:
        return True
    if mid and '%s|%s|%s' % (name, folder, mid) in seen:
        return True
    return False


since = (datetime.now() - timedelta(days=2)).strftime('%d-%b-%Y')
results = []
newseen = []

for name, (user, pw) in MAILBOXES.items():
    M = None
    try:
        signal.alarm(90)
        M = imaplib.IMAP4_SSL('imap.gmail.com', 993)
        try:
            M.login(user, pw)
        except Exception:
            M.login(user, PWS_ALT[name])
        signal.alarm(0)
    except Exception as e:
        results.append({'mailbox': name, 'error': 'login: %s' % e})
        continue
    for folder in FOLDERS:
        try:
            signal.alarm(90)
            typ, _ = M.select('"%s"' % folder, readonly=True)
            if typ != 'OK':
                continue
            typ, data = M.search(None, '(SINCE "%s")' % since)
            ids = data[0].split()[-30:] if data and data[0] else []
            signal.alarm(0)
            for i in ids:
                iu = i.decode()
                try:
                    signal.alarm(60)
                    typ, d = M.fetch(i, '(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE TO MESSAGE-ID)])')
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
                    if already(name, folder, iu, mid):
                        continue
                    noise = is_noise(frm)
                    why = 'noise' if noise else ''
                    if folder == '[Gmail]/Sent Mail' and user.split('@')[0].lower() in frm.lower():
                        noise = True
                        why = 'self-send'
                    rec = {'mailbox': name, 'folder': folder, 'uid': iu, 'from': frm,
                           'subject': subj, 'date': date, 'msgid': mid,
                           'noise': noise, 'why': why}
                    if not noise:
                        try:
                            signal.alarm(60)
                            t2, dd = M.fetch(i, '(RFC822)')
                            signal.alarm(0)
                            if t2 == 'OK' and dd and dd[0]:
                                rec['body'] = get_body(email.message_from_bytes(dd[0][1]))[:8000]
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

json.dump({'since': since, 'results': results, 'newseen': newseen}, open(OUT, 'w'), indent=1)
print('SINCE', since)
for r in results:
    if r.get('error'):
        print('ERR', r)
    else:
        tag = 'NOISE' if r.get('noise') else 'NEW  '
        print('%s | %s | %s | %s | %s | %s | %s' % (tag, r['mailbox'], r['folder'], r['uid'],
                                               r['from'][:55], r['subject'][:75], r['date']))
print('TOTAL_CANDIDATES', len(results))
print('TOTAL_NEW', len([r for r in results if not r.get('error') and not r.get('noise')]))
