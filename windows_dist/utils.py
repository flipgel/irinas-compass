"""Utilities for input detection, fuzzy matching, and transliteration."""
import re
from typing import Literal

from rapidfuzz import fuzz


def detect_input_type(query: str) -> Literal["vat_id", "company_name", "owner_name"]:
    """Detect if query is a VAT/ID code, company name, or person name."""
    q = query.strip()
    # Georgian legal entities: 9 digits
    # Individual entrepreneurs: 11 digits
    if re.match(r"^\d{9}$", q):
        return "vat_id"
    if re.match(r"^\d{11}$", q):
        return "vat_id"
    # If mostly digits with some separators, probably an ID
    if re.match(r"^\d[\d\s\-]{5,20}\d$", q) and sum(c.isdigit() for c in q) / len(q) > 0.7:
        return "vat_id"
    # Heuristic: 2-4 words with typical Georgian name endings
    georgian_name_endings = (
        "shvili", "dze", "ia", "iani", "uri", "ava", "ovi", "ev", "adze", "idze",
        "svili", "man", "woman", "berg", "stein"
    )
    lower = q.lower()
    words = lower.split()
    if any(lower.endswith(end) for end in georgian_name_endings):
        return "owner_name"
    if len(words) <= 3 and all(w.isalpha() or w in "-.'" for w in words):
        # Could be name or short company name — ambiguous, but lean toward name for short inputs
        return "owner_name" if len(words) <= 2 else "company_name"
    return "company_name"


def normalize_name(name: str) -> str:
    """Normalize a name for fuzzy comparison."""
    return re.sub(r"[^\w\s]", "", name.lower()).strip()


def name_similarity(a: str, b: str) -> float:
    """Return similarity score 0-100 between two names."""
    return fuzz.ratio(normalize_name(a), normalize_name(b))


def transliterate_georgian_approximation(name: str) -> list:
    """
    Generate approximate transliterations for common Georgian letter mappings.
    This helps when searching Latin names that might have been transliterated
    from Georgian inconsistently.
    """
    variants = [name]
    # Common ambiguous mappings
    replacements = [
        ("ts", "c"), ("c", "ts"),
        ("kh", "x"), ("x", "kh"),
        ("gh", "g"), ("g", "gh"),
        ("zh", "j"), ("j", "zh"),
        ("sh", "s"), ("s", "sh"),
        ("ch", "ts"), ("ts", "ch"),
        ("k", "q"), ("q", "k"),
        ("i", "y"), ("y", "i"),
        ("o", "u"), ("u", "o"),
    ]
    for old, new in replacements:
        variant = name.lower().replace(old, new)
        if variant != name.lower() and variant not in variants:
            variants.append(variant)
    return variants
