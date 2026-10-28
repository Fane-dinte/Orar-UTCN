"""Read a timetable drawn as a ruled grid in a PDF (Excel export) into cells.

The page is a grid: one column per semigroup, one row per 2-hour slot, days stacked.
Merged cells have no interior border. A cell split by a diagonal holds two activities:
the upper half for odd weeks, the lower half for even weeks (UTCN convention).

grid(page) -> {
  cols: [(x0, x1)], rows: [{d, s, e, y0, y1}],
  head: [{x0, x1, top, text}]   header texts with the span of their header cell,
  cells: [{rows: [i..], cols: [j..], half: 'all'|'odd'|'even', text, lines, box}]
}
"""
import re
from collections import defaultdict

CLOCK_RE = re.compile(r'^(?:[A-ZĂÂÎȘȚŞŢ]\s*)?(\d{1,2})\s*:\s*(\d{2})(?:\s*([12]))?$')
HHMM_RE = re.compile(r'^(\d{2})(\d{2})[-–](\d{2})(\d{2})$')
TIME_RE = re.compile(r'^(\d{1,2})\s*[-–]\s*(\d{1,2})(?!\d)(?:\D{0,2})$')
DAYS = ['LUNI', 'MARTI', 'MIERCURI', 'JOI', 'VINERI', 'SAMBATA']


def _cluster(vals, tol):
    vals = sorted(vals)
    out = []
    for v in vals:
        if out and v - out[-1][-1] <= tol:
            out[-1].append(v)
        else:
            out.append([v])
    return out


def segments(page):
    """Horizontal, vertical and diagonal strokes. Borders come as thin filled rects/curves."""
    H, V, D = [], [], []
    for r in page.rects:   # an outlined box: its four edges are borders
        if r.get('stroke') and r['width'] > 2.6 and r['height'] > 2.6:
            H.append((r['top'], r['x0'], r['x1']))
            H.append((r['bottom'], r['x0'], r['x1']))
            V.append((r['x0'], r['top'], r['bottom']))
            V.append((r['x1'], r['top'], r['bottom']))
    for o in list(page.rects) + list(page.curves) + list(page.lines):
        pts = o.get('pts') or [(o['x0'], o['top']), (o['x1'], o['bottom'])]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        w, h = x1 - x0, y1 - y0
        if w <= 3.3 and h <= 3.3:          # a dot of a dotted line
            V.append(((x0 + x1) / 2, y0 - .4, y1 + .4))
            H.append(((y0 + y1) / 2, x0 - .4, x1 + .4))
        elif w <= 3.3 and h > 3 * w:
            V.append(((x0 + x1) / 2, y0, y1))
        elif h <= 3.3 and w > 3 * h:
            H.append(((y0 + y1) / 2, x0, x1))
        elif 'pts' in o and o.get('object_type') in ('curve', 'line'):
            # slanted stroke drawn as a thin polygon: take the mean y at each x end
            left = [p for p in pts if p[0] - x0 < 1.6]
            right = [p for p in pts if x1 - p[0] < 1.6]
            ya = sum(p[1] for p in left) / len(left)
            yb = sum(p[1] for p in right) / len(right)
            if abs(ya - yb) > 2.5 and w > 6:
                D.append((x0, ya, x1, yb))
    return H, V, D


def _merge_diagonals(D, corner=lambda x, y: False):
    """A long diagonal may be drawn in pieces; join collinear pieces that touch
    (but not at a grid corner, where two separate cells' diagonals meet)."""
    out = []
    for d in sorted(D):
        for i, p in enumerate(out):
            if corner(d[0], d[1]):
                continue
            sp = (p[3] - p[1]) / (p[2] - p[0])
            sd = (d[3] - d[1]) / (d[2] - d[0])
            if abs(d[0] - p[2]) < 2 and abs(d[1] - p[3]) < 2 and abs(sp - sd) < 0.2 * max(abs(sp), 0.03):
                out[i] = (p[0], p[1], d[2], d[3])
                break
        else:
            out.append(d)
    return out


