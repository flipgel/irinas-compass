"""Generate deep-link URLs to Georgian government portals.

NAPR (National Agency of Public Registry) and my.gov.ge do not expose
public APIs that return PDFs without browser interaction.  These helpers
produce the best-available direct links so Irina can open the relevant
page in her browser and download the most recent extract / corporate
decision herself.
"""

from typing import Optional


def napr_extract_url(id_code: str) -> str:
    """Deep link to NAPR English search portal pre-filled with company ID.

    The portal allows anyone to search by registration number and download
    a free electronic extract (PDF) with a QR verification code.
    """
    return f"https://enreg.reestri.gov.ge/main.php?c=search&m=search_by_number&n={id_code}"


def napr_extract_url_ka(id_code: str) -> str:
    """Georgian-language version of the NAPR search portal."""
    return f"https://www.reestri.gov.ge/main.php?c=search&m=search_by_number&n={id_code}"


def mygov_portal_url() -> str:
    """Link to my.gov.ge e-services portal.

    my.gov.ge is an Angular SPA.  Corporate decisions for a company are
    published under the company's personal account after login.  There is
    currently no public deep-link that accepts a company ID without
    authentication, so we link the main portal landing page.
    """
    return "https://www.my.gov.ge/"


def gov_links_for(id_code: str) -> dict:
    """Return both government links for a given company/person ID."""
    return {
        "napr_en": napr_extract_url(id_code),
        "napr_ka": napr_extract_url_ka(id_code),
        "mygov": mygov_portal_url(),
    }
