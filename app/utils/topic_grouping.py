"""Seed-based greedy topic grouping helpers."""

import math
from collections import Counter
from collections.abc import Sequence


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise ValueError("embedding dimensions must match")

    left_magnitude = math.sqrt(sum(value * value for value in left))
    right_magnitude = math.sqrt(sum(value * value for value in right))
    if left_magnitude == 0 or right_magnitude == 0:
        return 0.0

    return sum(a * b for a, b in zip(left, right)) / (
        left_magnitude * right_magnitude
    )


def group_articles(
    articles: Sequence[dict],
    embeddings: Sequence[Sequence[float]],
    *,
    similarity_threshold: float,
) -> list[dict]:
    if len(articles) != len(embeddings):
        raise ValueError("articles and embeddings must have the same length")
    if not 0 <= similarity_threshold <= 1:
        raise ValueError("similarity_threshold must be between zero and one")

    ranked_indexes = sorted(
        range(len(articles)),
        key=lambda index: (
            -articles[index]["importance_score"],
            articles[index]["id"],
        ),
    )
    unassigned = set(ranked_indexes)
    groups = []

    for seed_index in ranked_indexes:
        if seed_index not in unassigned:
            continue

        member_scores = [(seed_index, 1.0)]
        unassigned.remove(seed_index)

        for candidate_index in ranked_indexes:
            if candidate_index not in unassigned:
                continue
            similarity = cosine_similarity(
                embeddings[seed_index],
                embeddings[candidate_index],
            )
            if similarity >= similarity_threshold:
                member_scores.append((candidate_index, similarity))
                unassigned.remove(candidate_index)

        groups.append(
            _build_group(
                topic_number=len(groups) + 1,
                member_scores=member_scores,
                articles=articles,
            )
        )

    return groups


def _build_group(topic_number: int, member_scores: list[tuple[int, float]], articles):
    members = [
        {
            **articles[index],
            "similarity_to_seed": round(similarity, 4),
        }
        for index, similarity in member_scores
    ]
    representative = min(
        members,
        key=lambda article: (-article["importance_score"], article["id"]),
    )
    categories = Counter(article["topic_category"] for article in members)
    languages = Counter(article["detected_language"] for article in members)
    sources = {article["source"] for article in members if article["source"]}

    return {
        "topic_candidate_id": f"topic-{topic_number:04d}",
        "article_count": len(members),
        "source_count": len(sources),
        "category_distribution": dict(sorted(categories.items())),
        "language_distribution": dict(sorted(languages.items())),
        "representative_article": _serialize_article(representative),
        "average_similarity": round(
            sum(score for _, score in member_scores) / len(member_scores),
            4,
        ),
        "max_importance_article": _serialize_article(representative),
        "articles": [_serialize_article(article) for article in members],
    }


def _serialize_article(article: dict) -> dict:
    return {
        "id": article["id"],
        "source": article["source"],
        "title": article["title"],
        "source_category": article["source_category"],
        "rule_category": article["rule_category"],
        "topic_category": article["topic_category"],
        "detected_language": article["detected_language"],
        "importance_score": article["importance_score"],
        "similarity_to_seed": article["similarity_to_seed"],
        "published_at": article["published_at"],
        "created_at": article["created_at"],
    }
