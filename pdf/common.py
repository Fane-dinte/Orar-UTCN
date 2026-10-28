"""Shared text parsing for the PDF timetables (short UTCN notation: "PCLP - L - 366", "MEC 3, 7, 11 L", ...)."""
import re

ROMAN = {'I', 'II', 'III', 'IV', 'V', 'VI'}

PROF_RE = re.compile(r'(?:(?<=[\s\-–(/,])|^)((?:Prof|Conf|Ș\.\s?l|S\.\s?l|s\.\s?l|Sl|Lect(?:or)?|Asist|As|Dr|Ec)\.?\s?(?:univ\.?\s*)?(?:(?:dr|ing|ec|habil)\.?\s*)*[A-ZĂÂÎȘȚŞŢ][^()/]*?)(?=\)|$|\s/\s|\s\()')
WEEK_KW_RE = re.compile(r'\(?\s*\b(?:s[aă]pt(?:[aă]m[aâ]n(?:a|ile))?|weeks?)\b\.?\s*:?\s*((?:\d{1,2}\s*(?:[-–,]\s*|\s+(?=\d)))*\d{1,2})\s*\)?', re.I)
WEEK_LIST_RE = re.compile(r'(?<![\w.])(\d{1,2}(?:\s*,\s*\d{1,2})+)(?![\w.])')

ROOM_RES = [
    re.compile(r'\bsal(?:ile|a)\s*\(([^)]*)\)', re.I),
    re.compile(r'\b(?:Amf\.?|Amfiteatru(?:l)?|amf\.?)\s*((?:D0[24](?:\s+Doroba\w+)?)|Instala\w+|Recuperare|[A-Z]?\d+\w*)', re.I),
    re.compile(r'\b(D0[24]\s+Doroba\w+)(?:\s*-\s*Amf\.?)?'),
    re.compile(r'\b(?:sala|room(?:\s+no\.?)?)\s*:?\s*((?:Obs\.?\s*\d+\s?[A-Z]?\b)|(?:Amf\.?\s*\w+)|(?:[A-Za-z]{0,2}\s?\d[\w.]*(?:\s+Obs\.?)?)|(?:\w+\s+Obs\.?)|Obs\.?)', re.I),
    re.compile(r'\b(Bd\.?\s*Muncii\s+\w+)', re.I),
    re.compile(r'(?<![\w.])(Obs\.?\s*\d+\s?[A-Z]?(?![\w.])|\d+[A-Z]?\s*Obs\b\.?)', re.I),
    re.compile(r'(?<![\w.])(BT\s?\d[.,]\d{2}|BT\d{3}|BT\s?\d{3}|\d[.,]\d{1,2}\s?BT|\d\.0X\s?BT|\d\.\d{2}B)(?![\w.])', re.I),
    re.compile(r'(?<![\w.])(Bazin\s+Olimpic)', re.I),
    re.compile(r'(?<![\w.])([DHPESC]\d{2,3}[A-Za-z]?|D20[67]|EM\s?2|G\d|M\d|\d{2,3}\s?[A-Z]?(?:/[A-Z])?)(?![\w.])'),
    re.compile(r'(?<![\w.])(Energobit|Bib\.\s*\w+)', re.I),
    re.compile(r'(?<![\w.])(Obs)\b\.?', re.I),
]
KIND_TOKEN_RE = re.compile(r'(?<![A-Za-z0-9ĂÂÎȘȚăâîșț./&])([CSLP])(?![A-Za-z0-9ăâîșț/&])')
KIND_WORDS = {'curs': 'C', 'seminar': 'S', 'seminarii': 'S', 'laborator': 'L', 'lab': 'L', 'proiect': 'P', 'project': 'P', 'course': 'C', 'laboratory': 'L'}


def expand_weeks(s):
    out = set()
    for part in re.split(r'\s*,\s*|\s+', s.strip()):
        m = re.fullmatch(r'(\d{1,2})\s*[-–]\s*(\d{1,2})', part)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            out.update(range(a, b + 1))
        elif part.isdigit():
            out.add(int(part))
    # "1-7" with spaces around the dash
    m = re.fullmatch(r'\s*(\d{1,2})\s*[-–]\s*(\d{1,2})\s*', s)
    if m:
        out = set(range(int(m.group(1)), int(m.group(2)) + 1))
    return sorted(w for w in out if 1 <= w <= 14)


def weeks_parity(w):
    if w and all(x % 2 for x in w):
        return 'odd'
    if w and all(x % 2 == 0 for x in w):
        return 'even'
    return 'all'


