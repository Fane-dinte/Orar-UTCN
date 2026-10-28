"""Facultatea de Inginerie Industrială, Robotică și Managementul Producției (Cluj, licență): PDF timetables -> site data.

Each file has several pages, two days per page; a slot is "08:00" over "09:50", upper half odd weeks, lower half even.

python3 iirmp.py <dir-with-pdfs> | --fetch  -> JSON on stdout
"""
import glob
import json
import os
import re
import sys

import pdfplumber

sys.path.insert(0, os.path.dirname(__file__))
from builder import build_pages  # noqa: E402
from common import parse_lines  # noqa: E402

PAGE = 'https://iirmp.utcluj.ro/orar.html'
SPEC = {'5': 'rob', '4': 'iei', '1': 'tcm', '7': 'di'}
NAMES = {'rob': 'Robotică', 'iei': 'Inginerie economică industrială', 'tcm': 'TCM / Inginerie industrială', 'di': 'Design industrial'}


def meta_iirmp(gc, sheet, year, level, extra):
    code = gc['code']
    m = re.fullmatch(r'(\d)(\d)(\d)(\d)(e|g)?', code)
    if not m:
        return None
    spec = SPEC.get(m.group(2), 'tcm')
    lang = {'e': '-en', 'g': '-de'}.get(m.group(5) or '', '')
    prog = f'iirmp-{spec}{lang}' if lang != '-de' else f'iirmp-{spec}-de'
    return dict(id=f'iirmp-{code}', prog=prog, label=code, sub='')


def place_iirmp(room):
    if not room:
        return None
    return 'muncii'   # B-dul Muncii 103–105


def build(src_dir):
    pages = []
    for path in sorted(glob.glob(os.path.join(src_dir, '*.pdf'))):
        name = os.path.basename(path)
        m = re.search(r'(?:An_|^\d+_)(IV|III|II|I)[\s_]', name)
        if not m:
            continue
        year = {'I': 1, 'II': 2, 'III': 3, 'IV': 4}[m.group(1)]
        with pdfplumber.open(path) as pdf:
            n = len(pdf.pages)
            # a new table may start mid-page (its title row): cut the page there
            cuts = []
            for i in range(n):
                p = pdf.pages[i]
                words = p.extract_words()
                tops = sorted({round(w['top']) for w in words if re.fullmatch(r'Sem(?:\.|estrul)?', w['text'])})
                # only where timetable rows ("08 : 00") are printed above the title
                tops = [t for t in tops if sum(1 for w in words if w['top'] < t - 10 and re.fullmatch(r'\d{2}', w['text'])) >= 4]
                foot = [w['top'] for w in words if w['text'] == 'ULTIMA']
                cuts.append((tops, min(foot) - 5 if foot else None))
        for i in range(n):
            tops, foot = cuts[i]
            edges = [0] + [t - 8 for t in tops] + [foot]
            for k in range(len(edges) - 1):
                ex = {'page': i, 'fill': True}
                if len(edges) > 2 or foot:
                    ex['crop'] = (edges[k], edges[k + 1])
                pages.append((path, re.sub(r'\.pdf$', '', name)[:40], year, 'lic', ex))
    return build_pages('iirmp', pages, meta_iirmp, place_iirmp, parser=parse_lines, parser_lines=True)


def fetch(dest):
    import urllib.request
    from urllib.parse import urljoin, unquote
    ua = {'User-Agent': 'orar-utcn (+https://utcna.pages.dev)'}
    html = urllib.request.urlopen(urllib.request.Request(PAGE, headers=ua), timeout=60).read().decode('utf-8', 'replace')
    # the "Cluj-Napoca" licență lines come first in the page, before the extensions (Alba…)
    def pdf_links(text):
        found = re.findall(r'href\s*=\s*["\']([^"\']*\.pdf)["\']', text, re.I)
        sem1 = [h for h in found if re.search(r'sem\s*1|[_ ]s1[_ ]', h, re.I)]
        return sem1 or found
    # "Alba" also occurs earlier in the page (menu), so cut at the first one after the first Sem1 link
    first = re.search(r'href\s*=\s*["\'][^"\']*/Sem\s*1/', html, re.I)
    start = first.start() if first else 0
    end = html.find('Alba', start)
    links = pdf_links(html[start:end if end > 0 else len(html)]) or pdf_links(html)
    links = list(dict.fromkeys(links))
    print(f'iirmp: {len(links)} PDF-uri găsite pe {PAGE} ({len(html)} caractere)', file=sys.stderr)
    if not links:
        raise SystemExit('iirmp: niciun PDF găsit pe pagina de orar')
    os.makedirs(dest, exist_ok=True)
    for href in links:
        url = urljoin(PAGE, href).replace(' ', '%20')
        name = unquote(url.split('/')[-1])
        data = urllib.request.urlopen(urllib.request.Request(url, headers=ua), timeout=60).read()
        if data[:4] == b'%PDF':
            open(os.path.join(dest, name), 'wb').write(data)
    return dest


if __name__ == '__main__':
    src = sys.argv[1]
    if src == '--fetch':
        import tempfile
        src = fetch(tempfile.mkdtemp(prefix='iirmp-'))
    print(json.dumps(build(src), ensure_ascii=False))
