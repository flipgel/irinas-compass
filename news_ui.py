"""News UI rendering module for Irina's Compass — Visual Reading Experience.

Provides all Streamlit components for the news tab:
- Thumbnail-rich story cards with readable article previews
- Full article extraction with inline images and video embeds
- Bias bars, factuality meters, ownership badges (secondary overlay)
- Story cards with coverage visualization
- Blindspot indicators
"""
import html
import random
from datetime import datetime
from typing import List, Optional

import streamlit as st
import streamlit.components.v1 as components

from models import NewsStory, NewsArticle, NewsResult
from news import (
    fetch_news,
    fetch_full_article,
    analyze_coverage,
    get_blindspot_stories,
    get_full_spectrum_stories,
    search_news_stories,
    load_sources,
)


def _h(text: str) -> str:
    return html.escape(str(text) if text is not None else "")


# ═══════════════════════════════════════════════════════════════════════════════
#  COLOR SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

BIAS_COLORS = {
    "left": "#2563EB",
    "lean_left": "#60A5FA",
    "center": "#9CA3AF",
    "lean_right": "#F87171",
    "right": "#DC2626",
    "unknown": "#D1D5DB",
}

BIAS_LABELS = {
    "left": "Left",
    "lean_left": "Lean Left",
    "center": "Center",
    "lean_right": "Lean Right",
    "right": "Right",
    "unknown": "Unknown",
}

FACTUALITY_COLORS = {
    "high": "#16A34A",
    "mixed": "#EAB308",
    "low": "#DC2626",
}


def _bias_badge_html(bias: str) -> str:
    color = BIAS_COLORS.get(bias, BIAS_COLORS["unknown"])
    label = BIAS_LABELS.get(bias, bias)
    return (
        f'<span style="display:inline-block;padding:2px 8px;border-radius:2px;'
        f'font-size:0.6rem;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;'
        f'background-color:{color}22;color:{color};border:1px solid {color}44;">'
        f'{_h(label)}</span>'
    )


def _factuality_badge_html(factuality: str, score: int) -> str:
    color = FACTUALITY_COLORS.get(factuality, "#9CA3AF")
    bg = {"high": "#DCFCE7", "mixed": "#FEF9C3", "low": "#FEE2E2"}.get(factuality, "#F3F4F6")
    label = factuality.capitalize()
    return (
        f'<span style="display:inline-block;padding:2px 8px;border-radius:2px;'
        f'font-size:0.6rem;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;'
        f'background-color:{bg};color:{color};border:1px solid {color}33;">'
        f'{_h(label)} · {score}</span>'
    )


def _coverage_bar_html(story: NewsStory) -> str:
    total = story.coverage_total
    if total == 0:
        return '<div style="height:4px;background:#E5E7EB;border-radius:2px;"></div>'
    left_pct = (story.coverage_left / total) * 100
    center_pct = (story.coverage_center / total) * 100
    right_pct = (story.coverage_right / total) * 100
    segments = []
    if left_pct > 0:
        segments.append(f'<div style="width:{left_pct:.1f}%;height:100%;background:{BIAS_COLORS["left"]};"></div>')
    if center_pct > 0:
        segments.append(f'<div style="width:{center_pct:.1f}%;height:100%;background:{BIAS_COLORS["center"]};"></div>')
    if right_pct > 0:
        segments.append(f'<div style="width:{right_pct:.1f}%;height:100%;background:{BIAS_COLORS["right"]};"></div>')
    return f'<div style="display:flex;height:4px;border-radius:2px;overflow:hidden;background:#E5E7EB;">{"".join(segments)}</div>'


# ═══════════════════════════════════════════════════════════════════════════════
#  ARTICLE READER (full text + images + video)
# ═══════════════════════════════════════════════════════════════════════════════

