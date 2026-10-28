// Room -> building/address, from the room legends in both official timetables.
const P = {
  obs2: ['clădirea AC Observator, str. Observatorului 2, etaj 2', 'Strada Observatorului 2, Cluj-Napoca'],
  obs3: ['clădirea AC Observator, str. Observatorului 2, etaj 3', 'Strada Observatorului 2, Cluj-Napoca'],
  obs5: ['clădirea AC Observator, str. Observatorului 2, etaj 5', 'Strada Observatorului 2, Cluj-Napoca'],
  obsP: ['clădirea AC Observator, str. Observatorului 2, parter', 'Strada Observatorului 2, Cluj-Napoca'],
  bar: ['clădirea AC, str. G. Barițiu 26–28', 'Strada George Barițiu 26, Cluj-Napoca'],
  barE04: ['str. G. Barițiu 26–28, corp A (clădirea din spate)', 'Strada George Barițiu 26, Cluj-Napoca'],
  p03: ['clădirea AC nouă (Sport), str. G. Barițiu 26–28', 'Strada George Barițiu 26, Cluj-Napoca'],
  somS: ['clădirea Someș Stânga, str. G. Barițiu 26', 'Strada George Barițiu 26, Cluj-Napoca'],
  s42: ['str. G. Barițiu 28, clădirea din spatele sălii P03, etaj 4', 'Strada George Barițiu 28, Cluj-Napoca'],
  somD: ['clădirea Someș Dreapta, str. G. Barițiu 26–28', 'Strada George Barițiu 26, Cluj-Napoca'],
  constr: ['clădirea Construcții, str. G. Barițiu 25', 'Strada George Barițiu 25, Cluj-Napoca'],
  bt: ['str. G. Barițiu 6–8 (fosta Banca Transilvania)', 'Strada George Barițiu 8, Cluj-Napoca'],
  turn: ['clădirea turn, str. C. Daicoviciu 15', 'Strada Constantin Daicoviciu 15, Cluj-Napoca'],
  daic: ['str. C. Daicoviciu 15, etaj 1', 'Strada Constantin Daicoviciu 15, Cluj-Napoca'],
  aula: ['B-dul 21 Decembrie 1989 nr. 128–130', 'Bulevardul 21 Decembrie 1989 128, Cluj-Napoca'],
  dor: ['str. Dorobanților 71–73', 'Strada Dorobanților 71, Cluj-Napoca'],
  muncii: ['B-dul Muncii 103–105 (Construcții de Mașini)', 'Bulevardul Muncii 103, Cluj-Napoca'],
  sport: ['Complexul de natație Politehnica, Splaiul Independenței', 'Complex de Natatie Politehnica Cluj-Napoca'],
  emil: ['str. Emil Isac, ultimul etaj', 'Strada Emil Isac, Cluj-Napoca'],
  obs: ['clădirea Observator, str. Observatorului 2', 'Strada Observatorului 2, Cluj-Napoca'],
  simtex: ['B-dul Muncii 14, clădirea Simtex', 'Bulevardul Muncii 14, Cluj-Napoca'],
  hub: ['Cluj Hub, Magazinul Central, str. Regele Ferdinand 20, etaj 3', 'Cluj Hub, Strada Regele Ferdinand 20, Cluj-Napoca'],
};

export function placeOf(room, ctx = {}) {
  if (!room) return null;
  const r = room.replace(/^Amf\.\s*/i, '').replace(/\s+/g, ' ').trim();
  const R = r.toUpperCase();
  let k = null;
  if (/^BT\s?\d/.test(R)) k = 'bt';
  else if (/^AULA/.test(R) || /^I(204|205|109|110)$/.test(R)) k = 'aula';
  else if (/^P0?3$/.test(R)) k = 'p03';
  else if (/^E04$/.test(R)) k = 'barE04';
  else if (/^(F|40|45|356|359|E15|E17|D2[12]|D1[12]|G[126]|320|329|16B|26B|36)$/.test(R)) k = 'bar';
  else if (/^S\s?3\.?5$|^S\s?4\.?1$|^S35$/.test(R)) k = 'somS';
  else if (/^S\s?4\.?2$/.test(R)) k = 's42';
  else if (/^H\.?\s?\d{2}$/.test(R)) k = 'somD';
  else if (/^(A2|B2|152|192|197|211\s?LS|216\s?LS)$/.test(R)) k = 'constr';
  else if (/^(D0[1-4]|C0[1-3]|C1[1-3]|A12|M[123]|10[1-8]|D[123])$/.test(R)) k = 'dor';
  else if (/^(467|479)$/.test(R)) k = 'daic';
  else if (/^206 \(TURN\)$/.test(R) || (R === '206' && ctx.ped)) k = 'turn';
  else if (/^EM\s?2$|^S\s?2$/.test(R)) k = ctx.dept === 'calc' ? 'emil' : 'turn';
  else if (/^(G11[24]|M201|E112|C408)$/.test(R)) k = 'muncii';
  else if (/^(7|6|7 OBS)$/.test(R)) k = 'obsP';
  else if (/^2(0\d|1[0-4])[A-Z]?$/.test(R)) k = 'obs2';
  else if (/^3(0\d|10)[A-Z]?$/.test(R)) k = 'obs3';
  else if (/^505B?$/.test(R)) k = 'obs5';
  else if (/^(BLUE|WHITE|GREY|FOREST)$/.test(R)) k = 'hub';
  if (!k) return null;
  return { k, place: P[k][0], maps: P[k][1] };
}

export const PLACES = P;
