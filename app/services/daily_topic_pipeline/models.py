"""Daily topic pipeline 단계 사이에서 전달하는 불변 결과 계약을 정의한다.

각 dataclass는 단계별 정상 결과와 실패 통계를 다음 단계에 전달한다. 이 모듈은
기사 선정, provider 호출, 파일 또는 DB 쓰기를 수행하지 않으며 집합 관계처럼
단계 경계에서 반드시 지켜야 하는 계약만 검증한다.
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any


@dataclass(frozen=True)
class PipelineContext:
    """한 번의 pipeline 실행에서 모든 단계가 공유하는 날짜와 시작 시각이다.

    `pipeline_date`는 `business_timezone` 기준으로 한 번만 결정되며 기사 처리
    단계와 최종 topic 저장이 같은 업무 날짜를 사용하도록 전달된다.
    """

    pipeline_date: date
    business_timezone: str
    started_at_utc: datetime
    started_at_local: datetime
    pipeline_date_source: str


@dataclass(frozen=True)
class EmbeddingStageResult:
    """Embedding 준비 단계의 정상 기사·vector 대응 관계와 처리 통계다.

    `articles_with_embeddings`의 각 tuple은 clustering에 함께 전달되는 기사와
    vector를 묶어 순서 불일치를 방지한다. 기사 단위 실패는 ID와 안전한 오류
    정보로 분리되며 반환 계약 위반은 이 결과가 생성되기 전에 stage 오류로
    전파된다.
    """

    articles_with_embeddings: list[tuple[dict, Any]]
    failed_article_ids: list[int]
    created_count: int
    updated_count: int
    reused_count: int
    failed_count: int
    failures: list[dict]

    @property
    def articles(self):
        return [article for article, _embedding in self.articles_with_embeddings]

    @property
    def embeddings(self):
        return [embedding for _article, embedding in self.articles_with_embeddings]


@dataclass(frozen=True)
class TopicSelectionResult:
    """Clustering과 topic 선정 단계가 다음 단계에 전달하는 선택 결과다.

    `related_article_ids`는 Topic 관계로 유지할 기사 집합이고
    `summary_article_ids`는 원문 확보와 Summary 입력에 사용할 부분집합이다.
    두 집합은 같을 수 있다. Reference topic은 보고용이며 원문 추출, summary
    생성, 저장 대상에 포함되지 않는다. 잘못된 부분집합 관계는 생성 시 즉시
    차단한다.
    """

    selected_topics: list[dict]
    reference_topics: list[dict]
    representative_article_ids: list[int]
    related_article_ids: list[int]
    summary_article_ids: list[int]
    cluster_count: int
    selected_topic_count: int
    topic_candidate_count: int

    def __post_init__(self):
        """Summary 및 대표 기사 집합이 관련 기사 집합을 벗어나지 않게 검증한다."""

        related_ids = set(self.related_article_ids)
        summary_ids = set(self.summary_article_ids)
        representative_ids = set(self.representative_article_ids)
        if not summary_ids.issubset(related_ids):
            raise ValueError("summary articles must be a subset of related articles")
        if not representative_ids.issubset(summary_ids):
            raise ValueError(
                "representative articles must be included in summary articles"
            )

    @property
    def selected_article_ids(self):
        """기존 원문·Summary 단계가 사용하는 Summary 기사 ID alias를 반환한다."""

        return self.summary_article_ids


@dataclass(frozen=True)
class RawAcquisitionResult:
    """Selected article의 원문 확보 결과와 article 단위 상태다.

    저장 원문 재사용, 신규 추출, 실패, 최종 누락을 분리해 기록한다.
    `article_raw_texts`와 `summary_ready_topics`는 summary 단계의 입력이며,
    단일 기사 추출 실패는 다른 기사의 원문 사용을 막지 않는다.
    """

    article_raw_texts: dict[int, str]
    reused_article_ids: list[int]
    extracted_article_ids: list[int]
    failed_article_ids: list[int]
    missing_article_ids: list[int]
    summary_ready_topics: list[dict]
    extraction_results: list[dict]


@dataclass(frozen=True)
class TopicSaveResult:
    """Topic summary 생성과 저장 단계의 결과 및 topic 단위 통계다.

    생성된 summary와 save plan, 실제 저장된 topic ID를 함께 제공한다.
    원문 부족 topic은 skipped로, provider 처리 실패는 failed로 구분해
    다른 topic의 summary 생성과 저장을 계속할 수 있게 한다.
    """

    summaries: list[dict]
    save_plan: dict
    generated_topic_count: int
    saved_topic_count: int
    skipped_topic_count: int
    failed_topic_count: int
    saved_topic_ids: list[int]
    failures: list[dict]
