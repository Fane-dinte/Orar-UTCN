// Static calendar subscriptions: one .ics per group + semigroup, all weeks of the semester expanded.
import fs from 'node:fs';
import path from 'node:path';
import { PLACES } from './rooms.mjs';

const KIND = { C: 'curs', S: 'seminar', L: 'laborator', P: 'proiect', X: '', SP: 'sport' };
const pad = (n) => String(n).padStart(2, '0');
const esc = (s) => String(s || '').replace(/\\/g, '\\\\').replace(/;/g, '\\;').replace(/,/g, '\\,').replace(/\n/g, '\\n');
const fold = (line) => { const out = []; let s = line; while (s.length > 74) { out.push(s.slice(0, 74)); s = ' ' + s.slice(74); } out.push(s); return out.join('\r\n'); };

const VTZ = [
  'BEGIN:VTIMEZONE', 'TZID:Europe/Bucharest',
  'BEGIN:STANDARD', 'DTSTART:19701025T040000', 'TZOFFSETFROM:+0300', 'TZOFFSETTO:+0200', 'TZNAME:EET', 'RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU', 'END:STANDARD',
  'BEGIN:DAYLIGHT', 'DTSTART:19700329T030000', 'TZOFFSETFROM:+0200', 'TZOFFSETTO:+0300', 'TZNAME:EEST', 'RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU', 'END:DAYLIGHT',
  'END:VTIMEZONE',
];

export function occurs(e, week) {
  if (e.w) return e.w.includes(week);
  if (e.p === 'odd') return week % 2 === 1;
  if (e.p === 'even') return week % 2 === 0;
  return true;
}

function hh(x) { const h = Math.floor(x), m = Math.round((x - h) * 60); return `${pad(h)}${pad(m)}00`; }

export function groupIcs(group, sg, list, cal, opts = {}) {
  const hol = new Set(cal.holidays.map((h) => h[0]));
  const lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//utcna.pages.dev//orar//RO', 'CALSCALE:GREGORIAN', 'METHOD:PUBLISH',
    `X-WR-CALNAME:Orar ${group.label}${group.sgs.length > 1 ? '/' + sg : ''}`, 'X-WR-TIMEZONE:Europe/Bucharest', 'REFRESH-INTERVAL;VALUE=DURATION:PT6H', ...VTZ];
  const stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d+Z$/, 'Z');
  for (const e of list) {
    if (!e.sg.includes(sg)) continue;
    if (opts.skipOpt && e.opt && e.opt !== 'lang') continue;
    for (const [monday, week] of cal.weeks) {
      if (!occurs(e, week)) continue;
      const dt = new Date(monday + 'T12:00:00Z'); dt.setUTCDate(dt.getUTCDate() + e.d);
      const ymd = `${dt.getUTCFullYear()}${pad(dt.getUTCMonth() + 1)}${pad(dt.getUTCDate())}`;
      const iso = `${dt.getUTCFullYear()}-${pad(dt.getUTCMonth() + 1)}-${pad(dt.getUTCDate())}`;
      if (hol.has(iso)) continue;
      const kind = KIND[e.k] || '';
      const summary = `${e.t || e.a || 'Activitate'}${kind ? ` (${kind})` : ''}${e.opt && e.opt !== 'lang' ? ' · opțional' : ''}`;
      const place = e.pl && PLACES[e.pl] ? PLACES[e.pl][0] : '';
      const desc = [e.prof && `Cadru didactic: ${e.prof}`, e.note, `În orar: ${e.raw}`, 'utcna.pages.dev'].filter(Boolean).join('\n');
      lines.push('BEGIN:VEVENT',
        `UID:${group.id}-${sg}-${week}-${e.d}-${e.s}-${(e.a || e.t || '').replace(/[^A-Za-z0-9]/g, '')}@utcna.pages.dev`,
        `DTSTAMP:${stamp}`,
        `DTSTART;TZID=Europe/Bucharest:${ymd}T${hh(e.s)}`,
        `DTEND;TZID=Europe/Bucharest:${ymd}T${hh(e.e)}`,
        fold(`SUMMARY:${esc(summary)}`),
        ...(e.r ? [fold(`LOCATION:${esc(`Sala ${e.r}${place ? ', ' + place : ''}`)}`)] : []),
        fold(`DESCRIPTION:${esc(desc)}`),
        'END:VEVENT');
    }
  }
  lines.push('END:VCALENDAR');
  return lines.join('\r\n') + '\r\n';
}

export function writeIcs(dir, data, cal) {
  fs.mkdirSync(dir, { recursive: true });
  for (const g of data.groups) {
    for (const sg of g.sgs) fs.writeFileSync(path.join(dir, `${g.id}-${sg}.ics`), groupIcs(g, sg, data.entries[g.id] || [], cal));
  }
}
