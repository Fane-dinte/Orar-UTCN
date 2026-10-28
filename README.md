<p align="center"><img src="docs/banner.svg" alt="Orar UTCN" width="100%"></p>

<p align="center">
  <a href="https://utcna.pages.dev"><img alt="Deschide aplicația" src="https://img.shields.io/badge/deschide-utcna.pages.dev-4b2fb0"></a>
  <img alt="Se actualizează din oră în oră" src="https://img.shields.io/badge/actualizat-din%20or%C4%83%20%C3%AEn%20or%C4%83-2ea043">
  <img alt="PWA" src="https://img.shields.io/badge/PWA-instalabil-5A0FC8">
  <img alt="Cloudflare Pages" src="https://img.shields.io/badge/Cloudflare-Pages-F38020?logo=cloudflare&logoColor=white">
  <img alt="Licență MIT" src="https://img.shields.io/badge/licen%C8%9B%C4%83-MIT-green">
</p>

**Orar UTCN** e orarul facultăților Universității Tehnice din Cluj-Napoca, făcut pentru telefon: alegi facultatea, grupa și semigrupa și vezi ce ai azi, cu paritatea săptămânii, sălile și profesorii. Se citește singur din orarele oficiale, din oră în oră, deci nu rămâne în urmă.

> Preluat automat din orarele oficiale. **Nu e o pagină oficială UTCN.** La o nepotrivire, orarul oficial are dreptate.

<p align="center">
  <img src="docs/zi-light.png" alt="Vederea pe zi, temă luminoasă" width="250">
  &nbsp;
  <img src="docs/zi-dark.png" alt="Vederea pe zi, temă întunecată" width="250">
</p>
<p align="center"><img src="docs/saptamana.png" alt="Vederea pe săptămână, pe desktop" width="760"></p>

## Ce știe

- **8 surse, un singur loc:** Automatică, Calculatoare, IE, ETTI, ARMM, Construcții, Instalații și IIRMP (licență, Cluj; fără extensiile Alba, Bistrița, Satu Mare, Zalău).
- **Zi pe telefon, săptămână pe desktop**, cu paritate (săptămâni impare/pare), intervale („săpt. 1–7”) și butonul „Azi”.
- **Profesorii la fiecare oră**, limbi străine cu alegerea limbii, opțiuni (pedagogic, complemente de matematică, facultativ).
- **5 teme:** UTCN, întunecat, luminos, AMOLED și clasic. Variantă de tipărit în mod luminos.
- **Calendar `.ics`** pentru fiecare grupă și semigrupă, ca să-l pui în Google Calendar sau Apple Calendar.
- **Istoric de modificări** (ultimele 60) afișat în aplicație, ca să vezi ce s-a schimbat.
- **Instalabil ca PWA**, merge fără internet după prima deschidere. Share cu link care păstrează grupa.

## Cum funcționează

```
orarele oficiale (Excel, Google Sheets, PDF, EduPage)
        │   din oră în oră, GitHub Actions
        ▼
 scripts/build.mjs ── lib/*.mjs   (Excel: exceljs)
                  └── pdf/*.py    (PDF: pdfplumber, un modul pe facultate)
        │   date normalizate, doar dacă s-a schimbat ce vede un student
        ▼
 public/data/*.json + public/ics/*.ics + changes.json
        │   wrangler pages deploy
        ▼
 Cloudflare Pages  →  utcna.pages.dev
```

- O facultate care eșuează la descărcare **își păstrează datele vechi**, iar build-ul continuă. O sursă care iese cu 0 grupe nu le suprascrie.
- Edupage (Construcții) refuză uneori adresele runner-elor GitHub: apelurile trec atunci printr-un releu Cloudflare cu listă de permisiuni.
- Datele fiecărei facultăți: `public/data/<facultate>.json`, cu `groups[]` și `entries[grupă][]` (`d` ziua, `s`–`e` ora, `p` paritatea, `k` tipul, `a`/`t` materia, `r` sala, `sg` semigrupele, `prof`, `pl` locul).

## Rulează local

Ai nevoie de Node 20+ și Python 3.11+.

```bash
npm ci
pip install -r pdf/requirements.txt
node scripts/build.mjs --fetch                  # toate sursele, de pe internet
node scripts/build.mjs --only iirmp --fetch     # o singură facultate
python3 -m http.server 8765 -d public           # http://localhost:8765
```

Un parser PDF poate rula și singur, pe fișiere salvate: `python3 pdf/iirmp.py cale/către/pdf-uri > out.json`.

## Publică pe contul tău

1. Creează un proiect **Cloudflare Pages** (Direct Upload) și un token API cu dreptul „Cloudflare Pages: Edit”.
2. În GitHub, la repo-ul tău → Settings → Secrets and variables → Actions:
   - secrete: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`;
   - variabile: `CF_PROJECT` (numele proiectului Pages) și `ORAR_URL` (link-ul de SharePoint cu orarul de la Automatică).
3. Rulează workflow-ul **Actualizează orarul**. Apoi merge singur în fiecare oră între 7 și 22 (și de două ori pe zi în weekend).

La fiecare versiune nouă a site-ului crești `const V = "orar-v2-N"` din `public/sw.js`, ca telefoanele să ia versiunea nouă.

## Structura

| Cale | Ce conține |
|---|---|
| `public/` | Aplicația (`index.html`, `sw.js`, manifest, iconițe) și datele generate |
| `scripts/build.mjs` | Build-ul principal, cu sursele fiecărei facultăți |
| `lib/` | Parsere pentru Excel, titluri, săli și clădiri, calendare `.ics` |
| `pdf/` | Cititorul de grile PDF și câte un modul pe facultate |
| `.github/workflows/update.yml` | Actualizarea orară și publicarea |

## Contribuții

Ai găsit o oră greșită sau lipsă? Deschide un issue cu grupa și ce ar trebui să apară. Mai lipsesc: IMM, FAU, masterele și ETTI SICAS.

## Licență

[MIT](LICENSE) pentru cod. Orarele aparțin UTCN.
