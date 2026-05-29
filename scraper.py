"""API client for companyinfo.ge — Georgian business registry aggregator."""
import logging
import time
from datetime import datetime
from typing import List, Optional, Dict, Tuple

import requests

from models import Company, Person, SearchResult
from cache import get_company, save_company, save_search
from industry_heuristic import infer_industry

logger = logging.getLogger(__name__)

BASE_URL = "https://api.companyinfo.ge/api"

LEGAL_FORM_MAP = {
    "1": ("იმ", "Individual Entrepreneur"),
    "4": ("შპს", "Limited Liability Company"),
}

STATUS_MAP = {
    "რეგისტრირებულია": "Active",
    "აქტიური": "Active",
    "ლიკვიდაციაშია": "In Liquidation",
    "გაუქმებულია": "Terminated",
    "შეჩერებულია": "Suspended",
}

ROLE_MAP = {
    "დირექტორი": "Director",
    "პარტნიორი": "Partner / Shareholder",
    "დამფუძნებელი": "Founder",
}


def _to_en_status(ka_status: str) -> str:
    return STATUS_MAP.get(ka_status, ka_status)


def _to_en_role(ka_role: str) -> str:
    return ROLE_MAP.get(ka_role, ka_role)


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://www.companyinfo.ge/",
    })
    return s


def _get_json(path: str, params: Optional[dict] = None) -> dict:
    url = f"{BASE_URL}{path}"
    try:
        resp = _session().get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        logger.error(f"API error: {e}")
        raise


def _parse_shareholders(data: dict) -> Dict[str, Tuple[str, int]]:
    """Extract clean shareholder data from shareHolders 2D array."""
    result = {}
    sh = data.get("shareHolders", [])
    if len(sh) > 1:
        # First row is headers: ['Person', 'Share']
        for row in sh[1:]:
            if len(row) >= 2:
                name = str(row[0]).strip()
                share = int(row[1]) if row[1] else 0
                if name:
                    result[name] = (name, share)
    return result


def _parse_company(data: dict, internal_id: int) -> Company:
    """Parse corporation detail JSON into Company model."""
    corp = data.get("corporation", {})
    legal_form_code = data.get("legalForm", "")
    legal_form_ka, legal_form_en = LEGAL_FORM_MAP.get(legal_form_code, (legal_form_code, legal_form_code))

    # Get clean shareholder map
    shareholder_map = _parse_shareholders(data)

    directors = []
    shareholders = []
    seen_director_ids = set()
    seen_shareholder_keys = set()

    for aff in data.get("corporationAffiliations", []):
        person_name = aff.get("personName", "").strip()
        person_id = aff.get("personId")
        role = aff.get("role", "")
        share = aff.get("share", 0)

        # Skip garbage entries with suffixes like ".დირექტორი" in name
        if "." in person_name and any(role_suffix in person_name for role_suffix in ["დირექტორი", "პარტნიორი"]):
            continue

        person = Person(
            name=person_name,
            role=_to_en_role(role),
            person_id=str(person_id) if person_id else None,
            share_percent=str(share) if share else None,
            start_date=aff.get("date"),
        )

        if role == "დირექტორი":
            key = (person_id, "director")
            if key not in seen_director_ids:
                seen_director_ids.add(key)
                # Check if this director is also a real shareholder (>0 share or in shareholder map)
                is_shareholder = any(
                    s.get("personId") == person_id and s.get("role") in ("პარტნიორი", "დამფუძნებელი")
                    for s in data.get("corporationAffiliations", [])
                )
                person.is_nominee_warning = not is_shareholder
                directors.append(person)

        elif role in ("პარტნიორი", "დამფუძნებელი"):
            # Prefer share from shareholder_map if available
            clean_name = person_name
            if clean_name in shareholder_map:
                _, real_share = shareholder_map[clean_name]
                person.share_percent = str(real_share) if real_share else None
            
            key = (person_id, clean_name)
            if key not in seen_shareholder_keys:
                seen_shareholder_keys.add(key)
                shareholders.append(person)

    # Ensure all shareholders from shareHolders are included
    for clean_name, (_, real_share) in shareholder_map.items():
        if not any(s.name == clean_name for s in shareholders):
            shareholders.append(Person(
                name=clean_name,
                role="Partner / Shareholder",
                share_percent=str(real_share) if real_share else None,
            ))

    # IE case: the person IS the business
    if legal_form_code == "1" and corp.get("personalIdNumber"):
        ie_name = corp["name"].replace("ინდივიდუალური მეწარმე ", "")
        if not any(s.name == ie_name for s in shareholders):
            shareholders.append(Person(
                name=ie_name,
                role="Individual Entrepreneur",
            ))

    return Company(
        id_code=corp.get("idCode", ""),
        name=corp.get("name", ""),
        legal_form=legal_form_en,
        status=_to_en_status(data.get("status", "")),
        registration_date=corp.get("registrationDate", {}).get("date", "").split(" ")[0] if corp.get("registrationDate") else None,
        address=corp.get("address"),
        directors=directors,
        shareholders=shareholders,
        source_url=f"https://www.companyinfo.ge/en/corporations/{internal_id}",
        fetched_at=datetime.now(),
        confidence="high",
    )