def render_article_reader(article: NewsArticle, idx: int):
    """Render a full article reading experience with text, images, and video."""
    
    # Ensure full text is loaded
    if article.full_text is None:
        with st.spinner(f"Loading from {article.source}..."):
            article = fetch_full_article(article)
    
    # Source header
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:0.8rem;flex-wrap:wrap;">
        {_bias_badge_html(article.bias)}
        {_factuality_badge_html(article.factuality, article.factuality_score)}
        <span style="font-size:0.7rem;color:#6B7280;">{_h(article.source)}</span>
        <span style="font-size:0.65rem;color:#9CA3AF;">· {_h(article.ownership[:50])}</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Article title
    st.markdown(f"<h3 style='font-size:1.1rem;font-weight:600;color:#1A1A1A;margin-bottom:0.6rem;line-height:1.35;'>{_h(article.title)}</h3>", unsafe_allow_html=True)
    
    # Article images (from extraction)
    if article.article_images:
        cols = st.columns(min(len(article.article_images), 3))
        for i, img_url in enumerate(article.article_images[:3]):
            with cols[i]:
                try:
                    st.image(img_url, use_container_width=True)
                except Exception:
                    pass
    
    # Video embeds
    for vid_url in article.video_urls[:2]:
        if "youtube" in vid_url or "youtu.be" in vid_url:
            # Extract video ID for embed
            vid_id = None
            if "embed/" in vid_url:
                vid_id = vid_url.split("embed/")[-1].split("?")[0]
            elif "v=" in vid_url:
                vid_id = vid_url.split("v=")[-1].split("&")[0]
            elif "youtu.be/" in vid_url:
                vid_id = vid_url.split("youtu.be/")[-1].split("?")[0]
            
            if vid_id:
                components.html(
                    f'<iframe width="100%" height="360" src="https://www.youtube.com/embed/{vid_id}" '
                    f'frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" '
                    f'allowfullscreen></iframe>',
                    height=380,
                )
        else:
            st.video(vid_url)
    
    # Full article text
    if article.full_text and len(article.full_text) > 50:
        # Format paragraphs
        paragraphs = article.full_text.split('\n')
        formatted = []
        for p in paragraphs:
            p = p.strip()
            if p:
                formatted.append(f'<p style="margin-bottom:1rem;line-height:1.7;color:#374151;font-size:0.95rem;">{_h(p)}</p>')
        st.markdown("".join(formatted), unsafe_allow_html=True)
    else:
        # Fallback to summary
        if article.summary:
            st.markdown(f'<p style="line-height:1.7;color:#374151;font-size:0.95rem;">{_h(article.summary)}</p>', unsafe_allow_html=True)
        else:
            st.info("Full article text could not be extracted. Click the link below to read on the publisher's site.")
    
    # External link button
    st.link_button(f"🔗 Read on {article.source}", url=article.link, use_container_width=False)
    st.divider()


# ═══════════════════════════════════════════════════════════════════════════════
#  STORY CARD (visual, thumbnail-first)
# ═══════════════════════════════════════════════════════════════════════════════