def split_alternatives(text):
    """'A (sapt 1-7) / B (sapt 8-14)' or two courses separated by '/' -> parts. A lone '/' inside a name stays."""
    parts = [p.strip() for p in re.split(r'\s+/\s+', text) if p.strip()]
    if len(parts) > 1 and all(len(p) > 6 and re.search(r'(?:^|[\s\-–])[CSLP](?:$|[\s\-–])|curs|seminar|s[aă]pt', p, re.I) for p in parts):
        return parts
    return [text]


def clean_prof(p):
    p = re.sub(r'\s+', ' ', p).strip(' -–,)(')
    p = re.sub(r'\s+\.', '.', p)
    p = re.sub(r'\b(?:univ|dr|ing|habil|fiz|chim|mat|matem|ec)(?:\.|(?![\w.]))\s*', '', p, flags=re.I).strip()
    p = re.sub(r'\bDrd\.\s*', '', p).strip()
    p = re.sub(r'\.{2,}', '.', p)
    p = re.sub(r'^(?:S\.\s?[lL]\.?|Ș\.\s?l\.?|Ş\.\s?l\.?|SL\b|Sl\b\.?|Sef\b\.?|Șef\b\.?)\s*', 'Ș.l. ', p).strip()
    p = re.sub(r'^(Prof|Conf|Lect|Asist)\.?(?=\s|[A-ZĂÂÎȘȚŞŢ])\s*', r'\1. ', p)
    p = re.sub(r'(?<=\b[A-ZĂÂÎȘȚŞŢ])\.(?=[A-ZĂÂÎȘȚŞŢ][a-zăâîșțşţ]|[A-ZĂÂÎȘȚŞŢ]{3})', '. ', p)
    words = []
    for w in p.split(' '):
        if len(w) > 2 and w.isupper() and not w.endswith('.'):
            w = '-'.join(x.capitalize() for x in w.split('-'))
        words.append(w)
    return ' '.join(words).strip()


def _dedupe_tokens(name):
    w = name.split()
    out = []
    i = 0
    while i < len(w):
        # drop a repeat of the previous 1..3 tokens
        for n in (3, 2, 1):
            if len(out) >= n and w[i:i + n] == out[-n:]:
                i += n
                break
        else:
            out.append(w[i])
            i += 1
    return ' '.join(out)


UNIT_RE = re.compile(r'(?<![\w.(])([A-Za-z][A-Za-z0-9&./]{0,13}(?:\s[IVX]{1,3})?)\s*[-_–]\s*([CSLP])(?![A-Za-z0-9])')
UNIT_SP_RE = re.compile(r'(?<![\w.(/])([A-Za-z][A-Za-z0-9&./]{1,13})\s+([CSLP])(?:/[CSLP])?\s+(?=\d|[DHPSE]\d|BT)')
UNIT_REV_RE = re.compile(r'(?<![\w.(])([CSLP])\s*[-_–]\s*([A-Za-z][A-Za-z0-9&./]{1,13})(?![A-Za-z0-9])')


def split_units(s):
    """'IAD-S BT3.03 ME II-P BT4.02' -> two activities. A cell with a long written-out title is never split."""
    if re.search(r'[A-ZĂÂÎȘȚ]{6,}', s) and re.search(r'\(\w', s):
        return [s]
    occ = [(m.start(), m.group(1), m.group(2)) for m in UNIT_RE.finditer(s)]
    occ += [(m.start(), m.group(1), m.group(2)) for m in UNIT_SP_RE.finditer(s) if not any(abs(m.start() - o[0]) < 3 for o in occ)]
    for m in UNIT_REV_RE.finditer(s):
        before = s[:m.start()].rstrip()
        acr = m.group(2)
        if before.endswith(('-', '–')) or re.match(r'(?i)^(sala|room|amf|obs|bt\d|\d)', acr) or any(o[0] <= m.start() < o[0] + len(o[1]) + 4 for o in occ):
            continue
        occ.append((m.start(), acr, m.group(1)))
    occ.sort()
    keys = []
    for st, acr, kind in occ:
        k = (re.sub(r'\W', '', acr).upper(), kind)
        if k not in [x[0] for x in keys]:
            keys.append((k, st))
    if len(keys) < 2:
        return [s]
    cuts = [st for _, st in keys[1:]]
    parts, prev = [], 0
    for c in cuts:
        parts.append(s[prev:c])
        prev = c
    parts.append(s[prev:])
    return [p.strip() for p in parts if p.strip()]


