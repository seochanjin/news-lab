"""Runtime dependency adapters for the daily topic pipeline entrypoint."""

from sqlalchemy import text

from app.utils.article_embedding_storage import (
    DEFAULT_EMBEDDING_PROVIDER,
    DEFAULT_SOURCE_TEXT_TYPE,
    get_model_dimension,
    store_article_embedding,
)
from scripts.generate_topic_summary_report import get_raw_texts
from scripts.save_topic_summaries import execute_save_plan


def create_embedding_acquirer(engine, args, embedder):
    """기사별 embedding 저장소 접근 함수를 생성한다.

    Provider 모드가 아니면 별도 acquirer를 만들지 않는다. Execute 모드에서는
    기사마다 write transaction을 열어 vector를 생성·갱신하고, dry-run에서는
    read-only connection과 `persist=False`로 재사용 여부만 확인한다. 호출 예외는
    embedding stage에서 article 단위 실패로 격리된다.
    """

    if not args.use_embedding_provider:
        return None

    expected_dimension = get_model_dimension(embedder.model)

    def acquire(article):
        """한 기사의 embedding을 재사용하거나 생성해 `EmbeddingResult`를 반환한다."""

        if args.execute:
            with engine.begin() as connection:
                return store_article_embedding(
                    connection,
                    article=article,
                    embedding_provider=embedder,
                    provider=DEFAULT_EMBEDDING_PROVIDER,
                    source_text_type=DEFAULT_SOURCE_TEXT_TYPE,
                    expected_dimension=expected_dimension,
                )
        with engine.connect() as connection:
            connection.execute(text("set transaction read only"))
            return store_article_embedding(
                connection,
                article=article,
                embedding_provider=embedder,
                provider=DEFAULT_EMBEDDING_PROVIDER,
                source_text_type=DEFAULT_SOURCE_TEXT_TYPE,
                expected_dimension=expected_dimension,
                persist=False,
            )

    return acquire


def create_raw_text_loader(engine):
    """Selected article ID만 read-only connection으로 조회하는 loader를 만든다."""

    def load(article_ids):
        """요청된 article ID의 저장 원문 mapping을 반환한다."""

        with engine.connect() as connection:
            connection.execute(text("set transaction read only"))
            return get_raw_texts(connection, article_ids)

    return load


def create_save_executor(engine):
    """Topic save plan을 하나의 write transaction으로 실행하는 adapter를 만든다.

    Transaction 내부 저장 오류는 호출자에게 전파되어 부분 commit을 방지한다.
    실제 DB write는 execute 모드에서 이 adapter가 호출될 때만 발생한다.
    """

    def save(plan):
        """Topic과 topic_articles 저장 계획을 transaction 안에서 실행한다."""

        with engine.begin() as connection:
            return execute_save_plan(plan, connection)

    return save
