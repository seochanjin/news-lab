"""Deterministic URL and title normalization for duplicate analysis.

URL normalization is intentionally conservative:

- lowercase the scheme and host, remove a trailing host dot and default ports
- remove fragments and tracking query parameters
- sort retained query parameters while preserving duplicate values
- use ``/`` for an empty path and remove a non-root trailing slash
- preserve path case, percent encoding, and non-tracking query values
"""

import hashlib
import re
import unicodedata
from collections.abc import Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


TRACKING_QUERY_PARAMETERS = frozenset(
    {
        "at_campaign",
        "at_medium",
        "dclid",
        "fbclid",
        "gclid",
        "igshid",
        "mc_cid",
        "mc_eid",
        "msclkid",
        "traffic_source",
    }
)

DOMAIN_TRACKING_QUERY_PARAMETERS = {
    "aljazeera.com": frozenset({"traffic_source"}),
    "bbc.com": frozenset(
        {
            "at_format",
            "at_link_id",
            "at_link_origin",
            "at_link_type",
            "at_ptr_name",
        }
    ),
    "bbc.co.uk": frozenset(
        {
            "at_format",
            "at_link_id",
            "at_link_origin",
            "at_link_type",
            "at_ptr_name",
        }
    ),
    "dw.com": frozenset({"maca"}),
    "techcrunch.com": frozenset({"guccounter"}),
    "theguardian.com": frozenset({"cmp", "cmp_tu"}),
    "wired.com": frozenset({"source"}),
}

_WHITESPACE_RE = re.compile(r"\s+")
_TITLE_PUNCTUATION_RE = re.compile(r"[^\w\s]", re.UNICODE)


def _matching_domain_parameters(hostname: str) -> frozenset[str]:
    parameters: set[str] = set()

    for domain, domain_parameters in DOMAIN_TRACKING_QUERY_PARAMETERS.items():
        if hostname == domain or hostname.endswith(f".{domain}"):
            parameters.update(domain_parameters)

    return frozenset(parameters)


def _is_tracking_parameter(name: str, domain_parameters: Iterable[str]) -> bool:
    lowered_name = name.casefold()
    return (
        lowered_name.startswith("utm_")
        or lowered_name in TRACKING_QUERY_PARAMETERS
        or lowered_name in domain_parameters
    )


def normalize_url(url: str | None) -> str | None:
    """Return a conservative canonical URL, or ``None`` for an unusable URL."""
    if not url or not url.strip():
        return None

    candidate = url.strip()
    try:
        parsed = urlsplit(candidate)
        port = parsed.port
    except ValueError:
        return None

    if (
        parsed.scheme.casefold() not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        return None

    scheme = parsed.scheme.casefold()
    hostname = parsed.hostname.casefold().rstrip(".")

    if ":" in hostname and not hostname.startswith("["):
        host = f"[{hostname}]"
    else:
        host = hostname

    if port and not (
        (scheme == "http" and port == 80)
        or (scheme == "https" and port == 443)
    ):
        host = f"{host}:{port}"

    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/") or "/"

    domain_parameters = _matching_domain_parameters(hostname)
    query_pairs = [
        (name, value)
        for name, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not _is_tracking_parameter(name, domain_parameters)
    ]
    query_pairs.sort(key=lambda item: (item[0].casefold(), item[0], item[1]))
    query = urlencode(query_pairs, doseq=True)

    return urlunsplit((scheme, host, path, query, ""))


def normalize_title(title: str | None) -> str | None:
    """Normalize a title for deterministic exact-match duplicate candidates."""
    if not title or not title.strip():
        return None

    normalized = unicodedata.normalize("NFKC", title).casefold()
    normalized = _TITLE_PUNCTUATION_RE.sub(" ", normalized)
    normalized = _WHITESPACE_RE.sub(" ", normalized).strip()
    return normalized or None


def make_title_hash(title: str | None) -> str | None:
    """Return a SHA-256 hex digest of the normalized title."""
    normalized = normalize_title(title)
    if normalized is None:
        return None

    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
