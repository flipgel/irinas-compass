"""Network analysis: build ownership graphs and detect risks.

Keeps API calls bounded to avoid rate limits:
- Max 1 person match
- Max 8 companies per person
- Max 3 co-directors traced per company
- 0.5s delay between calls
"""
import logging
import re
import time
from datetime import datetime
from typing import List, Optional, Dict, Set

from models import Company, Person, NetworkNode, NetworkEdge, NetworkResult
from scraper import _get_json, _parse_company
from cache import get_company, save_company

logger = logging.getLogger(__name__)

MAX_COMPANIES_PER_PERSON = 8
MAX_CO_DIRECTORS = 3
REQUEST_DELAY = 0.5


def _safe_id(text: str) -> str:
    """Create a Mermaid-safe node ID."""
    safe = re.sub(r"[^a-zA-Z0-9_\u10A0-\u10FF]", "_", text)
    safe = safe.strip("_")
    if not safe:
        safe = "node"
    # Mermaid IDs can't start with numbers
    if safe[0].isdigit():
        safe = "n" + safe
    return safe[:40]


def _is_fresh(date_str: Optional[str]) -> bool:
    """Check if company was registered within last 6 months."""
    if not date_str:
        return False
    try:
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"):
            try:
                reg = datetime.strptime(date_str.split()[0], "%Y-%m-%d")
                break
            except ValueError:
                continue
        else:
            return False
        return (datetime.now() - reg).days < 180
    except Exception:
        return False


def _detect_company_risks(company: Company) -> List[str]:
    """Return risk flags for a single company."""
    flags = []
    if company.status in ("Terminated", "Liquidated", "In Liquidation", "Suspended"):
        flags.append(f"⚠️ Status: {company.status}")
    if _is_fresh(company.registration_date):
        flags.append("⚠️ Registered less than 6 months ago")
    if not company.address or len(company.address) < 5:
        flags.append("⚠️ No valid address")
    if not company.shareholders and not company.is_individual_entrepreneur:
        flags.append("⚠️ No shareholders disclosed")
    # Shell indicator: generic name
    generic = ("სავაჭრო", "სამშენებლო", "სატრანსპორტო", "სასტუმრო", "სარესტორნო",
               "trading", "consulting", "holding", "group", "investment")
    name_lower = company.name.lower()
    if any(g in name_lower for g in generic) and not company.shareholders:
        flags.append("⚠️ Generic name + no ownership = possible shell")
    return flags


def _count_director_companies(person_id: int) -> int:
    """Count how many companies a person directs (best-effort, limited)."""
    try:
        detail = _get_json(f"/people/{person_id}")
        return len(detail.get("affiliations", []))
    except Exception:
        return 0


