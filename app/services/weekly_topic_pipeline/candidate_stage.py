"""직전 완료 주간 기사와 기존 article embedding을 read-only로 결합한다.

Weekly context의 명시적 월요일-월요일 window와 주간 전용 기사 상한으로 후보를
먼저 결정한 뒤 저장된 embedding metadata, source hash와 vector를 검증한다.
유효한 vector만 7일 재클러스터링 입력으로 반환하고 누락·불일치는 사유별로
제외한다. Provider 호출과 DB 쓰기는 수행하지 않는다.
"""

import logging

from app.services.topic_pipeline.candidate_stage import (
    load_stored_embedding_candidates,
)
from app.utils.article_embedding_storage import (
    DEFAULT_EMBEDDING_DIMENSION,
    DEFAULT_EMBEDDING_PROVIDER,
    DEFAULT_SOURCE_TEXT_TYPE,
)
from app.utils.article_embeddings import DEFAULT_EMBEDDING_MODEL

from .models import WeeklyCandidateStageResult, WeeklyPipelineContext


LOGGER = logging.getLogger(__name__)


def load_weekly_candidates(
    connection,
    *,
    pipeline_context: WeeklyPipelineContext,
    max_articles: int,
    provider: str = DEFAULT_EMBEDDING_PROVIDER,
    model: str = DEFAULT_EMBEDDING_MODEL,
    dimension: int = DEFAULT_EMBEDDING_DIMENSION,
    source_text_type: str = DEFAULT_SOURCE_TEXT_TYPE,
) -> WeeklyCandidateStageResult:
    """주간 window 후보를 조회하고 호환되는 기존 embedding만 순서대로 재사용한다.

    Args:
        connection: SQLAlchemy 호환 read connection.
        pipeline_context: 실행 전체에서 공유하는 완료 주간 절대 범위.
        max_articles: 결정론적 정렬 뒤 조회할 최대 기사 수.
        provider/model/dimension/source_text_type: 허용할 저장 embedding 계약.

    Returns:
        검증된 기사·vector 쌍과 기사별 안전한 누락 사유.

    Raises:
        ValueError: 기사 상한이나 embedding 설정이 유효하지 않은 경우.
    """

    result = load_stored_embedding_candidates(
        connection,
        window_start=pipeline_context.window_start,
        window_end=pipeline_context.window_end,
        max_articles=max_articles,
        result_factory=WeeklyCandidateStageResult,
        provider=provider,
        model=model,
        dimension=dimension,
        source_text_type=source_text_type,
    )
    LOGGER.info(
        "weekly candidate stage: week_start=%s week_end=%s window_start=%s "
        "window_end=%s candidate_count=%d embedding_count=%d "
        "missing_embedding_count=%d missing_reasons=%s",
        pipeline_context.week_start.isoformat(),
        pipeline_context.week_end.isoformat(),
        pipeline_context.window_start.isoformat(),
        pipeline_context.window_end.isoformat(),
        result.candidate_count,
        result.embedding_count,
        result.missing_embedding_count,
        result.missing_reason_counts,
    )
    return result

