"""Latin-to-Georgian (Mkhedruli) transliteration for Irina's Compass.

Implements the Georgian National transliteration system used in passports
and official documents. Multi-character combinations are processed first
to avoid ambiguity (e.g. 'sh' -> შ, not ს+ჰ).
"""

# Multi-character mappings (process these FIRST)
MULTI_CHAR_MAP = {
    'gh': 'ღ',
    'kh': 'ხ',
    'ts': 'ც',
    'dz': 'ძ',
    'ch': 'ჩ',
    'sh': 'შ',
    'zh': 'ჟ',
}

# Single-character mappings
SINGLE_CHAR_MAP = {
    'a': 'ა',
    'b': 'ბ',
    'g': 'გ',
    'd': 'დ',
    'e': 'ე',
    'v': 'ვ',
    'z': 'ზ',
    't': 'თ',
    'i': 'ი',
    'k': 'კ',
    'l': 'ლ',
    'm': 'მ',
    'n': 'ნ',
    'o': 'ო',
    'p': 'პ',
    'j': 'ჯ',
    'r': 'რ',
    's': 'ს',
    'u': 'უ',
    'f': 'ფ',
    'q': 'ყ',
    'x': 'ხ',  # Common in Russian-influenced transliteration (e.g. Xomeriki -> ხომერიკი)
    'y': 'ჲ',
    'h': 'ჰ',
    # Uppercase
    'A': 'ა', 'B': 'ბ', 'G': 'გ', 'D': 'დ', 'E': 'ე',
    'V': 'ვ', 'Z': 'ზ', 'T': 'თ', 'I': 'ი', 'K': 'კ',
    'L': 'ლ', 'M': 'მ', 'N': 'ნ', 'O': 'ო', 'P': 'პ',
    'J': 'ჯ', 'R': 'რ', 'S': 'ს', 'U': 'უ', 'F': 'ფ',
    'Q': 'ყ', 'X': 'ხ', 'Y': 'ჲ', 'H': 'ჰ',
}

# Common surname ending fixes
SUFFIX_FIXES = {
    'ზე': 'ძე',  # -dze ending (e.g. Nakashidze -> ნაკაშიძე)
}


def latin_to_georgian(text: str) -> str:
    """Convert Latin text to Georgian Mkhedruli script.
    
    Examples:
        'giorgi'      -> 'გიორგი'
        'maisuradze'  -> 'მაისურაძე'
        'Nana'        -> 'ნანა'
        'suliko'      -> 'სულიკო'
        'xomeriki'    -> 'ხომერიკი'
    """
    result = []
    i = 0
    
    while i < len(text):
        # Try 2-char match first
        if i + 1 < len(text):
            two_char = text[i:i+2]
            two_lower = two_char.lower()
            if two_lower in MULTI_CHAR_MAP:
                result.append(MULTI_CHAR_MAP[two_lower])
                i += 2
                continue
        
        # Single char match
        char = text[i]
        if char in SINGLE_CHAR_MAP:
            result.append(SINGLE_CHAR_MAP[char])
        else:
            # Keep spaces, numbers, punctuation as-is
            result.append(char)
        i += 1
    
    georgian = ''.join(result)
    
    # Apply suffix fixes for common surname endings
    for wrong, right in SUFFIX_FIXES.items():
        if georgian.endswith(wrong):
            georgian = georgian[:-len(wrong)] + right
    
    return georgian


def is_georgian_script(text: str) -> bool:
    """Check if text contains Georgian Mkhedruli characters."""
    for char in text:
        if '\u10A0' <= char <= '\u10FF':  # Georgian Unicode block
            return True
    return False


def auto_transliterate_if_needed(text: str) -> str:
    """If text has no Georgian chars, transliterate from Latin."""
    if not text or is_georgian_script(text):
        return text
    return latin_to_georgian(text)
