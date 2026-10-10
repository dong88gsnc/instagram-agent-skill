"""Local Korean/English heuristics. Timing is an estimate, not measured audio."""
import re
import unicodedata

WORD_RE = re.compile(r"[A-Za-z0-9가-힣$%'’-]+")
HANGUL_RE = re.compile(r"[가-힣]")
KOREAN_STAKES = re.compile(r"손해|잃|실패|낭비|위험|주의|실수|문제|눌리|불편|확인|넣기 전|고르기 전|마세요|않")
KOREAN_NUMBERS = re.compile(r"(?:한|두|세|네|다섯|여섯|일곱|여덟|아홉|열)\s*(?:가지|개|번|초|분|원|배)")
BRANDS = re.compile(r"\b[A-Z][A-Z0-9]{2,}\b|템퍼")
KOREAN_OBJECTS = re.compile(r"인솔|깔창|발등|사이즈|신발")

def normalize(text):
    return unicodedata.normalize("NFC", text)

def has_korean(text):
    return bool(HANGUL_RE.search(normalize(text)))

def words(text):
    return WORD_RE.findall(re.sub(r"(?<=\d),(?=\d)", "", normalize(text)))

def duration(text, wpm=165, korean_sps=5.0):
    if wpm <= 0 or korean_sps <= 0:
        raise ValueError("speech rates must be positive")
    text = re.sub(r"(?<=\d),(?=\d)", "", normalize(text))
    # Mixed words: count Hangul syllables and remaining Latin/numeric tokens.
    # Digits and brand pronunciations remain approximations; calibrate with audio.
    syllables = len(HANGUL_RE.findall(text))
    latin = WORD_RE.findall(HANGUL_RE.sub(" ", text))
    return syllables / korean_sps + len(latin) * 60 / wpm

def concrete_count(text):
    text = normalize(text)
    return len(re.findall(r"\d[\d,.]*", text)) + len(BRANDS.findall(text)) + len(KOREAN_NUMBERS.findall(text)) + len(KOREAN_OBJECTS.findall(text))
