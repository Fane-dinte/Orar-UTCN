"""Facultatea de Electronică, Telecomunicații și Tehnologia Informației: PDF timetables -> site data.

python3 etti.py <dir-with-pdfs> | --fetch  -> JSON on stdout
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from builder import build_pages  # noqa: E402

BASE = 'https://etti.utcluj.ro/files/Acasa/Site/orar/'
PAGE = 'https://etti.utcluj.ro/orar.html'

# file, year, level, program, series/spec
FILES = [
    ('i_a', 1, 'lic', 'etti-ro', 'A'), ('i_b', 1, 'lic', 'etti-ro', 'B'), ('i_eng', 1, 'lic', 'etti-en', ''),
    ('ii_a', 2, 'lic', 'etti-ro', 'A'), ('ii_b', 2, 'lic', 'etti-ro', 'B'), ('ii_eng', 2, 'lic', 'etti-en', ''),
    ('iii_ea_mon', 3, 'lic', 'etti-ro', 'EA'), ('iii_tst', 3, 'lic', 'etti-ro', 'TST'), ('iii_eng', 3, 'lic', 'etti-en', ''),
    ('iii_ie', 3, 'lic', 'etti-ie', 'IE'),
    ('iv_ea_eng', 4, 'lic', 'etti-ro', 'EA'), ('iv_tst_eng', 4, 'lic', 'etti-ro', 'TST'), ('iv_ie', 4, 'lic', 'etti-ie', 'IE'),
    ('m_i_csi', 1, 'master', 'm-etti', 'CSI'), ('m_i_ie', 1, 'master', 'm-etti', 'MIE'), ('m_i_iapset', 1, 'master', 'm-etti', 'IAPSET'),
    ('m_i_tm', 1, 'master', 'm-etti', 'TM'), ('m_i_tc', 1, 'master', 'm-etti', 'TC'), ('m_i_tsaea', 1, 'master', 'm-etti', 'TSAeA'),
    ('m_ii_csi', 2, 'master', 'm-etti', 'CSI'), ('m_ii_ie', 2, 'master', 'm-etti', 'MIE'), ('m_ii_iapset', 2, 'master', 'm-etti', 'IAPSET'),
    ('m_ii_tm', 2, 'master', 'm-etti', 'TM'), ('m_ii_tc', 2, 'master', 'm-etti', 'TC'), ('m_ii_tsaea', 2, 'master', 'm-etti', 'TSAeA'),
]
# SICAS (m_i_sicas, m_ii_sicas) is a week-by-week modular plan with AFT Sibiu, not a weekly grid: not imported.


def place_etti(room):
    """From Legenda_locatii.pdf."""
    if not room:
        return None
    R = room.upper().replace(' ', '')
    if 'BAZIN' in R or 'NATATIE' in R:
        return 'sport'
    if re.fullmatch(r'\d\.\d{1,2}B(T)?|BT\d\.?\d{2}|\d\.0XBT', R):
        return 'bt'
    if re.fullmatch(r'359|41|40|367|368|32[0189]|D1[12]|D22|P0[13]|E04|S01|S22|H01|H22', R):
        return 'bar'
    if re.fullmatch(r'211|216', R):
        return 'constr'
    if re.fullmatch(r'205|424', R):
        return 'daic'
    if re.fullmatch(r'(3\d\d|4\d\d|5[01]\d)[A-Z]?(/[A-Z])?', R):
        return 'obs'
    if re.fullmatch(r'(2[01]\d)[A-Z]?(/[A-Z])?|D02|M\d', R):
        return 'dor'
    return None


def split_ie(gcols):
    """A third column labelled '3 - IE' under an ELTC group is the Economic Engineering group: make it its own group."""
    out = []
    for gc in gcols:
        ie_cols = [j for j, lab in gc.get('sg_text', {}).items() if re.search(r'-\s*IE\b', lab)]
        if ie_cols and len(ie_cols) < len(gc['cols']):
            rest = {j: s for j, s in gc['cols'].items() if j not in ie_cols}
            out.append(dict(gc, cols=rest, sgs=sorted(set(rest.values()))))
            out.append(dict(gc, code='IE', spec='IE', cols={j: 1 for j in ie_cols}, sgs=[1], force_prog='etti-ie'))
        elif ie_cols:
            out.append(dict(gc, spec='IE', force_prog='etti-ie'))
        else:
            out.append(gc)
    return out


def meta_etti(gc, sheet, year, level, extra):
    prog, series = extra['prog'], extra['series']
    if gc.get('force_prog'):
        prog = gc['force_prog']
    code = gc['code']
    spec = (gc.get('spec') or '').strip()
    if level == 'master':
        return dict(id=f'etti-m{year}-{series.lower()}', prog='m-etti', label=series, sub='')
    if prog == 'etti-ie':
        return dict(id=f'etti-{year}ie' + ('' if code in ('1', 'IE') else f'-{code}'), prog=prog, label=f'IE {year}' if code in ('1', 'IE') else f'IE {code}', sub='Inginerie economică')
    if prog == 'etti-en' or re.fullmatch(r'Eng', spec, re.I):
        sp = spec if spec and not re.fullmatch(r'Eng', spec, re.I) else (series if series in ('EA', 'TST') else '')
        return dict(id=f'etti-{year}en-{(sp or "g").lower()}{code}', prog='etti-en', label=(f'{sp} {code}' if sp else f'Grupa {code}'), sub='English')
    if spec in ('MON',):
        return dict(id=f'etti-{year}mon-{code}', prog=prog, label=f'MON {code}', sub='Microelectronică')
    if year <= 2:
        return dict(id=f'etti-{year}{series.lower()}-{code}', prog=prog, label=code, sub=f'seria {series}')
    return dict(id=f'etti-{year}{series.lower()}-{code}', prog=prog, label=f'{series} {code}', sub={'EA': 'Electronică aplicată', 'TST': 'Telecomunicații'}.get(series, series))


def build(src_dir):
    pages, missing = [], []
    for stem, year, level, prog, series in FILES:
        path = os.path.join(src_dir, stem + '.pdf')
        if not os.path.exists(path):
            missing.append(f'lipsește {stem}')
            continue
        pages.append((path, stem, year, level, {'prog': prog, 'series': series, 'split_cols': split_ie}))
    res = build_pages('etti', pages, meta_etti, place_etti)
    res['warnings'] = missing + res['warnings']
    return res


def fetch(dest):
    import time
    import urllib.request
    ua = {'User-Agent': 'orar-utcn (+https://utcna.pages.dev)', 'Cache-Control': 'no-cache'}
    os.makedirs(dest, exist_ok=True)
    for stem, *_ in FILES:
        url = f'{BASE}{stem}.pdf?v={int(time.time())}'
        data = urllib.request.urlopen(urllib.request.Request(url, headers=ua), timeout=60).read()
        if data[:4] != b'%PDF':
            raise RuntimeError(f'{url}: nu e PDF')
        open(os.path.join(dest, stem + '.pdf'), 'wb').write(data)
    return dest


if __name__ == '__main__':
    src = sys.argv[1]
    if src == '--fetch':
        import tempfile
        src = fetch(tempfile.mkdtemp(prefix='etti-'))
    print(json.dumps(build(src), ensure_ascii=False))
