"""Facultatea de Inginerie a Instalațiilor: PDF timetables -> site data.

Hour rows (8-9, 9-10, ...), activity boxes drawn over the ruled grid, a diagonal for odd/even weeks.
Each box lists, one per line: subject, teacher, room, kind ("L", "S", "CURS"); reversed in the even-week half.

python3 inst.py <dir-with-pdfs> | --fetch  -> JSON on stdout
"""
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from builder import build_pages  # noqa: E402

PAGE = 'https://instalatii.utcluj.ro/studenti/orar.html'
KIND_W = {'L': 'L', 'S': 'S', 'C': 'C', 'P': 'P', 'CURS': 'C', 'SEMINAR': 'S', 'LAB': 'L', 'LABORATOR': 'L', 'PROIECT': 'P', 'LECTURE': 'C', 'SEM': 'S', 'PROJECT': 'P'}
ROOM_RE = re.compile(r'(AULA\s+F\.?\s?I\.?\s?I\.?|SALA\s+\w+|\b[A-Z]_?\d{2,3}[a-z]?\b|\bI\s\d{2}\b|\bBAZIN\b)', re.I)
PROF_RE = re.compile(r'^(ŞEF\s+LUCR|ȘEF\s+LUCR|SEF\s+LUCR|LECTOR|LECT\.|CONF|PROF|S\.?\s?L\.?|Ş\.?\s?L\.?|Ș\.?\s?L\.?|ASIST|DR\.|ING\.|COLECTIV|PROF\.)', re.I)
NAME_RE = re.compile(r'^[A-ZĂÂÎȘȚŞŢ][A-ZĂÂÎȘȚŞŢ\-]{2,}(?:\s+[A-ZĂÂÎȘȚŞŢ][A-ZĂÂÎȘȚŞŢ\-]*\.?)*$')


def parse_inst(text):
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    if not lines:
        return []
    joined = ' '.join(lines)
    low = joined.lower()
    if re.search(r'ed\.?\s*fizic|educa[țţt]ie fizic', low):
        return [dict(k='SP', a=None, t='Educație fizică', r=None)]
    if re.search(r'limbi?\s+modern|limba\s+(engl|fran|germ)', low):
        m = re.search(r'limba\s+(\w+)', low)
        lang = {'e': 'engleză', 'f': 'franceză', 'g': 'germană'}.get(m.group(1)[0], '') if m else ''
        rm = ROOM_RE.search(re.sub(r'(?i)limb\w+.*?(?=[A-Z]\d|$)', ' ', joined))
        return [dict(k='S', a='LS', t='Limbă străină' + (f' ({lang})' if lang else ''), r=rm.group(1) if rm else None)]
    kind = room = None
    rest = []
    order = []   # role of each line
    for l in lines:
        toks = l.split()
        # a kind letter glued to another line ("L I302", "MARE R. L")
        if toks and toks[0].upper() in KIND_W and len(toks) > 1 and (toks[0] in ('L', 'S', 'C', 'P') or toks[0].upper() == 'CURS'):
            kind = kind or KIND_W[toks[0].upper()]
            l = ' '.join(toks[1:])
            toks = toks[1:]
        if toks and toks[-1] in ('L', 'S', 'C', 'P') and len(toks) > 1:
            kind = kind or toks[-1]
            l = ' '.join(toks[:-1])
        if l.upper() in KIND_W:
            kind = kind or KIND_W[l.upper()]
            order.append('k')
            continue
        m = ROOM_RE.search(l)
        if m and len(l) - len(m.group(0)) <= 3:
            room = room or re.sub(r'\s+', ' ', m.group(1)).strip()
            order.append('r')
            continue
        if m and not room:
            room = re.sub(r'\s+', ' ', m.group(1)).strip()
            l = (l[:m.start()] + l[m.end():]).strip()
        rest.append(l)
        order.append('x')
    if not rest:
        return []
    reversed_box = bool(order) and order[0] in ('k', 'r')
    INIT = re.compile(r'^[A-ZĂÂÎȘȚŞŢ][A-ZĂÂÎȘȚŞŢ\-]{2,}(?:\s+[A-ZĂÂÎȘȚŞŢ][A-ZĂÂÎȘȚŞŢ\-]+)*\s+[A-ZĂÂÎȘȚŞŢ]{1,2}\.?$')
    profs = [x for x in rest if PROF_RE.match(x) or INIT.match(x)]
    others = [x for x in rest if x not in profs]
    if not others:
        others, profs = [profs[0]], profs[1:]
    if len(others) > 1:
        # several bare lines: the subject plus continuation lines ("ŞI LIMBAJE ..."), or subject + a surname
        cont = [x for x in others if re.match(r'^(ŞI|ȘI|SI|DE|PENTRU|ÎN|IN|A|AL|CU)\b', x) or len(x) > 14]
        base = others[-1] if reversed_box else others[0]
        title = [x for x in others if x is base or x in cont]
        profs += [x for x in others if x not in title]
        subj = ' '.join(title)
    else:
        subj = others[0]
    act = {'k': kind, 'r': room}
    if profs:
        act['prof'] = ' '.join(profs).replace('COLECTIV E.F.S.', '').strip() or None
    if re.fullmatch(r"[A-ZĂÂÎȘȚŞŢ0-9][A-ZĂÂÎȘȚŞŢ0-9.]*\.(?:\s+(?:I{1,3}|IV|[A-Z]{1,4}\.?))*|[A-Z]{2,6}(?:\s+I{1,3})?", subj.strip()):
        act['a'] = subj.strip()
        act['t'] = None
    else:
        act['a'] = None
        act['t'] = subj.strip()
    return [act]