def parse_activity(text):
    """-> list of activities found in one cell half."""
    s = re.sub(r'[`´‘’]', '', text).replace('_', '-')
    s = re.sub(r'\s+', ' ', s).strip()
    if not s:
        return []
    low = s.lower()
    if re.search(r'\bsport\b|educa[tț]ie fizic', low):
        return [dict(k='SP', a=None, t='Educație fizică', r='Bazin Olimpic' if 'bazin' in low else None)]
    common = {}
    m = re.search(r'\s*[-–]?\s*\bcom\.?\s*((?:ANII|anii|\d|I{1,3}V?\b|IV\b|TST|EA|IE|MASTER|cu\b).*?)\s*$', s)
    if m:
        common['note'] = 'comun cu ' + m.group(1).strip(' .')
        s = s[:m.start()]
    if re.search(r'\bonline\b', s, re.I):
        common['note'] = (common.get('note', '') + '; ' if common.get('note') else '') + 'online'
        s = re.sub(r'\s*[-–]?\s*\bonline\b', ' ', s, flags=re.I)
    if re.search(r'\bFACULTATIV\b', s, re.I):
        common['opt'] = 'fac'
        s = re.sub(r'\s*[-–]?\s*\bFACULTATIV\b', ' ', s, flags=re.I)
    m = PROF_RE.search(s)
    if not m:   # a bare "G Chindris" after the room of a course
        m2 = re.search(r'(?<=\s)([A-Z]\.?\s?[A-ZĂÂÎȘȚ][a-zăâîșț]{2,}(?:[\s-][A-ZĂÂÎȘȚ][a-zăâîșț]{2,})?)\s*$', s)
        if m2 and re.search(r'\b(?:C|S)\s+\S+\s+' + re.escape(m2.group(1)) + r'\s*$', s):
            m = m2
    if m and len(m.group(1)) > 6:
        common['prof'] = m.group(1)
        s = (s[:m.start(1)] + s[m.end(1):])
        s = re.sub(r'\(\s*\)', ' ', s)
    s = re.sub(r'\s(?:Ș\.?l|S\.?l|Conf|Prof|Lect)\.?\s?(?:dr\.?\s?)?(?:ing\.?)?\s*$', ' ', s + ' ').rstrip()   # a title without a name
    m = re.search(r'\(([^()]*\b[a-zăâîșț]{3,}\b[^()]*\s[^()]*\s[^()]*)\)', s)
    if m and not re.search(r'sal(a|ile)|engl|franc|germ', m.group(1), re.I):
        common['note'] = (common.get('note', '') + '; ' if common.get('note') else '') + m.group(1).strip()
        s = s[:m.start()] + ' ' + s[m.end():]
    if re.search(r'\bop[tț]ional\b', s, re.I):
        common['note'] = 'opțional'
        s = re.sub(r'\bop[tț]ional\b', ' ', s, flags=re.I)
    if re.search(r'limbi\s+moderne|limba\s+str|limbi\s+str', s, re.I):
        langs = re.findall(r'engl\w*|franc\w*|germ\w*', s, re.I)
        names = {'e': 'engleză', 'f': 'franceză', 'g': 'germană'}
        ln = ', '.join(dict.fromkeys(names[x[0].lower()] for x in langs)) if langs else ''
        rm = re.search(r'sal(?:ile|a)\s*\(([^)]*)\)', s, re.I) or re.search(r'sal(?:ile|a)\s+(.+)$', s, re.I)
        room = re.sub(r'\s+', ' ', rm.group(1)).strip(' ,') if rm else None
        if not room:
            rest = re.sub(r'(?i)limbi\s+(moderne|str\w*)|\b\d{1,2}\s*-\s*\d{1,2}\b', ' ', s)
            for rx in ROOM_RES[1:]:
                mm = rx.search(rest)
                if mm:
                    room = mm.group(1).strip()
                    break
        return [dict(common, k='S', a='LS', t='Limbă străină' + (f' ({ln})' if ln else ''), r=room)]
    out = []
    for part in split_units(s):
        act = _parse_one(part)
        if act:
            out.append(dict(common, **act))
    return out


LANG_ABBR = {'ENG': 'engleză', 'ENGLEZA': 'engleză', 'GER': 'germană', 'GERMANA': 'germană', 'FR': 'franceză', 'FRANCEZA': 'franceză'}