def build_person_network(name: str) -> NetworkResult:
    """Build a network centered on a person.
    
    Returns: person → companies → co-directors (1 hop).
    """
    result = NetworkResult(query=name, query_type="person")
    
    # 1. Search person
    try:
        data = _get_json("/people/search", {"name": name, "page": 1})
    except Exception as e:
        result.error = f"Person search failed: {e}"
        return result
    
    items = data.get("items", [])
    if not items:
        result.error = f"No person found for '{name}'."
        return result
    
    person_item = items[0]  # Take best match
    person_name = person_item.get("name", name)
    person_id = person_item.get("id")
    person_node_id = _safe_id(f"p_{person_name}")
    
    # Add person node
    result.nodes.append(NetworkNode(
        node_id=person_node_id,
        label=person_name,
        node_type="person",
    ))
    
    # 2. Get person detail
    try:
        person_detail = _get_json(f"/people/{person_id}")
    except Exception:
        result.error = f"Found '{person_name}' but could not load details."
        return result
    
    # Collect companies from affiliations + ownership
    company_ids: Set[int] = set()
    role_map: Dict[int, str] = {}  # company_id -> role label
    
    for aff in person_detail.get("affiliations", [])[:MAX_COMPANIES_PER_PERSON]:
        cid = aff.get("companyId")
        if cid:
            company_ids.add(cid)
            role = aff.get("role", "Director")
            share = aff.get("share", 0)
            label = f"{role}"
            if share:
                label += f" {share}%"
            role_map[cid] = label
    
    for own in person_detail.get("ownership", [])[:MAX_COMPANIES_PER_PERSON]:
        cid = own.get("companyId")
        if cid:
            company_ids.add(cid)
            share = own.get("share", 0)
            label = role_map.get(cid, "Shareholder")
            if share and f"{share}%" not in label:
                label += f" {share}%"
            role_map[cid] = label
    
    if not company_ids:
        result.error = f"'{person_name}' has no linked companies in the registry."
        return result
    
    # 3. Fetch company details
    co_director_pool: Dict[int, List[Person]] = {}  # company_id -> other directors
    
    for cid in list(company_ids)[:MAX_COMPANIES_PER_PERSON]:
        cached = get_company(str(cid))
        if cached:
            company = cached
        else:
            try:
                comp_detail = _get_json(f"/corporations/{cid}")
                company = _parse_company(comp_detail, cid)
                save_company(company)
                time.sleep(REQUEST_DELAY)
            except Exception as e:
                logger.warning(f"Failed to fetch company {cid}: {e}")
                continue
        
        result.companies.append(company)
        
        # Company node
        comp_node_id = _safe_id(f"c_{company.name}_{company.id_code}")
        comp_label = company.name
        if company.industry:
            comp_label += f"<br/><span style='font-size:0.8em'>{company.industry}</span>"
        
        comp_risks = _detect_company_risks(company)
        comp_type = "company"
        if comp_risks:
            comp_type = "risk_company"
            result.risk_flags.extend([f"{company.name}: {r}" for r in comp_risks])
        
        result.nodes.append(NetworkNode(
            node_id=comp_node_id,
            label=comp_label,
            node_type=comp_type,
            details=company.status,
        ))
        
        # Edge: person → company
        result.edges.append(NetworkEdge(
            source=person_node_id,
            target=comp_node_id,
            label=role_map.get(cid, "Linked"),
        ))
        
        # Collect other directors for tracing
        other_directors = [d for d in company.directors if d.name != person_name]
        if other_directors:
            co_director_pool[cid] = other_directors[:MAX_CO_DIRECTORS]
    
    # 4. Trace co-directors (1 hop out)
    seen_co_directors: Set[str] = set()
    for cid, directors in co_director_pool.items():
        comp_node_id = _safe_id(f"c_{next((c.name for c in result.companies if c.id_code == str(cid)), '')}_{cid}")
        
        for director in directors:
            dir_name = director.name
            if dir_name in seen_co_directors:
                continue
            seen_co_directors.add(dir_name)
            
            dir_node_id = _safe_id(f"d_{dir_name}")
            
            # Check if this director is a known nominee (directs many companies)
            dir_company_count = 0
            if director.person_id:
                try:
                    dir_company_count = _count_director_companies(int(director.person_id))
                    time.sleep(REQUEST_DELAY)
                except Exception:
                    pass
            
            is_nominee = dir_company_count > 20 or (dir_company_count > 10 and not director.share_percent)
            
            if is_nominee:
                dir_type = "risk_person"
                dir_label = f"⚠️ {dir_name}<br/><span style='font-size:0.75em'>Directs {dir_company_count}+ companies</span>"
                result.risk_flags.append(f"⚠️ {dir_name} appears to be a professional nominee (directs {dir_company_count}+ companies)")
            else:
                dir_type = "person"
                dir_label = dir_name
            
            result.nodes.append(NetworkNode(
                node_id=dir_node_id,
                label=dir_label,
                node_type=dir_type,
            ))
            
            result.edges.append(NetworkEdge(
                source=comp_node_id,
                target=dir_node_id,
                label="Also directed by",
            ))
    
    # Address clustering risk
    addresses: Dict[str, List[str]] = {}
    for c in result.companies:
        if c.address:
            addr = c.address.strip().lower()
            addresses.setdefault(addr, []).append(c.name)
    for addr, names in addresses.items():
        if len(names) > 5:
            result.risk_flags.append(f"⚠️ Address '{addr[:60]}...' is shared by {len(names)} companies")
    
    return result


