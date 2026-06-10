"""Deterministic representative article candidate scoring and reports."""

from collections.abc import Sequence
from datetime import datetime, timezone


COMPONENT_WEIGHTS = {
    "importance": 0.20,
    "topic_seed": 0.15,
    "similarity": 0.20,
    "source_diversity": 0.10,
    "information": 0.15,
    "recency": 0.15,
    "category": 0.05,
}


def select_topic_representatives(
    topics: Sequence[dict],
    *,
    max_candidates_per_topic: int = 3,
) -> list[dict]:
    if max_candidates_per_topic <= 0:
        raise ValueError("max_candidates_per_topic must be greater than zero")

    return [
        _select_topic_candidates(topic, max_candidates_per_topic)
        for topic in topics
    ]


def _select_topic_candidates(topic: dict, maximum: int) -> dict:
    articles = topic["articles"]
    article_times = [
        _as_utc(article.get("published_at") or article.get("created_at"))
        for article in articles
    ]
    newest_time = max(
        (article_time for article_time in article_times if article_time is not None),
        default=None,
    )
    remaining = list(articles)
    selected = []
    selected_sources = set()

    while remaining and len(selected) < maximum:
        scored = [
            _score_article(article, newest_time, selected_sources)
            for article in remaining
        ]
        winner = min(scored, key=_ranking_key)
        winner["representative_candidate_rank"] = len(selected) + 1
        winner["selected"] = True
        winner["selection_reason"] = _selection_reason(winner)
        winner["human_review_status"] = "Pending"
        selected.append(winner)
        if winner["source"]:
            selected_sources.add(winner["source"])
        remaining = [
            article for article in remaining if article["id"] != winner["id"]
        ]

    non_selected = []
    for article in remaining:
        scored = _score_article(article, newest_time, selected_sources)
        scored["representative_candidate_rank"] = None
        scored["selected"] = False
        scored["selection_reason"] = "Not selected within the candidate limit."
        scored["human_review_status"] = "Pending"
        non_selected.append(scored)
    non_selected.sort(key=_ranking_key)

    return {
        **{key: value for key, value in topic.items() if key != "articles"},
        "representative_candidate_count": len(selected),
        "representative_candidates": selected,
        "articles": selected + non_selected,
    }


def _score_article(
    article: dict,
    newest_time: datetime | None,
    selected_sources: set[str],
) -> dict:
    recency_time = article.get("published_at") or article.get("created_at")
    components = {
        "importance": min(max(float(article["importance_score"]), 0.0) / 20.0, 1.0),
        "topic_seed": 1.0 if article.get("is_topic_seed") else 0.0,
        "similarity": min(max(float(article["similarity_to_seed"]), 0.0), 1.0),
        "source_diversity": _source_diversity_score(article.get("source"), selected_sources),
        "information": _information_score(article.get("title"), article.get("summary")),
        "recency": _recency_score(recency_time, newest_time),
        "category": _category_score(
            article.get("source_category"),
            article.get("rule_category"),
        ),
    }
    weighted = {
        name: round(value * COMPONENT_WEIGHTS[name], 4)
        for name, value in components.items()
    }
    score = round(sum(weighted.values()), 4)
    return {
        **article,
        "recency_time": recency_time,
        "recency_time_source": (
            "published_at" if article.get("published_at") else "created_at"
        ),
        "candidate_score": score,
        "candidate_score_components": {
            name: {
                "normalized": round(value, 4),
                "weight": COMPONENT_WEIGHTS[name],
                "weighted": weighted[name],
            }
            for name, value in components.items()
        },
    }


def _source_diversity_score(source: str | None, selected_sources: set[str]) -> float:
    if not source:
        return 0.0
    if not selected_sources or source not in selected_sources:
        return 1.0
    return 0.25


def _information_score(title: str | None, summary: str | None) -> float:
    title_score = min(len((title or "").strip()) / 100.0, 1.0)
    summary_score = min(len((summary or "").strip()) / 300.0, 1.0)
    return title_score * 0.4 + summary_score * 0.6


def _recency_score(value: datetime | None, newest_time: datetime | None) -> float:
    article_time = _as_utc(value)
    if article_time is None or newest_time is None:
        return 0.0
    age_hours = max(0.0, (newest_time - article_time).total_seconds() / 3600)
    return max(0.0, 1.0 - age_hours / 72.0)


def _category_score(source_category: str | None, rule_category: str | None) -> float:
    known_count = sum(
        1
        for value in (source_category, rule_category)
        if value and value.strip().casefold() != "unknown"
    )
    if known_count == 2:
        return 1.0
    if known_count == 1:
        return 0.75
    return 0.0


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _ranking_key(article: dict) -> tuple:
    return (
        -article["candidate_score"],
        -article["candidate_score_components"]["similarity"]["normalized"],
        -article["candidate_score_components"]["importance"]["normalized"],
        article["id"],
    )


