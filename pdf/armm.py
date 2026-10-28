"""Facultatea de Autovehicule Rutiere, Mecatronică și Mecanică (Cluj): PDF timetables -> site data.

Layout: every 2-hour slot is two sub-rows, "Săpt. impară" above and "Săpt. pară" below.
Cells: "AEH (L) D08d2 Carausan", "G.D. B208 Cirebea", "ORGANE DE MAȘINI II (Curs) Haragâș A120".
A legend "ABBR : full name" is printed next to most timetables.

python3 armm.py <dir-with-pdfs> | --fetch  -> JSON on stdout
"""
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from builder import build_pages  # noqa: E402

PAGE = 'https://armm.utcluj.ro/orar.html'

KIND = {'curs': 'C', 'c': 'C', 'lecture': 'C', 's': 'S', 'seminar': 'S', 'l': 'L', 'le': 'L', 'lab': 'L', 'laborator': 'L',
        'p': 'P', 'proiect': 'P', 'project': 'P'}
KIND_RE = re.compile(r'^\((curs|c|lecture|s|seminar|l|le|lab|laborator|p|proiect|project)\),?$', re.I)
ROOM_RE = re.compile(r'(?<![\w.])\(?(?:Sala\s+)?([A-EM]\d{2,4}[a-z]?\d?[a-z]?(?:-\d)?|D0\d{2}|Bibliotec[aă])\)?,?(?![\w])')
LEGEND_RE = re.compile(r'^\s*([A-Za-zμ][\w.μ ]{0,18}?)\s*(?::|\s[-–]\s|-\s)\s*([A-ZĂÂÎȘȚ][^:]{6,})$')

SPEC = {
    'IA': ('armm-ar', ''), 'AR': ('armm-ar', ''),
    'ESCCA': ('armm-escca', ''), 'ITT': ('armm-itt', ''),
    'IM': ('armm-im', ''), 'MFN': ('armm-im', 'MFN'), 'MIAIA': ('armm-im', 'MIAIA'), 'SET': ('armm-im', 'SET'),
    'MTR': ('armm-mtr', ''), 'MTREng': ('armm-mtr-en', ''),
}


def norm_acr(a):
    a = re.sub(r'\s+', ' ', a.replace('.', ' ')).strip()
    # "C C A" -> "CCA", keep roman numerals apart: "D A II" -> "DA II"
    parts = a.split(' ')
    out, cur = [], ''
    for p in parts:
        if re.fullmatch(r'I{1,3}|IV|V|\d', p) and cur:
            out.append(cur)
            out.append(p)
            cur = ''
        elif len(p) <= 2 or (p.isupper() and len(p) <= 3):
            cur += p
        else:
            if cur:
                out.append(cur)
                cur = ''
            out.append(p)
    if cur:
        out.append(cur)
    return ' '.join(out)


def legend_of(g):
    out = {}
    for c in g['cells']:
        for part in re.split(r'\s{2,}', c['text']):
            m = LEGEND_RE.match(part)
            if m and ('.' in m.group(1) or m.group(1).replace(' ', '').isupper() or len(m.group(1)) <= 6):
                title = re.sub(r'\s*\(\d{3,5}\)\s*$', '', m.group(2)).strip()
                title = re.sub(r'\s+(Evaluare|Colocviu|Examen|Verificare)$', '', title)
                out[norm_acr(m.group(1)).replace(' ', '').upper()] = title
    return out


def _acrish(tok):
    return bool(re.fullmatch(r"[A-ZĂÂÎȘȚμ][\w.ĂÂÎȘȚăâîșțμ&-]*", tok)) and ('.' in tok or tok.isupper() or re.fullmatch(r'I{1,3}|IV', tok))


