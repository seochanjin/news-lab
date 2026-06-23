"""Daily pipeline의 Summary 입력과 관련 기사 저장 분리 계약을 검증한다.

외부 provider나 DB를 호출하지 않고 주입한 fake provider와 save executor로
Summary 근거 기사만 요약 입력에 포함되는지, 관련 기사 전체가 기존 순서와
역할로 저장되는지, Topic별 Summary 실패가 다른 Topic 저장을 막지 않는지
확인한다.
"""

import unittest
from datetime import date, datetime, timezone
from types import SimpleNamespace

from app.services.daily_topic_pipeline.models import (
    PipelineContext,
    RawAcquisitionResult,
    TopicSelectionResult,
)
from app.services.daily_topic_pipeline.summary_persistence_stage import (
    summarize_and_save_topics,
)
from app.utils.topic_summary import DeterministicSummaryProvider
from scripts.run_daily_topic_pipeline import build_pipeline, parse_args


class RecordingSummaryProvider(DeterministicSummaryProvider):
    """Provider 입력을 기록하면서 기존 deterministic Summary를 생성한다."""

    def __init__(self, *, failing_topic_id=None):
        """선택적으로 실패시킬 Topic ID와 입력 기록 저장소를 초기화한다."""

        self.failing_topic_id = failing_topic_id
        self.inputs = []

    def summarize(self, topic_input):
        """입력 복사본을 기록하고 지정 Topic이면 예외를 발생시킨다."""

        self.inputs.append(topic_input)
        if topic_input["topic_candidate_id"] == self.failing_topic_id:
            raise RuntimeError("summary provider unavailable")
        return super().summarize(topic_input)


class FixedEmbeddingProvider:
    """모든 기사를 하나의 Topic으로 묶는 고정 embedding을 반환한다."""

    model = "fixed-embedding-v1"

    def embed(self, texts):
        """입력 기사 수만큼 동일한 2차원 vector를 반환한다."""

        return [[1.0, 0.0] for _text in texts]


class DailyTopicSummaryPersistenceTests(unittest.TestCase):
    """Summary 기사와 저장 관련 기사 경계의 UNIT-03 회귀를 검증한다."""

    def test_summary_uses_subset_and_save_plan_links_all_related_articles(self):
        """Summary 3건만 provider에 전달하고 관련 기사 5건을 모두 저장 계획에 둔다."""

        topic_result = _topic_result([_topic("topic-1", range(1, 6))])
        raw_result = _raw_result({1: "raw 1", 2: "raw 2", 3: "raw 3"})
        provider = RecordingSummaryProvider()

        result = summarize_and_save_topics(
            topic_result,
            raw_result,
            _args(),
            pipeline_context=_context(),
            summary_provider=provider,
        )

        self.assertEqual(
            [article["article_id"] for article in provider.inputs[0]["used_articles"]],
            [1, 2, 3],
        )
        saved_topic = result.save_plan["topics"][0]
        self.assertEqual(
            [article["article_id"] for article in saved_topic["articles"]],
            [1, 2, 3, 4, 5],
        )
        self.assertEqual(
            [article["role"] for article in saved_topic["articles"]],
            ["representative", "supporting", "supporting", "supporting", "supporting"],
        )
        self.assertEqual(saved_topic["article_count"], 5)
        self.assertEqual(saved_topic["source_count"], 5)
        self.assertEqual(result.save_plan["analysis"]["related_article_count"], 5)
        self.assertEqual(result.save_plan["analysis"]["summary_article_count"], 3)
        self.assertEqual(result.save_plan["analysis"]["linked_article_count"], 0)

    def test_execute_counts_all_linked_articles_without_duplicate_relations(self):
        """Execute 결과 통계가 중복 제거된 관련 기사 관계 전체를 반영하는지 확인한다."""

        duplicated_topic = _topic("topic-1", [1, 2, 2, 3, 4])
        topic_result = _topic_result([duplicated_topic], related_ids=[1, 2, 3, 4])
        raw_result = _raw_result({1: "raw 1", 2: "raw 2", 3: "raw 3"})

        def save_executor(plan):
            """DB adapter 대신 저장 관계 수와 Topic ID를 기록한다."""

            plan["analysis"]["db_write_performed"] = True
            plan["analysis"]["saved_topic_count"] = len(plan["topics"])
            plan["analysis"]["linked_article_count"] = sum(
                len(topic["articles"]) for topic in plan["topics"]
            )
            plan["topics"][0]["topic_id"] = 101
            return plan

        result = summarize_and_save_topics(
            topic_result,
            raw_result,
            _args(execute=True),
            pipeline_context=_context(),
            summary_provider=RecordingSummaryProvider(),
            save_executor=save_executor,
        )

        self.assertEqual(result.saved_topic_count, 1)
        self.assertEqual(result.saved_topic_ids, [101])
        self.assertEqual(result.save_plan["analysis"]["linked_article_count"], 4)
        self.assertEqual(
            [article["article_id"] for article in result.save_plan["topics"][0]["articles"]],
            [1, 2, 3, 4],
        )

    def test_summary_failure_isolated_while_other_topic_keeps_all_relations(self):
        """한 Topic의 provider 실패가 다른 Topic Summary와 관련 기사 저장을 막지 않는다."""

        topics = [
            _topic("topic-fail", [1, 2, 3]),
            _topic("topic-ready", [4, 5, 6, 7]),
        ]
        topic_result = _topic_result(
            topics,
            related_ids=[1, 2, 3, 4, 5, 6, 7],
            summary_ids=[1, 2, 3, 4, 5, 6],
            representative_ids=[1, 4],
        )
        raw_result = _raw_result(
            {article_id: f"raw {article_id}" for article_id in [1, 2, 3, 4, 5, 6]}
        )

        result = summarize_and_save_topics(
            topic_result,
            raw_result,
            _args(max_topics=2),
            pipeline_context=_context(),
            summary_provider=RecordingSummaryProvider(
                failing_topic_id="topic-fail"
            ),
        )

        self.assertEqual(result.failed_topic_count, 1)
        self.assertEqual(result.generated_topic_count, 1)
        self.assertEqual(
            [topic["topic_candidate_id"] for topic in result.save_plan["topics"]],
            ["topic-ready"],
        )
        self.assertEqual(
            [
                article["article_id"]
                for article in result.save_plan["topics"][0]["articles"]
            ],
            [4, 5, 6, 7],
        )

    def test_pipeline_analysis_separates_related_summary_raw_and_saved_counts(self):
        """통합 실행 통계가 관련·Summary·원문 대상·저장 관계 수를 구분하는지 검증한다."""

        now = datetime(2026, 6, 23, tzinfo=timezone.utc)
        rows = [
            {
                "id": article_id,
                "source": f"Source {article_id}",
                "title": f"Article {article_id}",
                "summary": "Detailed artificial intelligence policy update.",
                "url": f"https://example.com/{article_id}",
                "source_category": "tech",
                "published_at": now,
                "created_at": now,
                "analysis_time": now,
            }
            for article_id in range(1, 6)
        ]
        args = parse_args(
            [
                "--execute",
                "--max-related-articles-per-topic",
                "5",
                "--max-summary-articles-per-topic",
                "3",
            ]
        )

        def save_executor(plan):
            """통합 결과 검증을 위해 실제 저장 adapter와 동일한 수 통계를 기록한다."""

            plan["analysis"]["db_write_performed"] = True
            plan["analysis"]["saved_topic_count"] = len(plan["topics"])
            plan["analysis"]["linked_article_count"] = sum(
                len(topic["articles"]) for topic in plan["topics"]
            )
            return plan

        result = build_pipeline(
            rows,
            {},
            {article_id: f"raw {article_id}" for article_id in range(1, 4)},
            args,
            pipeline_context=_context(),
            embedding_provider=FixedEmbeddingProvider(),
            summary_provider=RecordingSummaryProvider(),
            extraction_executor=lambda article_ids, limit: [],
            raw_text_loader=lambda article_ids: {
                article_id: f"raw {article_id}"
                for article_id in article_ids
                if article_id <= 3
            },
            save_executor=save_executor,
        )

        self.assertEqual(result["analysis"]["related_article_count"], 5)
        self.assertEqual(result["analysis"]["summary_article_count"], 3)
        self.assertEqual(result["analysis"]["raw_acquisition_target_count"], 3)
        self.assertEqual(result["analysis"]["saved_topic_article_count"], 5)


