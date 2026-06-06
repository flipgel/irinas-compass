"""Data models for Irina's Compass."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict


@dataclass
class NewsSource:
    """A news outlet with bias and ownership metadata."""
    name: str
    rss: str
    bias: str  # left, lean_left, center, lean_right, right
    bias_score: int  # -100 to +100
    factuality: str  # high, mixed, low
    factuality_score: int  # 0-100
    ownership: str
    country: str
    category: str


@dataclass
class NewsArticle:
    """A single news article from an RSS feed."""
    title: str
    link: str
    source: str
    published: Optional[datetime] = None
    summary: Optional[str] = None
    thumbnail: Optional[str] = None
    full_text: Optional[str] = None
    article_images: List[str] = field(default_factory=list)
    video_urls: List[str] = field(default_factory=list)
    bias: str = "unknown"
    bias_score: int = 0
    factuality: str = "unknown"
    factuality_score: int = 50
    ownership: str = "Unknown"
    topics: List[str] = field(default_factory=list)


@dataclass
class NewsStory:
    """A group of articles about the same topic/event."""
    story_id: str
    headline: str
    articles: List[NewsArticle] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    first_seen: datetime = field(default_factory=datetime.now)
    
    @property
    def coverage_left(self) -> int:
        return sum(1 for a in self.articles if a.bias in ("left", "lean_left"))
    
    @property
    def coverage_center(self) -> int:
        return sum(1 for a in self.articles if a.bias == "center")
    
    @property
    def coverage_right(self) -> int:
        return sum(1 for a in self.articles if a.bias in ("right", "lean_right"))
    
    @property
    def coverage_total(self) -> int:
        return len(self.articles)
    
    @property
    def bias_spread(self) -> str:
        """Describe the ideological spread of coverage."""
        if self.coverage_total == 0:
            return "none"
        left = self.coverage_left
        center = self.coverage_center
        right = self.coverage_right
        
        if left > 0 and right > 0 and center > 0:
            return "full_spectrum"
        elif left > 0 and right > 0:
            return "bipartisan"
        elif left > 0 and center > 0:
            return "left_center"
        elif right > 0 and center > 0:
            return "right_center"
        elif left > 0:
            return "left_only"
        elif right > 0:
            return "right_only"
        elif center > 0:
            return "center_only"
        return "mixed"
    
    @property
    def avg_factuality(self) -> float:
        if not self.articles:
            return 50.0
        return sum(a.factuality_score for a in self.articles) / len(self.articles)
    
    @property
    def is_blindspot(self) -> bool:
        """A story covered predominantly by one ideological side.
        
        Ground News-style blindspot: a story with political undertones
        that receives lopsided coverage (one side covers it, the other ignores).
        Requires at least 2 total articles to qualify.
        """
        if self.coverage_total < 2:
            return False
        left = self.coverage_left
        right = self.coverage_right
        # Blindspot: one side covers it significantly, the other essentially ignores it
        if (left >= 2 and right == 0) or (right >= 2 and left == 0):
            return True
        # Also flag if coverage is heavily skewed (e.g., 4:1 or worse)
        if left > 0 and right > 0:
            ratio = max(left, right) / min(left, right)
            if ratio >= 4:
                return True
        return False
    
    @property
    def blindspot_direction(self) -> Optional[str]:
        if not self.is_blindspot:
            return None
        if self.coverage_left > self.coverage_right:
            return "left"
        if self.coverage_right > self.coverage_left:
            return "right"
        return None
    
    @property
    def ownership_diversity(self) -> Dict[str, int]:
        """Count unique owners covering this story."""
        owners = {}
        for a in self.articles:
            owners[a.ownership] = owners.get(a.ownership, 0) + 1
        return owners
    
    @property
    def latest_article(self) -> Optional[NewsArticle]:
        if not self.articles:
            return None
        dated = [a for a in self.articles if a.published]
        if dated:
            return max(dated, key=lambda x: x.published or datetime.min)
        return self.articles[0]


@dataclass
class NewsResult:
    """Result of a news fetch operation."""
    stories: List[NewsStory] = field(default_factory=list)
    sources_fetched: int = 0
    articles_fetched: int = 0
    fetch_time_ms: int = 0
    error: Optional[str] = None
    cached: bool = False


@dataclass
class Person:
    """A director, shareholder, or founder."""
    name: str
    role: str  # "director", "shareholder", "founder", "individual_entrepreneur"
    person_id: Optional[str] = None  # companyinfo.ge person ID
    share_percent: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_nominee_warning: bool = False


@dataclass
class Company:
    """A Georgian legal entity or individual entrepreneur."""
    id_code: str  # 9-digit for LLC, 11-digit for IE
    name: str
    legal_form: str  # "შპს" (LLC), "იმ" (IE), etc.
    status: str  # "Active", "Liquidated", "Terminated", etc.
    registration_date: Optional[str] = None
    address: Optional[str] = None
    directors: List[Person] = field(default_factory=list)
    shareholders: List[Person] = field(default_factory=list)
    also_known_as: List[str] = field(default_factory=list)
    industry: Optional[str] = None  # heuristic guess from name, e.g. "G — Wholesale and retail trade"
    industry_source: str = "heuristic"  # "heuristic" (name-based guess) or "official" (rare)
    source_url: Optional[str] = None
    fetched_at: Optional[datetime] = None
    confidence: str = "high"  # high, medium, low

    @property
    def is_individual_entrepreneur(self) -> bool:
        return self.legal_form == "Individual Entrepreneur" or len(self.id_code) == 11

    @property
    def owners_summary(self) -> str:
        """Human-readable ownership summary."""
        if self.is_individual_entrepreneur:
            return f"Individual Entrepreneur: {self.name}"
        if self.shareholders:
            return ", ".join([f"{s.name} ({s.share_percent or '?'}%)" for s in self.shareholders])
        if self.directors:
            return ", ".join([f"{d.name} (Director — may be nominee)" for d in self.directors])
        return "No ownership data available"


@dataclass
class SearchResult:
    """Result of a search query."""
    query: str
    query_type: str  # "vat_id", "company_name", "owner_name"
    companies: List[Company] = field(default_factory=list)
    searched_at: datetime = field(default_factory=datetime.now)
    from_cache: bool = False
    error: Optional[str] = None


@dataclass
class NetworkNode:
    """A node in the ownership network."""
    node_id: str          # safe ID for Mermaid (no spaces/special chars)
    label: str            # display label (can have HTML)
    node_type: str        # "person", "company", "risk_person"
    details: str = ""     # extra line shown under label


@dataclass
class NetworkEdge:
    """A relationship between two nodes."""
    source: str
    target: str
    label: str            # e.g. "Director", "Shareholder 51%"


@dataclass
class NetworkResult:
    """Result of a network analysis."""
    query: str
    query_type: str       # "person", "company"
    nodes: List[NetworkNode] = field(default_factory=list)
    edges: List[NetworkEdge] = field(default_factory=list)
    risk_flags: List[str] = field(default_factory=list)
    companies: List[Company] = field(default_factory=list)
    error: Optional[str] = None
