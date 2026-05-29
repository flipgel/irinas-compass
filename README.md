# 🧭 Irina's Compass

**Georgian business ownership lookup tool** — find who owns restaurants and companies across Georgia using public registry data.

![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)

## What it does

Irina's Compass searches the [companyinfo.ge](https://www.companyinfo.ge) database (Transparency International Georgia) to help you:

- 🔢 **Search by VAT / ID Code** — Enter a 9-digit LLC code or 11-digit individual entrepreneur ID
- 🏢 **Search by Company Name** — Find any registered Georgian business by name
- 👤 **Reverse Search by Owner** — Discover every company a person owns or directs

## Key Features

- ✨ **Auto-transliteration** — Type owner names in Latin letters (e.g. `nana malenashvili`) and it auto-converts to Georgian (`ნანა მალენაშვილი`)
- 📱 **Mobile-friendly** — Works on phone, tablet, or laptop
- 💾 **Local caching** — Repeat lookups are instant; data cached for 7 days
- 📥 **CSV Export** — Download results for your records
- ⚠️ **Nominee warnings** — Flags directors who aren't shareholders (may just be employees/lawyers)
- 🔗 **Official verification** — Every result links directly to the government NAPR registry

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
