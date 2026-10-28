"""Facultatea de Ingineria Materialelor și a Mediului (Cluj): PDF timetables -> site data.

Layout: one page per pair of years ("Anul I-II", "Anul III-IV"). Each 2-hour slot is two sub-rows
("săptămâna impară" above, "pară" below); hours are printed "08:00-09:50" with the minutes as superscripts.
Cells: "Geometrie Descriptivă (L) / Conf. L. Scurtu / B310".
Groups are 4 digits (3811 = IM, year 1, group 1; 37xx = IPMI), each with "Sgr 1" and "Sgr 2".
The master timetables (a list per week, not a grid) are not imported yet.

python3 imm.py <dir-with-pdfs> | --fetch  -> JSON on stdout
"""
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from builder import build_pages  # noqa: E402
from common import parse_lines  # noqa: E402

PAGE = 'https://imm.utcluj.ro/orar.html'
ROOT = 'https://imm.utcluj.ro/'   # the page declares <base href> = the site root
PROG = {'8': 'imm-im', '7': 'imm-ipmi'}


def meta_imm(gc, sheet, year, level, extra):
    code = gc['code']
    m = re.fullmatch(r'3([78])(\d)(\d)', code)
    if not m:
        return None
    return dict(id=f'imm-{code}', prog=PROG[m.group(1)], label=code, sub='', year=int(m.group(2)))


def place_imm(room):
    # the faculty sits on the Muncii campus (B-dul Muncii 103-105): its rooms are letter + number
    return 'muncii' if room and re.match(r'^[A-Z]\d', room.replace(' ', '')) else None


_KIND_LINE = re.compile(r'\((?:C|S|L|P|C\+S)\)\s*$')
_PERSON = re.compile(r'^(?:Prof|Conf|Ș\.?l|S\.?l|Sl|Asist|Lect|Dr|Ing)\b', re.I)
_ROOM = re.compile(r'^(?:[A-Z]\s?\d{2,3}[a-z]?|[A-Z]\d{1,2})(?:\s|$)')


def parse_imm(text):
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    lines = [re.sub(r'(?<=\S)\(([CSLP])\)', r' (\1)', re.sub(r'\(([cslp])\)', lambda m: '(' + m.group(1).upper() + ')', l)) for l in lines]
    flat = ' '.join(lines)
    if re.search(r'\bLimbi\b.*\b(Engle|Fran|Germ)|Engle[zț]ă\s*\(S\).*Fran', flat):   # one cell, one line per language: "Limbi Engleză (S) - Paduretu S. - B102 Franceză ..."
        rooms = re.findall(r'\b([A-Z]\d{2,3})\b', flat)
        return [dict(k='S', a='LS', t='Limbă străină', r=rooms[0] if rooms else None)]
    # a subject name wrapped over two lines: "Programarea Calculatoarelor și Limbaje de" / "Programare (L)"
    for i, l in enumerate(lines):
        if _KIND_LINE.search(l):
            if i > 0 and not any(_PERSON.match(x) or _ROOM.match(x) for x in lines[:i]):
                lines[:i + 1] = [' '.join(lines[:i + 1])]
            break
    return parse_lines('\n'.join(lines))


def build(src_dir):
    pages = []
    for path in sorted(glob.glob(os.path.join(src_dir, '*.pdf'))):
        name = os.path.basename(path)
        if not re.search(r'licen', name, re.I):
            continue
        pages.append((path, re.sub(r'\.pdf$', '', name)[:40], 0, 'lic', {}))
    return build_pages('imm', pages, meta_imm, place_imm, parser=parse_imm, parser_lines=True)


def fetch(dest):
    import urllib.request
    from urllib.parse import urljoin, unquote
    ua = {'User-Agent': 'orar-utcn (+https://utcna.pages.dev)'}
    html = urllib.request.urlopen(urllib.request.Request(PAGE, headers=ua), timeout=60).read().decode('utf-8', 'replace')
    links = [h for h in re.findall(r'href\s*=\s*["\']([^"\']*\.pdf)["\']', html, re.I) if re.search(r'licen', unquote(h), re.I)]
    sem = [(max(map(int, re.findall(r'20\d\d', unquote(h)))), h) for h in links if re.search(r'Semestrul\s*1', unquote(h), re.I)]
    if not sem:
        raise SystemExit('imm: niciun PDF de licență găsit pe pagina de orar')
    newest = max(y for y, _ in sem)
    os.makedirs(dest, exist_ok=True)
    got = 0
    for y, href in sem:
        if y != newest:
            continue
        url = urljoin(ROOT, href).replace(' ', '%20')
        data = urllib.request.urlopen(urllib.request.Request(url, headers=ua), timeout=60).read()
        if data[:4] == b'%PDF':
            open(os.path.join(dest, unquote(url.split('/')[-1])), 'wb').write(data)
            got += 1
    print(f'imm: {got} PDF-uri de licență (semestrul 1 {newest - 1}-{newest})', file=sys.stderr)
    return dest


if __name__ == '__main__':
    src = sys.argv[1]
    if src == '--fetch':
        import tempfile
        src = fetch(tempfile.mkdtemp(prefix='imm-'))
    print(json.dumps(build(src), ensure_ascii=False))
