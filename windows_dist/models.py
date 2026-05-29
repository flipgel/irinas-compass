"""Data models for Irina's Compass."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


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
    source_url: Optional[str] = None
    fetched_at: Optional[datetime] = None
    confidence: str = "high"  # high, medium, low

    @property
    def is_individual_entrepreneur(self) -> bool:
        return self.legal_form == "იმ" or len(self.id_code) == 11

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
