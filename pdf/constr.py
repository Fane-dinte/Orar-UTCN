"""Facultatea de Construcții (Cluj): the EduPage timetable (structured JSON) -> site data.

python3 constr.py <tt.json> | --fetch  -> JSON on stdout
"""
import json
import os
import re
import sys
import urllib.request

BASE = 'https://constructiicluj.edupage.org'
PAGE = BASE + '/timetable/'

PROGS = {
    'IC': ('constr-ic', 'lic'), 'CCIA': ('constr-ic', 'lic'), 'CFDP': ('constr-ic', 'lic'), 'ACH': ('constr-ic', 'lic'), 'IUDR': ('constr-ic', 'lic'),
    'IMC': ('constr-imc', 'lic'), 'CE': ('constr-ce', 'lic'), 'MTC': ('constr-mtc', 'lic'),
}
SPEC = {'CCIA': 'CCIA', 'CFDP': 'Căi ferate, drumuri și poduri', 'ACH': 'Amenajări hidrotehnice', 'IUDR': 'Inginerie urbană'}
KIND = {'C': 'C', 'S': 'S', 'L': 'L', 'P': 'P', 'SP': 'SP'}
DAYMAP = {'10000': 0, '01000': 1, '00100': 2, '00010': 3, '00001': 4}


# Edupage drops connections from some GitHub runner IPs: then the same two calls go through an allow-listed Cloudflare relay
RELAY = os.environ.get('EDUPAGE_RELAY', '').rstrip('/')   # set as a repository variable; empty = no fallback


def _post(func, args):
    body = json.dumps({'__args': args, '__gsh': '00000000'}).encode()
    hdr = {'content-type': 'application/json; charset=UTF-8', 'User-Agent': 'orar-utcn (+https://utcna.pages.dev)'}
    last = None
    for base, wait in ((BASE, 25), (RELAY, 60)) if RELAY else ((BASE, 60),):
        try:
            req = urllib.request.Request(f'{base}/timetable/server/{func}', data=body, headers=hdr)
            return json.loads(urllib.request.urlopen(req, timeout=wait).read().decode('utf-8'))
        except Exception as e:  # noqa: BLE001
            last = e
            print(f'constr: {base} nu răspunde ({e})', file=sys.stderr)
    raise last


def fetch():
    v = _post('ttviewer.js?__func=getTTViewerData', [None, 2026])['r']['regular']
    tts = [t for t in v['timetables'] if not t.get('hidden') and re.search(r'Constructii Cluj', t['text'], re.I)]
    tt = max(tts, key=lambda t: t['datefrom']) if tts else {'tt_num': v['default_num'], 'text': ''}
    r = _post('regulartt.js?__func=regularttGetData', [None, tt['tt_num']])['r']['dbiAccessorRes']['tables']
    data = {t['id']: t['data_rows'] for t in r}
    data['_tt'] = tt
    return data


def _hour(hhmm, up=False):
    h, m = map(int, hhmm.split(':'))
    return h + (1 if up and m >= 30 else 0)


def place(room, building):
    if not room:
        return None
    if re.match(r'bazin', room, re.I):
        return 'sport'
    if 'Muncii' in room or building == '*6':
        return 'muncii'
    if 'DSPP' in room or building == '*4':
        return 'turn'
    if building == '*1':
        return 'constr'
    return None


