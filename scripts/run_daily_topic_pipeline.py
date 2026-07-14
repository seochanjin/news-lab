"""Daily topic pipeline의 CLI 설정과 네 단계 실행을 조정한다.

최근 기사 조회부터 embedding, topic 선정, 원문 확보, summary 저장 계획까지
service package의 단계를 순서대로 호출한다. 기본 실행은 dry-run이며
`--execute`가 지정된 경우에만 주입된 adapter를 통해 DB 쓰기와 원문 추출이
발생한다. Execute 모드의 topic 저장 commit이 성공한 뒤에는 PostgreSQL을 다시
조회해 Home Redis cache를 prewarm하지만, prewarm 실패는 pipeline 성공 여부에
영향을 주지 않는다.
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.home_topics_cache import get_home_topics_cache
from app.home_topics_payload import prewarm_home_topics_cache
from app.services.daily_topic_pipeline import (
    acquire_pipeline_embeddings,
    acquire_selected_article_raw_texts,
    cluster_and_select_topics,
    create_embedding_acquirer,
    create_raw_text_loader,
    create_save_executor,
    prepare_article_embeddings,
    public_topic,
    render_report,
    resolve_pipeline_context,
    summarize_and_save_topics,
    topic_selection_key,
)
from app.utils.topic_summary import DEFAULT_SUMMARY_MODEL, SUPPORTED_SUMMARY_MODELS
from scripts.analyze_raw_extraction_targets import get_raw_extraction_states
from scripts.analyze_topic_groups import (
    create_database_engine,
    create_embedding_provider,
    get_articles,
)


DEFAULT_MAX_ARTICLES = 100
DEFAULT_SIMILARITY_THRESHOLD = 0.78
DEFAULT_MAX_TOPICS = 5
DEFAULT_MAX_REFERENCE_TOPICS = 10
DEFAULT_MAX_RELATED_ARTICLES_PER_TOPIC = 20
DEFAULT_MAX_SUMMARY_ARTICLES_PER_TOPIC = 3
DEFAULT_MAX_RAW_CHARS_PER_ARTICLE = 3000
DEFAULT_EXTRACTION_LIMIT = 5
MAX_DAILY_PROVIDER_ARTICLES = 300
LOGGER = logging.getLogger(__name__)

# Preserve the existing test and caller import contract while implementations
# live in the service package.
_topic_selection_key = topic_selection_key


def parse_args(argv=None):
    """Daily pipeline CLI 인자를 읽고 기사 상한 관계와 provider 조건을 검증한다.

    기존 `--max-articles-per-topic`은 deprecated alias로 유지하며 단독 사용 시
    관련 기사와 Summary 기사 상한을 같은 값으로 설정해 과거 실행 의미를
    보존한다. 신규 상한 옵션과 alias를 함께 지정하면 모호한 구성을 차단한다.
    """

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
        "--max-related-articles-per-topic",
        type=int,
        default=None,
    )
    parser.add_argument(
        "--max-summary-articles-per-topic",
        type=int,
        default=None,
    )
    parser.add_argument(
        "--max-articles-per-topic",
        type=int,
        default=None,
        help=argparse.SUPPRESS,
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
    if args.max_articles_per_topic is not None:
        if (
            args.max_related_articles_per_topic is not None
            or args.max_summary_articles_per_topic is not None
        ):
            parser.error(
                "--max-articles-per-topic cannot be combined with the new "
                "per-topic article limit options"
            )
        args.max_related_articles_per_topic = args.max_articles_per_topic
        args.max_summary_articles_per_topic = args.max_articles_per_topic
    else:
        args.max_related_articles_per_topic = (
            args.max_related_articles_per_topic
            if args.max_related_articles_per_topic is not None
            else DEFAULT_MAX_RELATED_ARTICLES_PER_TOPIC
        )
        args.max_summary_articles_per_topic = (
            args.max_summary_articles_per_topic
            if args.max_summary_articles_per_topic is not None
            else DEFAULT_MAX_SUMMARY_ARTICLES_PER_TOPIC
        )
    if args.max_related_articles_per_topic < 1:
        parser.error("--max-related-articles-per-topic must be at least 1")
    if args.max_summary_articles_per_topic < 1:
        parser.error("--max-summary-articles-per-topic must be at least 1")
    if (
        args.max_summary_articles_per_topic
        > args.max_related_articles_per_topic
    ):
        parser.error(
            "--max-summary-articles-per-topic cannot exceed "
            "--max-related-articles-per-topic"
        )
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
    # 기존 downstream 호출자는 Summary 기사 상한을 단일 기사 상한으로 사용한다.
    args.max_articles_per_topic = args.max_summary_articles_per_topic
    args.max_candidates_per_topic = args.max_summary_articles_per_topic
    args.max_targets_per_topic = args.max_summary_articles_per_topic
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
    pipeline_context=None,
):
    """Daily topic pipeline의 네 stage를 기존 순서대로 조정한다.

    하나의 `PipelineContext`를 embedding, topic 선택, 원문 확보, summary/save
    단계에 전달한다. Provider와 DB adapter는 호출자가 주입할 수 있어 테스트와
    dry-run에서 외부 부수 효과를 차단한다. 반환값은 기존 report와 JSON 계약을
    유지하는 통합 결과다.
    """

    pipeline_started_at = time.monotonic()
    pipeline_context = pipeline_context or resolve_pipeline_context()
    embedder = embedding_provider or create_embedding_provider(args)

    embedding_result = prepare_article_embeddings(
        rows,
        args,
        pipeline_context=pipeline_context,
        embedding_provider=embedder,
        embedding_acquirer=embedding_acquirer,
    )
    topic_result = cluster_and_select_topics(
        embedding_result,
        args,
        pipeline_context=pipeline_context,
    )
    raw_result = acquire_selected_article_raw_texts(
        topic_result,
        raw_states,
        raw_texts,
        args,
        pipeline_context=pipeline_context,
        extraction_executor=extraction_executor,
        raw_text_loader=raw_text_loader,
    )
    save_result = summarize_and_save_topics(
        topic_result,
        raw_result,
        args,
        pipeline_context=pipeline_context,
        summary_provider=summary_provider,
        save_executor=save_executor,
    )

    return {
        "analysis": _build_analysis(
            args,
            embedder,
            pipeline_context,
            embedding_result,
            topic_result,
            raw_result,
            save_result,
            pipeline_started_at,
        ),
        "topics": [public_topic(topic) for topic in topic_result.selected_topics],
        "reference_topics": [
            public_topic(topic) for topic in topic_result.reference_topics
        ],
        "extraction_results": raw_result.extraction_results,
        "embedding_failures": embedding_result.failures,
        "topic_failures": save_result.failures,
        "topic_summaries": save_result.summaries,
        "save_plan": save_result.save_plan,
    }


def _build_analysis(
    args,
    embedder,
    pipeline_context,
    embedding_result,
    topic_result,
    raw_result,
    save_result,
    pipeline_started_at,
):
    """단계별 결과를 관련·Summary·원문·저장 수가 분리된 실행 통계로 합친다."""

    candidate_count = (
        len(embedding_result.articles_with_embeddings)
        + embedding_result.failed_count
    )
    return {
        "dry_run": not args.execute,
        "execute_requested": args.execute,
        "window_hours": args.window_hours,
        "article_count": candidate_count,
        "candidate_articles": candidate_count,
        "embedding_created": embedding_result.created_count,
        "embedding_updated": embedding_result.updated_count,
        "embedding_reused": embedding_result.reused_count,
        "embedding_failed": embedding_result.failed_count,
        "clustering_input_count": len(embedding_result.articles_with_embeddings),
        "cluster_count": topic_result.cluster_count,
        "topic_candidate_count": topic_result.topic_candidate_count,
        "selected_topic_count": topic_result.selected_topic_count,
        "topic_count": topic_result.selected_topic_count,
        "reference_topic_count": len(topic_result.reference_topics),
        "selected_article_ids": topic_result.selected_article_ids,
        "selected_article_count": len(topic_result.selected_article_ids),
        "related_article_ids": topic_result.related_article_ids,
        "related_article_count": len(topic_result.related_article_ids),
        "summary_article_ids": topic_result.summary_article_ids,
        "summary_article_count": len(topic_result.summary_article_ids),
        "raw_acquisition_target_count": len(topic_result.summary_article_ids),
        "embedding_provider": (
            "openai" if args.use_embedding_provider else "deterministic"
        ),
        "embedding_model": embedder.model,
        "summary_provider": save_result.save_plan["analysis"]["provider"],
        "summary_model": save_result.save_plan["analysis"]["model"],
        "raw_extraction_performed": bool(raw_result.extraction_results),
        "raw_extraction_success_count": len(raw_result.extracted_article_ids),
        "raw_extraction_failed_count": len(raw_result.failed_article_ids),
        "raw_reused_count": len(raw_result.reused_article_ids),
        "raw_extracted_count": len(raw_result.extracted_article_ids),
        "raw_failed_count": len(raw_result.failed_article_ids),
        "raw_missing_count": len(raw_result.missing_article_ids),
        "generated_topic_count": save_result.generated_topic_count,
        "saved_topic_count": save_result.saved_topic_count,
        "saved_topic_article_count": save_result.save_plan["analysis"][
            "linked_article_count"
        ],
        "skipped_topic_count": save_result.skipped_topic_count,
        "failed_topic_count": save_result.failed_topic_count,
        "db_write_performed": save_result.save_plan["analysis"][
            "db_write_performed"
        ],
        "pipeline_date": pipeline_context.pipeline_date,
        "business_timezone": pipeline_context.business_timezone,
        "started_at_utc": pipeline_context.started_at_utc,
        "started_at_local": pipeline_context.started_at_local,
        "pipeline_date_source": pipeline_context.pipeline_date_source,
        "pipeline_elapsed_seconds": round(
            time.monotonic() - pipeline_started_at,
            6,
        ),
    }


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
    """CLI 설정과 runtime 의존성을 구성하고 한 번의 pipeline을 실행한다.

    이 함수는 DB engine과 provider, extractor adapter를 조립하지만 단계별
    알고리즘은 service package에 위임한다. `--execute`가 없으면 embedding과
    topic 저장 adapter가 DB write를 수행하지 않는다.
    """

    args = parse_args()
    pipeline_context = resolve_pipeline_context()
    _log_pipeline_config(args, pipeline_context)

    LOGGER.info("database engine create start")
    engine = create_database_engine()
    LOGGER.info("database engine create end")
    rows, raw_states = _load_candidates(engine, args)

    embedder = create_embedding_provider(args)
    embedding_acquirer = create_embedding_acquirer(engine, args, embedder)
    raw_text_loader = create_raw_text_loader(engine)
    save_executor = create_save_executor(engine) if args.execute else None
    extraction_executor = _create_extraction_executor(args)

    result = build_pipeline(
        rows,
        raw_states,
        {},
        args,
        embedding_provider=embedder,
        embedding_acquirer=embedding_acquirer,
        extraction_executor=extraction_executor,
        raw_text_loader=raw_text_loader,
        save_executor=save_executor,
        pipeline_context=pipeline_context,
    )
    _prewarm_home_topics_cache_after_success(engine, result, args)
    if args.report_path:
        args.report_path.parent.mkdir(parents=True, exist_ok=True)
        args.report_path.write_text(render_report(result), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


def _prewarm_home_topics_cache_after_success(engine, result, args, *, cache=None):
    """DB 저장 성공 이후 Home cache prewarm을 시도하고 실패를 pipeline 밖으로 격리한다.

    Dry-run 또는 저장할 topic이 없어 실제 DB write가 없었던 실행에서는 prewarm을
    건너뛴다. Execute 모드에서 `db_write_performed`가 참이면 `engine.begin()`
    저장 transaction이 정상 종료된 뒤 새 read connection으로 Home payload를
    조회하고 Redis에 overwrite한다. Redis 미설정, SET 실패, payload 조회 실패는
    warning이나 bypass log만 남기며 호출자에게 예외를 전파하지 않는다.
    """

    if not args.execute:
        LOGGER.info("home_topics_cache event=bypass operation=prewarm reason=dry_run")
        return
    if not result.get("analysis", {}).get("db_write_performed"):
        LOGGER.info("home_topics_cache event=bypass operation=prewarm reason=no_db_write")
        return

    try:
        cache = cache or get_home_topics_cache()
        prewarm_home_topics_cache(
            cache=cache,
            connection_factory=engine.connect,
        )
    except Exception as exc:  # noqa: BLE001 - prewarm must not fail the pipeline.
        LOGGER.warning(
            "home_topics_cache event=bypass operation=prewarm error=%s",
            exc.__class__.__name__,
        )


def _load_candidates(engine, args):
    """최근 기사 후보와 raw extraction 상태를 한 read-only 연결에서 조회한다."""

    LOGGER.info("database connection start")
    with engine.connect() as connection:
        LOGGER.info("database connection established")
        connection.execute(text("set transaction read only"))
        LOGGER.info("article fetch start")
        rows = get_articles(connection, args)
        LOGGER.info("article fetch end: article_count=%d", len(rows))
        article_ids = [row["id"] for row in rows]
        LOGGER.info(
            "raw extraction state fetch start: article_count=%d",
            len(article_ids),
        )
        raw_states = get_raw_extraction_states(connection, article_ids)
        LOGGER.info(
            "raw extraction state fetch end: state_count=%d",
            len(raw_states),
        )
    return rows, raw_states


def _create_extraction_executor(args):
    """Execute 모드에서만 selected article extractor를 지연 import한다."""

    if not args.execute:
        return None
    from scripts.extract_raw_articles import extract_selected_article_ids

    return extract_selected_article_ids


def _log_pipeline_config(args, pipeline_context):
    """검증된 실행 설정과 공통 pipeline 날짜를 민감정보 없이 기록한다."""

    LOGGER.info(
        "pipeline config: window_hours=%d time_basis=%s max_articles=%d "
        "similarity_threshold=%.2f max_topics=%d max_reference_topics=%d "
        "max_related_articles_per_topic=%d "
        "max_summary_articles_per_topic=%d max_raw_chars_per_article=%d "
        "extraction_limit=%d use_embedding_provider=%s "
        "use_summary_provider=%s summary_model=%s execute=%s",
        args.window_hours,
        args.time_basis,
        args.max_articles,
        args.similarity_threshold,
        args.max_topics,
        args.max_reference_topics,
        args.max_related_articles_per_topic,
        args.max_summary_articles_per_topic,
        args.max_raw_chars_per_article,
        args.extraction_limit,
        args.use_embedding_provider,
        args.use_summary_provider,
        args.summary_model,
        args.execute,
    )
    LOGGER.info(
        "pipeline date resolved: pipeline_date=%s business_timezone=%s "
        "started_at_utc=%s started_at_local=%s source=%s",
        pipeline_context.pipeline_date,
        pipeline_context.business_timezone,
        pipeline_context.started_at_utc.isoformat(),
        pipeline_context.started_at_local.isoformat(),
        pipeline_context.pipeline_date_source,
    )


if __name__ == "__main__":
    main()
