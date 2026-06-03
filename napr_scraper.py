"""Fetch and parse NAPR (National Agency of Public Registry) search results.

NAPR's English portal sends UTF-8 bytes but declares `Content-Type: text/html`
without a charset, which causes browsers to render Georgian text as mojibake.
We fetch the raw bytes and force UTF-8 decoding server-side so Irina sees
clean text inside the Streamlit app.
"""

import re
from dataclasses import dataclass
from typing import Optional

import requests


@dataclass
class NaprResult:
    id_code: str
    internal_id: str
    name: str
    legal_form: str
    status: str
    source_url: str


def fetch_napr_search(id_code: str) -> Optional[NaprResult]:
    """Fetch NAPR search results for a company ID and return parsed data."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    })

    # NAPR main page to prime cookies
    session.get("https://enreg.reestri.gov.ge/main.php?m=new_index&l=en", timeout=15)

    # Search by identification code
    url = (
        "https://enreg.reestri.gov.ge/main.php"
        "?c=search&m=find_legal_persons"
        f"&s_legal_person_idnumber={id_code}"
    )
    resp = session.get(url, timeout=15)
    resp.encoding = "utf-8"  # server omits charset; force UTF-8

    # Extract table rows with company data
    rows = re.findall(r'<tr[^>]*bgcolor="#ffffff"[^>]*>(.*?)</tr>', resp.text, re.DOTALL)
    if not rows:
        return None

    # Take first match (exact ID search usually returns one result)
    row = rows[0]

    # Parse internal NAPR ID
    id_match = re.search(r'show_legal_person\((\d+)\)', row)
    internal_id = id_match.group(1) if id_match else ""

    # Extract all <td> text content
    tds = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
    clean_fields = []
    for td in tds:
        # Strip HTML tags
        text = re.sub(r'<[^>]+>', '', td)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        if text:
            clean_fields.append(text)

    if len(clean_fields) < 4:
        return None

    return NaprResult(
        id_code=clean_fields[0],
        internal_id=internal_id,
        name=clean_fields[1],
        legal_form=clean_fields[2],
        status=clean_fields[3],
        source_url=url,
    )
