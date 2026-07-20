"""LLM Topic 제목을 저장 가능한 내용 중심 문자열로 정제한다.

Provider가 만든 제목에서 날짜, 요일, 기간과 시간 범위를 제거하고 남은 문자열의
길이와 의미를 검증한다. 정제 결과를 신뢰할 수 없으면 keyword, 대표 기사 제목,
고정 기본 제목 순으로 결정적인 fallback을 선택한다. DB 접근이나 파일 쓰기는
수행하지 않으며 Daily·3-day·Weekly 저장 경로와 이후 read serializer가 함께
사용할 수 있는 공통 신뢰 경계를 제공한다.
"""

import re
import unicodedata
from collections.abc import Iterable, Mapping


MAX_TOPIC_TITLE_LENGTH = 120
DEFAULT_TOPIC_TITLE = "주요 뉴스 이슈"

_RANGE_SEPARATOR = r"(?:~|〜|～|-|–|—|부터)"
_WEEKDAY = r"(?:월|화|수|목|금|토|일)(?:요일)?"
_TITLE_DENY_PATTERNS = (
    re.compile(
        rf"(?<![가-힣]){_WEEKDAY}\s*{_RANGE_SEPARATOR}\s*{_WEEKDAY}"
        r"(?:간|의)?(?![가-힣])"
    ),
    re.compile(
        r"(?<!\d)(?:19|20)\d{2}\s*년(?:\s*\d{1,2}\s*월"
        r"(?:\s*\d{1,2}\s*일)?)?(?:의)?(?![가-힣])"
    ),
    re.compile(
        r"(?<![A-Za-z0-9])(?:19|20)\d{2}[-./]\d{1,2}"
        r"(?:[-./]\d{1,2})?(?!\d)(?:의)?"
    ),
    re.compile(r"(?<![A-Za-z0-9-])(?:19|20)\d{2}(?![A-Za-z0-9])"),
    re.compile(r"(?<!\d)\d{1,2}\s*월\s*\d{1,2}\s*일(?:의)?(?![가-힣])"),
    re.compile(r"(?<!\d)\d{1,2}\s*월(?:의)?(?![가-힣])"),
    re.compile(
        r"(?<!\d)(?:오전|오후)?\s*\d{1,2}(?::\d{2}|\s*시)"
        rf"\s*{_RANGE_SEPARATOR}\s*"
        r"(?:오전|오후)?\s*\d{1,2}(?::\d{2}|\s*시)"
    ),
    re.compile(
        r"(?:최근|지난|향후|앞으로|이전|이후)\s*\d+\s*"
        r"(?:시간|일|주|개월|달|년|개년)(?:간|동안)?(?:의)?(?![가-힣])"
    ),
    re.compile(
        r"(?<![A-Za-z0-9])\d+\s*(?:시간|일|주|개월|달|년|개년)"
        r"(?:차|간|동안)?(?:의)?(?![가-힣])"
    ),
    re.compile(
        r"(?:사흘|나흘|일주일|한\s*주|한\s*달)(?:간|동안|치|의)?(?![가-힣])"
    ),
    re.compile(r"(?:월|화|수|목|금|토|일)요일(?:의|부터|까지)?"),
    re.compile(r"(?:오늘|어제|내일|금일|전일|익일)(?:의)?"),
    re.compile(r"(?:이번\s*주|지난\s*주|다음\s*주)(?:의)?"),
    re.compile(
        r"(?:금주|주간|일간|월간|연간)(?:의)?(?![가-힣])|시간\s*범위"
    ),
)
_EMPTY_BRACKETS_PATTERN = re.compile(r"\(\s*\)|\[\s*]|\{\s*}")
_REPEATED_SEPARATOR_PATTERN = re.compile(r"\s*(?:[~〜～|,:;]+|\s[-–—]\s)\s*")
_EDGE_PUNCTUATION_PATTERN = re.compile(
    r"^[\s~〜～|,:;./\\\-–—]+|[\s~〜～|,:;./\\\-–—]+$"
)
_MEANINGFUL_PATTERN = re.compile(r"[A-Za-z0-9가-힣]")
_MEANINGLESS_TITLES = {
    "기록",
    "뉴스",
    "뉴스 요약",
    "뉴스 흐름",
    "요약",
    "이슈",
    "주제 요약",
    "흐름",
}


