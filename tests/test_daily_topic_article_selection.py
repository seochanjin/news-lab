"""Daily topic의 관련 기사·Summary 기사 선정과 원문 대상 분리를 검증한다.

실제 provider, DB, 네트워크는 호출하지 않고 stage 함수에 메모리 입력과 mock
extractor를 주입한다. 관련 기사 상한, 결정론적 Summary 부분집합, 대표 기사와
source 다양성, 중복 제외, 기존 원문 재사용 및 기사별 실패 격리의 회귀를
검증한다.
"""

import unittest
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

from app.services.daily_topic_pipeline.models import (
    EmbeddingStageResult,
    PipelineContext,
)
from app.services.daily_topic_pipeline.raw_acquisition_stage import (
    acquire_selected_article_raw_texts,
)
from app.services.daily_topic_pipeline.topic_selection_stage import (
    cluster_and_select_topics,
)


class DailyTopicArticleSelectionTests(unittest.TestCase):
    """UNIT-02의 기사 집합 선정과 Raw acquisition 경계를 검증한다."""

    def test_selects_related_limit_and_summary_subset_deterministically(self):
        """관련 기사 5건을 보존하고 Summary는 대표 포함 3건으로 제한한다."""

        embedding_result = _embedding_result(
            [
                _article(1, source="A", importance=20),
                _article(2, source="A", importance=19),
                _article(3, source="B", importance=18),
                _article(4, source="C", importance=17),
                _article(5, source="D", importance=16),
                _article(6, source="E", importance=15),
            ]
        )
        args = _args(max_related=5, max_summary=3)

        first = cluster_and_select_topics(
            embedding_result,
            args,
            pipeline_context=_pipeline_context(),
        )
        second = cluster_and_select_topics(
            embedding_result,
            args,
            pipeline_context=_pipeline_context(),
        )

        self.assertEqual(len(first.related_article_ids), 5)
        self.assertEqual(len(first.summary_article_ids), 3)
        self.assertEqual(first.representative_article_ids, [1])
        self.assertIn(1, first.summary_article_ids)
        self.assertTrue(
            set(first.summary_article_ids).issubset(first.related_article_ids)
        )
        self.assertGreaterEqual(
            len(
                {
                    _article_source(first.selected_topics, article_id)
                    for article_id in first.summary_article_ids
                }
            ),
            2,
        )
        self.assertEqual(first.related_article_ids, second.related_article_ids)
        self.assertEqual(first.summary_article_ids, second.summary_article_ids)

    def test_summary_selection_skips_duplicate_url_and_normalized_title(self):
        """중복 URL과 사실상 같은 제목을 제외하고 다음 관련 기사로 채운다."""

        embedding_result = _embedding_result(
            [
                _article(
                    1,
                    source="A",
                    importance=20,
                    title="Major AI Policy",
                    url="https://example.com/shared",
                ),
                _article(
                    2,
                    source="B",
                    importance=19,
                    title="Different wire title",
                    url="https://example.com/shared",
                ),
                _article(
                    3,
                    source="C",
                    importance=18,
                    title="  major   ai policy ",
                    url="https://example.com/3",
                ),
                _article(
                    4,
                    source="D",
                    importance=17,
                    title="Independent follow-up",
                    url="https://example.com/4",
                ),
            ]
        )

        result = cluster_and_select_topics(
            embedding_result,
            _args(max_related=4, max_summary=2),
            pipeline_context=_pipeline_context(),
        )

        self.assertEqual(result.summary_article_ids, [1, 4])

    def test_raw_acquisition_uses_only_summary_articles_and_isolates_failure(self):
        """관련 기사 4건 중 Summary 3건만 조회·추출하고 실패를 기사 단위로 남긴다."""

        topic_result = cluster_and_select_topics(
            _embedding_result(
                [
                    _article(1, source="A", importance=20),
                    _article(2, source="B", importance=19),
                    _article(3, source="C", importance=18),
                    _article(4, source="D", importance=17),
                ]
            ),
            _args(max_related=4, max_summary=3),
            pipeline_context=_pipeline_context(),
        )
        summary_ids = topic_result.summary_article_ids
        non_summary_ids = set(topic_result.related_article_ids) - set(summary_ids)
        extraction_executor = Mock(
            return_value=[
                {"article_id": summary_ids[1], "status": "success"},
                {"article_id": summary_ids[2], "status": "failed"},
            ]
        )
        raw_text_loader = Mock(
            return_value={
                summary_ids[0]: "stored raw",
                summary_ids[1]: "new raw",
            }
        )
        raw_states = {
            summary_ids[0]: {
                "has_raw_text": True,
                "extraction_status": "success",
            },
            summary_ids[1]: {
                "has_raw_text": False,
                "extraction_status": "pending",
            },
            summary_ids[2]: {
                "has_raw_text": False,
                "extraction_status": "pending",
            },
            **{
                article_id: {
                    "has_raw_text": False,
                    "extraction_status": "pending",
                }
                for article_id in non_summary_ids
            },
        }

        result = acquire_selected_article_raw_texts(
            topic_result,
            raw_states,
            {},
            _args(max_related=4, max_summary=3, execute=True),
            pipeline_context=_pipeline_context(),
            extraction_executor=extraction_executor,
            raw_text_loader=raw_text_loader,
        )

        extraction_executor.assert_called_once_with(summary_ids[1:], limit=5)
        raw_text_loader.assert_called_once_with(summary_ids)
        self.assertEqual(result.reused_article_ids, [summary_ids[0]])
        self.assertEqual(result.extracted_article_ids, [summary_ids[1]])
        self.assertEqual(result.failed_article_ids, [summary_ids[2]])
        self.assertEqual(result.missing_article_ids, [summary_ids[2]])
        self.assertTrue(non_summary_ids.isdisjoint(result.article_raw_texts))


