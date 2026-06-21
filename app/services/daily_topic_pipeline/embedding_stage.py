"""Article candidate preparation and embedding acquisition stage."""

import logging

from app.utils.article_embedding_storage import EmbeddingResult
from scripts.analyze_topic_groups import prepare_articles

from .errors import safe_error
from .models import EmbeddingStageResult, PipelineContext


LOGGER = logging.getLogger(__name__)


def prepare_article_embeddings(
    rows,
    args,
    *,
    pipeline_context: PipelineContext,
    embedding_provider,
    embedding_acquirer=None,
):
    """기사 후보를 정규화하고 clustering에 사용할 embedding을 준비한다.

    저장소 연동 acquirer가 있으면 동일 source hash의 vector를 재사용하고,
    없거나 입력이 변경된 기사만 생성·갱신한다. 기사 단위 provider·저장 실패는
    격리하지만 반환 타입, status, vector 계약 위반은 stage 오류로 전파한다.

    Returns:
        정상 기사와 vector의 대응 관계 및 created, updated, reused, failed
        통계를 포함한 `EmbeddingStageResult`.
    """

    LOGGER.info(
        "embedding stage start: pipeline_date=%s",
        pipeline_context.pipeline_date,
    )
    articles = prepare_articles(rows)
    LOGGER.info(
        "embedding provider start: provider=%s model=%s article_count=%d",
        "openai" if args.use_embedding_provider else "deterministic",
        embedding_provider.model,
        len(articles),
    )
    (
        clustering_articles,
        embeddings,
        embedding_stats,
        embedding_failures,
    ) = acquire_pipeline_embeddings(
        articles,
        embedding_provider,
        embedding_acquirer=embedding_acquirer,
    )
    LOGGER.info(
        "embedding provider end: provider=%s model=%s embedding_count=%d "
        "created=%d updated=%d reused=%d failed=%d",
        "openai" if args.use_embedding_provider else "deterministic",
        embedding_provider.model,
        len(embeddings),
        embedding_stats["created"],
        embedding_stats["updated"],
        embedding_stats["reused"],
        embedding_stats["failed"],
    )
    return EmbeddingStageResult(
        articles_with_embeddings=list(zip(clustering_articles, embeddings)),
        failed_article_ids=[
            failure["article_id"] for failure in embedding_failures
        ],
        created_count=embedding_stats["created"],
        updated_count=embedding_stats["updated"],
        reused_count=embedding_stats["reused"],
        failed_count=embedding_stats["failed"],
        failures=embedding_failures,
    )


def acquire_pipeline_embeddings(
    articles,
    embedding_provider,
    *,
    embedding_acquirer=None,
):
    """기사 순서를 유지하며 vector를 수집하고 article 단위 실패를 격리한다.

    Acquirer 호출 예외는 해당 기사만 실패 처리한다. 반면 acquirer의 반환 타입,
    status 또는 vector가 계약과 다르면 내부 구현 오류로 간주해 즉시 실패한다.
    Deterministic provider 경로에서도 기사 수와 vector 수가 다르면 fail-fast한다.
    """

    if embedding_acquirer is None:
        embeddings = embedding_provider.embed(
            [article["embedding_input"] for article in articles]
        )
        if len(articles) != len(embeddings):
            raise ValueError("articles and embeddings must have the same length")
        return (
            articles,
            embeddings,
            {
                "created": len(embeddings),
                "updated": 0,
                "reused": 0,
                "failed": 0,
            },
            [],
        )

    clustering_articles = []
    embeddings = []
    stats = {"created": 0, "updated": 0, "reused": 0, "failed": 0}
    failures = []
    for article in articles:
        try:
            result = embedding_acquirer(article)
        except Exception as error:
            stats["failed"] += 1
            failure = {
                "article_id": article.get("id"),
                "error": safe_error(error),
            }
            failures.append(failure)
            LOGGER.warning(
                "article embedding failed: article_id=%s error=%s",
                failure["article_id"],
                failure["error"],
            )
            continue

        if not isinstance(result, EmbeddingResult):
            raise TypeError("embedding acquirer returned an invalid result")
        if result.status not in {"created", "updated", "reused"}:
            raise ValueError(f"unsupported embedding status: {result.status}")
        if result.embedding is None:
            raise ValueError("embedding result does not include a vector")

        clustering_articles.append(article)
        embeddings.append(result.embedding)
        stats[result.status] += 1
    return clustering_articles, embeddings, stats, failures
