"""7일 Topic pipeline의 CLI 설정과 주간 실행 단계를 조정한다.

명시적인 완료 주간 context로 기존 article embedding 후보를 조회하고 재클러스터링한
뒤 선택 원문, 주간 흐름 Summary와 전용 repository 저장 단계를 순서대로 호출한다.
기본 실행은 dry-run이며 `--execute`에서만 run 이력, 지연 원문 추출과 Topic 결과
교체가 발생한다. 이 진입점은 신규 article embedding을 생성하지 않는다.
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.home_topics_cache import get_weekly_home_topics_cache
from app.home_topics_payload import prewarm_weekly_home_topics_cache
from app.services.daily_topic_pipeline import create_raw_text_loader
from app.services.weekly_topic_pipeline import (
    WeeklyOpenAISummaryProvider,
    WeeklyRawAcquisitionResult,
    WeeklyTopicProcessingResult,
    WeeklyTopicRepository,
    WeeklyTopicRunCompletion,
    WeeklyTopicRunStart,
    acquire_weekly_topic_raw_texts,
    cluster_and_select_weekly_topics,
    load_weekly_candidates,
    resolve_weekly_pipeline_context,
    summarize_and_persist_weekly_topics,
)
from app.utils.topic_summary import (
    DEFAULT_SUMMARY_MODEL,
    SUPPORTED_SUMMARY_MODELS,
    DeterministicSummaryProvider,
)
from scripts.analyze_raw_extraction_targets import get_raw_extraction_states
from scripts.analyze_topic_groups import create_database_engine


DEFAULT_MAX_ARTICLES = 1000
DEFAULT_SIMILARITY_THRESHOLD = 0.70
DEFAULT_MAX_TOPICS = 5
DEFAULT_MAX_RELATED_ARTICLES_PER_TOPIC = 20
DEFAULT_MAX_SUMMARY_ARTICLES_PER_TOPIC = 5
DEFAULT_MAX_RAW_CHARS_PER_ARTICLE = 3000
DEFAULT_EXTRACTION_LIMIT = 5
LOGGER = logging.getLogger(__name__)


def parse_args(argv=None):
    """Weekly 전용 CLI 인자를 읽고 주간 범위, 상한과 provider 조건을 검증한다."""

    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Completed-calendar-week topic pipeline (dry-run by default).",
    )
    parser.add_argument(
        "--week-start",
        type=_parse_week_start,
        help="재처리할 Asia/Seoul 기준 월요일 날짜(YYYY-MM-DD)",
    )
    parser.add_argument("--max-articles", type=int, default=DEFAULT_MAX_ARTICLES)
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=DEFAULT_SIMILARITY_THRESHOLD,
    )
    parser.add_argument("--max-topics", type=int, default=DEFAULT_MAX_TOPICS)
    parser.add_argument(
        "--max-related-articles-per-topic",
        type=int,
        default=DEFAULT_MAX_RELATED_ARTICLES_PER_TOPIC,
    )
    parser.add_argument(
        "--max-summary-articles-per-topic",
        type=int,
        default=DEFAULT_MAX_SUMMARY_ARTICLES_PER_TOPIC,
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
    parser.add_argument("--use-summary-provider", action="store_true")
    parser.add_argument("--summary-model", default=DEFAULT_SUMMARY_MODEL)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)

    if args.max_articles < 1:
        parser.error("--max-articles must be positive")
    if not 0 <= args.similarity_threshold <= 1:
        parser.error("--similarity-threshold must be between zero and one")
    if not 1 <= args.max_topics <= 10:
        parser.error("--max-topics must be between 1 and 10")
    if args.max_related_articles_per_topic < 5:
        parser.error(
            "--max-related-articles-per-topic must be at least weekly minimum"
        )
    if not 1 <= args.max_summary_articles_per_topic <= 5:
        parser.error("--max-summary-articles-per-topic must be between 1 and 5")
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
    if args.summary_model not in SUPPORTED_SUMMARY_MODELS:
        parser.error(
            "--summary-model must be one of: "
            + ", ".join(sorted(SUPPORTED_SUMMARY_MODELS))
        )
    if (
        args.execute
        and args.use_summary_provider
        and not os.getenv("OPENAI_SUMMARY_API_KEY")
    ):
        parser.error("--use-summary-provider requires OPENAI_SUMMARY_API_KEY")
    if args.execute and not args.use_summary_provider:
        parser.error("--execute requires --use-summary-provider")
    return args


def build_pipeline(
    candidate_result,
    args,
    *,
    pipeline_context,
    summary_provider,
    repository=None,
    run_id=0,
    raw_state_loader=None,
    raw_text_loader=None,
    extraction_executor=None,
):
    """Materialized 후보로 선정부터 Summary와 선택적 원자 저장까지 실행한다.

    후보 조회 connection은 이 함수 호출 전에 반환되어야 한다. 원문 상태·본문
    loader, extractor, provider와 repository는 주입 가능해 테스트와 dry-run에서
    외부 부수 효과를 차단한다. 반환값은 실행 통계와 단계별 안전한 결과만
    포함한다.
    """

    pipeline_started_at = time.monotonic()
    topic_result = cluster_and_select_weekly_topics(
        candidate_result,
        pipeline_context=pipeline_context,
        similarity_threshold=args.similarity_threshold,
        max_topics=args.max_topics,
        max_related_articles_per_topic=args.max_related_articles_per_topic,
        max_summary_articles_per_topic=args.max_summary_articles_per_topic,
    )
    if args.execute:
        raw_states = (
            raw_state_loader(topic_result.summary_article_ids)
            if raw_state_loader is not None
            else {}
        )
        raw_result = acquire_weekly_topic_raw_texts(
            topic_result,
            raw_states,
            {},
            pipeline_context=pipeline_context,
            execute=True,
            extraction_limit=args.extraction_limit,
            extraction_executor=extraction_executor,
            raw_text_loader=raw_text_loader,
        )
        processing_result = summarize_and_persist_weekly_topics(
            topic_result,
            raw_result,
            pipeline_context=pipeline_context,
            summary_provider=summary_provider,
            repository=repository,
            run_id=run_id,
            execute=True,
            max_raw_chars_per_article=args.max_raw_chars_per_article,
        )
    else:
        raw_result = WeeklyRawAcquisitionResult(
            article_raw_texts={},
            reused_article_ids=[],
            extracted_article_ids=[],
            failed_article_ids=[],
            missing_article_ids=[],
            extraction_results=[],
        )
        processing_result = WeeklyTopicProcessingResult(
            topics=[],
            generated_topic_count=0,
            saved_topic_count=0,
            failed_topic_count=0,
            saved_topic_ids=[],
            failures=[],
            run_status="success",
        )
    analysis = _build_analysis(
        args,
        pipeline_context,
        candidate_result,
        topic_result,
        raw_result,
        processing_result,
        run_id=run_id,
        pipeline_started_at=pipeline_started_at,
    )
    return {
        "analysis": analysis,
        "missing_embeddings": candidate_result.missing_embeddings,
        "topic_failures": processing_result.failures,
        "saved_topic_ids": processing_result.saved_topic_ids,
    }


def load_candidates_for_context(engine, args, *, pipeline_context):
    """후보 조회 구간에만 read-only connection을 열고 결과를 materialize한다."""

    with engine.connect() as connection:
        connection.execute(text("set transaction read only"))
        return load_weekly_candidates(
            connection,
            pipeline_context=pipeline_context,
            max_articles=args.max_articles,
        )


def _build_analysis(
    args,
    pipeline_context,
    candidate_result,
    topic_result,
    raw_result,
    processing_result,
    *,
    run_id,
    pipeline_started_at,
):
    """단계 결과를 실행 계약의 count, week, window와 상태 필드로 합친다."""

    return {
        "dry_run": not args.execute,
        "execute_requested": args.execute,
        "week_start": pipeline_context.week_start,
        "week_end": pipeline_context.week_end,
        "window_start": pipeline_context.window_start,
        "window_end": pipeline_context.window_end,
        "window_days": pipeline_context.window_days,
        "window_source": pipeline_context.window_source,
        "candidate_count": candidate_result.candidate_count,
        "embedding_count": candidate_result.embedding_count,
        "missing_embedding_count": candidate_result.missing_embedding_count,
        "missing_embedding_reasons": candidate_result.missing_reason_counts,
        "clustering_input_count": candidate_result.embedding_count,
        "cluster_count": topic_result.cluster_count,
        "selected_topic_count": topic_result.selected_topic_count,
        "related_article_count": len(topic_result.related_article_ids),
        "summary_article_count": len(topic_result.summary_article_ids),
        "raw_reused_count": len(raw_result.reused_article_ids),
        "raw_extracted_count": len(raw_result.extracted_article_ids),
        "raw_failed_count": len(raw_result.failed_article_ids),
        "raw_missing_count": len(raw_result.missing_article_ids),
        "saved_topic_count": processing_result.saved_topic_count,
        "failed_topic_count": processing_result.failed_topic_count,
        "run_status": processing_result.run_status,
        "run_id": run_id if args.execute else None,
        "pipeline_elapsed_seconds": round(
            time.monotonic() - pipeline_started_at,
            6,
        ),
    }


def _parse_week_start(value: str) -> date:
    """CLI 날짜 문자열을 월요일 `date` 값으로 변환한다."""

    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "--week-start must be a valid YYYY-MM-DD date"
        ) from error
    if parsed.weekday() != 0:
        raise argparse.ArgumentTypeError("--week-start must be a Monday")
    return parsed


def _create_raw_state_loader(engine):
    """선택된 Summary 기사 ID의 원문 추출 상태를 read-only로 조회하는 함수를 만든다."""

    def load(article_ids):
        """요청된 기사 ID의 원문 존재 여부와 최근 추출 상태를 반환한다."""

        with engine.connect() as connection:
            connection.execute(text("set transaction read only"))
            return get_raw_extraction_states(connection, article_ids)

    return load


def _create_extraction_executor(args):
    """Execute 모드에서만 기존 selected article extractor를 지연 import한다."""

    if not args.execute:
        return None
    from scripts.extract_raw_articles import extract_selected_article_ids

    return extract_selected_article_ids


def _create_summary_provider(args):
    """Execute 설정에서만 OpenAI Weekly provider를 만들고 dry-run은 가짜 provider를 쓴다."""

    if not args.execute or not args.use_summary_provider:
        return DeterministicSummaryProvider()
    return WeeklyOpenAISummaryProvider(
        api_key=os.environ["OPENAI_SUMMARY_API_KEY"],
        model=args.summary_model,
    )


def _completion_from_analysis(analysis):
    """성공한 pipeline 분석 결과를 run 종료 model로 변환한다."""

    return WeeklyTopicRunCompletion(
        status=analysis["run_status"],
        candidate_count=analysis["candidate_count"],
        embedding_count=analysis["embedding_count"],
        missing_embedding_count=analysis["missing_embedding_count"],
        cluster_count=analysis["cluster_count"],
        selected_topic_count=analysis["selected_topic_count"],
        saved_topic_count=analysis["saved_topic_count"],
        failed_topic_count=analysis["failed_topic_count"],
    )


def _safe_error(error: Exception) -> str:
    """Run 이력과 로그에 남길 예외를 공백 정규화하고 최대 길이로 제한한다."""

    message = " ".join(str(error).split())
    rendered = f"{type(error).__name__}: {message}" if message else type(error).__name__
    return rendered[:1000]


def main():
    """로깅을 설정하고 CLI pipeline의 성공·실패 종료를 process 상태로 전달한다."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    LOGGER.info("weekly topic pipeline start")
    try:
        _run()
    except Exception:
        LOGGER.exception("weekly topic pipeline failed")
        raise
    LOGGER.info("weekly topic pipeline completion")


