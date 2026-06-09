"""Threshold comparison and human-review report helpers."""

from collections.abc import Sequence

from app.utils.topic_grouping import group_articles


def parse_thresholds(value: str) -> tuple[float, ...]:
    try:
        thresholds = tuple(float(item.strip()) for item in value.split(","))
    except ValueError as error:
        raise ValueError("thresholds must be comma-separated numbers") from error

    if not thresholds or any(not 0 <= threshold <= 1 for threshold in thresholds):
        raise ValueError("thresholds must be between zero and one")
    return tuple(dict.fromkeys(thresholds))


def compare_thresholds(
    articles: Sequence[dict],
    embeddings: Sequence[Sequence[float]],
    thresholds: Sequence[float],
) -> list[dict]:
    comparisons = []
    for threshold in thresholds:
        topics = group_articles(
            articles,
            embeddings,
            similarity_threshold=threshold,
        )
        multi_article_topics = [
            topic for topic in topics if topic["article_count"] > 1
        ]
        singleton_count = sum(topic["article_count"] == 1 for topic in topics)
        comparisons.append(
            {
                "threshold": threshold,
                "topic_candidate_count": len(topics),
                "multi_article_topic_candidate_count": len(multi_article_topics),
                "singleton_topic_count": singleton_count,
                "singleton_topic_ratio": (
                    round(singleton_count / len(topics), 4) if topics else 0
                ),
                "multi_article_topic_candidates": multi_article_topics,
            }
        )
    return comparisons


def summarize_comparisons(comparisons: Sequence[dict]) -> list[dict]:
    return [
        {
            key: comparison[key]
            for key in (
                "threshold",
                "topic_candidate_count",
                "multi_article_topic_candidate_count",
                "singleton_topic_count",
                "singleton_topic_ratio",
            )
        }
        for comparison in comparisons
    ]


def render_markdown_report(result: dict) -> str:
    analysis = result["analysis"]
    estimate = result.get("provider_call_estimate")
    lines = [
        "# Real embedding topic quality review",
        "",
        "## Review Status",
        "",
        "- Human review: **Pending**",
        f"- Embedding model: `{analysis['embedding_model']}`",
        f"- Real provider used: `{analysis['embedding_provider_enabled']}`",
        f"- Article count: {analysis['article_count']}",
        f"- Time basis: `{analysis['time_basis']}`",
        f"- Window hours: {analysis['window_hours']}",
        "- DB write performed: `false`",
        "",
        "## Provider Estimate",
        "",
    ]
    if estimate:
        lines.extend(
            [
                f"- Estimated tokens: {estimate['estimated_tokens']}",
                f"- Estimated cost USD: {estimate['estimated_cost_usd']}",
            ]
        )
    else:
        lines.append("- Real provider estimate: pending until an approved provider run")

    lines.extend(
        [
            "",
            "## Threshold Summary",
            "",
            "| Threshold | Topic Candidates | Multi-article Topics | Singleton Topics | Singleton Ratio |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for comparison in result["threshold_comparison"]:
        lines.append(
            f"| {comparison['threshold']:.2f} "
            f"| {comparison['topic_candidate_count']} "
            f"| {comparison['multi_article_topic_candidate_count']} "
            f"| {comparison['singleton_topic_count']} "
            f"| {comparison['singleton_topic_ratio']:.4f} |"
        )

    lines.extend(["", "## Deterministic Hash Comparison", ""])
    baseline = result.get("deterministic_hash_comparison")
    if baseline:
        lines.extend(
            [
                "| Threshold | Topic Candidates | Multi-article Topics | Singleton Ratio |",
                "| --- | ---: | ---: | ---: |",
            ]
        )
        for comparison in baseline:
            lines.append(
                f"| {comparison['threshold']:.2f} "
                f"| {comparison['topic_candidate_count']} "
                f"| {comparison['multi_article_topic_candidate_count']} "
                f"| {comparison['singleton_topic_ratio']:.4f} |"
            )
    else:
        lines.append(
            "- Real provider comparison is pending; this report currently contains "
            "the selected provider result only."
        )

    lines.extend(["", "## Multi-article Topic Candidates", ""])
    for comparison in result["threshold_comparison"]:
        lines.extend(
            [
                f"### Threshold {comparison['threshold']:.2f}",
                "",
                f"- Multi-article topic candidates: "
                f"{comparison['multi_article_topic_candidate_count']}",
                "",
            ]
        )
        for topic in comparison["multi_article_topic_candidates"]:
            lines.extend(_render_topic(topic))
        if not comparison["multi_article_topic_candidates"]:
            lines.extend(["- None", ""])

    lines.extend(
        [
            "## Human Review Notes",
            "",
            "- Same-event grouping quality: Pending",
            "- Cross-event over-grouping: Pending",
            "- Representative article suitability: Pending",
            "- Recommended threshold: Pending",
            "- Ready for representative article stage: Pending",
            "",
        ]
    )
    return "\n".join(lines)


def _render_topic(topic: dict) -> list[str]:
    representative = topic["representative_article"]
    maximum = topic["max_importance_article"]
    lines = [
        f"#### {topic['topic_candidate_id']}",
        "",
        f"- Article count: {topic['article_count']}",
        f"- Source count: {topic['source_count']}",
        f"- Category distribution: `{topic['category_distribution']}`",
        f"- Language distribution: `{topic['language_distribution']}`",
        f"- Average similarity: {topic['average_similarity']}",
        f"- Representative article: {_escape(representative['title'])}",
        f"- Max importance article: {_escape(maximum['title'])}",
        "",
        "| Title | Source | Source Category | Rule Category | Importance | Published At | Similarity |",
        "| --- | --- | --- | --- | ---: | --- | ---: |",
    ]
    for article in topic["articles"]:
        lines.append(
            f"| {_escape(article['title'])} "
            f"| {_escape(article['source'])} "
            f"| {_escape(article['source_category'])} "
            f"| {_escape(article['rule_category'])} "
            f"| {article['importance_score']} "
            f"| {_escape(article['published_at'])} "
            f"| {article['similarity_to_seed']} |"
        )
    lines.append("")
    return lines


def _escape(value) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")
