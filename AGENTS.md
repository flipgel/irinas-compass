# Irina's Compass — Agent Context

## Project Overview

**Name:** Irina's Compass  
**Purpose:** Georgian business registry OSINT tool for ownership lookup, network analysis, and risk detection. Built for a non-technical user (Irina) who researches restaurants and companies in Georgia.

**Live URL:** Streamlit Cloud (`*.streamlit.app`)  
**Repo:** `https://github.com/flipgel/irinas-compass`  
**Working Dir:** `/home/k56/Desktop/IrinasCompass/`

---

## Architecture

```
app.py              # Streamlit UI (sushi theme, 4 tabs)
scraper.py          # HTTP client for api.companyinfo.ge
models.py           # Dataclasses: Company, Person, SearchResult, NetworkResult
cache.py            # SQLite cache with 7-day TTL + search history
network.py          # Network graph builder + risk detection + Mermaid generation
industry_heuristic.py  # Name-based industry keyword matching
utils.py            # Input type detection, fuzzy matching
transliteration.py  # Latin→Georgian keyboard map (unused in web UI)
```

---

## API: companyinfo.ge

Base: `https://api.companyinfo.ge/api`

| Endpoint | Purpose |
|----------|---------|
| `GET /corporations/search?idCode={id}&page=1` | Search by 9-digit LLC ID or 11-digit IE ID |
| `GET /corporations/search?name={name}&page=1` | Search by company name (Georgian or Latin) |
| `GET /corporations/{id}` | Full company detail: corporation, corporationAffiliations, shareHolders, status, legalForm |
| `GET /people/search?name={name}&page=1` | Search people by name (requires Georgian script) |
| `GET /people/{id}` | Person detail: affiliations (director roles), ownership (shareholder roles) |

**Headers required:**
```python
{
    "User-Agent": "Mozilla/5.0 ...",
    "Accept": "application/json",
    "Referer": "https://www.companyinfo.ge/",
}
```

**Rate limiting:** 0.5s delay between calls in `scraper.py`. Be polite.

---

## Data Model

### `Company`
- `id_code` (9 or 11 digits)
- `name`, `legal_form` (შპს/იმ), `status`, `registration_date`, `address`
- `directors: List[Person]` — with `is_nominee_warning`
- `shareholders: List[Person]` — with `share_percent`
- `industry` — heuristic guess from name keywords
- `industry_source` — "heuristic" (always, since no free API has NACE)
- `source_url` — link to companyinfo.ge page
- `confidence` — high/medium/low

### `Person`
- `name`, `role`, `person_id`, `share_percent`, `is_nominee_warning`

### `NetworkResult`
- `nodes: List[NetworkNode]` — person/company/risk nodes for Mermaid
- `edges: List[NetworkEdge]` — relationships
- `risk_flags: List[str]` — auto-detected warnings
- `companies: List[Company]` — full data for detail cards

---

## Key Features

### Tab 1: By ID Code
Search by VAT/company ID (9 digits for LLC, 11 for IE).

### Tab 2: By Company Name
Search by company or restaurant name. Returns list of matching companies.

### Tab 3: By Owner Name
Reverse lookup: search person by Georgian name → find all linked companies.  
**Important:** Requires Georgian script (e.g. `ნანა მალენაშვილი`). Latin transliterations do NOT work with the API.

### Tab 4: 🔗 Network
**Person mode:** Search a person → map all their companies + co-directors (1 hop).  
**Company mode:** Search a company → map directors/shareholders with nominee detection.

**Auto-detected risk flags:**
- Nominee director (directs 20+ companies, 0% share)
- Fresh company (< 6 months old)
- Bad status (liquidation, terminated, suspended)
- Missing address or shareholders
- Address clustering (>5 companies at same address)
- Shell indicators (generic name + no ownership)

**Limits:** Max 8 companies, 3 co-directors per company, 0.5s delays.

---

## Design System

**Sushi theme (current):**
- Background: `#B0A494` (warm greyish-brown taupe)
- Cards: `#FFFCF7` (rice white)
- Text: `#1A1A1A` / `#5A5048`
- Accent: `#E85D4E` (salmon/coral)
- Typography: Inter (Helvetica-style), uppercase labels with wide tracking
- Sharp corners (2px radius), no shadows

**Loading spinner:** Sushi-themed messages ("🍣 Slicing fresh data...", etc.) with salmon-colored spinner.

---

## Known Limitations

1. **Industry data is heuristic only** — Georgian public registry does NOT publish NACE codes. Real data is on RS.ge (Revenue Service, behind CAPTCHA) or BIA.ge (commercial). The app guesses from company name keywords.
2. **No cross-source enrichment yet** — Only pulls from companyinfo.ge. RS.ge, BIA.ge, court records, procurement data are future work.
3. **Georgian script required for person search** — The API does not support Latin transliterations. Users must type in Georgian.
4. **Network graph is 1-hop only** — To avoid API rate limits and complexity.
5. **Cache is 7 days** — Old data may be stale. NAPR is the authoritative source.

---

## Development

**Python:** 3.13 venv  
**Dependencies:** streamlit, requests, rapidfuzz, beautifulsoup4, lxml, pandas

**Run locally:**
```bash
cd /home/k56/Desktop/IrinasCompass
source venv/bin/activate
streamlit run app.py
```

**Deploy to Streamlit Cloud:** Push to `flipgel/irinas-compass` main branch. Auto-deploys.

---

## Session Management for Kimi

To resume work on this project in a new terminal:

```bash
# Option 1: Continue previous session in this directory
cd /home/k56/Desktop/IrinasCompass && kimi --continue

# Option 2: Create alias (add to ~/.bashrc)
alias irinas-compass='cd /home/k56/Desktop/IrinasCompass && kimi --continue'
```

Then in Kimi, use `/title Irina's Compass` to name the session for easy finding via `/sessions`.
