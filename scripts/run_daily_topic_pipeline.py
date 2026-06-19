import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.utils.article_embedding_storage import (
    DEFAULT_EMBEDDING_PROVIDER,
    DEFAULT_SOURCE_TEXT_TYPE,
    EmbeddingResult,
    get_model_dimension,
    store_article_embedding,
)
from app.utils.raw_extraction_targets import select_raw_extraction_targets
from app.utils.topic_grouping import group_articles
from app.utils.topic_representatives import select_topic_representatives
from app.utils.topic_summary import (
    DEFAULT_SUMMARY_MODEL,
    SUPPORTED_SUMMARY_MODELS,
    build_topic_summary_inputs,
    summarize_topic_inputs,
)
from scripts.analyze_raw_extraction_targets import get_raw_extraction_states
from scripts.analyze_topic_groups import (
    create_database_engine,
    create_embedding_provider,
    get_articles,
    prepare_articles,
)
from scripts.generate_topic_summary_report import create_summary_provider, get_raw_texts
from scripts.save_topic_summaries import build_save_plan, execute_save_plan


DEFAULT_MAX_ARTICLES = 100
DEFAULT_SIMILARITY_THRESHOLD = 0.78
DEFAULT_MAX_TOPICS = 5
DEFAULT_MAX_REFERENCE_TOPICS = 10
DEFAULT_MAX_ARTICLES_PER_TOPIC = 3
DEFAULT_MAX_RAW_CHARS_PER_ARTICLE = 3000
DEFAULT_EXTRACTION_LIMIT = 5
MAX_DAILY_PROVIDER_ARTICLES = 300
MIN_CLUSTERING_ARTICLES = 2
LOGGER = logging.getLogger(__name__)


def parse_args(argv=None):
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Manual recent-24-hour topic pipeline (dry-run by default).",
    )
    parser.add_argument("--window-hours", type=int, choices=(24,), default=24)
    parser.add_argument(
        "--time-basis",
        choices=("published", "created"),
        default="published",
    )
    parser.add_argument("--max-articles", type=int, default=DEFAULT_MAX_ARTICLES)
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=DEFAULT_SIMILARITY_THRESHOLD,
    )
    parser.add_argument("--max-topics", type=int, default=DEFAULT_MAX_TOPICS)
    parser.add_argument(
        "--max-reference-topics",
        type=int,
        default=DEFAULT_MAX_REFERENCE_TOPICS,
    )
    parser.add_argument(
        "--max-articles-per-topic",
        type=int,
        default=DEFAULT_MAX_ARTICLES_PER_TOPIC,
    )
    parser.add_argument(
        "--max-raw-chars-per-article",
        type=int,
        default=DEFAULT_MAX_RAW_CHARS_PER_ARTICLE,
    )
    parser.add_argument(
        "--extraction-limit",
        type=int,
        default=DEFAULT_EXTRACTION_LIMIT,
    )
    parser.add_argument("--use-embedding-provider", action="store_true")
    parser.add_argument("--use-summary-provider", action="store_true")
    parser.add_argument("--summary-model", default=DEFAULT_SUMMARY_MODEL)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--report-path", type=Path)
    args = parser.parse_args(argv)

    if args.max_articles <= 0:
        parser.error("--max-articles must be greater than zero")
    if not 0 <= args.similarity_threshold <= 1:
        parser.error("--similarity-threshold must be between zero and one")
    if not 1 <= args.max_topics <= 10:
        parser.error("--max-topics must be between 1 and 10")
    if not 0 <= args.max_reference_topics <= 10:
        parser.error("--max-reference-topics must be between 0 and 10")
    if not 1 <= args.max_articles_per_topic <= 3:
        parser.error("--max-articles-per-topic must be between 1 and 3")
    if not 1 <= args.max_raw_chars_per_article <= 5000:
        parser.error("--max-raw-chars-per-article must be between 1 and 5000")
    if not 1 <= args.extraction_limit <= 5:
        parser.error("--extraction-limit must be between 1 and 5")
    if args.use_embedding_provider:
        if args.max_articles > MAX_DAILY_PROVIDER_ARTICLES:
            parser.error(
                "provider --max-articles cannot exceed "
                f"{MAX_DAILY_PROVIDER_ARTICLES}"
            )
        if not os.getenv("OPENAI_EMBEDDING_API_KEY"):
            parser.error(
                "--use-embedding-provider requires OPENAI_EMBEDDING_API_KEY"
            )
    if args.summary_model not in SUPPORTED_SUMMARY_MODELS:
        parser.error(
            "--summary-model must be one of: "
            + ", ".join(sorted(SUPPORTED_SUMMARY_MODELS))
        )
    if args.use_summary_provider and not os.getenv("OPENAI_SUMMARY_API_KEY"):
        parser.error("--use-summary-provider requires OPENAI_SUMMARY_API_KEY")

    args.all = False
    args.effective_max_articles = args.max_articles
    args.max_candidates_per_topic = args.max_articles_per_topic
    args.max_targets_per_topic = args.max_articles_per_topic
    return args


