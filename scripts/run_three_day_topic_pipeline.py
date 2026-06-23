"""3일 Topic pipeline의 CLI 설정과 실행 단계, run 이력을 조정한다.

명시적인 72시간 context로 저장 article embedding 후보를 조회하고 재클러스터링한
뒤 선택 원문, 3일 Summary와 전용 repository 저장 단계를 순서대로 호출한다.
기본 실행은 dry-run이며 `--execute`에서만 run 이력, 지연 원문 추출과 Topic
결과 교체가 발생한다. 이 진입점은 신규 article embedding을 생성하지 않는다.
"""

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

from app.services.daily_topic_pipeline import create_raw_text_loader
from app.services.three_day_topic_pipeline import (
    ThreeDayOpenAISummaryProvider,
    ThreeDayTopicRepository,
    ThreeDayTopicRunCompletion,
    ThreeDayTopicRunStart,
    acquire_three_day_topic_raw_texts,
    cluster_and_select_three_day_topics,
    load_three_day_candidates,
    resolve_three_day_pipeline_context,
    summarize_and_persist_three_day_topics,
)
from app.utils.topic_summary import (
    DEFAULT_SUMMARY_MODEL,
    SUPPORTED_SUMMARY_MODELS,
    DeterministicSummaryProvider,
)
from scripts.analyze_raw_extraction_targets import get_raw_extraction_states
from scripts.analyze_topic_groups import create_database_engine


DEFAULT_MAX_ARTICLES = 500
DEFAULT_SIMILARITY_THRESHOLD = 0.70
DEFAULT_MAX_TOPICS = 5
DEFAULT_MAX_RELATED_ARTICLES_PER_TOPIC = 20
DEFAULT_MAX_SUMMARY_ARTICLES_PER_TOPIC = 3
DEFAULT_MAX_RAW_CHARS_PER_ARTICLE = 3000
DEFAULT_EXTRACTION_LIMIT = 5
LOGGER = logging.getLogger(__name__)


def parse_args(argv=None):
    """3일 전용 CLI 인자를 읽고 window, 상한과 Summary provider 조건을 검증한다."""

    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Recent-72-hour topic pipeline (dry-run by default).",
    )
    parser.add_argument(
        "--window-end",
        type=_parse_window_end,
        help="재현 실행용 timezone-aware ISO 8601 종료 시각",
    )
    parser.add_argument("--window-hours", type=int, choices=(72,), default=72)
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
    if args.max_related_articles_per_topic < 1:
        parser.error("--max-related-articles-per-topic must be positive")
    if args.max_summary_articles_per_topic < 1:
        parser.error("--max-summary-articles-per-topic must be positive")
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
    if args.use_summary_provider and not os.getenv("OPENAI_SUMMARY_API_KEY"):
        parser.error("--use-summary-provider requires OPENAI_SUMMARY_API_KEY")
    if args.execute and not args.use_summary_provider:
        parser.error("--execute requires --use-summary-provider")
    return args


def build_pipeline(
    connection,
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
    """한 context로 후보 조회부터 Summary와 선택적 원자 저장까지 실행한다.

    Connection은 후보와 저장 embedding 조회에만 사용한다. 원문 상태·본문 loader,
    extractor, provider와 repository는 주입 가능해 테스트와 dry-run에서 외부
    부수 효과를 차단한다. 반환값은 실행 통계와 단계별 안전한 결과만 포함한다.
    """

    pipeline_started_at = time.monotonic()
    candidate_result = load_three_day_candidates(
        connection,
        pipeline_context=pipeline_context,
        max_articles=args.max_articles,
    )
    topic_result = cluster_and_select_three_day_topics(
        candidate_result,
        pipeline_context=pipeline_context,
        similarity_threshold=args.similarity_threshold,
        max_topics=args.max_topics,
        max_related_articles_per_topic=args.max_related_articles_per_topic,
        max_summary_articles_per_topic=args.max_summary_articles_per_topic,
    )
    raw_states = (
        raw_state_loader(topic_result.summary_article_ids)
        if raw_state_loader is not None
        else {}
    )
    raw_result = acquire_three_day_topic_raw_texts(
        topic_result,
        raw_states,
        {},
        pipeline_context=pipeline_context,
        execute=args.execute,
        extraction_limit=args.extraction_limit,
        extraction_executor=extraction_executor,
        raw_text_loader=raw_text_loader,
    )
    processing_result = summarize_and_persist_three_day_topics(
        topic_result,
        raw_result,
        pipeline_context=pipeline_context,
        summary_provider=summary_provider,
        repository=repository,
        run_id=run_id,
        execute=args.execute,
        max_raw_chars_per_article=args.max_raw_chars_per_article,
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
    """단계 결과를 실행 계약의 count, window와 상태 필드로 합친다."""

    return {
        "dry_run": not args.execute,
        "execute_requested": args.execute,
        "reference_date": pipeline_context.reference_date,
        "window_start": pipeline_context.window_start,
        "window_end": pipeline_context.window_end,
        "window_hours": pipeline_context.window_hours,
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


def _parse_window_end(value: str) -> datetime:
    """CLI ISO 8601 문자열을 timezone-aware datetime으로 변환한다."""

    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "--window-end must be a valid ISO 8601 datetime"
        ) from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("--window-end must include a timezone")
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
    """CLI 설정에 따라 dry-run deterministic 또는 OpenAI 3일 provider를 만든다."""

    if not args.use_summary_provider:
        return DeterministicSummaryProvider()
    return ThreeDayOpenAISummaryProvider(
        api_key=os.environ["OPENAI_SUMMARY_API_KEY"],
        model=args.summary_model,
    )


def _completion_from_analysis(analysis):
    """성공한 pipeline 분석 결과를 run 종료 model로 변환한다."""

    return ThreeDayTopicRunCompletion(
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
    LOGGER.info("three-day topic pipeline start")
    try:
        _run()
    except Exception:
        LOGGER.exception("three-day topic pipeline failed")
        raise
    LOGGER.info("three-day topic pipeline completion")


def _run():
    """Runtime dependency와 run 이력을 구성해 한 번의 3일 pipeline을 실행한다."""

    args = parse_args()
    context = resolve_three_day_pipeline_context(window_end=args.window_end)
    engine = create_database_engine()
    repository = ThreeDayTopicRepository(engine) if args.execute else None
    run_id = 0
    if repository is not None:
        run_id = repository.create_run(
            ThreeDayTopicRunStart(
                reference_date=context.reference_date,
                window_start=context.window_start,
                window_end=context.window_end,
                started_at=context.started_at_utc,
            )
        )

    try:
        with engine.connect() as connection:
            connection.execute(text("set transaction read only"))
            result = build_pipeline(
                connection,
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
    except Exception as error:
        if repository is not None:
            repository.finish_run(
                run_id,
                ThreeDayTopicRunCompletion(
                    status="failed",
                    error_message=_safe_error(error),
                    finished_at=datetime.now(timezone.utc),
                ),
            )
        raise

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