def _parse_one(s):
    act = {}
    m = re.match(r'^\s*(?:L\.|LB\.?|LIMBA)\s*(ENG|ENGLEZA|GER|GERMANA|FR|FRANCEZA)\.?(?=\s|$)', s, re.I)
    if m:
        act['t'] = 'Limba ' + LANG_ABBR[m.group(1).upper()]
        act['a'] = None
        s = s[m.end():]
    m = re.search(r'(?<![\w/])([CSLP])\s*/\s*([CSLP])(?![\w/])', s)
    if m:
        act['k'] = m.group(1)
        act['kk'] = m.group(1) + '/' + m.group(2)
        s = s[:m.start()] + ' ' + s[m.end():]
    wk = []
    for m in list(WEEK_KW_RE.finditer(s)):
        wk += expand_weeks(m.group(1))
    s = WEEK_KW_RE.sub(' ', s)
    for m in list(WEEK_LIST_RE.finditer(s)):
        nums = [int(x) for x in re.findall(r'\d+', m.group(1))]
        if all(1 <= x <= 14 for x in nums):
            wk += nums
            s = s[:m.start()] + ' ' * (m.end() - m.start()) + s[m.end():]
    if wk:
        act['w'] = sorted(set(wk))
    for rx in ROOM_RES:
        m = rx.search(s)
        if m:
            act['r'] = re.sub(r'\s+', ' ', m.group(1)).strip()
            s = s[:m.start()] + ' ' + s[m.end():]
            break
    for rx in ROOM_RES[-3:]:   # a second bare room token is a leftover of the same cell: drop it
        s = rx.sub(' ', s) if act.get('r') and rx.pattern.startswith('(?<![\\w.])([DHPESC]') else s
    for wd, k in KIND_WORDS.items():
        if re.search(rf'(?<![\w]){wd}(?![\w])', s, re.I):
            act['k'] = k
            s = re.sub(rf'(?<![\w]){wd}(?![\w])', ' ', s, flags=re.I)
            break
    cands = list(KIND_TOKEN_RE.finditer(s))

    def dashed(m):
        before = s[:m.start()].rstrip()
        after = s[m.end():].lstrip()
        return before.endswith(('-', '–')) or after.startswith(('-', '–'))
    if cands and 'k' not in act:
        pick = next((m for m in cands if dashed(m)), None)
        if pick is None:   # "L BZ ETH", "BZ ETH L", "EP Obs 12A L": a lone letter at either end
            ends = [m for m in cands if not s[:m.start()].strip() or not s[m.end():].strip()]
            pick = ends[0] if ends else cands[0]
        act['k'] = pick.group(1)
    if act.get('k'):
        k = act['k']
        s2 = ''
        last = 0
        for m in KIND_TOKEN_RE.finditer(s):
            if m.group(1) == k and (dashed(m) or not s[:m.start()].strip() or not s[m.end():].strip() or s[m.end():].lstrip()[:1] in '(-'):
                s2 += s[last:m.start()] + ' '
                last = m.end()
        s = s2 + s[last:]
    s = re.sub(r'\b(?:sala|room(?:\s+no)?\.?)(?=\s|$|\s*-)', ' ', s, flags=re.I)
    name = re.sub(r'\s*[-–]\s*', ' - ', s)
    name = re.sub(r'(\s-\s?)+', ' - ', name)
    name = re.sub(r'\s+', ' ', name).strip(' -–,;:/')
    m = re.search(r'\(([A-Za-z0-9 &.]{1,14})\)', name)
    um = re.search(r'^(.{8,}?)\s*\(\s*([A-Za-z][A-Za-z0-9 &.]{0,12})$', name) if not m else None
    if um:   # title wrapped before its closing parenthesis: "SISTEME ELECTROMEC. I (SE SE I"
        act['a'] = _dedupe_tokens(um.group(2).replace(' - ', ' ').strip())
        act['t'] = um.group(1).strip(' -–')
    elif re.fullmatch(r'[\W\dIVX]{0,4}', re.sub(r'\s', '', name)):
        if not act.get('t'):
            return None
    elif m and ',' not in m.group(1):
        act['a'] = m.group(1).strip()
        t = (name[:m.start()] + name[m.end():]).strip(' -–')
        act['t'] = re.sub(r'\s+', ' ', t) or None
    elif name:
        plain = _dedupe_tokens(name.replace(' - ', ' ').strip())
        words = plain.split()
        plain = plain.rstrip('.') if ' ' not in plain else plain
        longword = any(len(w) >= 6 and w.isalpha() and (w.isupper() or w[1:].islower()) for w in words)
        if len(plain) <= 18 and all(len(w) <= 14 for w in words) and sum(ch.isupper() for ch in plain) >= 2 and not re.search(r'[a-zăâîșț]{5,}|[A-ZĂÂÎȘȚ]{8,}', plain) and not longword and not (len(words) == 1 and plain.isalpha() and len(plain) >= 5 and plain.isupper()):
            act['a'] = plain
        else:
            act['t'] = name
    if act.get('t', '').startswith('Limba ') and act.get('a'):
        act['a'] = None
    if not act.get('a') and not act.get('t'):
        return None
    return act