def build_pipeline(
    rows,
    raw_states,
    raw_texts,
    args,
    *,
    embedding_provider=None,
    embedding_acquirer=None,
    summary_provider=None,
    extraction_executor=None,
    raw_text_loader=None,
    save_executor=None,
):
    pipeline_started_at = time.monotonic()
    articles = prepare_articles(rows)
    embedder = embedding_provider or create_embedding_provider(args)
    LOGGER.info(
        "embedding provider start: provider=%s model=%s article_count=%d",
        "openai" if args.use_embedding_provider else "deterministic",
        embedder.model,
        len(articles),
    )
    (
        clustering_articles,
        embeddings,
        embedding_stats,
        embedding_failures,
    ) = acquire_pipeline_embeddings(
        articles,
        embedder,
        embedding_acquirer=embedding_acquirer,
    )
    LOGGER.info(
        "embedding provider end: provider=%s model=%s embedding_count=%d "
        "created=%d updated=%d reused=%d failed=%d",
        "openai" if args.use_embedding_provider else "deterministic",
        embedder.model,
        len(embeddings),
        embedding_stats["created"],
        embedding_stats["updated"],
        embedding_stats["reused"],
        embedding_stats["failed"],
    )
    LOGGER.info(
        "topic candidate generation start: article_count=%d",
        len(clustering_articles),
    )
    if len(clustering_articles) < MIN_CLUSTERING_ARTICLES:
        LOGGER.warning(
            "topic candidate generation skipped: clustering_input_count=%d "
            "minimum=%d",
            len(clustering_articles),
            MIN_CLUSTERING_ARTICLES,
        )
        grouped = []
    else:
        grouped = group_articles(
            clustering_articles,
            embeddings,
            similarity_threshold=args.similarity_threshold,
        )
    representatives = select_topic_representatives(
        grouped,
        max_candidates_per_topic=args.max_articles_per_topic,
    )
    target_topics = select_raw_extraction_targets(
        representatives,
        raw_states,
        max_targets_per_topic=args.max_articles_per_topic,
    )
    _attach_report_metadata(target_topics, clustering_articles)
    ordered_topics = sorted(target_topics, key=_topic_selection_key)
    LOGGER.info(
        "topic candidate generation end: candidate_count=%d",
        len(ordered_topics),
    )
    selected_topics = ordered_topics[: args.max_topics]
    reference_topics = ordered_topics[
        args.max_topics : args.max_topics + args.max_reference_topics
    ]
    selected_article_ids = _selected_article_ids(selected_topics)
    LOGGER.info("selected topic count: %d", len(selected_topics))

    extraction_results = []
    if args.execute:
        LOGGER.info(
            "raw extraction start: article_count=%d article_ids=%s",
            len(selected_article_ids),
            selected_article_ids,
        )
        if selected_article_ids:
            if extraction_executor is None or raw_text_loader is None:
                raise ValueError(
                    "execute mode requires extraction_executor and raw_text_loader"
                )
            extraction_results = extraction_executor(
                selected_article_ids,
                limit=args.extraction_limit,
            )
            raw_texts = raw_text_loader(_topic_article_ids(selected_topics))
        LOGGER.info(
            "raw extraction end: requested_count=%d result_count=%d article_ids=%s",
            len(selected_article_ids),
            len(extraction_results),
            selected_article_ids,
        )

    provider = summary_provider or create_summary_provider(args)
    summary_inputs = build_topic_summary_inputs(
        selected_topics,
        raw_texts,
        max_topics=args.max_topics,
        max_articles_per_topic=args.max_articles_per_topic,
        max_raw_chars_per_article=args.max_raw_chars_per_article,
    )
    LOGGER.info(
        "summary provider start: provider=%s model=%s topic_count=%d",
        provider.provider,
        provider.model,
        len(summary_inputs),
    )
    summaries = summarize_topic_inputs(summary_inputs, provider)
    LOGGER.info(
        "summary provider end: provider=%s model=%s summary_count=%d",
        provider.provider,
        provider.model,
        len(summaries),
    )
    generation_result = {
        "analysis": {"provider": provider.provider, "model": provider.model},
        "topic_summaries": summaries,
    }
    save_plan = build_save_plan(generation_result, args)
    save_plan["analysis"]["raw_extraction_performed"] = bool(extraction_results)
    _apply_similarity_scores(save_plan, selected_topics)
    if args.execute and save_plan["topics"]:
        if save_executor is None:
            raise ValueError("execute mode requires save_executor")
        LOGGER.info(
            "DB write start: topic_count=%d",
            len(save_plan["topics"]),
        )
        save_plan = save_executor(save_plan)
        LOGGER.info(
            "DB write end: saved_topic_count=%d",
            save_plan["analysis"]["saved_topic_count"],
        )

    extraction_success_count = sum(
        result["status"] == "success" for result in extraction_results
    )
    extraction_failed_count = sum(
        result["status"] == "failed" for result in extraction_results
    )
    return {
        "analysis": {
            "dry_run": not args.execute,
            "execute_requested": args.execute,
            "window_hours": args.window_hours,
            "article_count": len(articles),
            "candidate_articles": len(articles),
            "embedding_created": embedding_stats["created"],
            "embedding_updated": embedding_stats["updated"],
            "embedding_reused": embedding_stats["reused"],
            "embedding_failed": embedding_stats["failed"],
            "clustering_input_count": len(clustering_articles),
            "topic_candidate_count": len(target_topics),
            "selected_topic_count": len(selected_topics),
            "topic_count": len(selected_topics),
            "reference_topic_count": len(reference_topics),
            "selected_article_ids": selected_article_ids,
            "embedding_provider": (
                "openai" if args.use_embedding_provider else "deterministic"
            ),
            "embedding_model": embedder.model,
            "summary_provider": provider.provider,
            "summary_model": provider.model,
            "raw_extraction_performed": bool(extraction_results),
            "raw_extraction_success_count": extraction_success_count,
            "raw_extraction_failed_count": extraction_failed_count,
            "db_write_performed": save_plan["analysis"]["db_write_performed"],
            "pipeline_elapsed_seconds": round(
                time.monotonic() - pipeline_started_at,
                6,
            ),
        },
        "topics": [_public_topic(topic) for topic in selected_topics],
        "reference_topics": [_public_topic(topic) for topic in reference_topics],
        "extraction_results": extraction_results,
        "embedding_failures": embedding_failures,
        "topic_summaries": summaries,
        "save_plan": save_plan,
    }


