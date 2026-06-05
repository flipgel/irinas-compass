"""Generate deep-link URLs to Georgian government portals.

NAPR (National Agency of Public Registry) and my.gov.ge do not expose
public APIs that return PDFs without browser interaction.  These helpers
produce the best-available direct links so Irina can open the relevant
page in her browser and download the most recent extract / corporate
decision herself.
"""


def napr_portal_url() -> str:
    """Link to the NAPR English portal main page.

    NAPR's site is a single-page application without deep-linking support.
    The raw search-results URL returns a broken HTML fragment (missing
    charset declaration and JavaScript).  We link the main portal page
    instead, which is fully functional and properly encoded.  Users can
    copy the ID code from our app and paste it into NAPR's search box.
    """
    return "https://enreg.reestri.gov.ge/main.php?m=new_index&l=en"


def mygov_portal_url() -> str:
    """Link to my.gov.ge e-services portal main page."""
    return "https://www.my.gov.ge/"


def mygov_company_url(id_code: str) -> str:
    """Link to the my.gov.ge business-entity search service.

    Service 179 under category 10 is the NAPR business-entity lookup.
    my.gov.ge is an Angular SPA that does not accept deep-link parameters
    for auto-search, so this links the generic search form. Users must
    paste the ID manually.
    """
    return "https://www.my.gov.ge/ka-ge/services/10/service/179"


def gov_links_for(id_code: str) -> dict:
    """Return both government links for a given company/person ID."""
    return {
        "napr": napr_portal_url(),
        "mygov": mygov_portal_url(),
        "mygov_company": mygov_company_url(id_code),
    }
