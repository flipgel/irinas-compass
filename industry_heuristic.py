"""Heuristic industry classification based on company name keywords.

Since Georgian public registries do NOT publish NACE/industry data via free APIs,
this module provides a best-effort guess based on keywords in the company name.

Sources researched:
- companyinfo.ge API: NO industry field
- NAPR official registry: NO NACE in free extracts or paid extracts
- RS.ge (Revenue Service): HAS NACE but behind CAPTCHA/login
- BIA.ge: Commercial only (sales@bia.ge)

This heuristic is a fallback to give Irina *some* directional signal.
It will be wrong sometimes — use with caution.
"""
from typing import Optional

# Keyword → (NACE Section, Description)
# Checks both Georgian and Latin/English keywords
INDUSTRY_KEYWORDS = [
    # Restaurants / Food / Hospitality
    (["რესტორან", "რესტორანი", "სასადილო", "კაფე", "ბარი", "ქეიტერინგ", "საცხობ", "პიც", "ბურგერ", "სუში",
      "restaurant", "cafe", "bar", "catering", "bakery", "pizza", "burger", "sushi", "kitchen", "food",
      "khinkali", "mwvadi", " Georgian", "phali", "lobiani", "khachapuri", "shashlik", "shawarma"],
     ("I", "Accommodation and food service activities")),

    # Hotels / Accommodation
    (["სასტუმრო", "ოთახ", "ჰოსტელ", "აპარტამენტ",
      "hotel", "hostel", "apartment", "rooms", "guesthouse", "resort"],
     ("I", "Accommodation and food service activities")),

    # Retail / Shops / Trade
    (["მარკეტ", "სუპერმარკეტ", "მაღაზია", "ბაზრობა", "ტორგოვლ", "სალარო", "დისტრიბუც",
      "market", "shop", "store", "retail", "trade", "trading", "distribution", "cashier", "mall", "boutique"],
     ("G", "Wholesale and retail trade")),

    # Construction
    (["სამშენებლო", "ბუმბალი", "კონსტრუქც", "რემონტ", "არქიტექტ", "ინჟინერ",
      "construction", "builder", "building", "renovation", "architecture", "engineering", "remont"],
     ("F", "Construction")),

    # Real Estate
    (["უძრავი", "ქონება", "ნედვიჟიმოსტ", "აგენტ", "ბროკერ",
      "real estate", "property", "broker", "agent", "developer", "rental"],
     ("L", "Real estate activities")),

    # Wine / Alcohol / Beverages
    (["ვინო", "ღვინო", "მარანი", "ყურძენ", "ალკოჰოლ", "ლიქიორ", "ვისკი",
      "wine", "winery", "vineyard", "alcohol", "liquor", "whiskey", "brewery", "chacha"],
     ("C", "Manufacturing — Beverages")),

    # Agriculture / Farming
    (["სოფლის", "მეურნეობ", "ფერმა", "მესაქონლე", "თესლი", "მოსავალი", "ბაღ",
      "farm", "agriculture", "farming", "livestock", "dairy", "orchard", "greenhouse"],
     ("A", "Agriculture, forestry and fishing")),

    # IT / Software / Technology
    (["ინფორმაციული", "ტექნოლოგი", "პროგრამ", "სოფტ", "დეველოპ", "ვებ", "აიტი",
      "it", "software", "tech", "technology", "digital", "web", "app", "developer", "programming", "cyber"],
     ("J", "Information and communication")),

    # Transport / Logistics
    (["ტრანსპორტ", "ლოგისტიკ", "გადაზიდვ", "ტაქსი", "ავტობუს", "ფურგონ",
      "transport", "logistics", "cargo", "delivery", "taxi", "trucking", "shipping", "freight"],
     ("H", "Transportation and storage")),

    # Manufacturing / Production
    (["წარმოებ", "ქარხანა", "ფაბრიკა", "მწარმოებ",
      "manufacturing", "factory", "production", "industrial", "plant"],
     ("C", "Manufacturing")),

    # Healthcare / Medical
    (["სამედიცინო", "კლინიკ", "აფთიაქ", "ჰოსპიტალ", "დერმატოლოგ",
      "medical", "clinic", "pharmacy", "hospital", "health", "dental", "doctor"],
     ("Q", "Human health and social work")),

    # Education
    (["სკოლა", "უნივერსიტეტ", "კოლეჯ", "სასწავლებ", "ტრენინგ",
      "school", "university", "college", "academy", "education", "training", "tutoring"],
     ("P", "Education")),

    # Finance / Banking / Insurance
    (["ბანკი", "ფინანს", "საკრედიტო", "დაზღვევ", "ინვესტიც",
      "bank", "finance", "financial", "credit", "insurance", "investment", "accounting", "audit"],
     ("K", "Financial and insurance activities")),

    # Energy / Utilities
    (["ელექტრო", "ენერგი", "გაზი", "წყალი", "სანტექნიკ",
      "energy", "electric", "electricity", "gas", "water", "utility", "solar"],
     ("D", "Electricity, gas, steam and air conditioning supply")),

    # Tourism / Travel
    (["ტურიზმ", "ტურისტ", "სათავგადასავლო", "ექსკურსი",
      "tourism", "tour", "travel", "tourist", "adventure", "excursion"],
     ("I", "Accommodation and food service activities")),

    # Beauty / Cosmetics / Wellness
    (["სილამაზე", "კოსმეტიკ", "სპა", "მასაჟ", "პარიკმახერ",
      "beauty", "cosmetic", "salon", "spa", "massage", "barbershop", "hairdresser"],
     ("S", "Other service activities")),

    # Cleaning / Services
    (["დასუფთავებ", "გამწმენდ",
      "cleaning", "cleaner", "janitorial", "maintenance"],
     ("N", "Administrative and support service activities")),
]


def infer_industry(name: str) -> Optional[str]:
    """Try to guess the industry from the company name.
    
    Returns a string like "G — Wholesale and retail trade" or None.
    """
    if not name:
        return None
    
    name_lower = name.lower()
    
    for keywords, (nace_section, description) in INDUSTRY_KEYWORDS:
        for keyword in keywords:
            if keyword.lower() in name_lower:
                return f"{nace_section} — {description}"
    
    return None