def _article(
    article_id,
    *,
    source,
    importance,
    title=None,
    url=None,
):
    """동일 cluster에 들어갈 결정론적 기사 fixture를 생성한다."""

    now = datetime(2026, 6, 23, tzinfo=timezone.utc)
    return {
        "id": article_id,
        "source": source,
        "title": title or f"Article {article_id}",
        "summary": f"Detailed summary for article {article_id}. " * 10,
        "url": url or f"https://example.com/{article_id}",
        "source_category": "tech",
        "rule_category": "ai",
        "topic_category": "ai",
        "detected_language": "en",
        "importance_score": importance,
        "published_at": now,
        "created_at": now,
    }


def _embedding_result(articles):
    """모든 기사가 같은 cluster가 되도록 동일 vector를 포함한 결과를 만든다."""

    return EmbeddingStageResult(
        articles_with_embeddings=[(article, (1.0, 0.0)) for article in articles],
        failed_article_ids=[],
        created_count=len(articles),
        updated_count=0,
        reused_count=0,
        failed_count=0,
        failures=[],
    )


def _args(*, max_related, max_summary, execute=False):
    """기사 선정과 원문 확보 stage에 필요한 최소 설정을 반환한다."""

    return SimpleNamespace(
        execute=execute,
        similarity_threshold=0.78,
        max_topics=5,
        max_reference_topics=10,
        max_related_articles_per_topic=max_related,
        max_summary_articles_per_topic=max_summary,
        max_articles_per_topic=max_summary,
        extraction_limit=5,
    )


def _pipeline_context():
    """Stage log와 날짜 계약에 사용할 고정 pipeline context를 반환한다."""

    started_at = datetime(2026, 6, 23, tzinfo=timezone.utc)
    return PipelineContext(
        pipeline_date=date(2026, 6, 23),
        business_timezone="Asia/Seoul",
        started_at_utc=started_at,
        started_at_local=started_at,
        pipeline_date_source="test",
    )


def _article_source(topics, article_id):
    """선택 topic에서 지정한 기사 ID의 source를 반환한다."""

    return next(
        article["source"]
        for topic in topics
        for article in topic["articles"]
        if article["id"] == article_id
    )


if __name__ == "__main__":
    unittest.main()
