"""Deterministic lightweight article classification candidate signals."""

import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone


CATEGORY_PRIORITY = (
    "security",
    "ai",
    "climate",
    "politics",
    "business",
    "sports",
    "world",
    "tech",
)

CATEGORY_KEYWORDS = {
    "tech": (
        "technology",
        "software",
        "hardware",
        "startup",
        "developer",
        "cloud",
        "chip",
        "semiconductor",
        "internet",
        "smartphone",
    ),
    "world": (
        "war",
        "conflict",
        "military",
        "diplomacy",
        "sanction",
        "refugee",
        "border",
        "humanitarian",
        "earthquake",
    ),
    "business": (
        "market",
        "stock",
        "earnings",
        "economy",
        "economic",
        "trade",
        "tariff",
        "merger",
        "acquisition",
        "investor",
    ),
    "politics": (
        "election",
        "president",
        "parliament",
        "government",
        "minister",
        "congress",
        "senate",
        "vote",
        "democracy",
    ),
    "security": (
        "cybersecurity",
        "cyberattack",
        "ransomware",
        "malware",
        "data breach",
        "vulnerability",
        "zero-day",
    ),
    "ai": (
        "artificial intelligence",
        "ai",
        "machine learning",
        "large language model",
        "llm",
        "generative ai",
        "chatbot",
        "neural network",
    ),
    "climate": (
        "climate",
        "global warming",
        "emission",
        "carbon",
        "renewable",
        "wildfire",
        "flood",
        "drought",
    ),
    "sports": (
        "football",
        "soccer",
        "baseball",
        "basketball",
        "tennis",
        "tournament",
        "championship",
        "olympic",
    ),
}

BREAKING_KEYWORDS = ("breaking", "live", "update", "urgent", "developing")

HIGH_IMPACT_KEYWORDS = (
    "war",
    "conflict",
    "military",
    "election",
    "market",
    "stock",
    "economy",
    "artificial intelligence",
    "ai",
    "cybersecurity",
    "cyberattack",
    "ransomware",
    "data breach",
)

SOURCE_CATEGORY_IMPORTANCE = {
    "security": 2,
    "ai": 2,
    "politics": 2,
    "world": 1,
    "business": 1,
    "climate": 1,
}

SUPPORTED_LANGUAGES = frozenset({"ar", "en", "ja", "ko", "ru", "zh"})

_WHITESPACE_RE = re.compile(r"\s+")
_SCRIPT_PATTERNS = {
    "ko": re.compile(r"[\uac00-\ud7a3]"),
    "ja": re.compile(r"[\u3040-\u30ff]"),
    "zh": re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]"),
    "ar": re.compile(r"[\u0600-\u06ff]"),
    "ru": re.compile(r"[\u0400-\u04ff]"),
    "en": re.compile(r"[A-Za-z]"),
}


def normalize_source_category(source_category: str | None) -> str:
    if not source_category:
        return "unknown"

    normalized = source_category.strip().casefold()
    if normalized in CATEGORY_KEYWORDS:
        return normalized

    return "unknown"


def normalize_source_language(source_language: str | None) -> str:
    if not source_language:
        return "unknown"

    normalized = source_language.strip().casefold().split("-", 1)[0]
    if normalized in SUPPORTED_LANGUAGES:
        return normalized

    return "unknown"


def normalize_classification_text(value: str | None) -> str:
    if not value:
        return ""

    normalized = unicodedata.normalize("NFKC", value).casefold()
    return _WHITESPACE_RE.sub(" ", normalized).strip()


def count_keyword_matches(text: str | None, keywords: tuple[str, ...]) -> int:
    normalized = normalize_classification_text(text)
    if not normalized:
        return 0

    count = 0
    for keyword in keywords:
        normalized_keyword = normalize_classification_text(keyword)
        escaped_keyword = re.escape(normalized_keyword).replace(r"\ ", r"\s+")
        pattern = rf"(?<!\w){escaped_keyword}(?!\w)"
        count += len(re.findall(pattern, normalized))

    return count


def get_category_match_counts(
    title: str | None,
    summary: str | None,
) -> dict[str, dict[str, int]]:
    return {
        category: {
            "title": count_keyword_matches(title, keywords),
            "summary": count_keyword_matches(summary, keywords),
        }
        for category, keywords in CATEGORY_KEYWORDS.items()
    }