def _topic(topic_id, article_ids):
    """테스트용 관련 기사 순서와 대표 rank를 가진 Topic을 생성한다."""

    articles = []
    for index, article_id in enumerate(article_ids, start=1):
        articles.append(
            {
                "id": article_id,
                "title": f"Article {article_id}",
                "source": f"Source {article_id}",
                "representative_candidate_rank": index,
                "similarity_to_seed": round(1 - index / 100, 2),
            }
        )
    return {
        "topic_candidate_id": topic_id,
        "article_count": len(articles),
        "source_count": len({article["source"] for article in articles}),
        "articles": articles,
    }


def _topic_result(
    topics,
    *,
    related_ids=None,
    summary_ids=None,
    representative_ids=None,
):
    """테스트 Topic들로 관련·Summary 기사 집합 계약을 구성한다."""

    all_ids = list(
        dict.fromkeys(article["id"] for topic in topics for article in topic["articles"])
    )
    related_ids = related_ids or all_ids
    summary_ids = summary_ids or all_ids[:3]
    representative_ids = representative_ids or [topics[0]["articles"][0]["id"]]
    return TopicSelectionResult(
        selected_topics=topics,
        reference_topics=[],
        representative_article_ids=representative_ids,
        related_article_ids=related_ids,
        summary_article_ids=summary_ids,
        cluster_count=len(topics),
        selected_topic_count=len(topics),
        topic_candidate_count=len(topics),
    )


def _raw_result(raw_texts):
    """주어진 원문 mapping을 Summary 단계 입력 결과로 감싼다."""

    return RawAcquisitionResult(
        article_raw_texts=raw_texts,
        reused_article_ids=list(raw_texts),
        extracted_article_ids=[],
        failed_article_ids=[],
        missing_article_ids=[],
        summary_ready_topics=[],
        extraction_results=[],
    )


def _args(*, execute=False, max_topics=1):
    """Summary·저장 단계에 필요한 최소 실행 인자를 만든다."""

    return SimpleNamespace(
        execute=execute,
        max_topics=max_topics,
        max_articles_per_topic=3,
        max_summary_articles_per_topic=3,
        max_raw_chars_per_article=3000,
        use_summary_provider=False,
        summary_model="gpt-5-nano",
    )


def _context():
    """고정된 업무 날짜를 가진 테스트 PipelineContext를 반환한다."""

    started_at = datetime(2026, 6, 23, tzinfo=timezone.utc)
    return PipelineContext(
        pipeline_date=date(2026, 6, 23),
        business_timezone="Asia/Seoul",
        started_at_utc=started_at,
        started_at_local=started_at,
        pipeline_date_source="test",
    )


if __name__ == "__main__":
    unittest.main()