def parse_armm(text):
    s = re.sub(r'\s+', ' ', text).strip()
    if not s or s.startswith('*') or re.match(r'^(Not[ăa]|NOT[ĂA])\b', s) or LEGEND_RE.match(s):
        return []
    if re.fullmatch(r'(?:I{1,3}|IV)\s+\S+|ANUL\s+\S+|\w+, \w+, An \w+', s):
        return []
    low = s.lower()
    if re.search(r'ed\.\s*fizic|educa[țt]ie fizic|\bsport\b', low):
        return [dict(k='SP', a=None, t='Educație fizică', r=None)]
    if re.search(r'limbi\s+str', low):
        rooms = ', '.join(re.findall(r'\b[A-EM]\d{2,4}\b', s))
        return [dict(k='S', a='LS', t='Limbă străină', r=rooms or None)]
    if re.match(r'practic', low):
        m = re.search(r'\((.*)\)', s)
        return [dict(k='P', a=None, t='Practică', r=None, note=m.group(1).strip() if m else None)]
    if re.match(r'(activitate de cercetare|a\.?c\.?p\.?\s*\d|r\.?a\.?\s*\d)', low):
        n = re.search(r'\d', s)
        return [dict(k='P', a=None, t='Activitate de cercetare-proiectare' + (f' {n.group(0)}' if n else ''), r=None)]
    common = {}
    m = re.search(r'\((?:curs\s+)?facultativ\)', s, re.I)
    if m:
        common['opt'] = 'fac'
        s = s[:m.start()] + ' (Curs) ' + s[m.end():]
    m = re.search(r'\borele\s+(\d{1,2})\s*-\s*(\d{1,2})', s)
    if m:
        common['note'] = f'orele {m.group(1)}–{m.group(2)}'
        s = s[:m.start()] + s[m.end():]
    s = re.sub(r'(\S)\(', r'\1 (', s)
    s = re.sub(r'\),?(?=\S)', ') ', s)
    toks = s.split(' ')
    kinds = [i for i, t in enumerate(toks) if KIND_RE.match(t)]
    acts = []
    if kinds:
        starts = []
        for n, k in enumerate(kinds):
            if n == 0:
                starts.append(0)
                continue
            i = k
            while i - 1 > kinds[n - 1] + 1 and _acrish(toks[i - 1]):
                i -= 1
            starts.append(i)
        for n, k in enumerate(kinds):
            end = starts[n + 1] if n + 1 < len(starts) else len(toks)
            acts.append((' '.join(toks[starts[n]:k]), KIND[KIND_RE.match(toks[k]).group(1).lower()], ' '.join(toks[k + 1:end])))
    else:
        m = ROOM_RE.search(s)
        if m:
            acts.append((s[:m.start()].strip(), None, s[m.start():].strip()))
        else:
            acts.append((s, None, ''))
    out = []
    for name, kind, rest in acts:
        name = name.strip(' ,-')
        if not name:
            continue
        room = None
        m = ROOM_RE.search(rest)
        if m:
            room = m.group(1)
            rest = rest[:m.start()] + ' ' + rest[m.end():]
        prof = re.sub(r'\bSala\b', '', rest)
        prof = re.sub(r'\s+', ' ', prof).strip(' ,.-')
        prof = prof if re.search(r'[A-Za-zĂÂÎȘȚăâîșț]{3,}', prof) else None
        act = dict(common, k=kind, r=room)
        if prof:
            act['prof'] = prof
        if _acrish(name.split(' ')[0]) and len(name) <= 16 and not re.search(r'[a-zăâîșț]{4,}', name):
            act['a'] = norm_acr(name)
            act['t'] = None
        else:
            act['a'] = None
            act['t'] = name
        out.append(act)
    return out


def place_armm(room):
    if not room:
        return None
    if re.match(r'Bibliotec', room, re.I):
        return None
    return 'muncii'


def meta_armm(gc, sheet, year, level, extra):
    if level == 'master':
        head = next((h for h in gc['heads'] if re.match(r'^\w+, \w+, An', h)), sheet)
        prog = head.split(',')[0].strip()
        n = gc['code'].split('/')[-1]
        multi = extra.get('n', 1) > 1
        return dict(id=f"armm-m{year}-{prog.lower()}{'-' + n if multi else ''}", prog='m-armm', label=prog + (f' {n}' if multi else ''), sub='')
    spec = re.sub(r'^(?:I{1,3}|IV)\s+', '', gc['heads'][-1] if gc['heads'] else '').replace('.', '').replace(' ', '')
    prog, sub = SPEC.get(spec, ('armm-im', spec))
    return dict(id=gc['code'], prog=prog, label=gc['code'], sub=sub)


def build(src_dir):
    pages = []
    for path in sorted(glob.glob(os.path.join(src_dir, '*.pdf'))):
        name = os.path.basename(path)
        if re.search(r'Alba|-AB_|Master', name):
            continue   # Alba Iulia; the transposed master grids are not imported yet
        m = re.match(r'^(I{1,3}|IV)\s+(.+)\.pdf$', name)
        if not m:
            continue
        year = {'I': 1, 'II': 2, 'III': 3, 'IV': 4}[m.group(1)]
        progs = m.group(2)
        level = 'master' if progs in ('AM', 'SMCA', 'ATAE', 'LST', 'IBAIA') else 'lic'
        pages.append((path, name[:-4], year, level, {'n': 2 if progs == 'ATAE' and year == 1 else 1}))
    return build_pages('armm', pages, meta_armm, place_armm, parser=parse_armm, legend=legend_of)


def fetch(dest):
    import urllib.request
    from urllib.parse import urljoin, unquote
    ua = {'User-Agent': 'orar-utcn (+https://utcna.pages.dev)'}
    html = urllib.request.urlopen(urllib.request.Request(PAGE, headers=ua), timeout=60).read().decode('utf-8', 'replace')
    links = sorted(set(re.findall(r'href="([^"]*/ORAR/[^"]*\.pdf)"', html, re.I)))
    os.makedirs(dest, exist_ok=True)
    for href in links:
        url = urljoin(PAGE, href)
        name = unquote(url.split('/')[-1])
        if re.search(r'Alba|-AB_', name):
            continue
        data = urllib.request.urlopen(urllib.request.Request(url.replace(' ', '%20'), headers=ua), timeout=60).read()
        if data[:4] == b'%PDF':
            open(os.path.join(dest, name), 'wb').write(data)
    return dest


if __name__ == '__main__':
    src = sys.argv[1]
    if src == '--fetch':
        import tempfile
        src = fetch(tempfile.mkdtemp(prefix='armm-'))
    print(json.dumps(build(src), ensure_ascii=False))
