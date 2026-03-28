from dataclasses import dataclass, field
from typing import Any


@dataclass
class WeightedTerms:
    terms: list[str]
    weight: int


@dataclass
class JobScoreConfig:
    title_contains: list[WeightedTerms] = field(default_factory=list)
    body_contains: list[WeightedTerms] = field(default_factory=list)
    allowed_languages: list[str] = field(default_factory=lambda: ["en"])
    min_score_for_selection: int = 0


@dataclass
class JobScoreResult:
    score: int
    selected: bool
    detected_language: str | None = None
    rejection_reason: str | None = None
    reasons: dict[str, Any] = field(default_factory=dict)