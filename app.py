import random
import streamlit as st
import pandas as pd
from datetime import datetime

from scraper import search_by_vat_id, search_by_company_name, search_by_owner_name
from cache import get_recent_searches
from models import SearchResult

# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Irina's Compass · Georgian Business Registry",
    page_icon="🍣",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ═══════════════════════════════════════════════════════════════════════════════
#  SUSHI-THEMED CSS — Warm Greyish-Brown Luxury
# ═══════════════════════════════════════════════════════════════════════════════
# Cache-busting version: bump this number when CSS changes to force client refresh
_CSS_VERSION = "2"

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* ── Global ── */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        background-color: #B0A494 !important;
        color: #1A1A1A;
    }

    #MainMenu, footer, header { visibility: hidden; }

    /* ── Typography system ── */
    .h1 {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 3.2rem;
        letter-spacing: -0.03em;
        line-height: 1.05;
        color: #1A1A1A;
        text-transform: none;
    }
    .label {
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        font-size: 0.6rem;
        text-transform: uppercase;
        letter-spacing: 0.14em;
        color: #5A5048;
    }
    .body {
        font-family: 'Inter', sans-serif;
        font-size: 0.9rem;
        line-height: 1.5;
        color: #1A1A1A;
    }
    .caption {
        font-family: 'Inter', sans-serif;
        font-size: 0.75rem;
        color: #5A5048;
    }

    /* ── Hero ── */
    .hero {
        text-align: center;
        padding: 3rem 0 2rem 0;
        border-bottom: 1px solid #9E9486;
        margin-bottom: 2rem;
    }
    .hero-title {
        font-family: 'Inter', sans-serif;
        font-size: 3.5rem;
        font-weight: 700;
        letter-spacing: -0.04em;
        color: #1A1A1A;
        line-height: 1.0;
        margin-bottom: 0.4rem;
    }
    .hero-sub {
        font-family: 'Inter', sans-serif;
        font-size: 0.85rem;
        font-weight: 400;
        color: #5A5048;
        letter-spacing: 0.04em;
    }
    .hero-ornament {
        font-size: 1.2rem;
        margin-top: 0.8rem;
        letter-spacing: 0.2em;
    }

    /* ── Cards ── */
    .result-card {
        background-color: #FFFCF7;
        border: 1px solid #C8BEB0;
        border-radius: 2px;
        padding: 1.8rem 2rem;
        margin-bottom: 1.2rem;
    }
    .company-title {
        font-family: 'Inter', sans-serif;
        font-size: 1.35rem;
        font-weight: 600;
        color: #1A1A1A;
        letter-spacing: -0.01em;
        margin-bottom: 0.5rem;
    }
    .badge-row {
        margin-bottom: 0.8rem;
    }
    .badge {
        display: inline-block;
        padding: 0.2rem 0.55rem;
        border-radius: 2px;
        font-family: 'Inter', sans-serif;
        font-size: 0.6rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-right: 0.4rem;
        margin-bottom: 0.25rem;
    }
    .badge-active {
        background-color: #E0E8E0;
        color: #1A4A1A;
    }
    .badge-liquidation {
        background-color: #F0E8D0;
        color: #7A5C00;
    }
    .badge-terminated {
        background-color: #F0E0E0;
        color: #7A1A1A;
    }
    .badge-ie {
        background-color: #E8E0F0;
        color: #4A1A7A;
    }
    .badge-llc {
        background-color: #E0E8F0;
        color: #1A3A7A;
    }
    .badge-high { background-color: #E0E8E0; color: #1A4A1A; }
    .badge-medium { background-color: #F0E8D0; color: #7A5C00; }
    .badge-low { background-color: #F0E0E0; color: #7A1A1A; }
    .badge-heuristic {
        background-color: #F5EDE0;
        color: #6A4A1A;
        border: 1px dashed #D0C4B0;
    }
    .badge-cache {
        background-color: #E8E4DE;
        color: #5A5548;
    }

    .meta-line {
        font-size: 0.85rem;
        color: #5A5048;
        line-height: 1.6;
        margin-bottom: 0.6rem;
    }
    .meta-line strong {
        color: #1A1A1A;
        font-weight: 500;
    }

    /* ── Sections inside card ── */
    .section-title {
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        font-size: 0.6rem;
        text-transform: uppercase;
        letter-spacing: 0.14em;
        color: #5A5048;
        margin-top: 1.2rem;
        margin-bottom: 0.5rem;
        padding-bottom: 0.3rem;
        border-bottom: 1px solid #E0D8CE;
    }
    .person-row {
        padding: 0.2rem 0;
        font-size: 0.9rem;
        color: #1A1A1A;
    }
    .person-share {
        color: #5A5048;
        font-size: 0.8rem;
    }
    .nominee-warning {
        color: #B07030;
        font-size: 0.75rem;
        font-style: italic;
    }

    /* ── Industry ── */
    .industry-line {
        margin: 0.6rem 0;
        padding: 0.5rem 0;
        border-top: 1px solid #F0E8E0;
        border-bottom: 1px solid #F0E8E0;
    }
    .industry-value {
        font-size: 0.85rem;
        color: #1A1A1A;
        font-weight: 500;
    }
    .industry-missing {
        font-size: 0.85rem;
        color: #8A7E70;
        font-style: italic;
    }
    .industry-links {
        font-size: 0.7rem;
        color: #8A7E70;
    }
    .industry-links a {
        color: #5A5048;
        text-decoration: underline;
        text-underline-offset: 2px;
    }
    .industry-links a:hover {
        color: #E85D4E;
    }

    /* ── Card footer ── */
    .card-footer {
        margin-top: 1.2rem;
        padding-top: 0.8rem;
        border-top: 1px solid #E0D8CE;
        font-size: 0.7rem;
        color: #8A7E70;
    }
    .card-footer a {
        color: #5A5048;
        text-decoration: underline;
        text-underline-offset: 2px;
    }
    .card-footer a:hover {
        color: #E85D4E;
    }

    /* ── Disclaimer ── */
    .disclaimer {
        background-color: #E8E0D8;
        border-left: 2px solid #5A5048;
        padding: 1rem 1.2rem;
        border-radius: 2px;
        color: #5A5048;
        font-size: 0.78rem;
        margin-top: 2rem;
        line-height: 1.5;
    }
    .disclaimer a {
        color: #1A1A1A;
        text-decoration: underline;
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        border-bottom: 1px solid #9E9486;
    }
    .stTabs [data-baseweb="tab"] {
        font-family: 'Inter', sans-serif;
        font-weight: 400;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #7A7060;
        padding: 0.7rem 1.2rem;
        border-radius: 0;
        border-bottom: 2px solid transparent;
        margin-bottom: -1px;
    }
    .stTabs [aria-selected="true"] {
        color: #1A1A1A !important;
        font-weight: 600;
        border-bottom: 2px solid #E85D4E !important;
    }

    /* ── Inputs ── */
    div[data-baseweb="input"] > div {
        border-radius: 2px !important;
        border-color: #9E9486 !important;
        background-color: #FFFCF7 !important;
    }
    div[data-baseweb="input"] > div:focus-within {
        border-color: #1A1A1A !important;
        box-shadow: 0 0 0 1px #1A1A1A !important;
    }

    /* ── Primary buttons ── */
    .stButton > button {
        border-radius: 2px !important;
        background-color: #1A1A1A !important;
        color: #FFFCF7 !important;
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        border: none !important;
        padding: 0.55rem 1.4rem;
    }
    .stButton > button:hover {
        background-color: #E85D4E !important;
        color: #FFFCF7 !important;
    }
    .stButton > button:active {
        background-color: #D44A3B !important;
    }

    /* ── Download button ── */
    [data-testid="stDownloadButton"] > button {
        background-color: transparent !important;
        color: #1A1A1A !important;
        border: 1px solid #1A1A1A !important;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    [data-testid="stDownloadButton"] > button:hover {
        background-color: #1A1A1A !important;
        color: #FFFCF7 !important;
    }

    /* ── Tip box ── */
    .tip-box {
        background-color: #E8E0D8;
        border: 1px solid #C8BEB0;
        padding: 0.7rem 1rem;
        font-size: 0.82rem;
        color: #5A5048;
        margin-bottom: 1rem;
        border-radius: 2px;
    }

    /* ── Results header ── */
    .results-header {
        font-family: 'Inter', sans-serif;
        font-size: 1.4rem;
        font-weight: 600;
        color: #1A1A1A;
        margin: 1.5rem 0 1rem 0;
        padding-bottom: 0.4rem;
        border-bottom: 1px solid #9E9486;
        letter-spacing: -0.01em;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background-color: #A89888 !important;
        border-right: 1px solid #9E9486;
    }
    [data-testid="stSidebar"] .stButton > button {
        background-color: transparent !important;
        color: #1A1A1A !important;
        border: 1px solid #8A7E6E !important;
        text-align: left;
        font-size: 0.72rem;
        text-transform: none;
        letter-spacing: 0.02em;
        padding: 0.35rem 0.7rem;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background-color: #C8BEB0 !important;
        color: #1A1A1A !important;
    }

    /* ── Empty state ── */
    .empty-state {
        text-align: center;
        padding: 4rem 2rem;
        color: #7A7060;
    }
    .empty-state .big {
        font-size: 1.2rem;
        font-weight: 500;
        margin-bottom: 0.4rem;
        color: #5A5048;
    }

    /* ── Spinner custom color ── */
    .stSpinner > div > div > div {
        border-top-color: #E85D4E !important;
    }
    .stSpinner > div > div {
        color: #5A5048 !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.8rem !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  HERO
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="hero">
    <div class="hero-title">Irina's Compass</div>
    <div class="hero-sub">Georgian Business Registry — Ownership, Directors & Industry</div>
    <div class="hero-ornament">🍣 🍱 🍤</div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown('<div style="font-family: Inter; font-size: 1.3rem; font-weight: 700; color: #1A1A1A; margin-bottom: 0.2rem; letter-spacing: -0.02em;">Irina\'s Compass</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size: 0.68rem; color: #5A5048; letter-spacing: 0.06em; text-transform: uppercase; margin-bottom: 1.5rem;">Georgian Business Lookup</div>', unsafe_allow_html=True)
    st.markdown('<div class="label" style="margin-bottom: 0.6rem;">Recent Searches</div>', unsafe_allow_html=True)

    recent = get_recent_searches(limit=12)
    if not recent:
        st.caption("No searches yet.")
    else:
        for idx, r in enumerate(recent):
            icon = {"vat_id": "#", "company_name": "◎", "owner_name": "◈"}.get(r.query_type, "◇")
            label = f"{icon}  {r.query[:32]}"
            if st.button(label, key=f"recent_{idx}_{r.query_type}", use_container_width=True):
                with st.spinner(random.choice([
                    "🍣 Slicing fresh data...",
                    "🍱 Preparing your bento...",
                    "🍤 Frying tempura results...",
                    "🍙 Rolling rice & records...",
                    "🍥 Spinning the fish cake...",
                ])):
                    try:
                        if r.query_type == "vat_id":
                            result = search_by_vat_id(r.query.strip())
                        elif r.query_type == "company_name":
                            result = search_by_company_name(r.query.strip())
                        else:
                            result = search_by_owner_name(r.query.strip())
                        st.session_state["last_result"] = result
                    except Exception as e:
                        st.error(f"Search failed: {e}")

    st.markdown("""
    <div style="margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #9E9486; font-size: 0.68rem; color: #7A7060; line-height: 1.5;">
        Data: <a href="https://www.companyinfo.ge" target="_blank" style="color: #5A5048;">companyinfo.ge</a> (TI Georgia)<br>
        Cache: 7 days · <a href="https://github.com/flipgel/irinas-compass" target="_blank" style="color: #5A5048;">GitHub ↗</a>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  SEARCH TABS
# ═══════════════════════════════════════════════════════════════════════════════
tab_vat, tab_company, tab_owner = st.tabs(["By ID Code", "By Company Name", "By Owner Name"])


def do_search(query: str, query_type: str):
    msg = random.choice([
        "🍣 Slicing fresh data...",
        "🍱 Preparing your bento...",
        "🍤 Frying tempura results...",
        "🍙 Rolling rice & records...",
        "🍥 Spinning the fish cake...",
    ])
    with st.spinner(msg):
        try:
            if query_type == "vat_id":
                result = search_by_vat_id(query.strip())
            elif query_type == "company_name":
                result = search_by_company_name(query.strip())
            else:
                result = search_by_owner_name(query.strip())
            st.session_state["last_result"] = result
        except Exception as e:
            st.error(f"Search failed: {e}")


with tab_vat:
    c1, c2 = st.columns([4, 1])
    with c1:
        vat_query = st.text_input(
            "Enter VAT or Company ID",
            placeholder="404447924  (9 digits for LLC, 11 for individual entrepreneur)",
            key="vat_input",
            label_visibility="collapsed",
        )
    with c2:
        st.write("")
        st.write("")
        if st.button("Search", key="btn_vat", use_container_width=True):
            if vat_query.strip():
                do_search(vat_query, "vat_id")
            else:
                st.warning("Please enter an ID code")


with tab_company:
    c1, c2 = st.columns([4, 1])
    with c1:
        company_query = st.text_input(
            "Enter Company or Restaurant Name",
            placeholder="Good Shepherd  or  შპს არბითიეს გრუფი",
            key="company_input",
            label_visibility="collapsed",
        )
    with c2:
        st.write("")
        st.write("")
        if st.button("Search", key="btn_company", use_container_width=True):
            if company_query.strip():
                do_search(company_query, "company_name")
            else:
                st.warning("Please enter a name")


with tab_owner:
    st.markdown("""
    <div class="tip-box">
        <span class="label">Tip</span> &nbsp;Type the owner's name in <strong>Georgian script</strong>
        (e.g. <em>ნანა მალენაშვილი</em>). The API does not support Latin transliterations.
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns([4, 1])
    with c1:
        owner_query = st.text_input(
            "Enter Owner Name (Georgian script)",
            placeholder="ნანა მალენაშვილი",
            key="owner_input",
            label_visibility="collapsed",
        )
    with c2:
        st.write("")
        st.write("")
        if st.button("Search", key="btn_owner", use_container_width=True):
            if owner_query.strip():
                do_search(owner_query, "owner_name")
            else:
                st.warning("Please enter a name")


# ═══════════════════════════════════════════════════════════════════════════════
#  RESULTS DISPLAY
# ═══════════════════════════════════════════════════════════════════════════════
result: SearchResult = st.session_state.get("last_result")

if result:
    st.divider()

    icon = {"vat_id": "#", "company_name": "◎", "owner_name": "◈"}.get(result.query_type, "◇")
    st.markdown(
        f'<div class="results-header">{icon}&nbsp;&nbsp;Results for "{result.query}"</div>',
        unsafe_allow_html=True
    )

    if result.from_cache:
        st.caption("📦 Served from cache")

    if result.error:
        st.error(result.error)

    if not result.companies:
        if not result.error:
            st.info("No companies found. Try a different search term.")
    else:
        # ── Export ──
        export_data = []
        for c in result.companies:
            export_data.append({
                "ID Code": c.id_code,
                "Name": c.name,
                "Legal Form": c.legal_form,
                "Status": c.status,
                "Industry (Guess)": c.industry or "Unknown",
                "Registration Date": c.registration_date,
                "Address": c.address,
                "Directors": ", ".join([d.name for d in c.directors]),
                "Shareholders": ", ".join([f"{s.name} ({s.share_percent}%)" if s.share_percent else s.name for s in c.shareholders]),
                "Source URL": c.source_url,
                "Confidence": c.confidence,
            })
        df = pd.DataFrame(export_data)

        col1, col2 = st.columns([6, 1])
        with col2:
            st.download_button(
                label="Export CSV",
                data=df.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"irina_compass_{result.query.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True,
            )

        # ── Cards ──
        for company in result.companies:
            status_class = {
                "Active": "badge-active",
                "In Liquidation": "badge-liquidation",
                "Terminated": "badge-terminated",
                "Suspended": "badge-terminated",
            }.get(company.status, "badge-medium")

            form_class = "badge-ie" if company.is_individual_entrepreneur else "badge-llc"
            conf_class = f"badge-{company.confidence}"

            # Build badges
            badges = [
                f'<span class="badge {form_class}">{company.legal_form}</span>',
                f'<span class="badge {status_class}">{company.status}</span>',
                f'<span class="badge {conf_class}">{company.confidence}</span>',
            ]
            if result.from_cache:
                badges.append('<span class="badge badge-cache">Cached</span>')
            if company.industry and company.industry_source == "heuristic":
                badges.append('<span class="badge badge-heuristic">Heuristic</span>')
            badges_html = " ".join(badges)

            # Meta line
            meta_parts = [f"<strong>ID:</strong> {company.id_code}"]
            if company.registration_date:
                meta_parts.append(f"<strong>Registered:</strong> {company.registration_date}")
            if company.address:
                meta_parts.append(f"<strong>Address:</strong> {company.address}")
            meta_html = "&nbsp;&nbsp;|&nbsp;&nbsp;".join(meta_parts)

            # Industry
            if company.industry:
                industry_html = f'''
                <div class="industry-line">
                    <span class="label">Industry (inferred)</span><br>
                    <span class="industry-value">{company.industry}</span>
                </div>'''
            else:
                industry_html = f'''
                <div class="industry-line">
                    <span class="label">Industry</span><br>
                    <span class="industry-missing">Not available in public registry</span>
                    <span class="industry-links">
                        &nbsp;· <a href="https://www.bia.ge/" target="_blank">BIA.ge ↗</a>
                        &nbsp;· <a href="https://rs.ge/" target="_blank">RS.ge ↗</a>
                    </span>
                </div>'''

            # Directors section
            directors_html = ""
            if company.directors:
                rows = []
                for d in company.directors:
                    warn = " <span class='nominee-warning'>— may be nominee</span>" if d.is_nominee_warning else ""
                    rows.append(f"<div class='person-row'>• {d.name}{warn}</div>")
                directors_html = f'<div class="section-title">Directors & Representatives</div>{"".join(rows)}'

            # Shareholders section
            shareholders_html = ""
            if company.shareholders:
                rows = []
                for s in company.shareholders:
                    share_info = f" <span class='person-share'>({s.share_percent}%)</span>" if s.share_percent else ""
                    rows.append(f"<div class='person-row'>• {s.name}{share_info}</div>")
                shareholders_html = f'<div class="section-title">Owners & Shareholders</div>{"".join(rows)}'
            elif not company.is_individual_entrepreneur:
                shareholders_html = '<div class="section-title">Owners & Shareholders</div><div class="person-row" style="color: #8A7E70; font-style: italic;">No shareholder data available in this record.</div>'

            # Footer
            fetched_str = company.fetched_at.strftime('%Y-%m-%d %H:%M') if company.fetched_at else 'unknown'
            footer_html = f'''
                Source: <a href="{company.source_url}" target="_blank">companyinfo.ge</a>
                &nbsp;&nbsp;·&nbsp;&nbsp;
                Fetched: {fetched_str}
                &nbsp;&nbsp;·&nbsp;&nbsp;
                <a href="https://enreg.reestri.gov.ge/main.php?c=search&m=search_by_number&n={company.id_code}" target="_blank">Verify on NAPR ↗</a>
            '''

            # ── Assemble entire card as ONE HTML block ──
            card_html = f"""
            <div class="result-card">
                <div class="company-title">{company.name}</div>
                <div class="badge-row">{badges_html}</div>
                <div class="meta-line">{meta_html}</div>
                {industry_html}
                {directors_html}
                {shareholders_html}
                <div class="card-footer">{footer_html}</div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)

        # ── Disclaimer ──
        st.markdown("""
        <div class="disclaimer">
            <strong>Note.</strong> This tool aggregates publicly available data from
            <a href="https://www.companyinfo.ge" target="_blank">companyinfo.ge</a> (Transparency International Georgia).
            Industry data is <em>not published</em> by the Georgian public registry and is inferred here from company name keywords only — it may be incorrect.
            For authoritative records, order an extract from the
            <a href="https://enreg.reestri.gov.ge" target="_blank">National Agency of Public Registry</a>
            or check <a href="https://www.bia.ge/" target="_blank">BIA.ge</a> for commercial NACE data.
        </div>
        """, unsafe_allow_html=True)

else:
    # Empty state
    st.markdown("""
    <div class="empty-state">
        <div class="big">Welcome 🍣</div>
        <div style="font-size: 0.82rem; color: #7A7060;">
            Search by company ID, name, or owner to explore the Georgian business registry.<br>
            Results include directors, shareholders, and an industry estimate.
        </div>
    </div>
    """, unsafe_allow_html=True)
