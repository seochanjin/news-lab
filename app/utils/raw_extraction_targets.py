"""Raw extraction target selection and report rendering."""

from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone


ELIGIBLE_RAW_STATUSES = {"not_extracted", "pending"}


def select_raw_extraction_targets(
    topics: Sequence[dict],
    raw_states: Mapping[int, dict],
    *,
    max_targets_per_topic: int = 1,
) -> list[dict]:
    if not 1 <= max_targets_per_topic <= 3:
        raise ValueError("max_targets_per_topic must be between 1 and 3")

    selected_topics = [
        _select_topic_targets(topic, raw_states, max_targets_per_topic)
        for topic in topics
    ]
    return sorted(selected_topics, key=_topic_priority_key)


def _select_topic_targets(topic: dict, raw_states: Mapping[int, dict], maximum: int):
    target_count = 0
    articles = []
    multi_article_topic = topic["article_count"] > 1

    for article in sorted(topic["articles"], key=_article_rank_key):
        raw_status = _raw_status(raw_states.get(article["id"]))
        rank = article.get("representative_candidate_rank")

        if raw_status == "already_extracted":
            target_status = "already_extracted"
            reason = "Raw text already exists; extraction is not needed."
        elif raw_status == "failed":
            target_status = "failed"
            reason = "Previous raw extraction failed; automatic retry is disabled."
        elif not multi_article_topic:
            target_status = "skipped"
            reason = "Singleton topics are excluded from the default target policy."
        elif rank is None:
            target_status = "skipped"
            reason = "Article is outside the representative candidate limit."
        elif raw_status not in ELIGIBLE_RAW_STATUSES:
            target_status = "skipped"
            reason = f"Raw extraction status `{raw_status}` is not eligible."
        elif target_count < maximum:
            target_count += 1
            target_status = "target"
            reason = (
                f"Selected representative candidate rank {rank}; "
                f"raw status is `{raw_status}`."
            )
        else:
            target_status = "backup"
            reason = (
                f"Eligible representative candidate rank {rank} exceeds the "
                f"topic target limit of {maximum}."
            )

        articles.append(
            {
                **article,
                "raw_extraction_status": raw_status,
                "extraction_target_status": target_status,
                "extraction_target_reason": reason,
            }
        )

    status_counts = Counter(
        article["extraction_target_status"] for article in articles
    )
    return {
        **{key: value for key, value in topic.items() if key != "articles"},
        "extraction_target_count": status_counts["target"],
        "extraction_target_status_counts": dict(sorted(status_counts.items())),
        "articles": articles,
    }


def _article_rank_key(article: dict) -> tuple:
    rank = article.get("representative_candidate_rank")
    return (rank is None, rank if rank is not None else 0, article["id"])


def _raw_status(raw_state: dict | None) -> str:
    if raw_state is None:
        return "not_extracted"
    if raw_state.get("has_raw_text"):
        return "already_extracted"
    return str(raw_state.get("extraction_status") or "pending").casefold()


def _topic_priority_key(topic: dict) -> tuple:
    latest = max(
        (
            article_time
            for article in topic["articles"]
            if (
                article_time := _as_utc(
                    article.get("published_at") or article.get("created_at")
                )
            )
            is not None
        ),
        default=None,
    )
    latest_timestamp = latest.timestamp() if latest else float("-inf")
    return (
        -(topic["article_count"] > 1),
        -topic["source_count"],
        -topic["article_count"],
        -latest_timestamp,
        topic["topic_candidate_id"],
    )


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def render_raw_extraction_target_report(result: dict) -> str:
    analysis = result["analysis"]
    topics = [
        topic for topic in result["topic_candidates"] if topic["article_count"] > 1
    ]
    lines = [
        "# Raw extraction target review",
        "",
        "## Warning",
        "",
    ]
    if analysis["embedding_provider"] == "deterministic":
        lines.extend(
            [
                "- 이 report는 `deterministic-hash-v1` 기반 검증용 산출물이다.",
                "- 현재 target 목록은 실제 raw extraction 승인 목록이 아니다.",
                "- 실제 extraction 대상 검토는 human-approved embedding provider 결과를 기준으로 수행해야 한다.",
            ]
        )
    if analysis["max_targets_per_topic"] > 1:
        lines.extend(
            [
                "- 이 report는 복수 target 정책 comparison/비교용 산출물이다.",
                "- max2/max3 결과는 실제 raw extraction 실행 승인을 의미하지 않는다.",
            ]
        )
    lines.extend(
        [
            "",
        "## Summary",
        "",
        "- Human review status: **Pending**",
        f"- Analyzed article count: {analysis['article_count']}",
        f"- Topic candidate count: {analysis['topic_candidate_count']}",
        f"- Multi-article topic count: {analysis['multi_article_topic_count']}",
        f"- Report detail topic count: {len(topics)}",
        f"- Extraction target count: {analysis['extraction_target_count']}",
        f"- Max targets per topic: {analysis['max_targets_per_topic']}",
        f"- Similarity threshold: {analysis['similarity_threshold']:.2f}",
        f"- Embedding provider/model: `{analysis['embedding_provider']}` / `{analysis['embedding_model']}`",
        "- DB write performed: `false`",
        "- Raw extraction performed: `false`",
        "",
        "## Target Policy",
        "",
        "- Candidate score ranks representative candidates within the same topic.",
        "- Candidate score is not used to prioritize topics against each other.",
        "- Multi-article topics are ordered by source count, article count, then recency.",
        "- Only `pending` or `not_extracted` representative candidates can become targets.",
        "- Existing raw text is marked `already_extracted`; failed extraction is not retried.",
        "",
        "## Topic Targets",
        "",
        ]
    )
    for topic in topics:
        lines.extend(_render_topic(topic))
    if not topics:
        lines.extend(["- None", ""])

    lines.extend(
        [
            "## Human Review Notes",
            "",
            "- Target suitability: Pending",
            "- Topic ordering suitability: Pending",
            "- Max targets per topic suitability: Pending",
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
        f"- Extraction target count: {topic['extraction_target_count']}",
        f"- Target status counts: `{topic['extraction_target_status_counts']}`",
        "",
        "| Target Status | Rank | Title | Source | Raw Status | Candidate Score |",
        "| --- | ---: | --- | --- | --- | ---: |",
    ]
    for article in topic["articles"]:
        lines.append(
            f"| {article['extraction_target_status']} "
            f"| {article.get('representative_candidate_rank') or ''} "
            f"| {_escape(article['title'])} "
            f"| {_escape(article['source'])} "
            f"| {article['raw_extraction_status']} "
            f"| {article['candidate_score']:.4f} |"
        )
    lines.extend(["", "#### Target Decisions", ""])
    for article in topic["articles"]:
        lines.append(
            f"- **Article {article['id']} "
            f"({article['extraction_target_status']}):** "
            f"{article['extraction_target_reason']}"
        )
    lines.append("")
    return lines


def _escape(value) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")
