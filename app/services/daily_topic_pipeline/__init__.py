"""Daily topic pipeline stage contracts and implementations."""

from .context import BUSINESS_TIMEZONE, resolve_pipeline_context
from .embedding_stage import (
    acquire_pipeline_embeddings,
    prepare_article_embeddings,
)
from .models import (
    EmbeddingStageResult,
    PipelineContext,
    RawAcquisitionResult,
    TopicSaveResult,
    TopicSelectionResult,
)
from .raw_acquisition_stage import acquire_selected_article_raw_texts
from .reporting import render_report
from .runtime import (
    create_embedding_acquirer,
    create_raw_text_loader,
    create_save_executor,
)
from .summary_persistence_stage import summarize_and_save_topics
from .topic_selection_stage import (
    cluster_and_select_topics,
    public_topic,
    topic_selection_key,
)


__all__ = [
    "BUSINESS_TIMEZONE",
    "EmbeddingStageResult",
    "PipelineContext",
    "RawAcquisitionResult",
    "TopicSaveResult",
    "TopicSelectionResult",
    "acquire_pipeline_embeddings",
    "acquire_selected_article_raw_texts",
    "cluster_and_select_topics",
    "create_embedding_acquirer",
    "create_raw_text_loader",
    "create_save_executor",
    "prepare_article_embeddings",
    "public_topic",
    "render_report",
    "resolve_pipeline_context",
    "summarize_and_save_topics",
    "topic_selection_key",
]
