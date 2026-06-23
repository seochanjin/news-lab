"""3일 Topic 실행 이력과 활성 window 결과를 PostgreSQL에 저장한다.

Repository는 주입받은 SQLAlchemy engine으로 실행 이력 transaction과 결과 교체
transaction을 분리한다. 결과 교체 시 window advisory lock을 획득한 뒤 기존
Topic 삭제와 신규 Topic·기사 관계 삽입을 한 transaction에서 수행한다. 후보
조회, provider 호출, migration 적용은 담당하지 않는다.
"""

import json
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import text

from .models import (
    ThreeDayTopicRecord,
    ThreeDayTopicRunCompletion,
    ThreeDayTopicRunStart,
    _validate_window,
)


INSERT_RUN_QUERY = text("""
insert into three_day_topic_runs (
    reference_date,
    window_start,
    window_end,
    status,
    started_at
) values (
    :reference_date,
    :window_start,
    :window_end,
    'running',
    :started_at
)
returning id
""")

FINISH_RUN_QUERY = text("""
update three_day_topic_runs
set
    status = :status,
    candidate_count = :candidate_count,
    embedding_count = :embedding_count,
    missing_embedding_count = :missing_embedding_count,
    cluster_count = :cluster_count,
    selected_topic_count = :selected_topic_count,
    saved_topic_count = :saved_topic_count,
    failed_topic_count = :failed_topic_count,
    error_message = :error_message,
    finished_at = :finished_at
where id = :run_id
  and status = 'running'
""")

LOCK_WINDOW_QUERY = text("""
select pg_advisory_xact_lock(hashtextextended(:window_key, 0))
""")

DELETE_WINDOW_TOPICS_QUERY = text("""
delete from three_day_topics
where window_start = :window_start
  and window_end = :window_end
""")

INSERT_TOPIC_QUERY = text("""
insert into three_day_topics (
    run_id,
    reference_date,
    window_start,
    window_end,
    topic_candidate_id,
    title_ko,
    summary_ko,
    key_points,
    keywords,
    confidence,
    article_count,
    source_count,
    status,
    provider,
    model,
    prompt_version,
    summary_input_hash
) values (
    :run_id,
    :reference_date,
    :window_start,
    :window_end,
    :topic_candidate_id,
    :title_ko,
    :summary_ko,
    cast(:key_points as jsonb),
    cast(:keywords as jsonb),
    :confidence,
    :article_count,
    :source_count,
    :status,
    :provider,
    :model,
    :prompt_version,
    :summary_input_hash
)
returning id
""")

INSERT_TOPIC_ARTICLE_QUERY = text("""
insert into three_day_topic_articles (
    three_day_topic_id,
    article_id,
    rank,
    similarity,
    is_representative,
    is_summary_evidence
) values (
    :three_day_topic_id,
    :article_id,
    :rank,
    :similarity,
    :is_representative,
    :is_summary_evidence
)
""")


