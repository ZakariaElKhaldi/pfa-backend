import html
import re

# Financial emoji to sentiment token mapping (Paper 3)
EMOJI_SENTIMENT_MAP = {
    "\U0001f680": " bullish ",   # rocket
    "\U0001f4c8": " bullish ",   # chart increasing
    "\U0001f4b0": " bullish ",   # money bag
    "\U0001f4b5": " bullish ",   # dollar
    "\U0001f389": " bullish ",   # party
    "\U0001f525": " bullish ",   # fire
    "\U0001f4aa": " bullish ",   # flexed biceps
    "\U0001f43b": " bearish ",   # bear
    "\U0001f4c9": " bearish ",   # chart decreasing
    "\U0001f6a8": " bearish ",   # rotating light
    "\U0001f4a9": " bearish ",   # poop
    "\U0001f62d": " bearish ",   # loudly crying
}

# Common financial abbreviations (Paper 3)
FINANCIAL_ABBREVIATIONS = {
    r"\bPT\b": "price target",
    r"\bDD\b": "due diligence",
    r"\bYOLO\b": "high risk trade",
    r"\bFOMO\b": "fear of missing out",
    r"\bIMO\b": "in my opinion",
    r"\bDCA\b": "dollar cost average",
    r"\bATH\b": "all time high",
    r"\bATL\b": "all time low",
    r"\bBTD\b": "buy the dip",
    r"\bFUD\b": "fear uncertainty doubt",
    r"\bEPS\b": "earnings per share",
    r"\bP/E\b": "price to earnings",
}


def clean_text(text: str) -> str:
    # Decode HTML entities
    text = html.unescape(text)

    # Remove URLs (before cashtag handling)
    text = re.sub(r"https?://\S+", "", text)

    # Preserve cashtags: $AAPL -> AAPL (strip $ but keep ticker symbol)
    text = re.sub(r"\$([A-Za-z]{1,5})\b", r"\1", text)

    # Remove @mentions
    text = re.sub(r"@\w+", "", text)

    # Map financial emojis to sentiment tokens
    for emoji, token in EMOJI_SENTIMENT_MAP.items():
        text = text.replace(emoji, token)

    # Remove remaining non-text characters (emojis, special symbols)
    text = re.sub(r"[^\w\s.,!?'\-/&]", " ", text)

    # Expand financial abbreviations
    for pattern, expansion in FINANCIAL_ABBREVIATIONS.items():
        text = re.sub(pattern, expansion, text)

    # Reduce repeated characters (3+ of same char -> 2)
    text = re.sub(r"(.)\1{2,}", r"\1\1", text)

    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def is_quality_post(text: str, min_length: int = 20, min_alpha_ratio: float = 0.4) -> bool:
    stripped = text.strip()
    if len(stripped) < min_length:
        return False

    # Reject posts that are mostly URLs
    if re.match(r"^https?://", stripped):
        return False

    # Check alpha character ratio
    alpha_count = sum(1 for c in stripped if c.isalpha())
    if len(stripped) > 0 and alpha_count / len(stripped) < min_alpha_ratio:
        return False

    return True