def render_report(result):
    analysis = result["analysis"]
    lines = [
        "# Daily topic pipeline report",
        "",
        "## Summary",
        "",
        f"- Dry-run: `{str(analysis['dry_run']).lower()}`",
        f"- Execute requested: `{str(analysis['execute_requested']).lower()}`",
        f"- Window hours: {analysis['window_hours']}",
        f"- Article count: {analysis['article_count']}",
        f"- Candidate articles: {analysis['candidate_articles']}",
        f"- Embedding created/updated/reused/failed: {analysis['embedding_created']} / {analysis['embedding_updated']} / {analysis['embedding_reused']} / {analysis['embedding_failed']}",
        f"- Clustering input count: {analysis['clustering_input_count']}",
        f"- Topic candidate count: {analysis['topic_candidate_count']}",
        f"- Selected topic count: {analysis['selected_topic_count']}",
        f"- Topic count: {analysis['topic_count']}",
        f"- Reference topic count: {analysis['reference_topic_count']}",
        f"- Selected article IDs: `{analysis['selected_article_ids']}`",
        "- Topic ordering: `article_count desc, source_count desc, average similarity desc, latest published_at desc, topic_candidate_id asc`",
        f"- Embedding provider/model: `{analysis['embedding_provider']}` / `{analysis['embedding_model']}`",
        f"- Summary provider/model: `{analysis['summary_provider']}` / `{analysis['summary_model']}`",
        f"- Raw extraction performed: `{str(analysis['raw_extraction_performed']).lower()}`",
        f"- Raw extraction success/failure: {analysis['raw_extraction_success_count']} / {analysis['raw_extraction_failed_count']}",
        f"- DB write performed: `{str(analysis['db_write_performed']).lower()}`",
        f"- Pipeline elapsed seconds: {analysis['pipeline_elapsed_seconds']}",
        "",
        "## Selected Topics",
        "",
    ]
    summaries_by_topic = {
        summary["topic_candidate_id"]: summary
        for summary in result["topic_summaries"]
    }
    for topic in result["topics"]:
        lines.extend(
            _render_report_topic(
                topic,
                summary=summaries_by_topic.get(topic["topic_candidate_id"]),
            )
        )
    if not result["topics"]:
        lines.extend(["- None", ""])
    lines.extend(
        [
            "## Reference Candidates",
            "",
            "These candidates were outside `--max-topics` and are shown only for human review.",
            "They are not raw extraction, summary provider, or DB save targets.",
            "",
        ]
    )
    for topic in result["reference_topics"]:
        lines.extend(_render_report_topic(topic, reference=True))
    if not result["reference_topics"]:
        lines.extend(["- None", ""])
    lines.extend(
        [
            "## Safety",
            "",
            "- Embedding vectors and topic candidate intermediate results are memory-only.",
            "- Actual raw extraction and DB writes require explicit `--execute`.",
            "- Provider calls require explicit provider flags and API keys.",
            "",
        ]
    )
    return "\n".join(lines)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    LOGGER.info("daily topic pipeline start")
    try:
        _run()
    except Exception:
        LOGGER.exception("daily topic pipeline failed")
        raise
    LOGGER.info("daily topic pipeline completion")


