"""3일 Topic pipeline의 기간 전용 저장 계약을 제공한다.

현재 package는 공통 72시간 context, 저장 article embedding 후보 조회,
재클러스터링·기사 선정, 선택 원문 확보와 Topic별 Summary·저장 계약을 공개한다.
package 초기화 과정에서는 DB 연결, provider 호출이나 쓰기를 수행하지 않는다.
"""

from .candidate_stage import load_three_day_candidates
from .context import resolve_three_day_pipeline_context
from .models import (
    ThreeDayCandidateStageResult,
    ThreeDayPipelineContext,
    ThreeDayRawAcquisitionResult,
    ThreeDayTopicSelectionResult,
    ThreeDayTopicArticleRecord,
    ThreeDayTopicProcessingResult,
    ThreeDayTopicRecord,
    ThreeDayTopicRunCompletion,
    ThreeDayTopicRunStart,
)
from .repository import ThreeDayTopicRepository
from .raw_acquisition_stage import acquire_three_day_topic_raw_texts
from .summary_persistence_stage import (
    PROMPT_VERSION,
    ThreeDayOpenAISummaryProvider,
    build_three_day_summary_input,
    build_three_day_summary_input_hash,
    build_three_day_summary_prompt,
    summarize_and_persist_three_day_topics,
)
from .topic_selection_stage import cluster_and_select_three_day_topics

__all__ = [
    "ThreeDayCandidateStageResult",
    "ThreeDayPipelineContext",
    "ThreeDayOpenAISummaryProvider",
    "ThreeDayRawAcquisitionResult",
    "ThreeDayTopicArticleRecord",
    "ThreeDayTopicProcessingResult",
    "ThreeDayTopicRecord",
    "ThreeDayTopicRepository",
    "ThreeDayTopicRunCompletion",
    "ThreeDayTopicRunStart",
    "ThreeDayTopicSelectionResult",
    "PROMPT_VERSION",
    "acquire_three_day_topic_raw_texts",
    "build_three_day_summary_input",
    "build_three_day_summary_input_hash",
    "build_three_day_summary_prompt",
    "cluster_and_select_three_day_topics",
    "load_three_day_candidates",
    "resolve_three_day_pipeline_context",
    "summarize_and_persist_three_day_topics",
]
