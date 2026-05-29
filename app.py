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
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ═══════════════════════════════════════════════════════════════════════════════
#  HERMÈS-INSPIRED CSS — Quiet Luxury
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,400&family=Inter:wght@300;400;500;600&display=swap');

    /* ── Global reset ── */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #F6F1EB !important;
        color: #000000;
    }

    /* Hide Streamlit chrome */
    #MainMenu, footer, header { visibility: hidden; }

    /* ── Typography ── */
    .editorial {
        font-family: 'EB Garamond', serif;
        font-weight: 400;
        letter-spacing: -0.01em;
    }

    .label {
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        font-size: 0.65rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: #2B333F;
    }

    /* ── Hero ── */
    .hero {
        text-align: center;
        padding: 3.5rem 0 2.5rem 0;
        border-bottom: 1px solid #E0D8CE;
        margin-bottom: 2rem;
    }
    .hero-title {
        font-family: 'EB Garamond', serif;
        font-size: 3rem;
        font-weight: 400;
        color: #000000;
        letter-spacing: -0.02em;
        line-height: 1.1;
        margin-bottom: 0.5rem;
    }
    .hero-sub {
        font-family: 'Inter', sans-serif;
        font-size: 0.9rem;
        font-weight: 300;
        color: #2B333F;
        letter-spacing: 0.02em;
    }
    .hero-ornament {
        color: #FF7700;
        font-size: 0.7rem;
        letter-spacing: 0.3em;
        margin-top: 1rem;
    }

    /* ── Cards ── */
    .result-card {
        background-color: #FFFCF7;
        border: 1px solid #E0D8CE;
        border-radius: 0;
        padding: 2rem;
        margin-bottom: 1.5rem;
    }

    /* ── Badges (pills) ── */
    .badge {
        display: inline-block;
        padding: 0.15rem 0.5rem;
        border-radius: 0;
        font-family: 'Inter', sans-serif;
        font-size: 0.65rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-right: 0.5rem;
        margin-bottom: 0.3rem;
    }
    .badge-active {
        background-color: #E8F0E8;
        color: #1A4A1A;
    }
    .badge-liquidation {
        background-color: #F5EDD8;
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
    .badge-high {
        background-color: #E8F0E8;
        color: #1A4A1A;
    }
    .badge-medium {
        background-color: #F5EDD8;
        color: #7A5C00;
    }
    .badge-low {
        background-color: #F0E0E0;
        color: #7A1A1A;
    }
    .badge-heuristic {
        background-color: #F0EAE0;
        color: #5A3A1A;
        border: 1px dashed #D0C4B0;
    }
    .badge-cache {
        background-color: #F0EDE8;
        color: #5A5548;
    }

    /* ── Section dividers ── */
    .section-title {
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        font-size: 0.65rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: #2B333F;
        margin-top: 1.5rem;
        margin-bottom: 0.6rem;
        padding-bottom: 0.3rem;
        border-bottom: 1px solid #E0D8CE;
    }

    .person-row {
        padding: 0.25rem 0;
        font-size: 0.9rem;
        color: #000000;
    }
    .person-share {
        color: #2B333F;
        font-size: 0.8rem;
    }

    .nominee-warning {
        color: #B07030;
        font-size: 0.75rem;
        font-style: italic;
        font-family: 'EB Garamond', serif;
    }

    /* ── Meta / footer within card ── */
    .card-footer {
        margin-top: 1.5rem;
        padding-top: 1rem;
        border-top: 1px solid #E0D8CE;
        font-size: 0.75rem;
        color: #5A5548;
    }
    .card-footer a {
        color: #2B333F;
        text-decoration: underline;
        text-underline-offset: 2px;
    }
    .card-footer a:hover {
        color: #FF7700;
    }

    /* ── Industry ── */
    .industry-line {
        margin: 0.8rem 0;
        font-size: 0.85rem;
        color: #2B333F;
    }
    .industry-value {
        color: #000000;
        font-weight: 500;
    }
    .industry-missing {
        color: #8A7E70;
        font-style: italic;
        font-family: 'EB Garamond', serif;
    }

    /* ── Disclaimer ── */
    .disclaimer {
        background-color: #F0EDE8;
        border-left: 2px solid #2B333F;
        padding: 1rem 1.2rem;
        border-radius: 0;
        color: #5A5548;
        font-size: 0.8rem;
        margin-top: 2rem;
        line-height: 1.5;
    }
    .disclaimer a {
        color: #2B333F;
        text-decoration: underline;
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        border-bottom: 1px solid #E0D8CE;
    }
    .stTabs [data-baseweb="tab"] {
        font-family: 'Inter', sans-serif;
        font-weight: 400;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #8A7E70;
        padding: 0.8rem 1.5rem;
        border-radius: 0;
        border-bottom: 2px solid transparent;
        margin-bottom: -1px;
    }
    .stTabs [aria-selected="true"] {
        color: #000000 !important;
        font-weight: 500;
        border-bottom: 2px solid #FF7700 !important;
    }

    /* ── Inputs ── */
    div[data-baseweb="input"] > div {
        border-radius: 0 !important;
        border-color: #C8BEB4 !important;
        background-color: #FFFCF7 !important;
    }
    div[data-baseweb="input"] > div:focus-within {
        border-color: #000000 !important;
    }

    /* ── Buttons ── */
    .stButton > button {
        border-radius: 0 !important;
        background-color: #000000 !important;
        color: #FFFCF7 !important;
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        border: none !important;
        padding: 0.6rem 1.5rem;
    }
    .stButton > button:hover {
        background-color: #FF7700 !important;
        color: #FFFCF7 !important;
    }
    .stButton > button:active {
        background-color: #CC5F00 !important;
    }

    /* ── Download button override ── */
    [data-testid="stDownloadButton"] > button {
        background-color: #FFFCF7 !important;
        color: #000000 !important;
        border: 1px solid #000000 !important;
    }
    [data-testid="stDownloadButton"] > button:hover {
        background-color: #000000 !important;
        color: #FFFCF7 !important;
        border-color: #000000 !important;
    }

    /* ── Tip box ── */
    .tip-box {
        background-color: #F0EDE8;
        border: 1px solid #E0D8CE;
        padding: 0.8rem 1rem;
        font-size: 0.85rem;
        color: #2B333F;
        margin-bottom: 1rem;
    }

    /* ── Results header ── */
    .results-header {
        font-family: 'EB Garamond', serif;
        font-size: 1.6rem;
        color: #000000;
        margin: 2rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #E0D8CE;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background-color: #F0EDE8 !important;
        border-right: 1px solid #E0D8CE;
    }
    [data-testid="stSidebar"] .stButton > button {
        background-color: transparent !important;
        color: #2B333F !important;
        border: 1px solid #C8BEB4 !important;
        text-align: left;
        font-size: 0.75rem;
        text-transform: none;
        letter-spacing: 0.02em;
        padding: 0.4rem 0.8rem;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background-color: #E0D8CE !important;
        color: #000000 !important;
    }

    /* ── Empty state ── */
    .empty-state {
        text-align: center;
        padding: 4rem 2rem;
        color: #8A7E70;
    }
    .empty-state .editorial {
        font-size: 1.3rem;
        margin-bottom: 0.5rem;
        color: #2B333F;
    }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  HERO
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="hero">
    <div class="hero-title editorial">Irina's Compass</div>
    <div class="hero-sub">Georgian Business Registry — Ownership, Directors & Industry</div>
    <div class="hero-ornament">◆ ◆ ◆</div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown('<div style="font-family: EB Garamond; font-size: 1.4rem; color: #000; margin-bottom: 0.2rem;">Irina\'s Compass</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size: 0.75rem; color: #5A5548; letter-spacing: 0.05em; text-transform: uppercase; margin-bottom: 1.5rem;">Georgian Business Lookup</div>', unsafe_allow_html=True)
    st.markdown('<div class="label" style="margin-bottom: 0.8rem;">Recent Searches</div>', unsafe_allow_html=True)

    recent = get_recent_searches(limit=12)
    if not recent:
        st.caption("No searches yet.")
    else:
        for idx, r in enumerate(recent):
            icon = {"vat_id": "#", "company_name": "◎", "owner_name": "◈"}.get(r.query_type, "◇")
            label = f"{icon}  {r.query[:32]}"
            if st.button(label, key=f"recent_{idx}_{r.query_type}", use_container_width=True):
                with st.spinner("Searching..."):
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
    <div style="margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #D0C8BE; font-size: 0.7rem; color: #8A7E70; line-height: 1.5;">
        Data: <a href="https://www.companyinfo.ge" target="_blank" style="color: #2B333F;">companyinfo.ge</a> (TI Georgia)<br>
        Cache: 7 days<br>
        <a href="https://github.com/flipgel/irinas-compass" target="_blank" style="color: #2B333F;">GitHub ↗</a>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  SEARCH TABS
# ═══════════════════════════════════════════════════════════════════════════════
tab_vat, tab_company, tab_owner = st.tabs(["By ID Code", "By Company Name", "By Owner Name"])


def do_search(query: str, query_type: str):
    with st.spinner("Searching Georgian registry..."):
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
        (e.g. <em style="font-family: EB Garamond;">ნანა მალენაშვილი</em>).
        The API does not support Latin transliterations.
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
        f'<div class="results-header editorial">{icon}&nbsp;&nbsp;Results for "{result.query}"</div>',
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

            # Build meta HTML
            meta_parts = [f'<span class="badge {form_class}">{company.legal_form}</span>']
            meta_parts.append(f'<span class="badge {status_class}">{company.status}</span>')
            meta_parts.append(f'<span class="badge {conf_class}">{company.confidence} confidence</span>')
            if result.from_cache:
                meta_parts.append('<span class="badge badge-cache">Cached</span>')
            if company.industry and company.industry_source == "heuristic":
                meta_parts.append('<span class="badge badge-heuristic">Heuristic</span>')

            meta_html = " ".join(meta_parts)

            # Registration / address line
            reg_line = f"""
                <strong>ID:</strong> {company.id_code}
                {f'&nbsp;&nbsp;|&nbsp;&nbsp;<strong>Registered:</strong> {company.registration_date}' if company.registration_date else ''}
                {f'&nbsp;&nbsp;|&nbsp;&nbsp;<strong>Address:</strong> {company.address}' if company.address else ''}
            """

            # Industry
            if company.industry:
                industry_html = f'<div class="industry-line"><span class="label">Industry (inferred)</span><br><span class="industry-value">{company.industry}</span></div>'
            else:
                industry_html = f'''<div class="industry-line">
                    <span class="label">Industry</span><br>
                    <span class="industry-missing">Not available in public registry</span>
                    <span style="font-size: 0.75rem; color: #8A7E70;">
                        &nbsp;· <a href="https://www.bia.ge/" target="_blank">Check BIA.ge ↗</a>
                        &nbsp;· <a href="https://rs.ge/" target="_blank">RS.ge ↗</a>
                    </span>
                </div>'''

            st.markdown(f"""
            <div class="result-card">
                <div class="editorial" style="font-size: 1.5rem; color: #000; margin-bottom: 0.4rem;">{company.name}</div>
                <div style="margin-bottom: 0.6rem;">{meta_html}</div>
                <div style="font-size: 0.85rem; color: #2B333F; line-height: 1.5;">
                    {reg_line}
                </div>
                {industry_html}
            </div>
            """, unsafe_allow_html=True)

            # Directors section
            if company.directors:
                st.markdown('<div class="section-title">Directors & Representatives</div>', unsafe_allow_html=True)
                for d in company.directors:
                    warn = " <span class='nominee-warning'>— may be nominee</span>" if d.is_nominee_warning else ""
                    st.markdown(f"<div class='person-row'>◆&nbsp;&nbsp;{d.name}{warn}</div>", unsafe_allow_html=True)

            # Shareholders section
            if company.shareholders:
                st.markdown('<div class="section-title">Owners & Shareholders</div>', unsafe_allow_html=True)
                for s in company.shareholders:
                    share_info = f" <span class='person-share'>({s.share_percent}%)</span>" if s.share_percent else ""
                    st.markdown(f"<div class='person-row'>◆&nbsp;&nbsp;{s.name}{share_info}</div>", unsafe_allow_html=True)
            elif not company.is_individual_entrepreneur:
                st.markdown("<div class='person-row' style='color: #8A7E70; font-style: italic; font-family: EB Garamond;'>No shareholder data available in this record.</div>", unsafe_allow_html=True)

            # Card footer with source & verification links
            st.markdown(f"""
            <div class="card-footer">
                Source: <a href="{company.source_url}" target="_blank">companyinfo.ge</a>
                &nbsp;&nbsp;·&nbsp;&nbsp;
                Fetched: {company.fetched_at.strftime('%Y-%m-%d %H:%M') if company.fetched_at else 'unknown'}
                &nbsp;&nbsp;·&nbsp;&nbsp;
                <a href="https://enreg.reestri.gov.ge/main.php?c=search&m=search_by_number&n={company.id_code}" target="_blank">Verify on NAPR ↗</a>
            </div>
            """, unsafe_allow_html=True)

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
        <div class="editorial">Welcome</div>
        <div style="font-size: 0.85rem; color: #8A7E70;">
            Search by company ID, name, or owner to explore the Georgian business registry.<br>
            Results include directors, shareholders, and an industry estimate.
        </div>
    </div>
    """, unsafe_allow_html=True)