_FOLD = str.maketrans('ĂÂÎȘȚŞŢăâîșțşţ', 'AAISTSTaaistst')


def initials(title):
    title = title.translate(_FOLD)
    stop = {'si', 'și', 'de', 'in', 'în', 'a', 'al', 'ale', 'la', 'cu', 'pe', 'pentru', 'din', 'and', 'of', 'the', 'for', 'in', 'to'}
    ws = re.findall(r'[A-Za-zĂÂÎȘȚăâîșț]+', title)
    return ''.join(w[0].upper() for w in ws if w.lower() not in stop), ''.join(w[0].upper() for w in ws)


def _subseq(a, b):
    it = iter(b)
    return all(ch in it for ch in a)


def title_index(entries):
    """acronym -> title, per sheet and global (from 'TITLE (ACR)' cells)."""
    by_sheet, glob = {}, {}
    titles = {}
    for e in entries:
        if e.get('a') and e.get('t') and e.get('a') != 'LS':
            for d in (by_sheet.setdefault(e['sheet'], {}), glob):
                if e['a'] not in d or len(e['t']) > len(d[e['a']]):
                    d[e['a']] = e['t']
        if e.get('t') and len(e['t'].strip()) >= 8:
            titles.setdefault(e['sheet'], set()).add(e['t'])
    return {'sheet': by_sheet, 'glob': glob, 'titles': titles}


def resolve_title(e, ix):
    a, t = e.get('a'), e.get('t')
    if t and not a and ' ' not in t.strip() and len(t) <= 12:
        # one word ("FIZICA", "Algebra", "PROGR", "Tcem"): the start of a long title, or an acronym in lower case
        w = re.sub(r'\W', '', t).upper()
        for d in (ix['titles'].get(e['sheet'], ()), {x for v in ix['titles'].values() for x in v}):
            hits = {x for x in d if re.sub(r'[^A-Z]', '', x.split()[0].upper()).startswith(w) and len(x) > len(t)}
            if len(hits) == 1:
                return None, hits.pop()
            if hits:
                break
        if t.strip()[1:].islower() and len(t.strip()) >= 5:
            return None, t.strip()   # "Chimie": a plain word
        a, t = t.strip(), None
    if t or not a:
        return a, t
    if not any(ch.isupper() for ch in a[1:]):
        for d in (ix['sheet'].get(e['sheet'], {}), ix['glob']):
            for k, v in d.items():
                if k.upper() == a.upper():
                    return k, v
    sh = ix['sheet'].get(e['sheet'], {})
    key = a.replace(' ', '').upper()
    for d in (sh, ix['glob']):
        for k, v in d.items():
            if k.replace(' ', '').upper() == key:
                return k, v
    for d in (sh,):
        cands = [k for k in d if k.replace(' ', '').upper().startswith(key) or key.startswith(k.replace(' ', '').upper())]
        if len(cands) == 1 and min(len(cands[0].replace(' ', '')), len(key)) >= 2:
            return cands[0], d[cands[0]]
    w = re.sub(r'\W', '', a).upper()
    if len(w) >= 3:
        hits = {x for x in ix['titles'].get(e['sheet'], ()) if re.sub(r'[^A-Z]', '', x.split()[0].upper()).startswith(w)}
        if len(hits) == 1:
            return a, hits.pop()
    # "AN. MAT." <- "ANALIZĂ MATEMATICĂ I": each abbreviated word starts a word of the title, in order
    aw = [w for w in re.split(r'[\s.]+', a.upper().translate(_FOLD)) if w]
    if len(aw) >= 2 and all(len(w) >= 2 for w in aw if not re.fullmatch(r'I{1,3}|IV', w)):
        hits = set()
        for title in ix['titles'].get(e['sheet'], ()):
            tw = [w for w in re.split(r'[\s,.-]+', title.upper().translate(_FOLD)) if w and w not in ('SI', 'DE', 'IN', 'PENTRU', 'A', 'AL', 'CU')]
            j = 0
            for w in tw:
                if j < len(aw) and w.startswith(aw[j]):
                    j += 1
            if j == len(aw):
                hits.add(title)
        if len(hits) == 1:
            return a, hits.pop()
    # "OM II" <- "ORGANE DE MAȘINI II": same roman numeral, initials of the rest
    m = re.fullmatch(r'(.+?)\s+(I{1,3}|IV|V)', a.strip())
    if m:
        core = re.sub(r'[^A-Z]', '', m.group(1).upper())
        hits = set()
        for title in ix['titles'].get(e['sheet'], ()):
            tm = re.fullmatch(r'(.+?)\s+(I{1,3}|IV|V)', title.strip())
            if tm and tm.group(2) == m.group(2):
                i1, i2 = initials(tm.group(1))
                if core and (core == i1 or core == i2 or (i1 and i1[0] == core[0] and _subseq(core, i1))):
                    hits.add(title)
        if len(hits) == 1:
            return a, hits.pop()
    # acronym hidden in the initials of a long title of the same sheet (AGAD <- Algebra Liniara, Geometrie Analitica si Diferentiala)
    letters = re.sub(r'[^A-Z]', '', a.upper().translate(_FOLD))
    if len(letters) >= 2:
        hits = []
        for title in ix['titles'].get(e['sheet'], ()):
            i1, i2 = initials(title)
            if i1 and i1[0] == letters[0] and (_subseq(letters, i1) or _subseq(letters, i2)):
                hits.append(title)
        if len(set(hits)) == 1:
            return a, hits[0]
    return a, None


