import re


def clean_text(text: str) -> str:
    # Remove URLs
    text = re.sub(r"https?://\S+", "", text)
    # Remove @mentions and $cashtags
    text = re.sub(r"[@$]\w+", "", text)
    # Remove non-alphanumeric except basic punctuation
    text = re.sub(r"[^\w\s.,!?]", " ", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def is_quality_post(text: str, min_length: int = 20) -> bool:
    return len(text.strip()) >= min_length