def build_company_network(name: str) -> NetworkResult:
    """Build a network centered on a company.
    
    Returns: company → directors → their other companies (1 hop).
    """
    result = NetworkResult(query=name, query_type="company")
    
    # 1. Search company
    try:
        data = _get_json("/corporations/search", {"name": name, "page": 1})
    except Exception as e:
        result.error = f"Company search failed: {e}"
        return result
    
    items = data.get("items", [])
    if not items:
        result.error = f"No company found for '{name}'."
        return result
    
    # Take first match
    item = items[0]
    internal_id = item.get("id")
    id_code = item.get("idCode", "")
    
    cached = get_company(id_code)
    if cached:
        company = cached
    else:
        try:
            detail = _get_json(f"/corporations/{internal_id}")
            company = _parse_company(detail, internal_id)
            save_company(company)
        except Exception as e:
            result.error = f"Could not load company details: {e}"
            return result
    
    result.companies.append(company)
    
    # Company node (center)
    comp_node_id = _safe_id(f"c_{company.name}_{company.id_code}")
    comp_label = company.name
    if company.industry:
        comp_label += f"<br/><span style='font-size:0.8em'>{company.industry}</span>"
    
    comp_risks = _detect_company_risks(company)
    comp_type = "company"
    if comp_risks:
        comp_type = "risk_company"
        result.risk_flags.extend([f"{company.name}: {r}" for r in comp_risks])
    
    result.nodes.append(NetworkNode(
        node_id=comp_node_id,
        label=comp_label,
        node_type=comp_type,
        details=company.status,
    ))
    
    # 2. Directors and shareholders as nodes
    people_to_trace: List[Person] = []
    for p in company.directors[:MAX_CO_DIRECTORS]:
        people_to_trace.append(p)
    for p in company.shareholders[:MAX_CO_DIRECTORS]:
        if p.name not in [d.name for d in people_to_trace]:
            people_to_trace.append(p)
    
    for person in people_to_trace:
        p_node_id = _safe_id(f"p_{person.name}")
        p_label = person.name
        
        # Check if nominee
        dir_count = 0
        if person.person_id:
            try:
                dir_count = _count_director_companies(int(person.person_id))
                time.sleep(REQUEST_DELAY)
            except Exception:
                pass
        
        is_nominee = dir_count > 20
        if is_nominee:
            p_type = "risk_person"
            p_label += f"<br/><span style='font-size:0.75em'>⚠️ Directs {dir_count}+ companies</span>"
            result.risk_flags.append(f"⚠️ {person.name} appears to be a professional nominee")
        else:
            p_type = "person"
        
        result.nodes.append(NetworkNode(
            node_id=p_node_id,
            label=p_label,
            node_type=p_type,
        ))
        
        edge_label = person.role
        if person.share_percent:
            edge_label += f" {person.share_percent}%"
        result.edges.append(NetworkEdge(
            source=comp_node_id,
            target=p_node_id,
            label=edge_label,
        ))
    
    return result


def generate_mermaid(network: NetworkResult) -> str:
    """Generate Mermaid flowchart syntax from a network."""
    if not network.nodes:
        return "graph TD\n    EMPTY[No data]"
    
    lines = [
        "%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#FFFCF7', 'primaryTextColor': '#1A1A1A', 'primaryBorderColor': '#C8BEB0', 'lineColor': '#9E9486', 'secondaryColor': '#E8E0D8', 'tertiaryColor': '#F0E0E0', 'fontFamily': 'Inter, sans-serif', 'fontSize': '14px'}}}%%",
        "graph TD",
        "    classDef person fill:#1A1A1A,stroke:#1A1A1A,color:#FFFCF7,stroke-width:2px,rx:4,ry:4",
        "    classDef company fill:#FFFCF7,stroke:#C8BEB0,color:#1A1A1A,stroke-width:1px,rx:2,ry:2",
        "    classDef risk_person fill:#F0E0E0,stroke:#E85D4E,color:#7A1A1A,stroke-width:2px,rx:4,ry:4",
        "    classDef risk_company fill:#FFF0F0,stroke:#E85D4E,color:#7A1A1A,stroke-width:2px,rx:2,ry:2",
    ]
    
    # Nodes
    for node in network.nodes:
        label = node.label.replace('"', '&quot;')
        lines.append(f'    {node.node_id}["{label}"]')
    
    # Edges
    for edge in network.edges:
        label = edge.label.replace('"', '&quot;')
        lines.append(f'    {edge.source} -->|"{label}"| {edge.target}')
    
    # Class assignments
    person_nodes = [n.node_id for n in network.nodes if n.node_type == "person"]
    company_nodes = [n.node_id for n in network.nodes if n.node_type == "company"]
    risk_person_nodes = [n.node_id for n in network.nodes if n.node_type == "risk_person"]
    risk_company_nodes = [n.node_id for n in network.nodes if n.node_type == "risk_company"]
    
    if person_nodes:
        lines.append(f'    class {",".join(person_nodes)} person')
    if company_nodes:
        lines.append(f'    class {",".join(company_nodes)} company')
    if risk_person_nodes:
        lines.append(f'    class {",".join(risk_person_nodes)} risk_person')
    if risk_company_nodes:
        lines.append(f'    class {",".join(risk_company_nodes)} risk_company')
    
    return "\n".join(lines)
