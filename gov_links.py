"""Generate deep-link URLs to Georgian government portals.

NAPR (National Agency of Public Registry) and my.gov.ge do not expose
public APIs that return PDFs without browser interaction.  These helpers
produce the best-available direct links so Irina can open the relevant
page in her browser and download the most recent extract / corporate
decision herself.
"""


def napr_search_url(id_code: str) -> str:
    """Working deep link to NAPR English search results pre-filled with company ID.

    NAPR requires a CAPTCHA when viewing individual company details, but the
    search-results listing works directly.  Irina will see the company in the
    results table and can click it to complete the CAPTCHA and download the
    free electronic extract (PDF) with QR verification code.
    """
    return f"https://enreg.reestri.gov.ge/main.php?c=search&m=find_legal_persons&s_legal_person_idnumber={id_code}"


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
        "napr": napr_search_url(id_code),
        "mygov": mygov_portal_url(),
    }
