"""Facultatea de Inginerie Electrică: PDF timetables -> site data (same shape as the xlsx departments).

python3 ie.py <dir-with-pdfs>  -> JSON on stdout
"""
import glob
import json
import os
import re
import sys

import pdfplumber

sys.path.insert(0, os.path.dirname(__file__))
from builder import build_pages  # noqa: E402

PAGES = [  # file stem suffix, year, level
    ('An_I', 1, 'lic'), ('An_II', 2, 'lic'), ('An_III', 3, 'lic'), ('An_IV', 4, 'lic'),
    ('Master_I', 1, 'master'), ('Master_II', 2, 'master'),
]
PROG_BY_DIGIT = {'1': 'ie-el', '2': 'ie-el', '3': 'ie-el', '4': 'ie-el', '5': 'ie-en', '6': 'ie-med', '7': 'ie-econ'}
SPEC = {'ETH': 'Electrotehnică', 'I&AD': 'Instrumentație și achiziții de date', 'EP&AE': 'Electronică de putere și acționări electrice',
        'EM': 'Electromecanică', 'ISE': 'Ingineria sistemelor electroenergetice', 'SIST. EN': 'Ingineria sistemelor electroenergetice'}

# --- rooms (from ORAR_FIE_..._Legenda.pdf)
def place_ie(room):
    if not room:
        return None
    R = room.upper().translate(str.maketrans('ĂÂÎȘȚŞŢ', 'AAISTST')).replace('AMF.', '').replace('AMFITEATRU', '').replace('SALA', '').strip()
    R = re.sub(r'\s+', ' ', R)
    if 'BAZIN' in R:
        return 'sport'
    if 'INSTALATII' in R:
        return 'aula'
    if 'DOROB' in R or re.fullmatch(r'D0[24]|D20[67]|CEST.*', R):
        return 'dor'
    if 'OBS' in R or re.fullmatch(r'102|106A|13[AB]', R):
        return 'obs'
    if 'MUNCII' in R or re.fullmatch(r'A022|C ?105|C ?20[1]|C ?408|C ?103|D17|C ?304B?|C ?404M', R):
        return 'muncii'
    if re.fullmatch(r'S ?26', R):
        return 'simtex'
    if re.fullmatch(r'BT ?\d[.,]?\d\d|BT\d+', R):
        return 'bt'
    if re.fullmatch(r'EM ?2|206|504', R):
        return 'turn'
    if re.fullmatch(r'159|216|211', R):
        return 'constr'
    if re.fullmatch(r'49|E08|E15|H\d\d|24|P0[23]|D2[12]|D1[12]|S12|318|16A|366|41|51|17', R):
        return 'bar'
    return None


DEFAULT_ROOM = {('FIZ', 'L'): 'Lab. Fizică', ('BZ ETH', 'L'): 'BT 3.01'}
DEFAULT_PLACE = {'Lab. Fizică': 'constr'}


def norm_room(r):
    if not r:
        return r
    r = re.sub(r'^\s*[-–]\s*', '', r).strip(' -–,')
    r = re.sub(r'^BT\s?(\d)[.,]?(\d\d)$', r'BT\1.\2', r)  # BT403 / BT4.03 / BT 4.03
    r = re.sub(r'^BT(\d)(\d\d)$', r'BT\1.\2', r)
    m = re.match(r'^(?:Obs\.?\s*)(\w+)$|^(\w+)\s+Obs\.?$', r, re.I)
    if m:
        r = f"{m.group(1) or m.group(2)} Obs"
    r = re.sub(r'\bAmf(?:iteatru|\.)\s*(D0[24])\s*Doroba[nt]*ilor\b', r'\1 Dorobanților', r, flags=re.I)
    r = re.sub(r'^(D0[24])\s+Doroba[nt]*ilor(\s*-\s*Amf\.?)?$', r'\1 Dorobanților', r, flags=re.I)
    r = re.sub(r'^(?:Amfiteatru\s+|Amf\.\s*)?Instala[tț]ii$', 'Amf. Instalații', r, flags=re.I)
    return r


def meta_ie(gc, sheet, year, level, extra):
    if level == 'lic':
        sub = ''
        for t in gc['heads']:
            m = re.match(r'^Seria\s+([IVX]+)$', t, re.I)
            if m:
                sub = f'seria {m.group(1)}'
            m = re.match(r'^(?:I{1,3}|IV)\s+(ETH|I&AD|EP&AE|EM)$', t)
            if m:
                sub = m.group(1)
        prog = PROG_BY_DIGIT.get(gc['code'][1], 'ie-el') if len(gc['code']) == 4 else 'ie-el'
        return dict(id=gc['code'], prog=prog, label=gc['code'], sub=sub)
    mp = next((t for t in reversed(gc['heads']) if not re.search(r'INGINERIE|ING\.|^ING', t, re.I)), gc['heads'][-1] if gc['heads'] else 'master')
    mp = re.sub(r'\s+', ' ', mp).strip()
    return dict(id=f"ie-m{year}-{re.sub(r'[^a-z0-9]+', '', mp.lower())}-{gc['code']}", prog='m-ie', label=f"{mp} {gc['code']}", sub=mp)


def build(src_dir):
    pages = []
    missing = []
    for suffix, year, level in PAGES:
        files = sorted(glob.glob(os.path.join(src_dir, f'*_{suffix}.pdf')))
        if not files:
            missing.append(f'lipsește {suffix}')
            continue
        pages.append((files[0], suffix.replace('_', ' '), year, level, None))
    res = build_pages('ie', pages, meta_ie, place_ie, norm_room, DEFAULT_ROOM, DEFAULT_PLACE)
    res['warnings'] = missing + res['warnings']
    return res


PAGE = 'https://ie.utcluj.ro/schedule.html'


def fetch(dest):
    """Download the current PDFs listed on the faculty's timetable page (Cluj only, no Bistrița)."""
    import urllib.request
    from urllib.parse import urljoin
    ua = {'User-Agent': 'orar-utcn (+https://utcna.pages.dev)'}
    html = urllib.request.urlopen(urllib.request.Request(PAGE, headers=ua), timeout=60).read().decode('utf-8', 'replace')
    links = sorted(set(re.findall(r'href="([^"]*ORAR_FIE[^"]*\.pdf)"', html, re.I)))
    os.makedirs(dest, exist_ok=True)
    got = []
    for href in links:
        if re.search(r'_BN\.pdf$|Legenda', href, re.I):
            continue
        url = urljoin(PAGE, href)
        data = urllib.request.urlopen(urllib.request.Request(url, headers=ua), timeout=60).read()
        if data[:4] != b'%PDF':
            raise RuntimeError(f'{url}: nu e PDF')
        name = os.path.basename(href)
        open(os.path.join(dest, name), 'wb').write(data)
        got.append(name)
    if not got:
        raise RuntimeError('nu am găsit PDF-urile pe pagina facultății')
    return dest


if __name__ == '__main__':
    src = sys.argv[1]
    if src == '--fetch':
        import tempfile
        src = fetch(tempfile.mkdtemp(prefix='ie-'))
    print(json.dumps(build(src), ensure_ascii=False))