# --- line-based cells ("subject" / "kind  teacher" / "room"), used by IIRMP
_TITLE_RE = re.compile(r'(?<![\w.])(Prof|Conf|Lector|Lect|Sef|Șef|Şef|S\.\s?[lL]|Ș\.\s?[lL]|Ş\.\s?[lL]|(?-i:Asist|SL)|As\.|Dr\.|Drd\.|c\.\s?d\.\s?a\.)\.?(?!\s*(?-i:DE|ȘI|ŞI|SI|ASIST|A\b(?!\.))\b)', re.I)
_ROOM_RE = re.compile(r'(?<![\w.])([A-Z]{1,2}\s?\d{2,3}[a-zA-Z]?|Atelier[^,]*|Bibliotec\w+)(?![\w:])')
_INIT_RE = re.compile(r'(?<![\w.])([A-ZĂÂÎȘȚŞŢ](?:\.\s?|\s)(?!(?:I{1,3}|IV|VI{0,3})\b)[A-ZĂÂÎȘȚŞŢ][\wăâîșțşţĂÂÎȘȚŞŢ-]+(?:\s[A-ZĂÂÎȘȚŞŢ][\wăâîșțşţĂÂÎȘȚŞŢ-]+)?|[A-ZĂÂÎȘȚŞŢ]\.[A-ZĂÂÎȘȚŞŢ][a-zăâîșțşţ]{2,}(?:\s[A-ZĂÂÎȘȚŞŢ][\wăâîșțşţ-]+)?|[A-ZĂÂÎȘȚŞŢ][\wăâîșțşţĂÂÎȘȚŞŢ-]{2,}\s[A-ZĂÂÎȘȚŞŢ]\.(?!\w)|[A-ZĂÂÎȘȚŞŢ][a-zăâîșțşţ]+\s[A-ZĂÂÎȘȚŞŢ][a-zăâîșțşţ]+$)')
_KIND_TOK = re.compile(r'(?<![\w.(])\(?(C\+S|C|S|L|P)\)?(?![\w.+])')
_NAME_RE = re.compile(r'^(?:[A-ZĂÂÎȘȚŞŢ][a-zăâîșțşţ]{2,}|[A-ZĂÂÎȘȚŞŢ]{3,})(?:[\s-](?:[A-ZĂÂÎȘȚŞŢ][a-zăâîșțşţ]{2,}|[A-ZĂÂÎȘȚŞŢ]{3,}))?$')


def _person(s):
    """'Muresan Andrei', 'MURESAN Cosmin', 'Cirebea': looks like a name (not an all-caps subject word pair)"""
    s = s.strip().rstrip('.')
    if not _NAME_RE.match(s):
        return False
    return any(re.fullmatch(r'[A-ZĂÂÎȘȚŞŢ][a-zăâîșțşţ]+', w) for w in re.split(r'[\s-]', s))


def _despace(l):
    def f(m):
        letters = m.group(1).split(' ')
        after = l[m.end():]
        if letters[-1] in 'CSLP' and re.match(r'\s+[A-Za-zĂÂÎȘȚŞŢ]{2,}', after):
            return ''.join(letters[:-1]) + ' ' + letters[-1]
        return ''.join(letters)
    return re.sub(r'(?<!\S)((?:[A-ZĂÂÎȘȚŞŢ] ){3,}[A-ZĂÂÎȘȚŞŢ])(?!\S)', f, l)


