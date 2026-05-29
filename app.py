import streamlit as st
import pandas as pd
from datetime import datetime

from scraper import search_by_vat_id, search_by_company_name, search_by_owner_name
from cache import get_recent_searches
from models import SearchResult
from transliteration import latin_to_georgian, is_georgian_script

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Irina's Compass",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS: earthy Georgian tones ────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Inter:wght@300;400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .main-header {
        font-family: 'Playfair Display', serif;
        color: #5D2E1F;
        font-size: 2.8rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
        letter-spacing: -0.02em;
    }
    
    .sub-header {
        color: #8B6F5C;
        font-size: 1.1rem;
        font-weight: 300;
        margin-bottom: 2rem;
    }
    
    .result-card {
        background-color: #FDFBF7;
        border: 1px solid #E8DDD0;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(93, 46, 31, 0.06);
    }
    
    .company-title {
        font-family: 'Playfair Display', serif;
        color: #5D2E1F;
        font-size: 1.4rem;
        font-weight: 700;
        margin-bottom: 0.3rem;
    }
    
    .meta-line {
        color: #8B6F5C;
        font-size: 0.9rem;
        margin-bottom: 0.8rem;
    }
    
    .badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        margin-right: 0.4rem;
    }
    
    .badge-active {
        background-color: #D4E8D1;
        color: #2D5A27;
    }
    
    .badge-liquidation {
        background-color: #F5E6C8;
        color: #8B6914;
    }
    
    .badge-terminated {
        background-color: #F0D4D4;
        color: #8B2828;
    }
    
    .badge-high {
        background-color: #D4E8D1;
        color: #2D5A27;
    }
    
    .badge-medium {
        background-color: #F5E6C8;
        color: #8B6914;
    }
    
    .badge-low {
        background-color: #F0D4D4;
        color: #8B2828;
    }
    
    .badge-ie {
        background-color: #E0D4F0;
        color: #5A2D7A;
    }
    
    .badge-llc {
        background-color: #D4E0F0;
        color: #2D4A7A;
    }
    
    .section-title {
        font-weight: 600;
        color: #5D2E1F;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 1rem;
        margin-bottom: 0.4rem;
        border-bottom: 1px solid #E8DDD0;
        padding-bottom: 0.3rem;
    }
    
    .person-row {
        padding: 0.3rem 0;
        color: #4A3F35;
        font-size: 0.95rem;
    }
    
    .nominee-warning {
        color: #B87A3A;
        font-size: 0.8rem;
        font-style: italic;
    }
    
    .disclaimer {
        background-color: #F5F0EB;
        border-left: 3px solid #8B6F5C;
        padding: 0.8rem 1rem;
        border-radius: 0 8px 8px 0;
        color: #6B5B4F;
        font-size: 0.85rem;
        margin-top: 1rem;
    }
    
    .warning-box {
        background-color: #FFF8E7;
        border: 1px solid #E8C87A;
        border-radius: 8px;
        padding: 1rem;
        color: #7A5C1A;
        font-size: 0.9rem;
        margin-bottom: 1rem;
    }
    
    .info-box {
        background-color: #E8F4F0;
        border: 1px solid #7AB8A8;
        border-radius: 8px;
        padding: 1rem;
        color: #1A5A4A;
        font-size: 0.9rem;
        margin-bottom: 1rem;
    }
    
    .recent-item {
        padding: 0.5rem 0.8rem;
        margin-bottom: 0.3rem;
        border-radius: 6px;
        cursor: pointer;
        transition: background 0.2s;
    }
    
    .recent-item:hover {
        background-color: #F5F0EB;
    }
    
    .georgian-preview {
        background-color: #F8F5F0;
        border: 1px solid #D4C4B0;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        font-size: 1.1rem;
        color: #5D2E1F;
        font-family: 'Inter', sans-serif;
        margin-top: 0.5rem;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        font-weight: 500;
        color: #8B6F5C;
    }
    
    .stTabs [aria-selected="true"] {
        color: #5D2E1F !important;
    }
