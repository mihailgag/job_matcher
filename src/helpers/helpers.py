import json
from dataclasses import asdict
from typing import Any
import hashlib

from langdetect import detect, LangDetectException


def detect_language(text: str | None) -> str | None:
    if not text or len(text.strip()) < 30:
        return None

    try:
        return detect(text)
    except LangDetectException:
        return None
    
def build_config_hash(config: Any) -> str:
    payload = asdict(config)
    normalized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

def build_config_json(config: Any) -> dict[str, Any]:
    return asdict(config)