def parse_lines(text):
    lines = [re.sub(r'\s+', ' ', re.sub(r'\(\s*(C\+S|[CSLP])\s*\)', r'(\1)', re.sub(r'S[12]:\d*', ' ', l))).strip() for l in text.split('\n') if l.strip()]
    lines = [l for l in lines if l and not re.fullmatch(r'\d{1,2}\s*:\s*\d{2}(\s+[12])?|[12]|[IVX]+', l)]
    # tiny print glues words: "Chimieaplic.LC407" -> "Chimie aplic. L C407"
    lines = [re.sub(r'(?<=[a-zăâîșțşţ])(?=[A-ZĂÂÎȘȚŞŢ])|(?<=\.)(?=[A-Za-z])|(?<=[a-zăâîșț])(?=aplic|moderne)', ' ', l) if ' ' not in l and len(l) > 8 else l for l in lines]
    lines = [_despace(re.sub(r'(?<=[a-z]\.)([CSLP])(?=\s|$)', r' \1', re.sub(r'\b([CSLP])([A-Z]\d{2,3})\b', r'\1 \2', l))) for l in lines]
    # a name broken over two lines ("MURESAN" / "Cosmin")
    i = 0
    while i + 1 < len(lines):
        a_, b_ = lines[i], lines[i + 1]
        cap, up_ = r'[A-ZĂÂÎȘȚŞŢ][a-zăâîșțşţ]{2,}', r'[A-ZĂÂÎȘȚŞŢ]{3,}'
        if (re.fullmatch(up_, a_) and re.fullmatch(cap, b_)) or (re.fullmatch(cap, a_) and re.fullmatch(up_, b_)) or (i > 0 and re.fullmatch(cap, a_) and re.fullmatch(cap, b_)):
            lines[i:i + 2] = [a_ + ' ' + b_]
        i += 1
    if not lines:
        return []
    joined = ' '.join(lines)
    low = joined.lower()
    if re.search(r'ed\.?\s*fizic|educa[țţt]ie fizic|\bsport\b', low):
        return [dict(k='SP', a=None, t='Educație fizică', r=None)]
    note, weeks = [], None
    mw = re.search(r'\(?s[aă]pt\.?\s*(\d{1,2})\s*-\s*(\d{1,2})\)?', joined, re.I)
    if mw:
        weeks = list(range(int(mw.group(1)), int(mw.group(2)) + 1))
        joined_nw = joined[:mw.start()] + joined[mw.end():]
    else:
        joined_nw = joined
    m = re.search(r'\(?\b(\d{1,2})\s*-\s*(\d{1,2})\)?', joined_nw)
    if m and int(m.group(1)) >= 7 and int(m.group(2)) <= 22:
        note.append(f'orele {m.group(1)}–{m.group(2)}')
    if re.search(r'facultativ', low):
        note.append('facultativ')
    mp_ = re.search(r's[aă]pt\.?\s*(im)?par[aă]', low)
    par = ('odd' if mp_.group(1) else 'even') if mp_ else None
    if re.search(r'limbi\s*mod|limba\s+(engl|fran|germ)', low):
        rm = _ROOM_RE.search(joined)
        return [dict(k='S', a='LS', t='Limbă străină', r=rm.group(1).replace(' ', '') if rm else None)]
    clean = [re.sub(r'\(?s[aă]pt\.?\s*\d{1,2}\s*-\s*\d{1,2}\)?|\(?\b\d{1,2}\s*-\s*\d{1,2}\b\)?|\(?facultativ\)?|săptămânal|s[aă]pt\.?\s*(im)?par[aă]|\bs[aă]pt\.?$|^(im)?par[aă]$|\borele\b', ' ', l, flags=re.I).strip() for l in lines]
    kind = room = prof = None
    prof_titled = False
    subj_parts = []
    for i, l in enumerate(clean):
        if not l:
            continue
        mt = _TITLE_RE.search(l)
        if mt and prof and not prof_titled:
            subj_parts = [x for x in subj_parts if x != prof]
            prof = None
        if mt and not prof:
            prof_titled = True
            p = l[mt.start():]
            r = _ROOM_RE.search(p)
            if r:
                room = room or r.group(1).replace(' ', '')
                p = (p[:r.start()] + p[r.end():]).strip()
            # a surname continued on the next line ("Prof. Dr. Ing. Corina" / "BÎRLEANU", "Conf" / "A.RADU")
            if i + 1 < len(clean) and (re.fullmatch(r'(?:[A-ZĂÂÎȘȚŞŢ]\.\s?)?[A-ZĂÂÎȘȚŞŢ-]{3,}(?:\s[A-ZĂÂÎȘȚŞŢ][\wăâîșțşţ-]+)?', clean[i + 1] or '') or (re.search(r'\.\s*$', p) and _person(clean[i + 1] or ''))):
                p += ' ' + clean[i + 1]
                clean[i + 1] = ''
            # "SL Dr. Ing. G. BACILA M.T.G. C": the subject printed after the teacher
            mp = re.match(r'^(.*?[A-ZĂÂÎȘȚŞŢ]{3,})\s+((?:[A-ZĂÂÎȘȚŞŢ]\.){2,}.*)$', p)
            if mp:
                p, rest = mp.group(1), mp.group(2)
                l = (l[:mt.start()] + ' ' + rest).strip()
            else:
                l = l[:mt.start()].strip()
            prof = p
        r = _ROOM_RE.search(l)
        if r:
            room = room or r.group(1).replace(' ', '')
            l = (l[:r.start()] + ' ' + l[r.end():]).strip()
            l = re.sub(r'^[A-Z],\s*', '', l)
        k = _KIND_TOK.search(l)
        if k:
            kind = kind or k.group(1)[0]
            before, after = l[:k.start()].strip(), l[k.end():].strip()
            if not prof and after and _person(after):
                prof = after   # "G.D.D.T. L Cirebea", "PAC L Muresan Andrei"
                after = ''
            l = (before + ' ' + after).strip()
        l = re.sub(r'\(\s*\)', ' ', l).strip()
        if not prof and (subj_parts or kind or room) and _person(l) and (subj_parts or i > 0):
            prof = l   # a teacher's name on its own line, after the subject
            l = ''
        elif not prof and subj_parts:
            mi = _INIT_RE.search(l)
            if mi:
                prof = mi.group(1)
                l = (l[:mi.start()] + l[mi.end():]).strip()
        elif not prof and not subj_parts:
            mi = _INIT_RE.search(l)
            # on the subject's own line only a clear "X. Name" counts ("DESEN T.", "A FORMEI" are words)
            if mi and mi.start() > 0 and re.match(r'[A-ZĂÂÎȘȚŞŢ]\.\s?[A-ZĂÂÎȘȚŞŢ][\wăâîșțşţ-]{2,}', mi.group(1)) and mi.end() >= len(l.rstrip()) - 1:
                prof = mi.group(1)
                l = l[:mi.start()].strip()
            else:
                # "U.F.I. MURESAN Cosmin": an acronym then a name
                mn = re.match(r'^((?:[A-ZĂÂÎȘȚŞŢ]{1,5}\.\s?){2,}(?:I{1,3}\s)?)\s*(.+)$', l)
                if mn and _person(mn.group(2)):
                    prof = mn.group(2)
                    l = mn.group(1).strip()
        l = re.sub(r'\s+', ' ', l).strip(' -,')
        if l:
            subj_parts.append(l)
    if not subj_parts:
        return []
    subj = subj_parts[0]
    if len(subj_parts) > 1 and (subj.upper().endswith(('.', 'ŞI', 'ȘI', 'SI', ' DE', ' A', ' PT', ' PT.')) or re.match(r'^[A-ZĂÂÎȘȚŞŢ .]+$', subj_parts[1]) and subj.isupper()):
        subj = subj + ' ' + subj_parts[1]
    subj = re.sub(r'\(\s*\d+\s*cursuri\s*\)', '', subj, flags=re.I).strip()
    if _person(subj) and not kind and len(subj_parts) == 1 and ' ' in subj:
        return []   # only a teacher's name (the rest of a box cut by a row line)
    act = {'k': kind, 'r': room}
    if prof:
        act['prof'] = re.sub(r'(?<=[a-z])\.(?=[A-ZĂÂÎȘȚŞŢ])', '. ', re.sub(r'(?<=\w{3})\.$', '', prof.strip(' ,-')))
    if note:
        act['note'] = '; '.join(note)
    if weeks:
        act['w'] = weeks
    if par:
        act['par'] = par
    if 'facultativ' in note:
        act['opt'] = 'fac'
    if re.fullmatch(r"(?:[A-ZĂÂÎȘȚŞŢ]{1,5}\.\s?){2,}(?:\s?I{1,3})?|[A-Z]{2,6}(?:\s+I{1,3})?", subj):
        act['a'], act['t'] = subj, None
    else:
        act['a'], act['t'] = None, subj
    return [act]
