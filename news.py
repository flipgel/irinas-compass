"""News intelligence engine for Irina's Compass.

Fetches RSS feeds, deduplicates articles into stories, analyzes coverage bias,
detects blindspots, and exposes source ownership/factuality metadata.
"""
import json
import logging
import re
import time
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse

import feedparser
import requests
import trafilatura
from rapidfuzz import fuzz

from models import NewsSource, NewsArticle, NewsStory, NewsResult
from cache import get_news_cache, save_news_cache, get_article_cache, save_article_cache

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
#  CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
SOURCES_PATH = "news_sources.json"
REQUEST_TIMEOUT = 12
MAX_ARTICLES_PER_SOURCE = 15
SIMILARITY_THRESHOLD = 78  # rapidfuzz ratio for deduplication
MAX_STORIES = 80

# ═══════════════════════════════════════════════════════════════════════════════
#  SOURCE LOADING
# ═══════════════════════════════════════════════════════════════════════════════

_cache_sources: Optional[List[NewsSource]] = None


def load_sources() -> List[NewsSource]:
    """Load curated news sources with bias/ownership data."""
    global _cache_sources
    if _cache_sources is not None:
        return _cache_sources
    try:
        with open(SOURCES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        _cache_sources = [NewsSource(**s) for s in data.get("sources", [])]
        return _cache_sources
    except Exception as e:
        logger.error(f"Failed to load news sources: {e}")
        return []


def get_source_by_name(name: str) -> Optional[NewsSource]:
    for s in load_sources():
        if s.name.lower() == name.lower():
            return s
    return None


# ═══════════════════════════════════════════════════════════════════════════════
#  RSS FETCHING
# ═══════════════════════════════════════════════════════════════════════════════

def _parse_rss_date(entry) -> Optional[datetime]:
    """Extract datetime from RSS entry using multiple field strategies."""
    # feedparser parsed date
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            tt = entry.published_parsed
            return datetime(*tt[:6], tzinfo=timezone.utc)
        except Exception:
            pass
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        try:
            tt = entry.updated_parsed
            return datetime(*tt[:6], tzinfo=timezone.utc)
        except Exception:
            pass
    # Raw strings
    for field in ("published", "updated", "pubDate", "dc:date"):
        val = getattr(entry, field, None)
        if val:
            for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z",
                        "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%d %b %Y"):
                try:
                    return datetime.strptime(val.strip(), fmt)
                except ValueError:
                    continue
    return None