def classify_rule_category(
    title: str | None,
    summary: str | None,
) -> tuple[str, dict[str, int]]:
    match_counts = get_category_match_counts(title, summary)
    scores = {
        category: counts["title"] * 2 + counts["summary"]
        for category, counts in match_counts.items()
    }
    highest_score = max(scores.values(), default=0)

    if highest_score == 0:
        return "unknown", scores

    for category in CATEGORY_PRIORITY:
        if scores[category] == highest_score:
            return category, scores

    return "unknown", scores


def detect_language(
    title: str | None,
    summary: str | None,
    source_language: str | None = None,
) -> tuple[str, str]:
    text = f"{title or ''} {summary or ''}"
    counts = Counter(
        {
            language: len(pattern.findall(text))
            for language, pattern in _SCRIPT_PATTERNS.items()
        }
    )

    if counts["ja"] >= 2:
        return "ja", "detected"

    non_latin_counts = {
        language: count
        for language, count in counts.items()
        if language not in {"en", "ja"} and count >= 2
    }
    if non_latin_counts:
        language = max(
            non_latin_counts,
            key=lambda candidate: (
                non_latin_counts[candidate],
                candidate,
            ),
        )
        return language, "detected"

    if counts["en"] >= 20:
        return "en", "detected"

    fallback = normalize_source_language(source_language)
    if fallback != "unknown":
        return fallback, "source_fallback"

    return "unknown", "unknown"


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def get_recency_points(
    article_time: datetime | None,
    reference_time: datetime | None = None,
) -> int:
    if article_time is None:
        return 0

    reference = _as_utc(reference_time or datetime.now(timezone.utc))
    age_hours = max(0.0, (reference - _as_utc(article_time)).total_seconds() / 3600)

    if age_hours <= 6:
        return 3
    if age_hours <= 24:
        return 2
    if age_hours <= 72:
        return 1
    return 0


def calculate_importance_signals(
    title: str | None,
    summary: str | None,
    source_category: str | None,
    article_time: datetime | None,
    reference_time: datetime | None = None,
) -> dict[str, int]:
    all_keywords = tuple(
        keyword
        for keywords in CATEGORY_KEYWORDS.values()
        for keyword in keywords
    )
    title_keyword_count = count_keyword_matches(title, all_keywords)
    summary_keyword_count = count_keyword_matches(summary, all_keywords)
    breaking_keyword_count = count_keyword_matches(
        f"{title or ''} {summary or ''}",
        BREAKING_KEYWORDS,
    )
    high_impact_keyword_count = count_keyword_matches(
        f"{title or ''} {summary or ''}",
        HIGH_IMPACT_KEYWORDS,
    )
    normalized_source_category = normalize_source_category(source_category)
    source_category_points = SOURCE_CATEGORY_IMPORTANCE.get(
        normalized_source_category,
        0,
    )
    recency_points = get_recency_points(article_time, reference_time)
    score = (
        title_keyword_count * 3
        + summary_keyword_count
        + breaking_keyword_count * 3
        + high_impact_keyword_count * 2
        + source_category_points
        + recency_points
    )

    return {
        "score": score,
        "title_keyword_count": title_keyword_count,
        "summary_keyword_count": summary_keyword_count,
        "breaking_keyword_count": breaking_keyword_count,
        "high_impact_keyword_count": high_impact_keyword_count,
        "source_category_points": source_category_points,
        "recency_points": recency_points,
    }


def classify_article(
    title: str | None,
    summary: str | None,
    source_category: str | None,
    source_language: str | None,
    article_time: datetime | None,
    reference_time: datetime | None = None,
) -> dict:
    base_category = normalize_source_category(source_category)
    rule_category, category_scores = classify_rule_category(title, summary)
    language, language_basis = detect_language(title, summary, source_language)
    importance_signals = calculate_importance_signals(
        title=title,
        summary=summary,
        source_category=source_category,
        article_time=article_time,
        reference_time=reference_time,
    )

    return {
        "base_category": base_category,
        "rule_category": rule_category,
        "category_scores": category_scores,
        "detected_language": language,
        "language_basis": language_basis,
        "importance_score": importance_signals["score"],
        "importance_signals": importance_signals,
    }