def _run():
    args = parse_args()
    LOGGER.info(
        "pipeline config: window_hours=%d time_basis=%s max_articles=%d "
        "similarity_threshold=%.2f max_topics=%d max_reference_topics=%d "
        "max_articles_per_topic=%d max_raw_chars_per_article=%d "
        "extraction_limit=%d use_embedding_provider=%s "
        "use_summary_provider=%s summary_model=%s execute=%s",
        args.window_hours,
        args.time_basis,
        args.max_articles,
        args.similarity_threshold,
        args.max_topics,
        args.max_reference_topics,
        args.max_articles_per_topic,
        args.max_raw_chars_per_article,
        args.extraction_limit,
        args.use_embedding_provider,
        args.use_summary_provider,
        args.summary_model,
        args.execute,
    )
    LOGGER.info("database engine create start")
    engine = create_database_engine()
    LOGGER.info("database engine create end")
    LOGGER.info("database connection start")
    with engine.connect() as connection:
        LOGGER.info("database connection established")
        connection.execute(text("set transaction read only"))
        LOGGER.info("article fetch start")
        rows = get_articles(connection, args)
        LOGGER.info("article fetch end: article_count=%d", len(rows))
        article_ids = [row["id"] for row in rows]
        LOGGER.info("raw extraction state fetch start: article_count=%d", len(article_ids))
        raw_states = get_raw_extraction_states(connection, article_ids)
        LOGGER.info("raw extraction state fetch end: state_count=%d", len(raw_states))

        LOGGER.info("raw text fetch start: article_count=%d", len(article_ids))
        raw_texts = get_raw_texts(connection, article_ids)
        LOGGER.info("raw text fetch end: raw_text_count=%d", len(raw_texts))

    def load_raw_texts(article_ids):
        with engine.connect() as connection:
            connection.execute(text("set transaction read only"))
            return get_raw_texts(connection, article_ids)

    def save(plan):
        with engine.begin() as connection:
            return execute_save_plan(plan, connection)

    extraction_executor = None
    if args.execute:
        from scripts.extract_raw_articles import extract_selected_article_ids

        extraction_executor = extract_selected_article_ids

    embedder = create_embedding_provider(args)
    embedding_acquirer = None
    if args.use_embedding_provider:
        expected_dimension = get_model_dimension(embedder.model)

        def embedding_acquirer(article):
            if args.execute:
                with engine.begin() as connection:
                    return store_article_embedding(
                        connection,
                        article=article,
                        embedding_provider=embedder,
                        provider=DEFAULT_EMBEDDING_PROVIDER,
                        source_text_type=DEFAULT_SOURCE_TEXT_TYPE,
                        expected_dimension=expected_dimension,
                    )
            with engine.connect() as connection:
                connection.execute(text("set transaction read only"))
                return store_article_embedding(
                    connection,
                    article=article,
                    embedding_provider=embedder,
                    provider=DEFAULT_EMBEDDING_PROVIDER,
                    source_text_type=DEFAULT_SOURCE_TEXT_TYPE,
                    expected_dimension=expected_dimension,
                    persist=False,
                )

    result = build_pipeline(
        rows,
        raw_states,
        raw_texts,
        args,
        embedding_provider=embedder,
        embedding_acquirer=embedding_acquirer,
        extraction_executor=extraction_executor,
        raw_text_loader=load_raw_texts if args.execute else None,
        save_executor=save if args.execute else None,
    )
    if args.report_path:
        args.report_path.parent.mkdir(parents=True, exist_ok=True)
        args.report_path.write_text(render_report(result), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


def acquire_pipeline_embeddings(
    articles,
    embedding_provider,
    *,
    embedding_acquirer=None,
):
    if embedding_acquirer is None:
        embeddings = embedding_provider.embed(
            [article["embedding_input"] for article in articles]
        )
        if len(articles) != len(embeddings):
            raise ValueError("articles and embeddings must have the same length")
        return (
            articles,
            embeddings,
            {
                "created": len(embeddings),
                "updated": 0,
                "reused": 0,
                "failed": 0,
            },
            [],
        )

    clustering_articles = []
    embeddings = []
    stats = {"created": 0, "updated": 0, "reused": 0, "failed": 0}
    failures = []
    for article in articles:
        try:
            result = embedding_acquirer(article)
        except Exception as error:
            stats["failed"] += 1
            failure = {
                "article_id": article.get("id"),
                "error": _safe_embedding_error(error),
            }
            failures.append(failure)
            LOGGER.warning(
                "article embedding failed: article_id=%s error=%s",
                failure["article_id"],
                failure["error"],
            )
            continue

        if not isinstance(result, EmbeddingResult):
            raise TypeError("embedding acquirer returned an invalid result")
        if result.status not in {"created", "updated", "reused"}:
            raise ValueError(
                f"unsupported embedding status: {result.status}"
            )
        if result.embedding is None:
            raise ValueError("embedding result does not include a vector")

        clustering_articles.append(article)
        embeddings.append(result.embedding)
        stats[result.status] += 1
    return clustering_articles, embeddings, stats, failures


def _safe_embedding_error(error: Exception) -> str:
    message = " ".join(str(error).split())
    if len(message) > 200:
        message = message[:197] + "..."
    return f"{type(error).__name__}: {message}" if message else type(error).__name__


def _selected_article_ids(topics):
    ids = []
    for topic in topics:
        for article in topic["articles"]:
            if article["extraction_target_status"] == "target":
                ids.append(article["id"])
    return ids


def _topic_article_ids(topics):
    return list(
        dict.fromkeys(
            article["id"] for topic in topics for article in topic["articles"]
        )
    )


def _apply_similarity_scores(save_plan, topics):
    metadata_by_article = {
        article["id"]: {
            "role": (
                "representative"
                if article.get("representative_candidate_rank") == 1
                else "supporting"
            ),
            "similarity_score": article.get("similarity_to_seed"),
        }
        for topic in topics
        for article in topic["articles"]
        if article.get("representative_candidate_rank") is not None
    }
    for topic in save_plan["topics"]:
        for article in topic["articles"]:
            metadata = metadata_by_article.get(article["article_id"], {})
            article.update(metadata)


def _attach_report_metadata(topics, articles):
    url_by_article_id = {
        article["id"]: article.get("url")
        for article in articles
    }
    for topic in topics:
        for article in topic["articles"]:
            article["url"] = url_by_article_id.get(article["id"])


def _topic_selection_key(topic):
    selected = [
        article
        for article in topic["articles"]
        if article.get("representative_candidate_rank") is not None
    ]
    similarities = [
        float(article["similarity_to_seed"])
        for article in selected
        if article.get("similarity_to_seed") is not None
    ]
    average_similarity = (
        sum(similarities) / len(similarities) if similarities else 0.0
    )
    latest = max(
        (
            value
            for article in topic["articles"]
            if (
                value := _as_utc(
                    article.get("published_at") or article.get("created_at")
                )
            )
            is not None
        ),
        default=None,
    )
    latest_timestamp = latest.timestamp() if latest else float("-inf")
    return (
        -topic["article_count"],
        -topic["source_count"],
        -average_similarity,
        -latest_timestamp,
        topic["topic_candidate_id"],
    )


def _public_topic(topic):
    selected = [
        article
        for article in topic["articles"]
        if article.get("representative_candidate_rank") is not None
    ]
    return {
        "topic_candidate_id": topic["topic_candidate_id"],
        "article_count": topic["article_count"],
        "source_count": topic["source_count"],
        "selected_article_ids": [article["id"] for article in selected],
        "similarity_scores": {
            article["id"]: article.get("similarity_to_seed") for article in selected
        },
        "articles": [
            {
                "role": (
                    "representative"
                    if article.get("representative_candidate_rank") == 1
                    else "supporting"
                ),
                "article_id": article["id"],
                "similarity_score": article.get("similarity_to_seed"),
                "source": article.get("source"),
                "published_at": article.get("published_at"),
                "title": article.get("title"),
                "url": article.get("url"),
            }
            for article in selected
        ],
    }


def _render_report_topic(topic, *, summary=None, reference=False):
    article_id_label = "Article IDs" if reference else "Selected article IDs"
    lines = [
        f"### {topic['topic_candidate_id']}",
        "",
        f"- Article count: {topic['article_count']}",
        f"- Source count: {topic['source_count']}",
    ]
    if reference:
        lines.append("- Reason: outside max-topics")
    lines.extend(
        [
            f"- {article_id_label}: `{topic['selected_article_ids']}`",
            f"- Similarity scores: `{topic['similarity_scores']}`",
            "",
            "#### Selected Articles" if not reference else "#### Reference Articles",
            "",
            "| role | article_id | similarity | source | published_at | title | url |",
            "| --- | ---: | ---: | --- | --- | --- | --- |",
        ]
    )
    for article in topic["articles"]:
        lines.append(
            f"| {_escape(article['role'])} "
            f"| {article['article_id']} "
            f"| {_format_similarity(article['similarity_score'])} "
            f"| {_escape(article['source'])} "
            f"| {_escape(article['published_at'])} "
            f"| {_escape(article['title'])} "
            f"| {_escape(article['url'])} |"
        )
    lines.append("")
    if summary is not None:
        lines.extend(
            [
                "#### Generated Summary",
                "",
                f"- Status: `{summary['status']}`",
                f"- title_ko: {_escape(summary['title_ko'])}",
                f"- summary_ko: {_escape(summary['summary_ko'])}",
                "- key_points:",
            ]
        )
        lines.extend(f"  - {_escape(point)}" for point in summary["key_points"])
        lines.extend(
            [
                f"- keywords: `{', '.join(summary['keywords'])}`",
                "",
            ]
        )
    return lines


def _format_similarity(value):
    return "" if value is None else f"{float(value):.4f}"


def _as_utc(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _escape(value):
    return str(value or "").replace("|", "\\|").replace("\n", " ")


if __name__ == "__main__":
    main()