def search_by_vat_id(vat_id: str) -> SearchResult:
    """Search companies by 9-digit (LLC) or 11-digit (IE) ID code."""
    result = SearchResult(query=vat_id, query_type="vat_id")
    cached = get_company(vat_id)
    if cached:
        result.companies.append(cached)
        result.from_cache = True
        save_search(result)
        return result

    data = _get_json("/corporations/search", {"idCode": vat_id, "page": 1})
    items = data.get("items", [])

    for item in items:
        internal_id = item.get("id")
        if not internal_id:
            continue
        detail = _get_json(f"/corporations/{internal_id}")
        company = _parse_company(detail, internal_id)
        save_company(company)
        result.companies.append(company)

    save_search(result)
    return result


def search_by_company_name(name: str) -> SearchResult:
    """Search companies by name (Georgian or English if in official name)."""
    result = SearchResult(query=name, query_type="company_name")
    data = _get_json("/corporations/search", {"name": name, "page": 1})
    items = data.get("items", [])

    for item in items:
        internal_id = item.get("id")
        if not internal_id:
            continue
        # Check cache first
        cached = get_company(item.get("idCode", ""))
        if cached:
            result.companies.append(cached)
            continue
        detail = _get_json(f"/corporations/{internal_id}")
        company = _parse_company(detail, internal_id)
        save_company(company)
        result.companies.append(company)
        time.sleep(0.5)  # Be polite

    save_search(result)
    return result


def search_by_owner_name(name: str) -> SearchResult:
    """Reverse search: find all companies linked to a person by name."""
    result = SearchResult(query=name, query_type="owner_name")
    
    # Debug: log what we're sending
    logger.info(f"Searching people by name: '{name}' (len={len(name)}, bytes={name.encode('utf-8')!r})")
    
    try:
        data = _get_json("/people/search", {"name": name, "page": 1})
    except Exception as e:
        logger.error(f"API call failed for people search: {e}")
        result.error = f"API request failed: {e}"
        save_search(result)
        return result
    
    items = data.get("items", [])
    total_items = data.get("totalItems", 0)
    logger.info(f"People search returned {total_items} total items, {len(items)} in this page")

    if not items:
        result.error = (
            f"No people found for '{name}'.\n\n"
            "Possible reasons:\n"
            "• The name may be spelled differently in the registry\n"
            "• The person may not be registered as a director or shareholder\n"
            "• Try searching by company name or VAT ID first, then check the owner name in the result"
        )
        save_search(result)
        return result

    # For each person found, get their affiliations and ownerships
    seen_company_ids = set()
    for person_item in items:
        person_id = person_item.get("id")
        if not person_id:
            continue
        
        logger.info(f"Fetching person detail for id={person_id}, name='{person_item.get('name')}'")
        
        try:
            person_detail = _get_json(f"/people/{person_id}")
        except Exception as e:
            logger.warning(f"Failed to fetch person {person_id}: {e}")
            continue
        
        # Affiliations = director roles
        for aff in person_detail.get("affiliations", []):
            comp_id = aff.get("companyId")
            if comp_id and comp_id not in seen_company_ids:
                seen_company_ids.add(comp_id)
                try:
                    comp_detail = _get_json(f"/corporations/{comp_id}")
                    company = _parse_company(comp_detail, comp_id)
                    # Boost confidence if person is shareholder, lower if only director
                    company.confidence = "high" if any(
                        o.get("companyId") == comp_id for o in person_detail.get("ownership", [])
                    ) else "medium"
                    save_company(company)
                    result.companies.append(company)
                except Exception as e:
                    logger.warning(f"Failed to fetch company {comp_id}: {e}")
                time.sleep(0.5)
        
        # Ownership = shareholder roles (might overlap with affiliations)
        for own in person_detail.get("ownership", []):
            comp_id = own.get("companyId")
            if comp_id and comp_id not in seen_company_ids:
                seen_company_ids.add(comp_id)
                try:
                    comp_detail = _get_json(f"/corporations/{comp_id}")
                    company = _parse_company(comp_detail, comp_id)
                    company.confidence = "high"
                    save_company(company)
                    result.companies.append(company)
                except Exception as e:
                    logger.warning(f"Failed to fetch company {comp_id}: {e}")
                time.sleep(0.5)

    save_search(result)
    return result


def get_company_by_internal_id(internal_id: int) -> Optional[Company]:
    """Fetch a single company by its companyinfo.ge internal ID."""
    detail = _get_json(f"/corporations/{internal_id}")
    company = _parse_company(detail, internal_id)
    save_company(company)
    return company