def _run():
    """Runtime dependency와 run 이력을 구성해 한 번의 Weekly pipeline을 실행한다."""

    args = parse_args()
    context = resolve_weekly_pipeline_context(week_start=args.week_start)
    engine = create_database_engine()
    repository = WeeklyTopicRepository(engine) if args.execute else None
    run_id = 0
    if repository is not None:
        run_id = repository.create_run(
            WeeklyTopicRunStart(
                week_start=context.week_start,
                week_end=context.week_end,
                window_start=context.window_start,
                window_end=context.window_end,
                started_at=context.started_at_utc,
            )
        )

    try:
        candidate_result = load_candidates_for_context(
            engine,
            args,
            pipeline_context=context,
        )
        result = build_pipeline(
            candidate_result,
            args,
            pipeline_context=context,
            summary_provider=_create_summary_provider(args),
            repository=repository,
            run_id=run_id,
            raw_state_loader=_create_raw_state_loader(engine),
            raw_text_loader=create_raw_text_loader(engine),
            extraction_executor=_create_extraction_executor(args),
        )
        if repository is not None:
            repository.finish_run(
                run_id,
                _completion_from_analysis(result["analysis"]),
            )
        _prewarm_weekly_home_topics_cache_after_success(engine, result, args)
    except Exception as error:
        if repository is not None:
            repository.finish_run(
                run_id,
                WeeklyTopicRunCompletion(
                    status="failed",
                    error_message=_safe_error(error),
                    finished_at=datetime.now(timezone.utc),
                ),
            )
        raise

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