def _selection_reason(article: dict) -> str:
    labels = {
        "importance": "importance",
        "topic_seed": "topic seed",
        "similarity": "topic similarity",
        "source_diversity": "source diversity",
        "information": "title/summary information",
        "recency": "recency",
        "category": "category signal",
    }
    strongest = sorted(
        article["candidate_score_components"].items(),
        key=lambda item: (-item[1]["weighted"], item[0]),
    )[:3]
    return "Selected for " + ", ".join(labels[name] for name, _ in strongest) + "."


def render_representative_report(
    result: dict,
    *,
    include_singletons: bool = False,
) -> str:
    analysis = result["analysis"]
    topics = result["topic_candidates"]
    detail_topics = [
        topic
        for topic in topics
        if include_singletons or topic["article_count"] > 1
    ]
    singleton_count = sum(topic["article_count"] == 1 for topic in topics)
    lines = [
        "# Topic representative candidate review",
        "",
        "## Summary",
        "",
        "- Human review status: **Pending**",
        f"- Analyzed article count: {analysis['article_count']}",
        f"- Topic candidate count: {analysis['topic_candidate_count']}",
        f"- Multi-article topic count: {analysis['multi_article_topic_count']}",
        f"- Singleton topic count: {singleton_count}",
        f"- Report detail topic count: {len(detail_topics)}",
        f"- Singleton topic details included: `{include_singletons}`",
        f"- Representative candidate count: {analysis['representative_candidate_count']}",
        f"- Similarity threshold: {analysis['similarity_threshold']:.2f}",
        f"- Embedding provider/model: `{analysis['embedding_provider']}` / `{analysis['embedding_model']}`",
        "- DB write performed: `false`",
        "",
        "## Scoring Policy",
        "",
        "- Candidate score compares representative candidates within the same topic.",
        "- Candidate score must not be used as an importance score across topics.",
        "- Overall raw extraction priority requires a separate follow-up policy.",
        "",
    ]
    for name, weight in COMPONENT_WEIGHTS.items():
        lines.append(f"- `{name}` weight: {weight:.2f}")

    lines.extend(["", "## Topic Candidates", ""])
    for topic in detail_topics:
        lines.extend(_render_topic(topic))
    if not detail_topics:
        lines.extend(["- None", ""])

    lines.extend(
        [
            "## Human Review Notes",
            "",
            "- Candidate suitability: Pending",
            "- Source diversity suitability: Pending",
            "- Candidate count suitability: Pending",
            "",
        ]
    )
    return "\n".join(lines)


def _render_topic(topic: dict) -> list[str]:
    lines = [
        f"### {topic['topic_candidate_id']}",
        "",
        f"- Article count: {topic['article_count']}",
        f"- Source count: {topic['source_count']}",
        f"- Category distribution: `{topic['category_distribution']}`",
        f"- Language distribution: `{topic['language_distribution']}`",
        f"- Representative candidate count: {topic['representative_candidate_count']}",
        "- Human review status: **Pending**",
        "",
        "| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |",
        "| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |",
    ]
    for article in topic["articles"]:
        lines.append(
            f"| {'yes' if article['selected'] else 'no'} "
            f"| {article['representative_candidate_rank'] or ''} "
            f"| {_escape(article['title'])} "
            f"| {_escape(article['source'])} "
            f"| {_escape(article['source_category'])} "
            f"| {_escape(article['rule_category'])} "
            f"| {article['importance_score']} "
            f"| {article['similarity_to_seed']:.4f} "
            f"| {_escape(article['published_at'])} "
            f"| {_escape(article['created_at'])} "
            f"| {_escape(article['recency_time_source'])} "
            f"| {article['candidate_score']:.4f} |"
        )
    lines.extend(["", "#### Candidate Details", ""])
    for article in topic["articles"]:
        lines.extend(
            [
                f"- **Article {article['id']} components:** "
                f"`{_component_summary(article['candidate_score_components'])}`",
                f"- **Article {article['id']} selection reason:** "
                f"{article['selection_reason']}",
                f"- **Article {article['id']} recency time:** "
                f"{_escape(article['recency_time'])} "
                f"(`{article['recency_time_source']}`)",
                f"- **Article {article['id']} human review status:** "
                f"{article['human_review_status']}",
            ]
        )
    lines.append("")
    return lines


def _component_summary(components: dict) -> str:
    return ", ".join(
        f"{name}={values['weighted']:.4f}"
        for name, values in components.items()
    )


def _escape(value) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")
