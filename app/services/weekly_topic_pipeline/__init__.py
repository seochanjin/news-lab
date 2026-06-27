"""7일 Topic pipeline의 주간 context, 후보 조회, 선정, 원문·요약 저장 계약을 공개한다.

현재 package는 완료된 월요일-일요일 주간을 한 번만 결정하는 context, 기존
article embedding을 read-only로 재사용하는 후보 stage, 저장용 불변 model과
repository, 선택 기사 원문 확보와 주간 흐름 Summary persistence helper를 제공한다.
Package import 과정에서 DB 연결, provider 호출, 파일 쓰기나 migration 적용은
수행하지 않는다.
"""

from .candidate_stage import load_weekly_candidates
from .context import resolve_weekly_pipeline_context
from .models import (
    WeeklyCandidateStageResult,
    WeeklyPipelineContext,
    WeeklyRawAcquisitionResult,
    WeeklyTopicArticleRecord,
    WeeklyTopicProcessingResult,
    WeeklyTopicRecord,
    WeeklyTopicRunCompletion,
    WeeklyTopicRunStart,
    WeeklyTopicSelectionResult,
    PUBLISHABLE_TOPIC_STATUSES,
    TOPIC_STATUSES,
)
from .raw_acquisition_stage import acquire_weekly_topic_raw_texts
from .repository import WeeklyTopicRepository
from .summary_persistence_stage import (
    PROMPT_VERSION,
    WeeklyOpenAISummaryProvider,
    build_weekly_summary_input,
    build_weekly_summary_input_hash,
    build_weekly_summary_prompt,
    summarize_and_persist_weekly_topics,
)
from .topic_selection_stage import cluster_and_select_weekly_topics

__all__ = [
    "PROMPT_VERSION",
    "PUBLISHABLE_TOPIC_STATUSES",
    "TOPIC_STATUSES",
    "WeeklyCandidateStageResult",
    "WeeklyOpenAISummaryProvider",
    "WeeklyPipelineContext",
    "WeeklyRawAcquisitionResult",
    "WeeklyTopicArticleRecord",
    "WeeklyTopicProcessingResult",
    "WeeklyTopicRecord",
    "WeeklyTopicRepository",
    "WeeklyTopicRunCompletion",
    "WeeklyTopicRunStart",
    "WeeklyTopicSelectionResult",
    "acquire_weekly_topic_raw_texts",
    "build_weekly_summary_input",
    "build_weekly_summary_input_hash",
    "build_weekly_summary_prompt",
    "cluster_and_select_weekly_topics",
    "load_weekly_candidates",
    "resolve_weekly_pipeline_context",
    "summarize_and_persist_weekly_topics",
]
