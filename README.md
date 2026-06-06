# 🧭 Irina's Compass

**Georgian business ownership lookup tool** — find who owns restaurants and companies across Georgia using public registry data.

![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)

## What it does

Irina's Compass is a unified research platform with two independent modules:

### 🧭 Business Registry
Searches the [companyinfo.ge](https://www.companyinfo.ge) database (Transparency International Georgia) to help you:

- 🔢 **Search by VAT / ID Code** — Enter a 9-digit LLC code or 11-digit individual entrepreneur ID
- 🏢 **Search by Company Name** — Find any registered Georgian business by name
- 👤 **Reverse Search by Owner** — Discover every company a person owns or directs

### 📰 Newsroom
A Ground News-inspired news intelligence module for seeing every side of every story:

- **Bias Comparison** — Articles color-coded by source bias (Left / Center / Right)
- **Factuality Ratings** — Source-level credibility scores
- **Ownership Transparency** — Know who owns the news you read
- **Coverage Analysis** — See how many sources from each side cover a story
- **Blindspot Detection** — Find stories ignored by one ideological side
- **Topic & Search Filters** — Focus on what matters to you

## Key Features

### Business Registry
- ✨ **Auto-transliteration** — Type owner names in Latin letters (e.g. `nana malenashvili`) and it auto-converts to Georgian (`ნანა მალენაშვილი`)
- 📱 **Mobile-friendly** — Works on phone, tablet, or laptop
- 💾 **Local caching** — Repeat lookups are instant; data cached for 7 days
- 📥 **CSV Export** — Download results for your records
- ⚠️ **Nominee warnings** — Flags directors who aren't shareholders (may just be employees/lawyers)
- 🔗 **Official verification** — Every result links directly to the government NAPR registry
- 🔗 **Network Analysis** — Map ownership relationships and detect red flags

### Newsroom
- 📊 **Bias Visualization** — Color-coded coverage bars (blue = left, gray = center, red = right)
- ✅ **Factuality Ratings** — High / Mixed / Low source credibility scores
- 🏢 **Ownership Transparency** — Parent company revealed for every outlet
- 🔍 **Blindspot Detection** — Stories lopsidedly covered by one ideological side
- 🔎 **Search & Filter** — By topic, bias, keyword, or coverage type
- 📈 **Stats Dashboard** — Real-time breakdown of coverage distribution

## Quick Start (Local)

```bash
# Clone or extract the project
cd IrinasCompass

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run
streamlit run app.py
```

Then open `http://localhost:8501` in your browser.

## Deploy to Streamlit Cloud (Free)

See [DEPLOY.md](DEPLOY.md) for step-by-step instructions to host it online.

## Data Source & Disclaimer

All data comes from **companyinfo.ge**, a public transparency project by [Transparency International Georgia](https://transparency.ge). This is scraped public registry data and may have delays or gaps. For legally authoritative records, order an extract from the [National Agency of Public Registry](https://enreg.reestri.gov.ge).

**Privacy note:** This tool only queries public records. No personal data is collected or stored beyond your local search history.

---

Made with ☕ for Irina