def render_story_card(story: NewsStory, idx: int):
    """Render a visual news story card with thumbnail, preview, and expandable reader."""
    
    # Pick best thumbnail from any article
    thumbnail_url = None
    for a in story.articles:
        if a.thumbnail:
            thumbnail_url = a.thumbnail
            break
    
    # Pick lead article (most recent with thumbnail, or just most recent)
    lead = story.latest_article or story.articles[0]
    
    # Coverage breakdown
    cov_parts = []
    if story.coverage_left > 0:
        cov_parts.append(f'<span style="color:{BIAS_COLORS["left"]}">{story.coverage_left}L</span>')
    if story.coverage_center > 0:
        cov_parts.append(f'<span style="color:{BIAS_COLORS["center"]}">{story.coverage_center}C</span>')
    if story.coverage_right > 0:
        cov_parts.append(f'<span style="color:{BIAS_COLORS["right"]}">{story.coverage_right}R</span>')
    coverage_text = " · ".join(cov_parts) if cov_parts else ""
    
    # Blindspot indicator
    blindspot_html = ""
    if story.is_blindspot:
        direction = story.blindspot_direction
        dir_label = "LEFT" if direction == "left" else "RIGHT" if direction == "right" else "ONE-SIDE"
        dir_color = BIAS_COLORS.get(direction or "unknown", "#DC2626")
        blindspot_html = (
            f'<span style="display:inline-flex;align-items:center;gap:4px;'
            f'padding:2px 8px;border-radius:2px;font-size:0.6rem;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:0.06em;background:{dir_color}15;'
            f'color:{dir_color};border:1px solid {dir_color}33;">'
            f'⚠️ BLINDSPOT · {dir_label}</span>'
        )
    
    # Bias spread badge
    spread_labels = {
        "full_spectrum": ("Full Spectrum", "#16A34A"),
        "bipartisan": ("Bipartisan", "#0891B2"),
        "left_center": ("Left + Center", "#2563EB"),
        "right_center": ("Right + Center", "#DC2626"),
        "left_only": ("Left Only", "#2563EB"),
        "right_only": ("Right Only", "#DC2626"),
        "center_only": ("Center Only", "#6B7280"),
    }
    spread_label, spread_color = spread_labels.get(story.bias_spread, ("Mixed", "#6B7280"))
    spread_html = (
        f'<span style="display:inline-block;padding:2px 8px;border-radius:2px;'
        f'font-size:0.6rem;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;'
        f'background:{spread_color}11;color:{spread_color};border:1px solid {spread_color}22;">'
        f'{spread_label}</span>'
    )
    
    # Owners
    owners = story.ownership_diversity
    owner_badges = []
    for owner, count in sorted(owners.items(), key=lambda x: -x[1])[:3]:
        owner_badges.append(
            f'<span style="font-size:0.65rem;color:#6B7280;background:#F3F4F6;'
            f'padding:1px 6px;border-radius:2px;border:1px solid #E5E7EB;">'
            f'{_h(owner[:35])}{" · " + str(count) if count > 1 else ""}</span>'
        )
    
    # Preview text from lead article
    preview = lead.summary or ""
    if not preview and lead.full_text:
        preview = lead.full_text[:200]
    preview = preview[:180] + "…" if len(preview) > 180 else preview
    
    # Topic pills
    topic_pills = []
    for t in story.topics[:3]:
        topic_pills.append(
            f'<span style="font-size:0.6rem;color:#6B7280;background:#F3F4F6;'
            f'padding:1px 6px;border-radius:10px;text-transform:uppercase;letter-spacing:0.04em;">'
            f'{_h(t)}</span>'
        )
    
    # Card HTML
    card_html = f"""
    <div style="background:#FFFCF7;border:1px solid #C8BEB0;border-radius:4px;margin-bottom:1.2rem;'
    box-shadow:0 1px 3px rgba(0,0,0,0.04);overflow:hidden;"
    onmouseover="this.style.transform='translateY(-2px)';this.style.boxShadow='0 4px 12px rgba(0,0,0,0.06)';this.style.borderColor='#B0A494';"
    onmouseout="this.style.transform='translateY(0)';this.style.boxShadow='0 1px 3px rgba(0,0,0,0.04)';this.style.borderColor='#C8BEB0';">
    """
    
    st.markdown(card_html, unsafe_allow_html=True)
    
    # Thumbnail image (Streamlit native for reliability)
    if thumbnail_url:
        try:
            st.image(thumbnail_url, use_container_width=True)
        except Exception:
            pass
    
    # Card content padding
    st.markdown("""
    <div style="padding:1.2rem 1.4rem;">
    """, unsafe_allow_html=True)
    
    # Meta row
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:0.5rem;flex-wrap:wrap;">
        {spread_html}
        {blindspot_html}
        <span style="font-size:0.65rem;color:#9CA3AF;margin-left:auto;">{story.coverage_total} sources</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Headline
    st.markdown(f"""
    <div style="font-size:1.25rem;font-weight:600;color:#1A1A1A;line-height:1.35;margin-bottom:0.4rem;letter-spacing:-0.01em;">
        {_h(story.headline[:140])}{"…" if len(story.headline) > 140 else ""}
    </div>
    """, unsafe_allow_html=True)
    
    # Topics
    if topic_pills:
        st.markdown(f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:0.5rem;flex-wrap:wrap;">{" ".join(topic_pills)}</div>', unsafe_allow_html=True)
    
    # Preview text
    if preview:
        st.markdown(f'<p style="font-size:0.9rem;color:#5A5048;line-height:1.6;margin-bottom:0.6rem;">{_h(preview)}</p>', unsafe_allow_html=True)
    
    # Coverage bar
    st.markdown(f'<div style="margin-bottom:0.4rem;">{_coverage_bar_html(story)}</div>', unsafe_allow_html=True)
    
    # Footer meta
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:0.6rem;font-size:0.7rem;color:#6B7280;flex-wrap:wrap;">
        <span>{coverage_text}</span>
        <span style="color:#D1D5DB;">|</span>
        <span>Factuality: {story.avg_factuality:.0f}/100</span>
        <span style="color:#D1D5DB;">|</span>
        <span>{len(story.ownership_diversity)} owners</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Owner badges
    if owner_badges:
        st.markdown(f'<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:0.8rem;">{" ".join(owner_badges)}</div>', unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Article reader expanders
    if len(story.articles) == 1:
        # Single article — show reader directly with a toggle
        key = f"read_{story.story_id}_{idx}"
        if st.button(f"📰 Read full article from {story.articles[0].source}", key=key, use_container_width=True):
            st.session_state[f"show_{key}"] = not st.session_state.get(f"show_{key}", False)
        if st.session_state.get(f"show_{key}", False):
            render_article_reader(story.articles[0], idx)
    else:
        # Multiple articles — one expander per source
        for a_idx, article in enumerate(story.articles):
            exp_key = f"article_{story.story_id}_{idx}_{a_idx}"
            with st.expander(f"📰 Read from {article.source} ({BIAS_LABELS.get(article.bias, article.bias)})", expanded=False):
                render_article_reader(article, idx * 100 + a_idx)
    
    st.markdown("</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  STATS DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

def render_stats_dashboard(coverage: dict):
    st.markdown("""
    <style>
    .news-stat-box {
        background: #FFFCF7;
        border: 1px solid #C8BEB0;
        border-radius: 4px;
        padding: 1rem 1.2rem;
        text-align: center;
    }
    .news-stat-number {
        font-size: 1.6rem;
        font-weight: 700;
        color: #1A1A1A;
        line-height: 1;
    }
    .news-stat-label {
        font-size: 0.6rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #5A5048;
        margin-top: 0.3rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    stats = [
        (c1, str(coverage.get("total_stories", 0)), "Stories"),
        (c2, str(coverage.get("blindspots", 0)), "Blindspots"),
        (c3, str(coverage.get("full_spectrum", 0)), "Full Spectrum"),
        (c4, str(coverage.get("left_articles", 0)), "Left Articles"),
        (c5, str(coverage.get("center_articles", 0)), "Center Articles"),
        (c6, str(coverage.get("right_articles", 0)), "Right Articles"),
    ]
    for col, num, label in stats:
        with col:
            st.markdown(
                f'<div class="news-stat-box">'
                f'<div class="news-stat-number">{_h(num)}</div>'
                f'<div class="news-stat-label">{_h(label)}</div>'
                f'</div>',
                unsafe_allow_html=True
            )


# ═══════════════════════════════════════════════════════════════════════════════
#  SOURCE LEGEND
# ═══════════════════════════════════════════════════════════════════════════════

def render_source_legend():
    st.markdown("""
    <div style="margin-top:1.5rem;padding-top:1rem;border-top:1px solid #9E9486;">
        <div style="font-size:0.6rem;text-transform:uppercase;letter-spacing:0.14em;color:#5A5048;margin-bottom:0.8rem;font-weight:600;">
            Bias Legend
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    legend_items = [
        ("Left", BIAS_COLORS["left"]),
        ("Lean Left", BIAS_COLORS["lean_left"]),
        ("Center", BIAS_COLORS["center"]),
        ("Lean Right", BIAS_COLORS["lean_right"]),
        ("Right", BIAS_COLORS["right"]),
    ]
    for label, color in legend_items:
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">'
            f'<div style="width:12px;height:12px;border-radius:2px;background:{color};"></div>'
            f'<span style="font-size:0.7rem;color:#5A5048;">{_h(label)}</span>'
            f'</div>',
            unsafe_allow_html=True
        )
    
    st.markdown("""
    <div style="margin-top:1rem;padding-top:1rem;border-top:1px solid #9E9486;">
        <div style="font-size:0.6rem;text-transform:uppercase;letter-spacing:0.14em;color:#5A5048;margin-bottom:0.8rem;font-weight:600;">
            Factuality
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    fact_items = [
        ("High (85–100)", FACTUALITY_COLORS["high"]),
        ("Mixed (65–84)", FACTUALITY_COLORS["mixed"]),
        ("Low (0–64)", FACTUALITY_COLORS["low"]),
    ]
    for label, color in fact_items:
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">'
            f'<div style="width:12px;height:12px;border-radius:2px;background:{color};"></div>'
            f'<span style="font-size:0.7rem;color:#5A5048;">{_h(label)}</span>'
            f'</div>',
            unsafe_allow_html=True
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN NEWS TAB
# ═══════════════════════════════════════════════════════════════════════════════

def render_news_tab():
    st.markdown("""
    <div style="text-align:center;padding:2rem 0 1.5rem 0;margin-bottom:1.5rem;
    background:linear-gradient(180deg, rgba(255,252,247,0.35) 0%, rgba(255,252,247,0) 100%);border-radius:4px;">
        <div style="font-family:Inter,sans-serif;font-size:2.2rem;font-weight:700;letter-spacing:-0.03em;color:#1A1A1A;line-height:1.1;margin-bottom:0.3rem;">
            Irina's Newsroom
        </div>
        <div style="font-size:0.8rem;color:#5A5048;letter-spacing:0.04em;">
            Read every side of every story · Bias · Ownership · Factuality
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4, col5 = st.columns([2, 1.5, 1.5, 1.5, 1])
    
    with col1:
        search_query = st.text_input(
            "Search stories",
            placeholder="Keyword, topic, or headline...",
            key="news_search",
            label_visibility="collapsed",
        )
    
    with col2:
        topic_filter = st.selectbox(
            "Topic",
            options=["All", "Politics", "War", "Economy", "Tech", "Health", "Climate", "Crime", "Immigration", "Sport", "Entertainment"],
            key="news_topic",
            label_visibility="collapsed",
        )
    
    with col3:
        bias_filter = st.selectbox(
            "Bias filter",
            options=["All coverage", "Left only", "Center only", "Right only", "Blindspots"],
            key="news_bias_filter",
            label_visibility="collapsed",
        )
    
    with col4:
        sort_by = st.selectbox(
            "Sort by",
            options=["Most recent", "Most coverage", "Blindspots first", "Full spectrum"],
            key="news_sort",
            label_visibility="collapsed",
        )
    
    with col5:
        st.write("")
        st.write("")
        refresh = st.button("⟳ Refresh", key="news_refresh", use_container_width=True)
    
    topic = None if topic_filter == "All" else topic_filter.lower()
    bias_map = {
        "All coverage": None,
        "Left only": "left",
        "Center only": "center",
        "Right only": "right",
        "Blindspots": None,
    }
    bias = bias_map.get(bias_filter)
    blindspots_only = bias_filter == "Blindspots"
    
    with st.spinner(random.choice([
        "📡 Scanning the airwaves...",
        "📰 Gathering headlines...",
        "🔍 Analyzing coverage...",
        "📊 Computing bias maps...",
    ])):
        try:
            result = fetch_news(
                topic_filter=topic,
                bias_filter=bias,
                blindspots_only=blindspots_only,
                use_cache=not refresh,
            )
        except Exception as e:
            st.error(f"News fetch failed: {e}")
            return
    
    if result.error:
        st.error(result.error)
        return
    
    stories = result.stories
    
    if search_query.strip():
        stories = search_news_stories(stories, search_query.strip())
    
    if sort_by == "Most coverage":
        stories.sort(key=lambda s: s.coverage_total, reverse=True)
    elif sort_by == "Blindspots first":
        stories.sort(key=lambda s: (s.is_blindspot, s.coverage_total), reverse=True)
    elif sort_by == "Full spectrum":
        stories.sort(key=lambda s: (s.bias_spread == "full_spectrum", s.coverage_total), reverse=True)
    
    coverage_stats = analyze_coverage(stories if stories else result.stories)
    render_stats_dashboard(coverage_stats)
    
    st.markdown(f"""
    <div style="display:flex;align-items:center;justify-content:space-between;margin:1.2rem 0 0.8rem 0;">
        <div style="font-size:0.6rem;text-transform:uppercase;letter-spacing:0.14em;color:#5A5048;font-weight:600;">
            {len(stories)} Stories · Fetched from {result.sources_fetched} sources in {result.fetch_time_ms}ms
            {" · Cached" if result.cached else ""}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if not stories:
        st.markdown("""
        <div style="text-align:center;padding:4rem 2rem;color:#7A7060;background:linear-gradient(180deg, rgba(255,252,247,0.25) 0%, rgba(255,252,247,0) 100%);border-radius:4px;border:1px dashed #C8BEB0;margin-top:1rem;">
            <div style="font-size:1.4rem;font-weight:600;margin-bottom:0.6rem;color:#5A5048;letter-spacing:-0.02em;">No stories found</div>
            <div style="font-size:0.85rem;color:#7A7060;line-height:1.6;">
                Try adjusting your filters or search query.<br>
                News sources may be temporarily unavailable.
            </div>
        </div>
        """, unsafe_allow_html=True)
        return
    
    for idx, story in enumerate(stories):
        render_story_card(story, idx)
    
    with st.expander("ℹ️ About source ratings & methodology"):
        st.markdown("""
        **Bias ratings** are aggregated from independent media monitoring organizations including 
        [Ad Fontes Media](https://www.adfontesmedia.com), [AllSides](https://www.allsides.com), and 
        [Media Bias/Fact Check](https://mediabiasfactcheck.com). Ratings reflect the *publication-level* 
        editorial tendency, not individual article bias.
        
        **Factuality scores** estimate a source's track record for factual reporting based on 
        correction rates, use of loaded language, and transparency about sources/methodology.
        
        **Ownership** reveals the parent company or controlling entity behind each outlet.
        
        **Blindspots** are stories receiving lopsided coverage (predominantly from one ideological side). 
        They highlight potential media gaps and filter bubbles.
        
        **Full article text** is extracted automatically from publisher websites for your convenience. 
        Always verify important information against the original source.
        
        *This is a transparency tool, not a fact-checker. Always read multiple sources.*
        """)
