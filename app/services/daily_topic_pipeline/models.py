"""Data contracts passed between daily topic pipeline stages."""

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

    선택된 topic 및 대표·관련 기사 ID는 원문 확보 대상의 경계를 정의한다.
    Reference topic은 보고용이며 원문 추출, summary 생성, 저장 대상에 포함되지
    않는다.
    """

    selected_topics: list[dict]
    reference_topics: list[dict]
    representative_article_ids: list[int]
    related_article_ids: list[int]
    selected_article_ids: list[int]
    cluster_count: int
    selected_topic_count: int
    topic_candidate_count: int


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
