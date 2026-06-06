"""SQLite cache layer with TTL for Irina's Compass."""
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from models import Company, Person, SearchResult, NewsResult

DB_PATH = Path(__file__).parent / "data" / "cache.db"
CACHE_TTL_DAYS = 7
NEWS_CACHE_TTL_HOURS = 1


def _ensure_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id_code TEXT PRIMARY KEY,
            name TEXT,
            legal_form TEXT,
            status TEXT,
            registration_date TEXT,
            address TEXT,
            directors TEXT,
            shareholders TEXT,
            also_known_as TEXT,
            source_url TEXT,
            fetched_at TEXT,
            confidence TEXT,
            industry TEXT,
            industry_source TEXT
        )
    """)
    # Migration: add industry columns to old tables
    c.execute("PRAGMA table_info(companies)")
    existing_cols = {row[1] for row in c.fetchall()}
    if "industry" not in existing_cols:
        c.execute("ALTER TABLE companies ADD COLUMN industry TEXT")
    if "industry_source" not in existing_cols:
        c.execute("ALTER TABLE companies ADD COLUMN industry_source TEXT")

    c.execute("""
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT,
            query_type TEXT,
            result_ids TEXT,
            searched_at TEXT,
            from_cache INTEGER
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS news_cache (
            cache_key TEXT PRIMARY KEY,
            data TEXT,
            fetched_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def _person_to_dict(p: Person) -> dict:
    return {
        "name": p.name,
        "role": p.role,
        "person_id": p.person_id,
        "share_percent": p.share_percent,
        "start_date": p.start_date,
        "end_date": p.end_date,
        "is_nominee_warning": p.is_nominee_warning,
    }


def _person_from_dict(d: dict) -> Person:
    return Person(**d)


def save_company(company: Company):
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        INSERT OR REPLACE INTO companies
        (id_code, name, legal_form, status, registration_date, address,
         directors, shareholders, also_known_as, source_url, fetched_at,
         confidence, industry, industry_source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            company.id_code,
            company.name,
            company.legal_form,
            company.status,
            company.registration_date,
            company.address,
            json.dumps([_person_to_dict(p) for p in company.directors]),
            json.dumps([_person_to_dict(p) for p in company.shareholders]),
            json.dumps(company.also_known_as),
            company.source_url,
            company.fetched_at.isoformat() if company.fetched_at else None,
            company.confidence,
            company.industry,
            company.industry_source,
        ),
    )
    conn.commit()
    conn.close()


def get_company(id_code: str) -> Optional[Company]:
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM companies WHERE id_code = ?", (id_code,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None

    fetched_at = datetime.fromisoformat(row[10]) if row[10] else None
    if fetched_at and datetime.now() - fetched_at > timedelta(days=CACHE_TTL_DAYS):
        return None  # Expired

    return Company(
        id_code=row[0],
        name=row[1],
        legal_form=row[2],
        status=row[3],
        registration_date=row[4],
        address=row[5],
        directors=[_person_from_dict(d) for d in json.loads(row[6] or "[]")],
        shareholders=[_person_from_dict(s) for s in json.loads(row[7] or "[]")],
        also_known_as=json.loads(row[8] or "[]"),
        source_url=row[9],
        fetched_at=fetched_at,
        confidence=row[11] or "high",
        industry=row[12],
        industry_source=row[13] or "heuristic",
    )


def save_search(result: SearchResult):
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    ids = [c.id_code for c in result.companies]
    c.execute(
        "INSERT INTO search_history (query, query_type, result_ids, searched_at, from_cache) VALUES (?, ?, ?, ?, ?)",
        (
            result.query,
            result.query_type,
            json.dumps(ids),
            result.searched_at.isoformat(),
            1 if result.from_cache else 0,
        ),
    )
    conn.commit()
    conn.close()