def sanitize_topic_title(
    title: object,
    *,
    keywords: Iterable[object] = (),
    article_titles: Iterable[object] = (),
) -> str:
    """제목을 정제하고 실패하면 제공된 근거에서 결정적 fallback을 만든다.

    Args:
        title: 신뢰하지 않는 provider 제목 값.
        keywords: provider 순서를 유지한 대표 keyword 후보.
        article_titles: 대표 기사를 먼저 둔 기사 제목 후보.

    Returns:
        날짜·기간 pattern이 없고 허용 길이와 의미 검증을 통과한 제목.
    """

    sanitized = _sanitize_candidate(title)
    if is_valid_topic_title(sanitized):
        return sanitized

    for candidate in (*keywords, *article_titles, DEFAULT_TOPIC_TITLE):
        sanitized = _sanitize_candidate(candidate)
        if is_valid_topic_title(sanitized):
            return sanitized
    return DEFAULT_TOPIC_TITLE


def topic_title_requires_fallback(title: object) -> bool:
    """Provider 제목 자체가 정제 후 검증에 실패해 fallback이 필요한지 판단한다."""

    return not is_valid_topic_title(_sanitize_candidate(title))


def with_sanitized_topic_title(row: Mapping[str, object]) -> dict:
    """Topic row를 복사하고 저장된 제목을 keyword 기반으로 read-time 정제한다.

    DB row나 cache 원본은 변경하지 않는다. ``keywords``가 문자열이 아닌 iterable일
    때만 fallback 후보로 사용하며, 잘못된 기존 metadata는 고정 fallback으로
    안전하게 처리한다.
    """

    item = dict(row)
    keywords = item.get("keywords")
    fallback_keywords = (
        keywords
        if isinstance(keywords, Iterable)
        and not isinstance(keywords, (str, bytes, Mapping))
        else ()
    )
    item["title_ko"] = sanitize_topic_title(
        item.get("title_ko"),
        keywords=fallback_keywords,
    )
    return item


def is_valid_topic_title(title: object) -> bool:
    """문자열의 길이·의미와 날짜·기간 pattern 부재를 검증한다."""

    if not isinstance(title, str):
        return False
    if not 1 <= len(title) <= MAX_TOPIC_TITLE_LENGTH:
        return False
    if not _MEANINGFUL_PATTERN.search(title):
        return False
    if title.casefold() in _MEANINGLESS_TITLES:
        return False
    return not has_forbidden_topic_title_pattern(title)


def has_forbidden_topic_title_pattern(title: object) -> bool:
    """제목에 날짜, 요일, 기간 또는 시간 범위 pattern이 남았는지 판단한다."""

    if not isinstance(title, str):
        return True
    normalized = unicodedata.normalize("NFKC", title)
    return any(pattern.search(normalized) for pattern in _TITLE_DENY_PATTERNS)


def _sanitize_candidate(candidate: object) -> str:
    """단일 후보를 문자열 정규화하고 deny-list와 잔여 구두점을 제거한다."""

    if not isinstance(candidate, str):
        return ""
    value = unicodedata.normalize("NFKC", candidate)
    value = " ".join(value.split())
    for pattern in _TITLE_DENY_PATTERNS:
        value = pattern.sub(" ", value)
    while _EMPTY_BRACKETS_PATTERN.search(value):
        value = _EMPTY_BRACKETS_PATTERN.sub(" ", value)
    value = _REPEATED_SEPARATOR_PATTERN.sub(" ", value)
    value = _EDGE_PUNCTUATION_PATTERN.sub("", value)
    return " ".join(value.split())