def _coverage(segs, pos, a, b, tol=2.2):
    """Fraction of [a, b] covered by segments lying at `pos` (±tol)."""
    iv = sorted((max(s0, a), min(s1, b)) for p, s0, s1 in segs if abs(p - pos) <= tol and s1 > a and s0 < b)
    tot, cur0, cur1 = 0, None, None
    for s0, s1 in iv:
        if cur1 is None or s0 > cur1 + 1.2:
            if cur1 is not None:
                tot += cur1 - cur0
            cur0, cur1 = s0, s1
        else:
            cur1 = max(cur1, s1)
    if cur1 is not None:
        tot += cur1 - cur0
    return tot / max(b - a, 1e-6)


def _lines_of(chars):
    """Group chars into text lines -> [{top, bottom, x0, x1, text, chars}] (phrases split on wide gaps)."""
    chars = sorted(chars, key=lambda c: (round(c['bottom'], 0), c['x0']))
    rows = []
    for c in sorted(chars, key=lambda c: c['bottom']):
        for r in rows:
            if abs(r['bottom'] - c['bottom']) < max(1.2, 0.3 * c['size']):
                r['chars'].append(c)
                break
        else:
            rows.append({'bottom': c['bottom'], 'chars': [c]})
    out = []
    for r in rows:
        cs = sorted(r['chars'], key=lambda c: c['x0'])
        phrase = []
        for c in cs:
            if phrase and c['x0'] - phrase[-1]['x1'] > 0.9 * c['size']:
                out.append(_mk_line(phrase))
                phrase = []
            phrase.append(c)
        if phrase:
            out.append(_mk_line(phrase))
    return out


def _mk_line(cs):
    s = ''
    for i, c in enumerate(cs):
        if i and c['x0'] - cs[i - 1]['x1'] > 0.18 * c['size'] and not s.endswith(' ') and c['text'] != ' ':
            s += ' '
        s += c['text']
    s = re.sub(r'\s+', ' ', s).strip()
    return {'top': min(c['top'] for c in cs), 'bottom': max(c['bottom'] for c in cs), 'x0': cs[0]['x0'], 'x1': cs[-1]['x1'],
            'text': s, 'chars': cs, 'size': max(c['size'] for c in cs)}