def get_recent_searches(limit: int = 20) -> List[SearchResult]:
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT query, query_type, result_ids, searched_at, from_cache FROM search_history ORDER BY searched_at DESC LIMIT ?",
        (limit,),
    )
    rows = c.fetchall()
    conn.close()

    results = []
    for row in rows:
        companies = []
        for id_code in json.loads(row[2] or "[]"):
            comp = get_company(id_code)
            if comp:
                companies.append(comp)
        results.append(
            SearchResult(
                query=row[0],
                query_type=row[1],
                companies=companies,
                searched_at=datetime.fromisoformat(row[3]),
                from_cache=bool(row[4]),
            )
        )
    return results


# ═══════════════════════════════════════════════════════════════════════════════
#  NEWS CACHE (short TTL)
# ═══════════════════════════════════════════════════════════════════════════════

def get_news_cache(cache_key: str) -> Optional[NewsResult]:
    """Retrieve cached news result if not expired."""
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT data, fetched_at FROM news_cache WHERE cache_key = ?", (cache_key,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None

    fetched_at = datetime.fromisoformat(row[1]) if row[1] else None
    if fetched_at and datetime.now() - fetched_at > timedelta(hours=NEWS_CACHE_TTL_HOURS):
        return None  # Expired

    try:
        import json
        data = json.loads(row[0])
        from models import NewsStory, NewsArticle
        stories = []
        for s_data in data.get("stories", []):
            articles = []
            for a_data in s_data.get("articles", []):
                published = None
                if a_data.get("published"):
                    try:
                        published = datetime.fromisoformat(a_data["published"])
                    except Exception:
                        pass
                articles.append(NewsArticle(
                    title=a_data["title"],
                    link=a_data["link"],
                    source=a_data["source"],
                    published=published,
                    summary=a_data.get("summary"),
                    bias=a_data.get("bias", "unknown"),
                    bias_score=a_data.get("bias_score", 0),
                    factuality=a_data.get("factuality", "unknown"),
                    factuality_score=a_data.get("factuality_score", 50),
                    ownership=a_data.get("ownership", "Unknown"),
                    topics=a_data.get("topics", []),
                ))
            stories.append(NewsStory(
                story_id=s_data["story_id"],
                headline=s_data["headline"],
                articles=articles,
                topics=s_data.get("topics", []),
                first_seen=datetime.fromisoformat(s_data["first_seen"]) if s_data.get("first_seen") else datetime.now(),
            ))
        return NewsResult(
            stories=stories,
            sources_fetched=data.get("sources_fetched", 0),
            articles_fetched=data.get("articles_fetched", 0),
            fetch_time_ms=data.get("fetch_time_ms", 0),
            cached=True,
        )
    except Exception as e:
        logger = __import__("logging").getLogger(__name__)
        logger.warning(f"Failed to deserialize news cache: {e}")
        return None


def save_news_cache(cache_key: str, result: NewsResult):
    """Save news result to cache."""
    _ensure_db()
    import json
    stories_data = []
    for s in result.stories:
        articles_data = []
        for a in s.articles:
            articles_data.append({
                "title": a.title,
                "link": a.link,
                "source": a.source,
                "published": a.published.isoformat() if a.published else None,
                "summary": a.summary,
                "bias": a.bias,
                "bias_score": a.bias_score,
                "factuality": a.factuality,
                "factuality_score": a.factuality_score,
                "ownership": a.ownership,
                "topics": a.topics,
            })
        stories_data.append({
            "story_id": s.story_id,
            "headline": s.headline,
            "articles": articles_data,
            "topics": s.topics,
            "first_seen": s.first_seen.isoformat(),
        })
    payload = json.dumps({
        "stories": stories_data,
        "sources_fetched": result.sources_fetched,
        "articles_fetched": result.articles_fetched,
        "fetch_time_ms": result.fetch_time_ms,
    })
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO news_cache (cache_key, data, fetched_at) VALUES (?, ?, ?)",
        (cache_key, payload, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