def _prewarm_weekly_home_topics_cache_after_success(
    engine,
    result,
    args,
    *,
    cache=None,
):
    """Weekly Topic 저장과 run 종료 성공 이후 Home cache prewarm을 fail-open으로 실행한다.

    Dry-run 또는 publishable topic이 저장되지 않은 실행에서는 prewarm을 건너뛴다.
    Execute 모드에서 `saved_topic_count`가 1 이상이면 최신 run이 success 또는
    partial_success 상태로 종료된 뒤 새 read connection으로 Home payload를 읽고
    `weekly-topics:home:v1`을 overwrite한다. Redis 미설정, SET 실패, payload
    조회 실패는 warning이나 bypass log만 남기며 호출자에게 예외를 전파하지 않는다.
    """

    if not args.execute:
        LOGGER.info(
            "home_topics_cache event=bypass operation=prewarm key=weekly "
            "reason=dry_run"
        )
        return
    if result.get("analysis", {}).get("saved_topic_count", 0) < 1:
        LOGGER.info(
            "home_topics_cache event=bypass operation=prewarm key=weekly "
            "reason=no_publishable_result"
        )
        return

    try:
        cache = cache or get_weekly_home_topics_cache()
        prewarm_weekly_home_topics_cache(
            cache=cache,
            connection_factory=engine.connect,
        )
    except Exception as exc:  # noqa: BLE001 - prewarm must not fail the pipeline.
        LOGGER.warning(
            "home_topics_cache event=bypass operation=prewarm key=weekly error=%s",
            exc.__class__.__name__,
        )


if __name__ == "__main__":
    main()