def place_inst(room):
    if not room:
        return None
    if re.match(r'AULA', room, re.I):
        return 'aula'   # Aula FII, B-dul 21 Decembrie 1989 nr. 128
    if re.match(r'I', room):
        return 'aula'
    if re.match(r'BAZIN', room, re.I):
        return 'sport'
    return None


FILES = [(r'_AN_?1\.pdf$', 1, 'lic'), (r'_AN_?2\.pdf$', 2, 'lic'), (r'_AN_?3\.pdf$', 3, 'lic'), (r'_AN_?4\.pdf$', 4, 'lic'),
         ]
# masters (M1, M2, IOR) draw their course boxes with loose lines over a crossed-out grid: not imported yet


def meta_inst(gc, sheet, year, level, extra):
    if level == 'lic':
        return dict(id=gc['code'], prog='inst-ii', label=gc['code'], sub='')
    name = 'BSRC' if level == 'master-en' else 'Master II'
    prog = 'm-inst-en' if level == 'master-en' else 'm-inst'
    code = re.sub(r'^[a-z]_', '', gc['code'])
    return dict(id=f"inst-m{year}{'en' if level == 'master-en' else ''}-{code}", prog=prog, label=code, sub=name)


def build(src_dir):
    pages = []
    files = sorted(glob.glob(os.path.join(src_dir, '*.pdf')))
    for rx, year, level in FILES:
        hit = [f for f in files if re.search(rx, os.path.basename(f), re.I)]
        if hit:
            pages.append((hit[-1], os.path.basename(hit[-1])[:-4], year, level, {'ruled': True}))
    return build_pages('inst', pages, meta_inst, place_inst, parser=parse_inst, parser_lines=True)


def fetch(dest):
    import urllib.request
    from urllib.parse import urljoin, unquote
    ua = {'User-Agent': 'orar-utcn (+https://utcna.pages.dev)'}
    html = urllib.request.urlopen(urllib.request.Request(PAGE, headers=ua), timeout=60).read().decode('utf-8', 'replace')
    links = sorted(set(re.findall(r'href="([^"]*/Orar/S1_[^"]*\.pdf)"', html, re.I)))
    os.makedirs(dest, exist_ok=True)
    for href in links:
        url = urljoin(PAGE, href).replace(' ', '%20')
        name = unquote(url.split('/')[-1])
        if re.search(r'psihopedagog|exemplu', name, re.I):
            continue
        data = urllib.request.urlopen(urllib.request.Request(url, headers=ua), timeout=60).read()
        if data[:4] == b'%PDF':
            open(os.path.join(dest, name), 'wb').write(data)
    return dest


if __name__ == '__main__':
    src = sys.argv[1]
    if src == '--fetch':
        import tempfile
        src = fetch(tempfile.mkdtemp(prefix='inst-'))
    print(json.dumps(build(src), ensure_ascii=False))