class ThreeDayTopicRepository:
    """Engine transaction을 사용해 3일 Topic run과 현재 결과 세대를 저장한다."""

    def __init__(self, engine) -> None:
        """SQLAlchemy 호환 `begin()`을 제공하는 engine을 보관한다."""

        self._engine = engine

    def create_run(self, run: ThreeDayTopicRunStart) -> int:
        """`running` 실행 이력을 별도 transaction으로 생성하고 ID를 반환한다."""

        with self._engine.begin() as connection:
            run_id = connection.execute(
                INSERT_RUN_QUERY,
                {
                    "reference_date": run.reference_date,
                    "window_start": run.window_start,
                    "window_end": run.window_end,
                    "started_at": run.started_at,
                },
            ).scalar_one()
        return int(run_id)

    def finish_run(
        self,
        run_id: int,
        completion: ThreeDayTopicRunCompletion,
    ) -> None:
        """`running` run을 최종 상태와 통계로 한 번만 종료한다.

        `finished_at`이 없으면 호출 시점 UTC를 사용한다. 대상 run이 없거나 이미
        종료되어 update되지 않으면 상태 덮어쓰기를 막기 위해 `ValueError`를
        발생시킨다.
        """

        if run_id < 1:
            raise ValueError("run_id must be positive")
        finished_at = completion.finished_at or datetime.now(timezone.utc)
        with self._engine.begin() as connection:
            result = connection.execute(
                FINISH_RUN_QUERY,
                {
                    "run_id": run_id,
                    "status": completion.status,
                    "candidate_count": completion.candidate_count,
                    "embedding_count": completion.embedding_count,
                    "missing_embedding_count": completion.missing_embedding_count,
                    "cluster_count": completion.cluster_count,
                    "selected_topic_count": completion.selected_topic_count,
                    "saved_topic_count": completion.saved_topic_count,
                    "failed_topic_count": completion.failed_topic_count,
                    "error_message": completion.error_message,
                    "finished_at": finished_at,
                },
            )
            if result.rowcount != 1:
                raise ValueError(f"running three-day topic run not found: {run_id}")

    def replace_window_topics(
        self,
        *,
        run_id: int,
        window_start: datetime,
        window_end: datetime,
        topics: Sequence[ThreeDayTopicRecord],
    ) -> list[int]:
        """동일 window의 기존 Topic을 신규 결과로 원자적으로 교체한다.

        모든 Topic model을 transaction 전에 검증하고, transaction 안에서는
        advisory lock, 기존 결과 삭제, Topic과 관계 삽입 순서를 지킨다. 빈
        `topics`도 정상 결과로 취급해 기존 window를 빈 결과로 교체한다.
        """

        if run_id < 1:
            raise ValueError("run_id must be positive")
        _validate_replacement_window(window_start, window_end, topics)
        window_key = _window_lock_key(window_start, window_end)
        topic_ids = []
        with self._engine.begin() as connection:
            connection.execute(LOCK_WINDOW_QUERY, {"window_key": window_key})
            connection.execute(
                DELETE_WINDOW_TOPICS_QUERY,
                {"window_start": window_start, "window_end": window_end},
            )
            for topic in topics:
                topic_id = int(
                    connection.execute(
                        INSERT_TOPIC_QUERY,
                        _topic_parameters(run_id, topic),
                    ).scalar_one()
                )
                topic_ids.append(topic_id)
                for article in topic.articles:
                    connection.execute(
                        INSERT_TOPIC_ARTICLE_QUERY,
                        {
                            "three_day_topic_id": topic_id,
                            "article_id": article.article_id,
                            "rank": article.rank,
                            "similarity": article.similarity,
                            "is_representative": article.is_representative,
                            "is_summary_evidence": article.is_summary_evidence,
                        },
                    )
        return topic_ids


def _validate_replacement_window(
    window_start: datetime,
    window_end: datetime,
    topics: Sequence[ThreeDayTopicRecord],
) -> None:
    """교체 window와 모든 Topic window가 같은 absolute instant인지 검증한다."""

    _validate_window(window_start, window_end)
    candidate_ids = [topic.topic_candidate_id for topic in topics]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("topic candidate IDs must be unique within a window")
    for topic in topics:
        if topic.window_start != window_start or topic.window_end != window_end:
            raise ValueError("all topics must use the replacement window")


def _window_lock_key(window_start: datetime, window_end: datetime) -> str:
    """PostgreSQL advisory lock hash 입력으로 사용할 안정적인 UTC window key를 만든다."""

    start_utc = window_start.astimezone(timezone.utc).isoformat()
    end_utc = window_end.astimezone(timezone.utc).isoformat()
    return f"three-day-topics:{start_utc}:{end_utc}"


def _topic_parameters(run_id: int, topic: ThreeDayTopicRecord) -> dict:
    """Topic insert query에 전달할 bind parameter와 JSON 문자열을 구성한다."""

    return {
        "run_id": run_id,
        "reference_date": topic.reference_date,
        "window_start": topic.window_start,
        "window_end": topic.window_end,
        "topic_candidate_id": topic.topic_candidate_id,
        "title_ko": topic.title_ko,
        "summary_ko": topic.summary_ko,
        "key_points": json.dumps(topic.key_points, ensure_ascii=False),
        "keywords": json.dumps(topic.keywords, ensure_ascii=False),
        "confidence": topic.confidence,
        "article_count": topic.article_count,
        "source_count": topic.source_count,
        "status": topic.status,
        "provider": topic.provider,
        "model": topic.model,
        "prompt_version": topic.prompt_version,
        "summary_input_hash": topic.summary_input_hash,
    }
