"""Shared PDF-faculty builder: pages -> groups + entries in the site's data shape."""
import json
import os
import re

import pdfplumber

from pdfgrid import grid, group_columns
from common import (parse_activity, split_alternatives, title_index, resolve_title, weeks_parity, clean_prof)

DAY = ['L', 'Ma', 'Mi', 'J', 'V', 'S']


def stamp_of(path):
    try:
        with pdfplumber.open(path) as pdf:
            md = pdf.metadata.get('ModDate') or pdf.metadata.get('CreationDate') or ''
        m = re.search(r'(\d{4})(\d{2})(\d{2})', str(md))
        if m:
            return f'{m.group(3)}.{m.group(2)}.{m.group(1)}'
    except Exception:
        pass
    return None


def later(a, b):
    if not a:
        return b
    if not b:
        return a
    return a if a[6:] + a[3:5] + a[:2] >= b[6:] + b[3:5] + b[:2] else b


def build_pages(dept, pages, meta, place, norm_room=lambda r: r, default_room=None, default_place=None, page_index=0, parser=None, legend=None, parser_lines=False):
    """pages: [(path, sheet, year, level, extra)]; meta(gc, sheet, year, level, extra) -> dict(id, prog, label, sub) or None (skip)."""
    default_room = default_room or {}
    default_place = default_place or {}
    groups, entries, notes, warnings = [], {}, {}, []
    stamp = None
    raw = []
    parser = parser or parse_activity
    legends = {}
    carry = {}
    for path, sheet, year, level, extra in pages:
        stamp = later(stamp, stamp_of(path))
        try:
            with pdfplumber.open(path) as pdf:
                pidx = (extra or {}).get('page', page_index)
                pg = pdf.pages[pidx]
                if (extra or {}).get('crop'):
                    pg = pg.crop((0, extra['crop'][0], pg.width, extra['crop'][1] or pg.height))
                g = grid(pg, ruled_background=bool((extra or {}).get('ruled')), fill_boxes=bool((extra or {}).get('fill')), min_clock=(extra or {}).get('min_clock', 4))
        except Exception as e:  # noqa: BLE001
            if (extra or {}).get('tail') and carry.get(path):
                carry[path]['last_day'] += 1   # a table cut by the page edge: its first slot is the start of the next day, the rest is on the next page
                continue
            if not (extra or {}).get('min_clock'):
                warnings.append(f'{sheet}: {e}')
            continue
        gcols = group_columns(g)
        ex = extra or {}
        if ex.get('page') is not None:
            # a page of a multi-page file: days continue from the previous page, the header may be missing
            prev = carry.get(path)
            blocks = []
            for r in g['rows']:
                if not blocks or blocks[-1][0] != r.get('blk', r['d']):
                    blocks.append((r.get('blk', r['d']), r.get('named'), r['s'] + (100 if r.get('cont') else 0)))
            day_of = {}
            last = prev['last_day'] if prev else -1
            for bi, (blk, named, s0) in enumerate(blocks):
                if named is not None:
                    d_ = named
                elif bi == 0 and prev and s0 > 8:
                    d_ = prev['last_day']
                else:
                    d_ = last + 1
                day_of[blk] = d_
                last = d_
            for r in g['rows']:
                r['d'] = day_of.get(r.get('blk', r['d']), r['d'])
            if not gcols and prev:
                pc = prev['cols']
                for gc0 in prev['gcols']:
                    cm = {}
                    for j, (a_, b_) in enumerate(g['cols']):
                        cx = (a_ + b_) / 2
                        k = min(range(len(pc)), key=lambda i: abs((pc[i][0] + pc[i][1]) / 2 - cx))
                        if abs((pc[k][0] + pc[k][1]) / 2 - cx) < 12 and k in gc0['cols']:
                            cm[j] = gc0['cols'][k]
                    if cm:
                        gcols.append(dict(gc0, cols=cm))
            carry[path] = {'last_day': last, 'cols': g['cols'] if group_columns(g) or not prev else prev['cols'],
                           'gcols': [dict(x) for x in (group_columns(g) or (prev['gcols'] if prev else []))]}
        if extra and extra.get('split_cols'):
            gcols = extra['split_cols'](gcols)
        if not gcols:
            warnings.append(f'{sheet}: nu găsesc grupele în antet')
            continue
        page_groups = []
        for gc in gcols:
            m = meta(gc, sheet, year, level, extra or {})
            if not m:
                continue
            gc.update(m)
            if gc['id'] in entries and (extra or {}).get('page'):
                page_groups.append(gc)   # same group, continued on another page of the same file
                continue
            if gc['id'] in entries:
                gc['id'] += f'-{len(entries)}'
            groups.append({'id': gc['id'], 'label': gc['label'], 'prog': gc['prog'], 'year': year, 'sgs': gc['sgs'], 'sub': gc.get('sub', ''), 'sheet': sheet, 'dept': dept, 'fac': gc.get('fac', dept)})
            entries[gc['id']] = []
            page_groups.append(gc)
        notes.setdefault(sheet, [])
        if legend:
            legends[sheet] = legend(g)
        for ci, c in enumerate(g['cells']):
            r0, r1 = g['rows'][c['rows'][0]], g['rows'][c['rows'][-1]]
            if r0['d'] != r1['d']:
                continue
            t_s, t_e = r0['s'], r1['e']
            if r0.get('par') and (r0['par'] == 'even' or r1['par'] == 'odd') and len(c['rows']) >= 2:
                # odd/even sub-rows used as hours: a block over 3 sub-rows is a 3-hour activity
                t_s = r0['s'] + (1 if r0['par'] == 'even' else 0)
                t_e = r1['e'] - (1 if r1['par'] == 'odd' else 0)
            text = c['text'].strip()
            if not text or re.fullmatch(r'[\W_]*', text):
                continue
            col = c['cols'][0]
            src = f"{sheet}{'/p' + str(pidx) if pidx else ''}!{DAY[r0['d']]}{r0['s']}-{r1['e']}#{col}"
            alts = ['\n'.join(c.get('lines') or [text])] if parser_lines else split_alternatives(text)
            ncell = len({gc['id'] for gc in page_groups if any(j in gc['cols'] for j in c['cols'])})
            for alt_i, alt in enumerate(alts):
                for act_i, act in enumerate(parser(alt)):
                    if act.get('w'):
                        act['p'] = weeks_parity(act['w'])
                        if c['half'] != 'all' and act['p'] == 'all':
                            act['p'] = c['half']
                    else:
                        act['p'] = act.pop('par', None) or c['half']
                    if len(alts) > 1 and not act.get('w'):
                        act['choice'] = 1
                    for gc in page_groups:
                        sgs = sorted({gc['cols'][j] for j in c['cols'] if j in gc['cols']})
                        if not sgs:
                            continue
                        e = dict(act)
                        if not e.get('k'):
                            # unmarked: a course when it spans groups or has a long name, a lab for part of a group
                            e['k'] = 'C' if ncell > 1 or (e.get('t') and len(e['t']) > 16) else ('L' if sgs != gc['sgs'] else 'S')
                        e.update(d=r0['d'], s=t_s, e=t_e, sg=sgs, all=sgs == gc['sgs'], raw=alt, src=src + (f'/{alt_i}' if alt_i else '') + (f'.{act_i}' if act_i else ''), sheet=sheet)
                        raw.append((gc['id'], e))
    # titles: long names written in course cells, matched to the short acronyms used elsewhere
    tix = title_index([e for _, e in raw])
    for sheet, lg in legends.items():   # "ABBR : full name" tables printed next to the timetable
        for k, v in lg.items():
            tix['sheet'].setdefault(sheet, {})[k] = v
            tix['glob'].setdefault(k, v)
            tix['titles'].setdefault(sheet, set()).add(v)
    for gid, e in raw:
        a, t = resolve_title(e, tix)
        w0 = a.split()[0] if a else ''
        if not t and a and re.fullmatch(r'[A-ZĂÂÎȘȚ]{6,}(?: I{1,3})?', a) and (len(w0) >= 8 or sum(ch in 'AEIOUĂÂÎ' for ch in w0) / len(w0) >= 0.4):
            a, t = None, a   # a plain word written in capitals is a name, not an acronym
        k = e.get('k')
        r = e.get('r')
        if not r and (a, k) in default_room:
            r = default_room[(a, k)]
        mo = re.search(r'orele (\d+)–(\d+)', e.get('note') or '')
        if mo and e['s'] <= int(mo.group(1)) < int(mo.group(2)) <= e['e'] + 1:
            e['s'], e['e'] = int(mo.group(1)), int(mo.group(2))   # "(orele 16-17)" in a 2-hour box
            e['note'] = re.sub(r';?\s*orele \d+–\d+;?\s*', '; ', e['note']).strip('; ') or None
        out = {'d': e['d'], 's': e['s'], 'e': e['e'], 'p': e['p'], 'k': k or 'C', 'a': a, 't': t, 'r': norm_room(r) or None, 'sg': e['sg'], 'all': e['all']}
        if e.get('w'):
            out['w'] = e['w']
        if e.get('prof'):
            out['prof'] = clean_prof(e['prof'])
        if e.get('note'):
            out['note'] = e['note']
        if e.get('choice'):
            out['choice'] = 1
        if e.get('opt'):
            out['opt'] = e['opt']
        if e.get('kk'):
            out['note'] = (out.get('note', '') + '; ' if out.get('note') else '') + {'L/P': 'laborator/proiect', 'C/S': 'curs/seminar', 'S/L': 'seminar/laborator'}.get(e['kk'], e['kk'])
        pl = default_place.get(out['r']) or place(out['r']) or ('sport' if k == 'SP' else None)
        if pl:
            out['pl'] = pl
        out['raw'] = re.sub(r'\s+', ' ', e['raw']).strip() if not os.environ.get('RAWLINES') else e['raw']
        out['src'] = e['src'].split('!', 1)[1]
        out['_sheet'] = e['sheet']
        entries[gid].append(out)
    # same source cell for several groups -> "n"
    share = {}
    for gid, lst in entries.items():
        for e in lst:
            share.setdefault((e['_sheet'], e['src']), set()).add(gid)
    for gid, lst in entries.items():
        seen = set()
        keep = []
        for e in sorted(lst, key=lambda x: (x['d'], x['s'], x['e'])):
            n = len(share[(e['_sheet'], e['src'])])
            if n > 1:
                e['n'] = n
            del e['_sheet']
            key = json.dumps([e['d'], e['s'], e['e'], e['p'], e.get('w'), e['sg'], e['a'], e['t'], e['r'], e['k']])
            if key in seen:
                continue
            seen.add(key)
            keep.append(e)
        # a 4h lab drawn as two stacked 2h cells -> one entry
        merged = []
        for e in keep:
            p = next((x for x in reversed(merged) if x['d'] == e['d'] and x['e'] == e['s'] and all(x.get(k) == e.get(k) for k in ('p', 'w', 'sg', 'k', 'a', 't', 'r', 'prof'))), None)
            if p:
                p['e'] = e['e']
                p['src'] += '+' + e['src']
            else:
                merged.append(e)
        entries[gid] = merged
    return {'dept': dept, 'stamp': stamp, 'groups': groups, 'entries': entries, 'notes': notes, 'langs': {}, 'warnings': warnings}