def build(d):
    P = {p['period']: p for p in d['periods']}
    S = {s['id']: s for s in d['subjects']}
    T = {t['id']: t for t in d['teachers']}
    R = {r['id']: r for r in d['classrooms']}
    G = {g['id']: g for g in d['groups']}
    C = {c['id']: c for c in d['classes']}
    L = {l['id']: l for l in d['lessons']}
    groups, entries = [], {}
    sgs_of = {}
    for c in d['classes']:
        m = re.match(r'^([A-Z]+)(?:_([A-C]))?_(\d+)$', c['name'])
        if not m:
            continue
        prefix, series, code = m.groups()
        if prefix in PROGS:
            prog, level = PROGS[prefix]
            year = int(code[2])
            sub = (f'seria {series}' if series else '') if prefix in ('IC',) else SPEC.get(prefix, '')
            label = code
        else:
            prog, level = 'm-constr', 'master'
            year = int(code[-2])
            sub = ''
            label = prefix
        halves = sorted({g['name'] for g in d['groups'] if g['classid'] == c['id'] and re.match(r'Semigrupa [ab]', g['name'])})
        sgs = [1, 2] if len(halves) == 2 else [1]
        sgs_of[c['id']] = sgs
        gid = code if level == 'lic' else f'constr-m{year}-{prefix.lower()}-{code[-1]}'
        if level == 'master' and sum(1 for x in d['classes'] if x['name'].startswith(prefix + '_') and re.search(r'\d', x['name']) and x['name'][-2] == code[-2]) > 1:
            label = f'{prefix} {code[-1]}'
        groups.append({'id': gid, 'label': label, 'prog': prog, 'year': year, 'sgs': sgs, 'sub': sub, 'sheet': prefix, 'dept': 'constr', 'fac': 'constr'})
        entries[gid] = []
        c['_gid'] = gid
    for card in d['cards']:
        l = L.get(card['lessonid'])
        if not l or not card.get('period') or card['days'] not in DAYMAP:
            continue
        subj = S.get(l['subjectid'], {})
        name = subj.get('name', '')
        m = re.match(r'^(.*?)\s*\((C|S|L|P|SP|Curs|Seminar|Laborator|Proiect)\)\s*$', name)
        title, kind = (m.group(1), m.group(2)[0] if m.group(2) != 'SP' else 'SP') if m else (name, None)
        short = re.sub(r'\s*\([A-Z]+\)\s*$', '', subj.get('short', '')).strip() or None
        if re.search(r'educa[tț]ie fizic|sport|physical education', title, re.I):
            kind, title, short = 'SP', 'Educație fizică', None
        p0 = P[card['period']]
        p1 = P.get(str(int(card['period']) + int(l.get('durationperiods') or 1) - 1), p0)
        s, e = _hour(p0['starttime']), _hour(p1['endtime'], up=True)
        weeks = card.get('weeks') or '11'
        par = {'10': 'odd', '01': 'even'}.get(weeks, 'all')
        rooms = [R[x]['name'] for x in card.get('classroomids', []) if x in R]
        room = ', '.join(rooms) or None
        bld = R[card['classroomids'][0]]['buildingid'] if card.get('classroomids') and card['classroomids'][0] in R else None
        prof = ', '.join(T[t]['name'] for t in l.get('teacherids', []) if t in T) or None
        for cid in l.get('classids', []):
            c = C.get(cid)
            if not c or '_gid' not in c:
                continue
            gs = [G[g] for g in l.get('groupids', []) if g in G and G[g]['classid'] == cid]
            sgs = sgs_of[cid]
            if gs and not any(g['entireclass'] for g in gs):
                pick = sorted({1 if g['name'].endswith('a') else 2 for g in gs if re.match(r'Semigrupa [ab]', g['name'])})
                if pick:
                    sgs = pick
            out = {'d': DAYMAP[card['days']], 's': s, 'e': e, 'p': par, 'k': kind or ('C' if len(l['classids']) > 1 else 'S'),
                   'a': short if short and short.upper() != title.upper() else None, 't': title, 'r': room, 'sg': sgs, 'all': sgs == sgs_of[cid]}
            if prof:
                out['prof'] = prof
            pl = place(room, bld)
            if pl:
                out['pl'] = pl
            if len(l['classids']) > 1:
                out['n'] = len(l['classids'])
            out['raw'] = f"{name} · {room or ''} · {prof or ''}".strip(' ·')
            out['src'] = f"card {card['id']}"
            entries[c['_gid']].append(out)
    for gid in entries:
        seen, keep = set(), []
        for x in sorted(entries[gid], key=lambda x: (x['d'], x['s'], x['e'])):
            k = json.dumps([x['d'], x['s'], x['e'], x['p'], x['sg'], x['t'], x['k'], x['r']])
            if k not in seen:
                seen.add(k)
                keep.append(x)
        entries[gid] = keep
    tt = d.get('_tt', {})
    m = re.search(r'_(\d{1,2})\.(\d{1,2})\b', tt.get('text', ''))
    stamp = f"{int(m.group(1)):02d}.{int(m.group(2)):02d}.2026" if m else None
    return {'dept': 'constr', 'stamp': stamp, 'groups': groups, 'entries': entries, 'notes': {}, 'langs': {}, 'warnings': []}


if __name__ == '__main__':
    src = sys.argv[1]
    data = fetch() if src == '--fetch' else json.load(open(src))
    print(json.dumps(build(data), ensure_ascii=False))