def _clean_html(text: str) -> str:
    """Strip HTML tags and decode entities roughly."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    text = text.replace("&lt;", "<").replace("&gt;", ">")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_thumbnail(entry) -> Optional[str]:
    """Extract best thumbnail image from RSS entry."""
    # media:thumbnail
    if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
        thumbs = entry.media_thumbnail
        if isinstance(thumbs, list) and thumbs:
            # Pick largest thumbnail
            best = max(thumbs, key=lambda t: int(t.get("width", "0") or "0"))
            return best.get("url")
    # media:content with medium=image
    if hasattr(entry, "media_content") and entry.media_content:
        contents = entry.media_content
        if isinstance(contents, list):
            for mc in contents:
                if mc.get("medium") == "image" or mc.get("type", "").startswith("image/"):
                    return mc.get("url")
        elif isinstance(contents, dict):
            if contents.get("medium") == "image" or contents.get("type", "").startswith("image/"):
                return contents.get("url")
    # enclosure with image
    if hasattr(entry, "enclosures") and entry.enclosures:
        for enc in entry.enclosures:
            if enc.get("type", "").startswith("image/"):
                return enc.get("href")
    # Look for image in summary/description HTML
    html_text = getattr(entry, "summary", "") or getattr(entry, "description", "")
    if html_text:
        m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html_text)
        if m:
            return m.group(1)
    return None


def _extract_topics(title: str, summary: str) -> List[str]:
    """Simple keyword extraction for topic grouping."""
    text = f"{title} {summary}".lower()
    topics = []
    topic_map = {
        "politics": ["election", "vote", "parliament", "congress", "president", "minister", "government", "senate", "law", "bill", "policy", "campaign"],
        "war": ["war", "military", "attack", "bomb", "missile", "conflict", "invasion", "troop", "defense", "weapon", "ceasefire"],
        "economy": ["economy", "inflation", "recession", "stock", "market", "trade", "tariff", "gdp", "unemployment", "bank", "finance", "investment", "oil", "gas"],
        "tech": ["ai", "artificial intelligence", "tech", "cyber", "software", "chip", "semiconductor", "google", "apple", "microsoft", "meta", "crypto", "bitcoin", "hack"],
        "health": ["health", "covid", "pandemic", "vaccine", "medicine", "hospital", "disease", "virus", "mental health", "fda"],
        "climate": ["climate", "warming", "carbon", "green", "renewable", "energy", "flood", "hurricane", "drought", "extreme weather"],
        "crime": ["crime", "police", "shooting", "murder", "arrest", "court", "trial", "prison", "gun", "violence"],
        "immigration": ["immigration", "migrant", "border", "refugee", "asylum", "deport", "visa"],
        "sport": ["sport", "football", "soccer", "basketball", "tennis", "olympic", "fifa", "nfl", "nba"],
        "entertainment": ["celebrity", "movie", "film", "music", "oscar", "grammy", "hollywood", "actor", "netflix"],
    }
    for topic, keywords in topic_map.items():
        if any(kw in text for kw in keywords):
            topics.append(topic)
    return topics if topics else ["general"]


def fetch_source(source: NewsSource) -> List[NewsArticle]:
    """Fetch and parse articles from a single RSS source."""
    articles = []
    try:
        # Use requests first to get raw feed, then feedparser
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(source.rss, headers=headers, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        parsed = feedparser.parse(resp.content)
    except Exception as e:
        logger.warning(f"RSS fetch failed for {source.name}: {e}")
        return articles

    for entry in parsed.entries[:MAX_ARTICLES_PER_SOURCE]:
        try:
            title = _clean_html(getattr(entry, "title", ""))
            link = getattr(entry, "link", "")
            summary = _clean_html(getattr(entry, "summary", getattr(entry, "description", "")))
            if not title or not link:
                continue

            published = _parse_rss_date(entry)
            topics = _extract_topics(title, summary)

            thumbnail = _extract_thumbnail(entry)
            article = NewsArticle(
                title=title,
                link=link,
                source=source.name,
                published=published,
                summary=summary[:400] if summary else None,
                thumbnail=thumbnail,
                bias=source.bias,
                bias_score=source.bias_score,
                factuality=source.factuality,
                factuality_score=source.factuality_score,
                ownership=source.ownership,
                topics=topics,
            )
            articles.append(article)
        except Exception as e:
            logger.debug(f"Error parsing entry from {source.name}: {e}")
            continue

    return articles


# ═══════════════════════════════════════════════════════════════════════════════
#  DEDUPLICATION & STORY GROUPING
# ═══════════════════════════════════════════════════════════════════════════════

def _title_similarity(a: str, b: str) -> float:
    """Compute fuzzy similarity between two article titles."""
    return fuzz.ratio(a.lower(), b.lower())


def _normalize_title(title: str) -> str:
    """Strip prefixes/suffixes that vary across sources."""
    t = title.lower()
    t = re.sub(r"^(breaking:|update:|exclusive:|watch:|live:)\s*", "", t)
    t = re.sub(r"\s*-\s*bbc news\s*$", "", t)
    t = re.sub(r"\s*\|.*$", "", t)
    return t.strip()


def group_articles_into_stories(articles: List[NewsArticle]) -> List[NewsStory]:
    """Cluster articles into stories by title similarity."""
    stories: List[NewsStory] = []

    for article in articles:
        norm = _normalize_title(article.title)
        matched = False

        # Try to match to existing story
        for story in stories:
            story_norm = _normalize_title(story.headline)
            if _title_similarity(norm, story_norm) >= SIMILARITY_THRESHOLD:
                story.articles.append(article)
                # Merge topics
                story.topics = list(set(story.topics + article.topics))
                matched = True
                break

        if not matched:
            story_id = hashlib.md5(norm.encode()).hexdigest()[:12]
            stories.append(NewsStory(
                story_id=story_id,
                headline=article.title,
                articles=[article],
                topics=article.topics,
            ))

    # Sort by most recent article date, then by coverage count
    def _sort_key(s: NewsStory):
        latest = s.latest_article
        dt = latest.published if latest and latest.published else datetime.min
        return (dt, s.coverage_total)

    stories.sort(key=_sort_key, reverse=True)
    return stories[:MAX_STORIES]


# ═══════════════════════════════════════════════════════════════════════════════
#  COVERAGE ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_coverage(stories: List[NewsStory]) -> Dict:
    """Compute aggregate coverage statistics."""
    total = len(stories)
    blindspots = sum(1 for s in stories if s.is_blindspot)
    full_spectrum = sum(1 for s in stories if s.bias_spread == "full_spectrum")
    bipartisan = sum(1 for s in stories if s.bias_spread == "bipartisan")
    left_only = sum(1 for s in stories if s.bias_spread == "left_only")
    right_only = sum(1 for s in stories if s.bias_spread == "right_only")
    center_only = sum(1 for s in stories if s.bias_spread == "center_only")

    all_articles = [a for s in stories for a in s.articles]
    left_count = sum(1 for a in all_articles if a.bias in ("left", "lean_left"))
    center_count = sum(1 for a in all_articles if a.bias == "center")
    right_count = sum(1 for a in all_articles if a.bias in ("right", "lean_right"))

    return {
        "total_stories": total,
        "total_articles": len(all_articles),
        "blindspots": blindspots,
        "full_spectrum": full_spectrum,
        "bipartisan": bipartisan,
        "left_only": left_only,
        "right_only": right_only,
        "center_only": center_only,
        "left_articles": left_count,
        "center_articles": center_count,
        "right_articles": right_count,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  FULL ARTICLE EXTRACTION (on-demand)
# ═══════════════════════════════════════════════════════════════════════════════

YOUTUBE_PATTERNS = [
    re.compile(r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})'),
    re.compile(r'youtube\.com/embed/([a-zA-Z0-9_-]{11})'),
]


def _detect_videos(html_text: str) -> List[str]:
    """Detect YouTube video embeds in HTML."""
    videos = []
    seen = set()
    for pattern in YOUTUBE_PATTERNS:
        for match in pattern.finditer(html_text):
            vid = match.group(1)
            if vid not in seen:
                seen.add(vid)
                videos.append(f"https://www.youtube.com/embed/{vid}")
    # Also detect generic iframe video embeds
    for match in re.finditer(r'<iframe[^>]+src=["\'](https?://[^"\']+)["\']', html_text):
        url = match.group(1)
        if any(x in url for x in ["youtube", "youtu.be", "vimeo", "dailymotion"]):
            if url not in seen:
                seen.add(url)
                videos.append(url)
    return videos


def fetch_full_article(article: NewsArticle) -> NewsArticle:
    """Fetch and extract full article text, images, and videos on demand.
    
    Mutates and returns the article with full_text, article_images, video_urls populated.
    """
    # Check cache
    cached = get_article_cache(article.link)
    if cached:
        article.full_text = cached["full_text"]
        article.article_images = cached["images"]
        article.video_urls = cached["videos"]
        return article

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(article.link, headers=headers, timeout=15)
        resp.raise_for_status()
        html = resp.text

        # Extract main content with trafilatura
        extracted = trafilatura.extract(
            html,
            include_images=True,
            include_links=False,
            include_comments=False,
            include_tables=False,
            deduplicate=True,
            url=article.link,
        )

        # Extract images from HTML (trafilatura include_images returns markdown image refs)
        images = []
        if extracted:
            # Find markdown image syntax: ![alt](url)
            for match in re.finditer(r'!\[([^\]]*)\]\((https?://[^\)]+)\)', extracted):
                img_url = match.group(2).strip()
                if img_url and img_url not in images:
                    images.append(img_url)
            # Also find bare image URLs in the extracted text
            for match in re.finditer(r'https?://[^\s\)]+\.(?:jpg|jpeg|png|webp|gif)', extracted):
                img_url = match.group(0)
                if img_url not in images:
                    images.append(img_url)

        # Fallback: extract images directly from HTML
        if not images:
            for match in re.finditer(r'<img[^>]+src=["\'](https?://[^"\']+)["\']', html):
                img_url = match.group(1)
                if img_url and img_url not in images and not any(x in img_url.lower() for x in ["icon", "logo", "avatar", "tracking", "pixel"]):
                    images.append(img_url)

        # Detect videos
        videos = _detect_videos(html)

        # Clean up extracted text
        full_text = extracted or ""
        if full_text:
            # Remove markdown image references for cleaner text
            full_text = re.sub(r'!\[([^\]]*)\]\(([^\)]+)\)', r'', full_text)
            # Clean up extra whitespace
            full_text = re.sub(r'\n{3,}', '\n\n', full_text).strip()

        article.full_text = full_text[:8000] if full_text else None
        article.article_images = images[:8]  # Limit images
        article.video_urls = videos

        # Save to cache
        save_article_cache(
            article.link,
            article.title,
            article.full_text or "",
            article.article_images,
            article.video_urls,
        )

    except Exception as e:
        logger.warning(f"Full article extraction failed for {article.link}: {e}")
        article.full_text = article.summary or "Could not load full article. Click the source link to read on the publisher's site."

    return article


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_news(topic_filter: Optional[str] = None,
               bias_filter: Optional[str] = None,
               blindspots_only: bool = False,
               use_cache: bool = True) -> NewsResult:
    """Fetch news from all sources, group into stories, analyze coverage.
    
    Args:
        topic_filter: Filter stories by topic keyword (e.g. 'politics', 'war')
        bias_filter: Show only stories with coverage from this bias ('left','center','right')
        blindspots_only: If True, only return blindspot stories
        use_cache: Use cached results if available (1-hour TTL)
    """
    start = time.time()
    
    # Check cache
    if use_cache:
        cache_key = f"news_{topic_filter or 'all'}_{bias_filter or 'all'}_{blindspots_only}"
        cached = get_news_cache(cache_key)
        if cached:
            cached.cached = True
            return cached

    sources = load_sources()
    if not sources:
        return NewsResult(error="No news sources configured.")

    all_articles: List[NewsArticle] = []
    sources_ok = 0

    for source in sources:
        articles = fetch_source(source)
        if articles:
            sources_ok += 1
        all_articles.extend(articles)
        # Small delay to be polite
        time.sleep(0.2)

    if not all_articles:
        return NewsResult(
            error="No articles could be fetched. Sources may be temporarily unavailable.",
            sources_fetched=sources_ok,
        )

    stories = group_articles_into_stories(all_articles)

    # Apply filters
    if topic_filter:
        kw = topic_filter.lower()
        stories = [s for s in stories if any(kw in t for t in s.topics) or any(kw in a.title.lower() for a in s.articles)]
    
    if bias_filter:
        stories = [s for s in stories if getattr(s, f"coverage_{bias_filter}", 0) > 0]
    
    if blindspots_only:
        stories = [s for s in stories if s.is_blindspot]

    result = NewsResult(
        stories=stories,
        sources_fetched=sources_ok,
        articles_fetched=len(all_articles),
        fetch_time_ms=int((time.time() - start) * 1000),
    )

    if use_cache:
        save_news_cache(cache_key, result)

    return result


def get_blindspot_stories(stories: List[NewsStory]) -> List[NewsStory]:
    """Return only blindspot stories, sorted by most lopsided."""
    blindspots = [s for s in stories if s.is_blindspot]
    # Sort by coverage gap (difference between dominant side and others)
    def _gap(s: NewsStory):
        return abs(s.coverage_left - s.coverage_right)
    blindspots.sort(key=_gap, reverse=True)
    return blindspots


def get_full_spectrum_stories(stories: List[NewsStory]) -> List[NewsStory]:
    """Return stories with the most balanced coverage."""
    balanced = [s for s in stories if s.bias_spread in ("full_spectrum", "bipartisan")]
    balanced.sort(key=lambda s: s.coverage_total, reverse=True)
    return balanced


def search_news_stories(stories: List[NewsStory], query: str) -> List[NewsStory]:
    """Filter stories by search query across titles and article text."""
    q = query.lower().strip()
    if not q:
        return stories
    matched = []
    for story in stories:
        score = 0
        # Headline match
        if q in story.headline.lower():
            score += 10
        # Article title matches
        for a in story.articles:
            if q in a.title.lower():
                score += 5
            if a.summary and q in a.summary.lower():
                score += 2
        # Topic match
        if any(q in t for t in story.topics):
            score += 3
        if score > 0:
            matched.append((score, story))
    
    matched.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in matched]