def grid(page, ruled_background=False, fill_boxes=False, min_clock=4):
    H, V, D = segments(page)
    up = [c for c in page.chars if c.get('upright', True) and c['text'].strip()]
    lines = _lines_of(up)

    # --- rows: the time labels in the leftmost columns
    # the time column: the first long vertical border with time labels to its left
    vlen = defaultdict(float)
    for x, a, b in V:
        if b - a > 3:
            vlen[round(x, 1)] += b - a
    vcl = []
    for cl in _cluster(list(vlen), 1.5):
        vcl.append((min(cl), sum(vlen[x] for x in cl)))
    tl = []
    mode = 'range'
    longs = sorted(x for x, L in vcl if L > page.height * 0.3)
    for i, x in enumerate(longs):
        left = longs[i - 1] - 0.8 if i else -1
        cand = [l for l in _lines_of([c for c in up if c['x1'] <= x + 0.8 and c['x0'] >= left]) if TIME_RE.match(l['text'].replace(' ', ''))]
        if len(cand) < 8:
            cand = [l for l in _lines_of([c for c in up if c['x1'] <= x + 0.8]) if TIME_RE.match(l['text'].replace(' ', ''))]
        if len(cand) >= 8:
            tl = cand
            break
        clock = [l for l in _lines_of([c for c in up if c['x1'] <= x + 0.8 and c['x0'] >= left]) if CLOCK_RE.match(l['text'].strip())]
        if len(clock) >= min_clock:
            tl = clock
            mode = 'clock'
            break
    if not tl:
        # "08:00-09:50" with the minutes printed as superscripts: the pieces sit on slightly different baselines
        for i, x in enumerate(longs):
            left = longs[i - 1] - 0.8 if i else -1
            cs = sorted((c for c in up if left <= c['x0'] and c['x1'] <= x + 0.8 and (c['text'].isdigit() or c['text'] in '-–')), key=lambda c: (c['top'] + c['bottom']) / 2)
            bands = []
            for c in cs:
                cy = (c['top'] + c['bottom']) / 2
                if bands and cy - bands[-1][0] <= 6:
                    bands[-1][1].append(c)
                else:
                    bands.append((cy, [c]))
            found = []
            for _, b in bands:
                m_ = HHMM_RE.match(''.join(c['text'] for c in sorted(b, key=lambda c: c['x0'])))
                if m_:
                    s_, e_ = int(m_.group(1)), int(m_.group(3)) + (1 if int(m_.group(4)) >= 30 else 0)
                    found.append({'top': min(c['top'] for c in b), 'bottom': max(c['bottom'] for c in b), 'x0': min(c['x0'] for c in b), 'x1': max(c['x1'] for c in b), 'text': f'{s_}-{e_}', 'size': max(c['size'] for c in b)})
            if len(found) >= 4:
                tl = found
                break
    tl.sort(key=lambda l: l['top'])
    if not tl:
        raise ValueError('nu găsesc coloana cu orele')
    if min_clock < 4 and mode == 'clock' and len(tl) < 2:
        raise ValueError('rând rupt la marginea paginii')
    tx0 = min(l['x0'] for l in tl) - 1
    tx1 = max(l['x1'] for l in tl) + 1
    # row borders: horizontal strokes, weighted by how much of the page width they cover
    ylen = defaultdict(float)
    for y, a, b in H:
        if b - a > 3:
            ylen[round(y, 1)] += b - a
    ycl = []
    for cl in _cluster(list(ylen), 1.6):
        tot = sum(ylen[y] for y in cl)
        ycl.append((sum(y * ylen[y] for y in cl) / tot, tot))
    strong = [y for y, L in ycl if L > page.width * 0.15]
    labels = []
    day = 0
    prev = None
    pars = []
    lone_first = False
    if mode == 'clock':
        # "08:00" over "09:50": one slot, the upper half for odd weeks, the lower for even weeks
        # roles: the "1"/"2" marker when printed next to the time, else alternate start/end (":50" is always an end)
        roles = []
        for l in tl:
            m_ = CLOCK_RE.match(l['text'].strip())
            if m_.group(3):
                roles.append('s' if m_.group(3) == '1' else 'e')
            elif int(m_.group(2)) >= 30:
                roles.append('e')
            else:
                roles.append('e' if roles and roles[-1] == 's' else 's')
        i = 0
        while i < len(tl):
            if i + 1 >= len(tl) or roles[i] != 's' or roles[i + 1] != 'e':
                if roles[i] == 'e' and not labels:
                    lone_first = True   # the second half of a slot that began on the previous page: this page goes on from that day
                i += 1
                continue
            a_, b_ = CLOCK_RE.match(tl[i]['text'].strip()), CLOCK_RE.match(tl[i + 1]['text'].strip())
            s_ = int(a_.group(1))
            e_ = int(b_.group(1)) + (1 if int(b_.group(2)) >= 30 else 0)
            if prev is not None and s_ <= prev:
                day += 1
            prev = s_
            labels.append((day, s_, e_, (tl[i]['top'] + tl[i]['bottom']) / 2, tl[i]))
            labels.append((day, s_, e_, (tl[i + 1]['top'] + tl[i + 1]['bottom']) / 2, tl[i + 1]))
            pars += ['odd', 'even']
            i += 2
    for l in (tl if mode == 'range' else []):
        m = TIME_RE.match(l['text'].replace(' ', ''))
        s_, e_ = int(m.group(1)), int(m.group(2))
        if prev is not None and s_ <= prev:
            day += 1
        prev = s_
        labels.append((day, s_, e_, (l['top'] + l['bottom']) / 2, l))
    if not labels:
        raise ValueError('pagină fără rânduri')
    rows = []
    for i, (d, s_, e_, cy, l) in enumerate(labels):
        yu = labels[i - 1][3] if i else None
        dn = labels[i + 1][3] if i + 1 < len(labels) else None
        h_up = (cy - yu) / 2 if yu is not None else ((dn - cy) / 2 if dn is not None else 6)
        h_dn = (dn - cy) / 2 if dn is not None else h_up
        if mode == 'clock' and len(labels) > 4:
            gaps = sorted(labels[j + 1][3] - labels[j][3] for j in range(len(labels) - 1))
            med = gaps[len(gaps) // 2] / 2
            if i + 1 < len(labels) and labels[i + 1][0] != d:
                h_dn = min(h_dn, med * 1.15)   # the last hour of a day: not down to the next day's first label
            if i and labels[i - 1][0] != d:
                h_up = min(h_up, med * 1.15)
        def snap(y, lo, hi):
            c = [z for z in strong if lo < z < hi]
            return min(c, key=lambda z: abs(z - y)) if c else y
        y0 = snap(cy - h_up, l['top'] - 2 * h_up, l['top'] + 0.5)
        y1 = snap(cy + h_dn, l['bottom'] - 0.5, l['bottom'] + 2 * h_dn)
        if mode == 'clock' and len(labels) > 4:
            if i + 1 < len(labels) and labels[i + 1][0] != d and y1 - cy > med * 1.3:
                y1 = cy + med * 1.15
        rows.append({'d': d, 's': s_, 'e': e_, 'y0': y0, 'y1': y1})
        if pars:
            rows[-1]['par'] = pars[i]
        if i == 0 and lone_first:
            rows[-1]['cont'] = True   # second half of a slot that began on the previous page
    for a_, b_ in zip(rows, rows[1:]):   # no gaps/overlaps between consecutive rows
        if mode == 'clock' and a_['d'] != b_['d'] and b_['y0'] >= a_['y1']:
            continue   # the band between two days (hour totals) belongs to neither
        if abs(a_['y1'] - b_['y0']) > 0.01:
            m = (a_['y1'] + b_['y0']) / 2 if b_['y0'] < a_['y1'] else None
            if m is not None:
                a_['y1'] = b_['y0'] = m
            else:
                b_['y0'] = a_['y1'] = (a_['y1'] + b_['y0']) / 2
    body_top, body_bot = rows[0]['y0'], rows[-1]['y1']
    # day names spelled down the left edge ("L U N I"): use them when present (a page may start on Wednesday)
    names = ['LUNI', 'MARTI', 'MIERCURI', 'JOI', 'VINERI', 'SAMBATA']
    fold = str.maketrans('ĂÂÎȘȚŞŢăâîșțşţ', 'AAISTSTaaistst')
    for d_ in sorted({r['d'] for r in rows}):
        rs = [r for r in rows if r['d'] == d_]
        y0_, y1_ = rs[0]['y0'], rs[-1]['y1']
        letters = ''.join(c['text'] for c in sorted((c for c in page.chars if c['x1'] <= tx0 + 1 and y0_ - 2 <= (c['top'] + c['bottom']) / 2 <= y1_ + 2 and c['text'].strip()), key=lambda c: (c['top'], c['x0'])))
        word = re.sub(r'[^A-Z]', '', letters.upper().translate(fold))
        hit = next((k for k, n in enumerate(names) if word and (word == n or (len(word) >= 3 and n.startswith(word)) or (len(word) >= 3 and word.startswith(n)))), None)
        for r in rs:
            r['blk'] = d_
            r['named'] = hit
        if hit is not None and mode == 'clock':
            for r in rs:
                r['d'] = hit

    # --- columns: vertical borders that run through the body
    xs_len = defaultdict(float)
    for x, a, b in V:
        ov = min(b, body_bot) - max(a, body_top)
        if ov > 0:
            xs_len[round(x, 1)] += ov
    cand = [x for x, L in xs_len.items() if L > 6 and x > tx1 - 2.5]
    bounds = []
    for cl in _cluster(cand, 3.2):
        tot = sum(xs_len[x] for x in cl)
        if tot >= (0.3 if len(rows) == 1 else 2) * (rows[0]['y1'] - rows[0]['y0']):
            bounds.append(sum(x * xs_len[x] for x in cl) / tot)
    cols = [(a, b) for a, b in zip(bounds, bounds[1:]) if b - a > 6]
    # a "Săpt. impară / Săpt. pară" column after the hours: every slot is two sub-rows (odd weeks above, even below)
    if cols:
        a0, b0 = cols[0]
        inside = ''.join(c['text'] for c in up if a0 <= (c['x0'] + c['x1']) / 2 <= b0 and c['top'] > body_top - 2)
        if b0 - a0 < 35 and len(re.findall(r'ar[ăa]', inside, re.I)) >= len(rows) * 0.8 and len(re.findall(r'[Ii]mp', inside)) >= len(rows) * 0.3:
            cols = cols[1:]
            tx1 = b0
            split = []
            for r in rows:
                h = r['y1'] - r['y0']
                mids = [y for y, L in ycl if r['y0'] + h * 0.25 < y < r['y1'] - h * 0.25 and L > (b0 - a0)]
                ym = min(mids, key=lambda y: abs(y - (r['y0'] + r['y1']) / 2)) if mids else (r['y0'] + r['y1']) / 2
                split.append(dict(r, y1=ym, par='odd'))
                split.append(dict(r, y0=ym, par='even'))
            rows = split
    # label columns repeated on the right (hours, day letters) are not part of the timetable
    while cols:
        a0, b0 = cols[-1]
        texts = [l['text'] for l in _lines_of([c for c in up if a0 <= (c['x0'] + c['x1']) / 2 <= b0 and c['top'] > body_top - 2])]
        if texts and all(TIME_RE.match(t.replace(' ', '')) or len(t.strip()) <= 2 for t in texts):
            cols = cols[:-1]
        else:
            break
    ybounds = sorted({r['y0'] for r in rows} | {r['y1'] for r in rows})
    D = _merge_diagonals(D, lambda x, y: any(abs(x - b) < 2 for b in bounds) and any(abs(y - b) < 2 for b in ybounds))

    # --- header: text above the body, each with the span of its own header cell
    head = []
    for l in lines:
        if l['bottom'] > body_top + 1:
            continue
        cy = (l['top'] + l['bottom']) / 2
        cx = (l['x0'] + l['x1']) / 2
        vb = sorted(x for x, a, b in V if a <= cy + 1 and b >= cy - 1)
        vb = [sum(c) / len(c) for c in _cluster(vb, 3.2)]
        left = [x for x in vb if x <= cx]
        right = [x for x in vb if x >= cx]
        txt = l['text']
        if re.fullmatch(r'(?:\S\s){2,}\S+', txt):   # letter-spaced: "1 5 1 1", "R O M Â N Ă"
            txt = txt.replace(' ', '')
        head.append({'x0': max(left) if left else l['x0'], 'x1': min(right) if right else l['x1'], 'top': l['top'], 'cx': cx, 'text': txt})

    # --- merged regions: union-find over (row, col) cells
    if ruled_background:
        # a ruled sheet (lines through the whole table) with activity boxes drawn on top: only the boxes separate cells
        bw = cols[-1][1] - cols[0][0] if cols else 0
        bh = body_bot - body_top
        H = [s for s in H if s[2] - s[1] < 0.97 * bw]
        V = [s for s in V if s[2] - s[1] < 0.8 * bh]
        for r in page.rects:   # box outlines always separate, however wide
            if r.get('stroke') and r['width'] > 2.6 and r['height'] > 2.6 and r['height'] < 0.5 * bh:
                H += [(r['top'], r['x0'], r['x1']), (r['bottom'], r['x0'], r['x1'])]
                V += [(r['x0'], r['top'], r['bottom']), (r['x1'], r['top'], r['bottom'])]
    nR, nC = len(rows), len(cols)
    parent = list(range(nR * nC))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    # cell background colour: two touching blocks of different colour are different activities even without a border
    def _col(v):
        if isinstance(v, (int, float)):
            v = (v,)
        return tuple(round(x, 2) for x in (v or ()) if isinstance(x, (int, float)))
    fills = [(r['x0'], r['top'], r['x1'], r['bottom'], _col(r.get('non_stroking_color')))
             for r in page.rects if r.get('fill') and r['width'] > 3 and r['height'] > 3]

    def colour(r, c):
        x, y = (cols[c][0] + cols[c][1]) / 2, (rows[r]['y0'] + rows[r]['y1']) / 2
        best = None
        for f in fills:
            if f[0] <= x <= f[2] and f[1] <= y <= f[3] and (best is None or (f[2] - f[0]) * (f[3] - f[1]) < (best[2] - best[0]) * (best[3] - best[1])):
                best = f
        if not best or not best[4] or all(v > 0.97 for v in best[4]) or best[2] - best[0] > (cols[-1][1] - cols[0][0]) * 0.9:
            return None
        return best[4]

    col_of = {(r, c): colour(r, c) for r in range(nR) for c in range(nC)} if len(fills) < 4000 else {}

    def differ(a, b):
        ca, cb = col_of.get(a), col_of.get(b)
        if fill_boxes:   # every activity is its own filled box: a box never runs into a blank cell or another box
            return ca != cb
        return ca is not None and cb is not None and ca != cb

    for r in range(nR):
        y0, y1 = rows[r]['y0'], rows[r]['y1']
        pad = min(2, (y1 - y0) * 0.15)
        for c in range(nC - 1):
            x = cols[c][1]
            if _coverage(V, x, y0 + pad, y1 - pad) < 0.45 and not differ((r, c), (r, c + 1)):
                union(r * nC + c, r * nC + c + 1)
    for r in range(nR - 1):
        if rows[r + 1]['d'] != rows[r]['d']:
            continue
        y = (rows[r]['y1'] + rows[r + 1]['y0']) / 2
        for c in range(nC):
            x0, x1 = cols[c]
            pad = min(2, (x1 - x0) * 0.1)
            if _coverage(H, y, x0 + pad, x1 - pad, tol=2.4) < 0.45 and not differ((r, c), (r + 1, c)):
                union(r * nC + c, (r + 1) * nC + c)
    # activity boxes drawn as stroked rectangles over a ruled background (Instalații): one box = one region
    for rc in page.rects:
        if rc.get('fill') or not rc.get('stroke') or rc['width'] < 5 or rc['height'] < 5:
            continue
        inside = [(r, c) for r in range(nR) for c in range(nC)
                  if rc['x0'] - 1 <= (cols[c][0] + cols[c][1]) / 2 <= rc['x1'] + 1 and rc['top'] - 1 <= (rows[r]['y0'] + rows[r]['y1']) / 2 <= rc['bottom'] + 1]
        rs = {r for r, _ in inside}
        if len(inside) < 2 or len(rs) > 6 or len({rows[r]['d'] for r in rs}) > 1:
            continue
        # the box must line up with the grid
        if abs(rc['x0'] - min(cols[c][0] for _, c in inside)) > 2.5 or abs(rc['x1'] - max(cols[c][1] for _, c in inside)) > 2.5:
            continue
        first = inside[0]
        for r, c in inside[1:]:
            union(first[0] * nC + first[1], r * nC + c)
    regions = defaultdict(list)
    for i in range(nR * nC):
        regions[find(i)].append(i)

    # map a point to a cell index
    def cell_at(x, y):
        c = next((j for j, (a, b) in enumerate(cols) if a - 0.5 <= x < b + 0.5), None)
        r = next((i for i, rw in enumerate(rows) if rw['y0'] - 0.5 <= y < rw['y1'] + 0.5), None)
        if c is None or r is None:
            return None
        return r * nC + c

    reg_of = {}
    for root, cells in regions.items():
        for i in cells:
            reg_of[i] = root

    # body text: phrases, assigned to the region holding their centre
    body_lines = _lines_of([c for c in up if c['x0'] >= tx1 - 0.5 and c['top'] >= body_top - 1])
    by_reg = defaultdict(list)
    multi = []
    for l in body_lines:
        parts = defaultdict(list)
        for ch in l['chars']:
            i = cell_at((ch['x0'] + ch['x1']) / 2, (ch['top'] + ch['bottom']) / 2)
            if i is not None:
                parts[reg_of[i]].append(ch)
        if len(parts) == 1:
            by_reg[next(iter(parts))].append(l)
        elif parts:
            multi.append((l, parts))
    for l, parts in multi:
        # a phrase crossing a border: overflow into empty neighbours stays whole,
        # otherwise it is two neighbouring texts that happen to touch
        main = max(parts, key=lambda k: len(parts[k]))
        if any(by_reg.get(k) or any(k in p2 for l2, p2 in multi if l2 is not l) for k in parts if k != main):
            for k, cs in parts.items():
                by_reg[k].append(_mk_line(sorted(cs, key=lambda c: c['x0'])))
        else:
            by_reg[main].append(l)

    cells = []
    for root, ls in by_reg.items():
        idx = regions[root]
        rr = sorted({i // nC for i in idx})
        cc = sorted({i % nC for i in idx})
        box = (cols[cc[0]][0], rows[rr[0]]['y0'], cols[cc[-1]][1], rows[rr[-1]]['y1'])
        diags = sorted((d for d in D if _diag_in_box(d, box)), key=lambda d: d[0])
        # several diagonals side by side split the region into sub-columns
        if len(diags) > 1:
            groups = []
            for d in diags:
                cs = [j for j in cc if min(cols[j][1], d[2]) - max(cols[j][0], d[0]) > 0.5 * (cols[j][1] - cols[j][0])]
                groups.append((d, cs or cc))
        else:
            groups = [(diags[0] if diags else None, cc)]
        halves = defaultdict(list)
        for l in ls:
            cx = (l['x0'] + l['x1']) / 2
            gi = min(range(len(groups)), key=lambda i: 0 if cols[groups[i][1][0]][0] - 1 <= cx <= cols[groups[i][1][-1]][1] + 1 else min(abs(cx - cols[groups[i][1][0]][0]), abs(cx - cols[groups[i][1][-1]][1])))
            d = groups[gi][0]
            if d is None:
                pars = {rows[i].get('par') for i in rr}
                halves[(gi, pars.pop() if len(pars) == 1 and None not in pars else 'all')].append(l)
                continue
            gx0, gx1 = cols[groups[gi][1][0]][0], cols[groups[gi][1][-1]][1]
            near_l, near_r = l['x0'] - gx0 < 6, gx1 - l['x1'] < 6
            if d[1] > d[3] and near_l != near_r:
                # Excel puts the odd-week text flush left and the even-week text flush right
                half = 'odd' if near_l else 'even'
            else:
                ly = lambda x: d[1] + (min(max(x, d[0]), d[2]) - d[0]) / (d[2] - d[0]) * (d[3] - d[1])
                score = (l['top'] - ly(l['x0'])) + (l['bottom'] - ly(l['x1']))
                half = 'odd' if score < 0 else 'even'
            halves[(gi, half)].append(l)
        for (gi, half), hl in halves.items():
            hl.sort(key=lambda l: (round(l['top']), l['x0']))
            rr_out = rr
            if ruled_background and len(rr) > 4:
                # an open area (box drawn with loose lines): keep the hours the text sits in
                t0, t1 = min(l['top'] for l in hl), max(l['bottom'] for l in hl)
                rr_out = [i for i in rr if rows[i]['y1'] > t0 + 1 and rows[i]['y0'] < t1 - 1] or rr
                if len(rr_out) == 1 and rr_out[0] + 1 in rr:
                    rr_out = [rr_out[0], rr_out[0] + 1]
            cells.append({'rows': rr_out, 'cols': groups[gi][1], 'half': half, 'diag': bool(diags),
                          'text': ' '.join(l['text'] for l in hl), 'lines': [l['text'] for l in hl], 'sizes': [round(l.get('size', 0), 1) for l in hl],
                          'box': [round(v, 1) for v in box]})
    return {'cols': cols, 'rows': rows, 'head': head, 'cells': cells, 'diags': D}


def _diag_in_box(d, box):
    x0, y0, x1, y1 = box
    # the diagonal must run inside the region for most of its length
    lo, hi = max(d[0], x0), min(d[2], x1)
    if hi - lo < 0.5 * (d[2] - d[0]) or hi - lo < 4:
        return False
    for t in (0.25, 0.5, 0.75):
        x = lo + t * (hi - lo)
        y = d[1] + (x - d[0]) / (d[2] - d[0]) * (d[3] - d[1])
        if not (y0 - 1.5 <= y <= y1 + 1.5):
            return False
    return True


def group_columns(g):
    """Header -> [{code, cols:{col: sg}, sgs, heads:[texts above]}]."""
    # "1 1 3 2g" -> "1132g"
    head = [dict(h, text=re.sub(r'(?<=\d)\s+(?=\d)', '', h['text'])) if re.search(r'\d \d \d', h['text']) else h for h in g['head']]
    cols = g['cols']
    rowlab = [h for h in head if re.fullmatch(r'GR\.?|Grupa|Grupe', h['text'].strip(), re.I)]
    named = [h for h in head if re.search(r'(?:Grupa|\bGR\.)\s*\w+', h['text'])]
    if named:
        gr = named
    elif rowlab:
        rl = rowlab[0]
        gr = [h for h in head if h is not rl and abs(h['top'] - rl['top']) < 3 and h['cx'] > rl['x1']]
    else:   # bare group codes in the header ("2711", "21011", "2A1_11/1")
        gr = [h for h in head if re.fullmatch(r'(?:[A-Z]{2,4}\s+)?\d{4,6}[eg]?(?:\s+[A-Z]{2,4})?|\d?[A-Z]+\d*_\d+(?:/\d+)?', h['text'].strip())]
    gr = sorted(gr, key=lambda h: h['cx'])
    gtop = min((h['top'] for h in gr), default=0)
    sg_labels = [h for h in head if h['top'] > gtop + 3 and re.fullmatch(r'\d(?:\s*-\s*\w+)?|Pachet\s*\d|[a-d]|\d{4,6}[eg]?\s*/\s*\d', h['text'].strip())]
    cxs = [h['cx'] for h in gr]
    spans = []
    for h in gr:
        own = [x for x in head if x['x0'] - 1 <= h['cx'] <= x['x1'] + 1 and not any(x['x0'] - 1 <= c <= x['x1'] + 1 for c in cxs if c != h['cx'])
               and not re.search(r'FACULTATEA|^ORAR', x['text'])]
        if own:
            w = max(own, key=lambda x: x['x1'] - x['x0'])
            spans.append([w['x0'], w['x1']])
        else:
            spans.append([h['x0'], h['x1']])
    bounds = sorted({round(a, 1) for a, b in cols} | {round(b, 1) for a, b in cols})
    for i in range(len(gr) - 1):
        if spans[i][1] > cxs[i + 1] or spans[i + 1][0] < cxs[i]:
            restart = [s_ for s_ in sg_labels if cxs[i] < s_['cx'] < cxs[i + 1] and s_['text'].strip() == '1']
            m = restart[0]['x0'] if restart else (cxs[i] + cxs[i + 1]) / 2
            bx = min((b_ for b_ in bounds if cxs[i] < b_ < cxs[i + 1]), key=lambda b_: abs(b_ - m), default=m)
            spans[i][1] = min(spans[i][1], bx) if spans[i][1] > cxs[i + 1] else spans[i][1]
            spans[i + 1][0] = max(spans[i + 1][0], bx) if spans[i + 1][0] < cxs[i] else spans[i + 1][0]
            spans[i][1] = min(spans[i][1], bx)
            spans[i + 1][0] = max(spans[i + 1][0], bx)
    out = []
    for h, (x0, x1) in zip(gr, spans):
        m = re.match(r'^(?:(\w+)\s*-\s*|[A-Z]{2,4}\s+(?=\d))?(?:Grupa\s*|GR\.\s*)?([\w/]+)(?:\s*-\s*(.+)|\s+([A-Z]{2,4}))?$', h['text'].strip())
        if not m:
            continue
        code = m.group(2)
        spec = (m.group(3) or m.group(4) or m.group(1) or '').strip()
        cc = [j for j, (a, b) in enumerate(cols) if x0 - 1 <= (a + b) / 2 <= x1 + 1]
        if not cc:
            continue
        labs = [s_ for s_ in sg_labels if x0 - 1 <= s_['cx'] <= x1 + 1]
        cmap, stext, picks = {}, {}, {}
        for j in cc:
            cx = sum(cols[j]) / 2
            inside = [s_ for s_ in labs if s_['x0'] - 1 <= cx <= s_['x1'] + 1]
            pick = min(inside or labs, key=lambda s_: abs(s_['cx'] - cx)) if labs else None
            cmap[j] = (int(re.search(r'/\s*(\d)$', pick['text']).group(1)) if pick and '/' in pick['text'] else int(re.search(r'\d', pick['text']).group(0)) if re.search(r'\d', pick['text']) else 'abcd'.index(pick['text'].strip()) + 1) if pick else (cc.index(j) + 1)
            stext[j] = pick['text'] if pick else ''
            picks[j] = id(pick) if pick else None
        distinct = list(dict.fromkeys(picks[j] for j in cc if picks[j] is not None))
        if len(distinct) > len(set(cmap.values())) and len(distinct) == len(cc) and all('/' in stext[j] for j in cc):
            cmap = {j: i + 1 for i, j in enumerate(cc)}   # "1731 / 1" printed twice: number them in order
        gx = h['cx']
        above = sorted((x for x in head if x['top'] < h['top'] - 1 and x['x0'] - 2 <= gx <= x['x1'] + 2), key=lambda x: x['top'])
        heads = [x['text'] for x in above if not re.search(r'FACULTATEA|^ORAR$|^AN$|^Serie$|^GR\.?$', x['text'])]
        out.append({'code': code, 'spec': spec, 'text': h['text'], 'cols': cmap, 'sg_text': stext, 'sgs': sorted(set(cmap.values())), 'heads': heads})
    return out
