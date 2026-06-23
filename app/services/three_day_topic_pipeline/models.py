"""3일 Topic 실행 이력과 원자적 결과 교체에 필요한 저장 model을 정의한다.

Pipeline의 처리 단계가 만든 primitive 값을 불변 dataclass로 받아 repository에
전달한다. 이 모듈은 DB를 조회하거나 수정하지 않으며, window 일치와 대표·요약
근거 기사 관계처럼 transaction 시작 전에 확인 가능한 저장 계약을 검증한다.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo


RUN_FINAL_STATUSES = frozenset({"success", "partial_success", "failed"})
THREE_DAY_WINDOW = timedelta(hours=72)
BUSINESS_TIMEZONE = ZoneInfo("Asia/Seoul")


@dataclass(frozen=True)
class ThreeDayPipelineContext:
    """한 실행에서 공유할 서울 기준일과 정확한 72시간 조회 범위를 보관한다."""

    reference_date: date
    business_timezone: str
    started_at_utc: datetime
    started_at_local: datetime
    window_start: datetime
    window_end: datetime
    window_hours: int
    window_source: str

    def __post_init__(self) -> None:
        """Context의 시각, 72시간 범위와 서울 기준일 계약을 검증한다."""

        _require_aware(self.started_at_utc, "started_at_utc")
        _require_aware(self.started_at_local, "started_at_local")
        _validate_window(self.window_start, self.window_end)
        _validate_reference_date(self.reference_date, self.window_end)
        if self.window_hours != 72:
            raise ValueError("three-day pipeline window_hours must be 72")
        if not self.business_timezone.strip():
            raise ValueError("business_timezone must not be blank")
        if not self.window_source.strip():
            raise ValueError("window_source must not be blank")


@dataclass(frozen=True)
class ThreeDayCandidateStageResult:
    """저장 embedding이 검증된 clustering 입력과 기사별 누락 사유를 보관한다."""

    articles_with_embeddings: list[tuple[dict, tuple[float, ...]]]
    missing_embeddings: list[dict]

    def __post_init__(self) -> None:
        """후보 기사 ID가 정상·누락 결과 사이에서 중복되지 않는지 확인한다."""

        embedded_ids = [
            int(article["id"]) for article, _embedding in self.articles_with_embeddings
        ]
        missing_ids = [int(item["article_id"]) for item in self.missing_embeddings]
        all_ids = embedded_ids + missing_ids
        if len(all_ids) != len(set(all_ids)):
            raise ValueError("candidate article IDs must be unique")

    @property
    def articles(self) -> list[dict]:
        """Clustering 입력 기사만 저장 vector와 같은 순서로 반환한다."""

        return [article for article, _embedding in self.articles_with_embeddings]

    @property
    def embeddings(self) -> list[tuple[float, ...]]:
        """검증된 저장 vector만 기사와 같은 순서로 반환한다."""

        return [embedding for _article, embedding in self.articles_with_embeddings]

    @property
    def candidate_count(self) -> int:
        """Window와 기사 상한을 통과한 전체 후보 수를 반환한다."""

        return len(self.articles_with_embeddings) + len(self.missing_embeddings)

    @property
    def embedding_count(self) -> int:
        """Clustering에 재사용할 수 있는 저장 embedding 수를 반환한다."""

        return len(self.articles_with_embeddings)

    @property
    def missing_embedding_count(self) -> int:
        """저장 embedding을 재사용하지 못해 제외된 기사 수를 반환한다."""

        return len(self.missing_embeddings)

    @property
    def missing_reason_counts(self) -> dict[str, int]:
        """로그와 실행 통계에 사용할 누락 사유별 건수를 반환한다."""

        counts: dict[str, int] = {}
        for item in self.missing_embeddings:
            reason = str(item["reason"])
            counts[reason] = counts.get(reason, 0) + 1
        return counts


@dataclass(frozen=True)
class ThreeDayTopicSelectionResult:
    """3일 재클러스터링 결과와 대표·관련·Summary 근거 기사 집합을 보관한다."""

    selected_topics: list[dict]
    representative_article_ids: list[int]
    related_article_ids: list[int]
    summary_article_ids: list[int]
    cluster_count: int
    topic_candidate_count: int

    def __post_init__(self) -> None:
        """기사 집합 부분관계, count와 선택 Topic 수의 일관성을 검증한다."""

        related_ids = set(self.related_article_ids)
        summary_ids = set(self.summary_article_ids)
        representative_ids = set(self.representative_article_ids)
        if len(self.related_article_ids) != len(related_ids):
            raise ValueError("related article IDs must be unique")
        if len(self.summary_article_ids) != len(summary_ids):
            raise ValueError("summary article IDs must be unique")
        if len(self.representative_article_ids) != len(representative_ids):
            raise ValueError("representative article IDs must be unique")
        if not summary_ids.issubset(related_ids):
            raise ValueError("summary articles must be a subset of related articles")
        if not representative_ids.issubset(summary_ids):
            raise ValueError(
                "representative articles must be included in summary articles"
            )
        if self.cluster_count < 0 or self.topic_candidate_count < 0:
            raise ValueError("topic selection counts must be non-negative")
        if self.topic_candidate_count > self.cluster_count:
            raise ValueError("topic_candidate_count cannot exceed cluster_count")
        if len(self.selected_topics) > self.topic_candidate_count:
            raise ValueError("selected topic count cannot exceed candidate count")

    @property
    def selected_topic_count(self) -> int:
        """최대 Topic 상한 적용 후 실제 선택된 Topic 수를 반환한다."""

        return len(self.selected_topics)

    @property
    def selected_article_ids(self) -> list[int]:
        """후속 원문 확보 단계가 사용할 Summary 근거 기사 ID를 반환한다."""

        return self.summary_article_ids


@dataclass(frozen=True)
class ThreeDayRawAcquisitionResult:
    """Summary 근거 기사에 한정한 원문 확보 결과와 기사별 상태를 보관한다."""

    article_raw_texts: dict[int, str]
    reused_article_ids: list[int]
    extracted_article_ids: list[int]
    failed_article_ids: list[int]
    missing_article_ids: list[int]
    extraction_results: list[dict]


@dataclass(frozen=True)
class ThreeDayTopicProcessingResult:
    """Topic별 Summary 생성·실패 격리와 window 저장 결과를 보관한다."""

    topics: list["ThreeDayTopicRecord"]
    generated_topic_count: int
    saved_topic_count: int
    failed_topic_count: int
    saved_topic_ids: list[int]
    failures: list[dict]
    run_status: str

    def __post_init__(self) -> None:
        """처리 count와 최종 run 상태가 결과 목록과 일치하는지 검증한다."""

        if self.generated_topic_count != len(self.topics):
            raise ValueError("generated_topic_count must match topics")
        if self.saved_topic_count != len(self.saved_topic_ids):
            raise ValueError("saved_topic_count must match saved_topic_ids")
        if self.failed_topic_count != len(self.failures):
            raise ValueError("failed_topic_count must match failures")
        if self.run_status not in RUN_FINAL_STATUSES:
            raise ValueError(f"unsupported final run status: {self.run_status}")


def _require_aware(value: datetime, field_name: str) -> None:
    """저장할 시각이 absolute instant를 표현하는 timezone-aware 값인지 확인한다."""

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


def _validate_window(window_start: datetime, window_end: datetime) -> None:
    """공통 window가 timezone-aware인 정확한 72시간 범위인지 확인한다."""

    _require_aware(window_start, "window_start")
    _require_aware(window_end, "window_end")
    if window_start >= window_end:
        raise ValueError("window_start must be earlier than window_end")
    if window_end - window_start != THREE_DAY_WINDOW:
        raise ValueError("three-day topic window must be exactly 72 hours")


def _validate_reference_date(reference_date: date, window_end: datetime) -> None:
    """기준일이 window 종료 instant의 서울 local 날짜와 같은지 확인한다."""

    expected_date = window_end.astimezone(BUSINESS_TIMEZONE).date()
    if reference_date != expected_date:
        raise ValueError(
            "reference_date must match the Asia/Seoul date of window_end"
        )


@dataclass(frozen=True)
class ThreeDayTopicRunStart:
    """새 실행 이력 row를 만들 때 고정하는 날짜, window와 시작 시각이다."""

    reference_date: date
    window_start: datetime
    window_end: datetime
    started_at: datetime

    def __post_init__(self) -> None:
        """실행 시작 전에 window와 시작 시각이 timezone-aware인지 검증한다."""

        _validate_window(self.window_start, self.window_end)
        _validate_reference_date(self.reference_date, self.window_end)
        _require_aware(self.started_at, "started_at")


@dataclass(frozen=True)
class ThreeDayTopicRunCompletion:
    """실행 종료 시 기록할 최종 상태, 단계별 count와 안전한 오류 메시지다."""

    status: str
    candidate_count: int = 0
    embedding_count: int = 0
    missing_embedding_count: int = 0
    cluster_count: int = 0
    selected_topic_count: int = 0
    saved_topic_count: int = 0
    failed_topic_count: int = 0
    error_message: str | None = None
    finished_at: datetime | None = None

    def __post_init__(self) -> None:
        """종료 상태, count 관계와 종료 시각을 repository 호출 전에 검증한다."""

        if self.status not in RUN_FINAL_STATUSES:
            raise ValueError(f"unsupported final run status: {self.status}")
        counts = (
            self.candidate_count,
            self.embedding_count,
            self.missing_embedding_count,
            self.cluster_count,
            self.selected_topic_count,
            self.saved_topic_count,
            self.failed_topic_count,
        )
        if any(value < 0 for value in counts):
            raise ValueError("run counts must be non-negative")
        if self.candidate_count != (
            self.embedding_count + self.missing_embedding_count
        ):
            raise ValueError(
                "candidate_count must equal embedding_count + "
                "missing_embedding_count"
            )
        if self.saved_topic_count > self.selected_topic_count:
            raise ValueError("saved_topic_count cannot exceed selected_topic_count")
        if self.finished_at is not None:
            _require_aware(self.finished_at, "finished_at")
        if self.error_message is not None and len(self.error_message) > 1000:
            raise ValueError("error_message must be at most 1000 characters")


@dataclass(frozen=True)
class ThreeDayTopicArticleRecord:
    """한 Topic에 연결할 관련 기사 순서와 대표·Summary 근거 역할을 보관한다."""

    article_id: int
    rank: int
    similarity: float | None
    is_representative: bool
    is_summary_evidence: bool

    def __post_init__(self) -> None:
        """양수 ID·rank와 대표 기사의 Summary 근거 포함 계약을 검증한다."""

        if self.article_id < 1:
            raise ValueError("article_id must be positive")
        if self.rank < 1:
            raise ValueError("rank must be at least 1")
        if self.is_representative and not self.is_summary_evidence:
            raise ValueError("representative article must be summary evidence")


@dataclass(frozen=True)
class ThreeDayTopicRecord:
    """저장 가능한 3일 Topic metadata와 관련 기사 전체를 표현한다."""

    topic_candidate_id: str
    reference_date: date
    window_start: datetime
    window_end: datetime
    title_ko: str
    summary_ko: str
    key_points: list[Any]
    keywords: list[str]
    confidence: float
    source_count: int
    status: str
    provider: str
    model: str
    prompt_version: str
    summary_input_hash: str
    articles: list[ThreeDayTopicArticleRecord] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Window, 필수 문자열, 기사 중복과 대표 기사 단일성 계약을 검증한다."""

        _validate_window(self.window_start, self.window_end)
        _validate_reference_date(self.reference_date, self.window_end)
        required_text = {
            "topic_candidate_id": self.topic_candidate_id,
            "title_ko": self.title_ko,
            "summary_ko": self.summary_ko,
            "status": self.status,
            "provider": self.provider,
            "model": self.model,
            "prompt_version": self.prompt_version,
            "summary_input_hash": self.summary_input_hash,
        }
        for field_name, value in required_text.items():
            if not value.strip():
                raise ValueError(f"{field_name} must not be blank")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        if self.source_count < 0:
            raise ValueError("source_count must be non-negative")
        if self.source_count > len(self.articles):
            raise ValueError("source_count cannot exceed article_count")

        article_ids = [article.article_id for article in self.articles]
        ranks = [article.rank for article in self.articles]
        if len(article_ids) != len(set(article_ids)):
            raise ValueError("topic article IDs must be unique")
        if len(ranks) != len(set(ranks)):
            raise ValueError("topic article ranks must be unique")
        if sorted(ranks) != list(range(1, len(ranks) + 1)):
            raise ValueError("topic article ranks must be contiguous from 1")
        representative_count = sum(
            article.is_representative for article in self.articles
        )
        if representative_count != 1:
            raise ValueError("topic must have exactly one representative article")

    @property
    def article_count(self) -> int:
        """중복 검증이 끝난 관련 기사 수를 Topic 저장 count로 반환한다."""

        return len(self.articles)