</style>
""", unsafe_allow_html=True)

# ── Sidebar: Recent searches ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<h2 style='font-family: Playfair Display; color: #5D2E1F;'>🧭 Irina's Compass</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #8B6F5C; font-size: 0.9rem;'>Georgian business ownership lookup</p>", unsafe_allow_html=True)
    st.divider()
    
    st.markdown("<h4 style='color: #5D2E1F;'>Recent Searches</h4>", unsafe_allow_html=True)
    recent = get_recent_searches(limit=15)
    if not recent:
        st.caption("No searches yet. Start above!")
    else:
        for r in recent:
            icon = {"vat_id": "🔢", "company_name": "🏢", "owner_name": "👤"}.get(r.query_type, "🔍")
            label = f"{icon} {r.query[:28]}"
            if st.button(label, key=f"recent_{r.searched_at.isoformat()}_{r.query}", use_container_width=True):
                st.session_state["search_query"] = r.query
                st.session_state["search_type"] = r.query_type
                st.rerun()
    
    st.divider()
    st.markdown("""
    <div style="font-size: 0.75rem; color: #8B6F5C;">
        Data source: <a href="https://www.companyinfo.ge" target="_blank">companyinfo.ge</a><br>
        (Transparency International Georgia)<br>
        Cached for 7 days.
    </div>
    """, unsafe_allow_html=True)

# ── Main header ──────────────────────────────────────────────────────────────
st.markdown('<div class="main-header">Irina\'s Compass</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Find who owns restaurants & companies across Georgia</div>', unsafe_allow_html=True)

# ── Search tabs ──────────────────────────────────────────────────────────────
tab_vat, tab_company, tab_owner = st.tabs(["🔢 By VAT / ID Code", "🏢 By Company Name", "👤 By Owner Name"])

# Helper to run search and store in session state
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
            st.session_state["search_query"] = query
            st.session_state["search_type"] = query_type
        except Exception as e:
            st.error(f"Search failed: {e}")

# ── Tab 1: VAT ID ────────────────────────────────────────────────────────────
with tab_vat:
    c1, c2 = st.columns([3, 1])
    with c1:
        vat_query = st.text_input(
            "Enter VAT or Company ID",
            placeholder="e.g. 404447924 (9 digits for LLC, 11 for individual)",
            value=st.session_state.get("search_query", "") if st.session_state.get("search_type") == "vat_id" else "",
            key="vat_input",
        )
    with c2:
        st.write("")
        st.write("")
        if st.button("Search", key="btn_vat", use_container_width=True):
            if vat_query.strip():
                do_search(vat_query, "vat_id")
            else:
                st.warning("Please enter an ID code")

# ── Tab 2: Company Name ──────────────────────────────────────────────────────
with tab_company:
    c1, c2 = st.columns([3, 1])
    with c1:
        company_query = st.text_input(
            "Enter Company or Restaurant Name",
            placeholder="e.g. Good Shepherd or შპს არბითიეს გრუფი",
            value=st.session_state.get("search_query", "") if st.session_state.get("search_type") == "company_name" else "",
            key="company_input",
        )
    with c2:
        st.write("")
        st.write("")
        if st.button("Search", key="btn_company", use_container_width=True):
            if company_query.strip():
                do_search(company_query, "company_name")
            else:
                st.warning("Please enter a name")

# ── Tab 3: Owner Name ────────────────────────────────────────────────────────
with tab_owner:
    st.markdown("""
    <div class="info-box">
        💡 <strong>Tip:</strong> Type in Latin letters and the app will auto-convert to Georgian. 
        Example: type <em>"nana malenashvili"</em> and it becomes <em>"ნანა მალენაშვილი"</em>.
    </div>
    """, unsafe_allow_html=True)
    
    # Transliteration toggle
    auto_translit = st.toggle("Auto-convert Latin → Georgian", value=True, key="translit_toggle")
    
    c1, c2 = st.columns([3, 1])
    with c1:
        owner_query_raw = st.text_input(
            "Enter Owner Name",
            placeholder="e.g. nana malenashvili or ნანა მალენაშვილი",
            value=st.session_state.get("search_query", "") if st.session_state.get("search_type") == "owner_name" else "",
            key="owner_input",
        )
        
        # Live Georgian preview
        if owner_query_raw:
            if is_georgian_script(owner_query_raw):
                owner_query = owner_query_raw
                st.caption("✓ Detected Georgian script")
            elif auto_translit:
                owner_query = latin_to_georgian(owner_query_raw)
                if owner_query != owner_query_raw:
                    st.markdown(f'<div class="georgian-preview">🇬🇪 {owner_query}</div>', unsafe_allow_html=True)
                else:
                    owner_query = owner_query_raw
            else:
                owner_query = owner_query_raw
                st.caption("⚠️ Latin input — may not find results. Toggle auto-convert above.")
        else:
            owner_query = ""
    
    with c2:
        st.write("")
        st.write("")
        if st.button("Search", key="btn_owner", use_container_width=True):
            if owner_query.strip():
                do_search(owner_query, "owner_name")
            else:
                st.warning("Please enter a name")

# ── Results display ──────────────────────────────────────────────────────────
result: SearchResult = st.session_state.get("last_result")

if result:
    st.divider()
    
    # Header bar
    icon = {"vat_id": "🔢", "company_name": "🏢", "owner_name": "👤"}.get(result.query_type, "🔍")
    st.markdown(f"<h3 style='color: #5D2E1F;'>{icon} Results for \"{result.query}\"</h3>", unsafe_allow_html=True)
    
    if result.from_cache:
        st.caption("📦 Served from local cache")
    
    if result.error:
        st.error(result.error)
    
    if not result.companies:
        if not result.error:
            st.info("No companies found. Try a different search term.")
    else:
        # Export button
        export_data = []
        for c in result.companies:
            export_data.append({
                "ID Code": c.id_code,
                "Name": c.name,
                "Legal Form": c.legal_form,
                "Status": c.status,
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
                label="📥 CSV",
                data=df.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"irina_compass_{result.query.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        
        # Result cards
        for company in result.companies:
            status_class = {
                "Active": "badge-active",
                "In Liquidation": "badge-liquidation",
                "Terminated": "badge-terminated",
                "Suspended": "badge-terminated",
            }.get(company.status, "badge-medium")
            
            form_class = "badge-ie" if company.is_individual_entrepreneur else "badge-llc"
            conf_class = f"badge-{company.confidence}"
            
            st.markdown(f"""
            <div class="result-card">
                <div class="company-title">{company.name}</div>
                <div class="meta-line">
                    <span class="badge {form_class}">{company.legal_form}</span>
                    <span class="badge {status_class}">{company.status}</span>
                    <span class="badge {conf_class}">{company.confidence} confidence</span>
                    {'<span class="badge badge-medium">Cached</span>' if result.from_cache else ''}
                </div>
                <div style="color: #6B5B4F; font-size: 0.9rem; margin-bottom: 0.8rem;">
                    <strong>ID:</strong> {company.id_code} 
                    {'&nbsp;|&nbsp;<strong>Reg. Date:</strong> ' + company.registration_date if company.registration_date else ''}
                    {'&nbsp;|&nbsp;<strong>Address:</strong> ' + company.address if company.address else ''}
                </div>
            """, unsafe_allow_html=True)
            
            # Directors
            if company.directors:
                st.markdown('<div class="section-title">Directors / Representatives</div>', unsafe_allow_html=True)
                for d in company.directors:
                    warn = " <span class='nominee-warning'>⚠️ may be nominee</span>" if d.is_nominee_warning else ""
                    st.markdown(f"<div class='person-row'>• {d.name} {warn}</div>", unsafe_allow_html=True)
            
            # Shareholders / Owners
            if company.shareholders:
                st.markdown('<div class="section-title">Owners / Shareholders</div>', unsafe_allow_html=True)
                for s in company.shareholders:
                    share_info = f" <span style='color: #8B6F5C;'>({s.share_percent}%)</span>" if s.share_percent else ""
                    st.markdown(f"<div class='person-row'>• {s.name}{share_info}</div>", unsafe_allow_html=True)
            elif not company.is_individual_entrepreneur:
                st.markdown("<div class='person-row' style='color: #B87A3A; font-style: italic;'>No shareholder data available in this record.</div>", unsafe_allow_html=True)
            
            # Source & verification
            st.markdown(f"""
                <div style="margin-top: 1rem; font-size: 0.8rem; color: #9E8E7E;">
                    Source: <a href="{company.source_url}" target="_blank">companyinfo.ge</a>
                    &nbsp;|&nbsp; Fetched: {company.fetched_at.strftime('%Y-%m-%d %H:%M') if company.fetched_at else 'unknown'}
                    &nbsp;|&nbsp; <a href="https://enreg.reestri.gov.ge/main.php?c=search&m=search_by_number&n={company.id_code}" target="_blank">Verify on official NAPR ↗</a>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Disclaimer
        st.markdown("""
        <div class="disclaimer">
            <strong>Disclaimer:</strong> This tool aggregates publicly available data from 
            <a href="https://www.companyinfo.ge" target="_blank">companyinfo.ge</a> (Transparency International Georgia).
            Data may be incomplete or delayed. Directors may be nominees — shareholders are more likely to be true owners.
            For legally authoritative records, order an extract from the 
            <a href="https://enreg.reestri.gov.ge" target="_blank">National Agency of Public Registry</a>.
        </div>
        """, unsafe_allow_html=True)
