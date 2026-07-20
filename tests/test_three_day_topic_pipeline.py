"""3일 Topic context와 저장 embedding 전용 후보 조회 계약을 검증한다.

가짜 SQLAlchemy connection만 사용해 명시적 72시간 경계, 후보 상한과 정렬,
metadata/hash/vector 검증 및 누락 통계를 확인한다. 실제 DB 쓰기나 embedding
provider·외부 API 호출은 수행하지 않는다.
"""

import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import Mock, patch

from app.services.three_day_topic_pipeline import (
    PROMPT_VERSION,
    ThreeDayCandidateStageResult,
    ThreeDayOpenAISummaryProvider,
    ThreeDayRawAcquisitionResult,
    ThreeDayTopicSelectionResult,
    acquire_three_day_topic_raw_texts,
    build_three_day_summary_input,
    build_three_day_summary_input_hash,
    build_three_day_summary_prompt,
    cluster_and_select_three_day_topics,
    load_three_day_candidates,
    resolve_three_day_pipeline_context,
    summarize_and_persist_three_day_topics,
)
from app.utils.article_embedding_storage import (
    build_article_embedding_input,
    hash_source_text,
)


class FakeMappings:
    """한 SQL 결과의 mapping row 목록을 반환한다."""

    def __init__(self, rows):
        """호출 순서에 맞는 row 목록을 보관한다."""

        self._rows = rows

    def all(self):
        """등록된 mapping row 전체를 반환한다."""

        return self._rows


class FakeResult:
    """Candidate stage가 사용하는 mappings 결과를 제공한다."""

    def __init__(self, rows):
        """SQL 실행 결과 row 목록을 보관한다."""

        self._rows = rows

    def mappings(self):
        """Mapping 접근자를 반환한다."""

        return FakeMappings(self._rows)


class FakeConnection:
    """기사와 embedding 조회를 순서대로 응답하고 SQL 호출을 기록한다."""

    def __init__(self, candidate_rows, embedding_rows):
        """두 read query의 고정 응답을 보관한다."""

        self._responses = [candidate_rows, embedding_rows]
        self.calls = []

    def execute(self, statement, parameters):
        """SQL과 bind parameter를 기록하고 다음 고정 응답을 반환한다."""

        self.calls.append((str(statement), parameters))
        return FakeResult(self._responses.pop(0))


class ThreeDayPipelineContextTests(unittest.TestCase):
    """서울 기준일과 재현 가능한 UTC 72시간 범위 계산을 확인한다."""

    def test_explicit_window_end_resolves_one_seoul_reference_date(self):
        """명시적 종료 시각이 UTC 범위와 서울 기준일로 한 번만 해석된다."""

        started_at = datetime(2026, 6, 23, 5, tzinfo=timezone.utc)
        window_end = datetime(
            2026,
            6,
            23,
            0,
            tzinfo=timezone(timedelta(hours=9)),
        )

        context = resolve_three_day_pipeline_context(
            started_at_utc=started_at,
            window_end=window_end,
        )

        self.assertEqual(context.reference_date, date(2026, 6, 23))
        self.assertEqual(
            context.window_end,
            datetime(2026, 6, 22, 15, tzinfo=timezone.utc),
        )
        self.assertEqual(
            context.window_start,
            datetime(2026, 6, 19, 15, tzinfo=timezone.utc),
        )
        self.assertEqual(context.window_source, "explicit_window_end")
        self.assertEqual(context.window_end - context.window_start, timedelta(hours=72))

    def test_naive_window_end_is_rejected(self):
        """Timezone 없는 재현 실행 경계가 환경별로 달라지는 회귀를 차단한다."""

        with self.assertRaisesRegex(ValueError, "window_end must be timezone-aware"):
            resolve_three_day_pipeline_context(
                started_at_utc=datetime(2026, 6, 23, 5, tzinfo=timezone.utc),
                window_end=datetime(2026, 6, 23, 0),
            )


class ThreeDayCandidateStageTests(unittest.TestCase):
    """후보 조회와 저장 embedding 검증·누락 분류를 확인한다."""

    def setUp(self):
        """고정 context와 기사 row 생성 기준 시각을 준비한다."""

        self.context = resolve_three_day_pipeline_context(
            started_at_utc=datetime(2026, 6, 23, 3, tzinfo=timezone.utc),
        )
        self.analysis_time = self.context.window_end - timedelta(hours=1)

    def test_query_uses_shared_half_open_window_and_candidate_limit(self):
        """기사 조회가 context 경계와 상한을 bind하고 embedding 조회는 후보만 사용한다."""

        article = self._article(1, title="기사", summary="요약")
        connection = FakeConnection(
            [article],
            [self._embedding(article)],
        )

        result = load_three_day_candidates(
            connection,
            pipeline_context=self.context,
            max_articles=25,
            dimension=3,
        )

        candidate_sql, candidate_params = connection.calls[0]
        self.assertIn("coalesce(a.published_at, a.created_at) >= :window_start", candidate_sql)
        self.assertIn("coalesce(a.published_at, a.created_at) < :window_end", candidate_sql)
        self.assertIn("a.id desc", candidate_sql)
        self.assertEqual(candidate_params["window_start"], self.context.window_start)
        self.assertEqual(candidate_params["window_end"], self.context.window_end)
        self.assertEqual(candidate_params["max_articles"], 25)
        self.assertEqual(connection.calls[1][1]["article_ids"], [1])
        executed_sql = " ".join(sql.lower() for sql, _params in connection.calls)
        self.assertNotIn("insert ", executed_sql)
        self.assertNotIn("update ", executed_sql)
        self.assertNotIn("delete ", executed_sql)
        self.assertEqual(result.candidate_count, 1)
        self.assertEqual(result.embedding_count, 1)
        self.assertEqual(result.embeddings, [(0.1, 0.2, 0.3)])

    def test_missing_and_invalid_embeddings_are_excluded_with_reason_counts(self):
        """저장 row 누락·metadata·hash·vector 결함이 실패 대신 통계로 집계된다."""

        articles = [
            self._article(1, title="정상", summary="요약"),
            self._article(2, title="없음", summary="요약"),
            self._article(3, title="호환 안 됨", summary="요약"),
            self._article(4, title="변경됨", summary="새 요약"),
            self._article(5, title="벡터 오류", summary="요약"),
        ]
        embedding_rows = [
            self._embedding(articles[0]),
            self._embedding(articles[2], provider="other"),
            self._embedding(articles[3], source_text_hash="old-hash"),
            self._embedding(articles[4], embedding="[0.1,0.2]"),
        ]
        connection = FakeConnection(articles, embedding_rows)

        result = load_three_day_candidates(
            connection,
            pipeline_context=self.context,
            max_articles=5,
            dimension=3,
        )

        self.assertEqual([article["id"] for article in result.articles], [1])
        self.assertEqual(result.candidate_count, 5)
        self.assertEqual(result.embedding_count, 1)
        self.assertEqual(result.missing_embedding_count, 4)
        self.assertEqual(
            result.missing_reason_counts,
            {
                "missing_row": 1,
                "incompatible_metadata": 1,
                "stale_hash": 1,
                "invalid_vector": 1,
            },
        )

    def test_empty_candidate_result_skips_embedding_query(self):
        """후보가 없으면 빈 정상 결과를 반환하고 불필요한 ANY 조회를 하지 않는다."""

        connection = FakeConnection([], [])

        result = load_three_day_candidates(
            connection,
            pipeline_context=self.context,
            max_articles=10,
            dimension=3,
        )

        self.assertEqual(len(connection.calls), 1)
        self.assertEqual(result.candidate_count, 0)
        self.assertEqual(result.embedding_count, 0)
        self.assertEqual(result.missing_embedding_count, 0)

    def test_embedding_settings_reject_non_string_and_blank_values(self):
        """문자열 metadata 설정 오류가 AttributeError 대신 field명 포함 ValueError가 된다."""

        invalid_cases = [
            ("provider", None),
            ("provider", 1),
            ("model", []),
            ("model", {}),
            ("source_text_type", ""),
            ("source_text_type", "   "),
        ]
        for field_name, value in invalid_cases:
            kwargs = {
                "provider": "openai",
                "model": "text-embedding-3-small",
                "source_text_type": "title_summary",
                field_name: value,
            }
            with self.subTest(field_name=field_name, value=value):
                with self.assertRaisesRegex(ValueError, field_name):
                    load_three_day_candidates(
                        FakeConnection([], []),
                        pipeline_context=self.context,
                        max_articles=10,
                        dimension=3,
                        **kwargs,
                    )

    def _article(self, article_id, *, title, summary):
        """분류와 source hash 계산에 필요한 최소 기사 row를 만든다."""

        return {
            "id": article_id,
            "source": "테스트 출처",
            "title": title,
            "url": f"https://example.com/{article_id}",
            "summary": summary,
            "source_category": "technology",
            "published_at": self.analysis_time,
            "created_at": self.analysis_time,
            "analysis_time": self.analysis_time,
        }

    @staticmethod
    def _embedding(
        article,
        *,
        provider="openai",
        source_text_hash=None,
        embedding="[0.1,0.2,0.3]",
    ):
        """기사와 일치하거나 의도적으로 결함이 있는 저장 embedding row를 만든다."""

        source_text = build_article_embedding_input(
            title=article["title"],
            summary=article["summary"],
        )
        return {
            "id": article["id"] * 10,
            "article_id": article["id"],
            "provider": provider,
            "model": "text-embedding-3-small",
            "dimension": 3,
            "source_text_type": "title_summary",
            "source_text_hash": source_text_hash or hash_source_text(source_text),
            "embedding": embedding,
            "updated_at": datetime(2026, 6, 23, tzinfo=timezone.utc),
        }


class ThreeDayTopicSelectionTests(unittest.TestCase):
    """3일 재클러스터링과 대표·관련·Summary 근거 기사 계약을 검증한다."""

    def setUp(self):
        """모든 선정 테스트가 공유할 고정 72시간 context를 준비한다."""

        self.context = resolve_three_day_pipeline_context(
            started_at_utc=datetime(2026, 6, 23, 3, tzinfo=timezone.utc),
        )

    def test_reclusters_embeddings_and_applies_independent_topic_limit(self):
        """기사 embedding을 직접 두 cluster로 나누고 더 큰 Topic 하나만 선택한다."""

        articles = [
            self._article(1, source="A", importance=20),
            self._article(2, source="B", importance=19),
            self._article(3, source="C", importance=18),
            self._article(4, source="D", importance=17),
            self._article(5, source="E", importance=16),
        ]
        result = self._select(
            articles,
            [
                (1.0, 0.0),
                (0.99, 0.01),
                (0.98, 0.02),
                (0.0, 1.0),
                (0.01, 0.99),
            ],
            max_topics=1,
        )

        self.assertEqual(result.cluster_count, 2)
        self.assertEqual(result.topic_candidate_count, 2)
        self.assertEqual(result.selected_topic_count, 1)
        self.assertEqual(result.selected_topics[0]["article_count"], 3)
        self.assertEqual(set(result.related_article_ids), {1, 2, 3})

    def test_selects_related_and_summary_evidence_as_deterministic_subsets(self):
        """관련 기사 상한과 중복 제거를 적용하고 대표 기사를 근거에 포함한다."""

        articles = [
            self._article(
                1,
                source="A",
                importance=20,
                title="Major AI Policy",
                url="https://example.com/shared",
            ),
            self._article(
                2,
                source="B",
                importance=19,
                title="Different wire title",
                url="https://example.com/shared",
            ),
            self._article(
                3,
                source="C",
                importance=18,
                title="  major   ai policy ",
                url="https://example.com/3",
            ),
            self._article(
                4,
                source="D",
                importance=17,
                title="Independent follow-up",
                url="https://example.com/4",
            ),
            self._article(5, source="E", importance=16),
        ]
        embeddings = [(1.0, 0.0)] * len(articles)

        first = self._select(
            articles,
            embeddings,
            max_related=4,
            max_summary=2,
        )
        second = self._select(
            articles,
            embeddings,
            max_related=4,
            max_summary=2,
        )

        self.assertEqual(first.representative_article_ids, [1])
        self.assertEqual(len(first.related_article_ids), 4)
        self.assertEqual(first.summary_article_ids, [1, 4])
        self.assertTrue(
            set(first.summary_article_ids).issubset(first.related_article_ids)
        )
        self.assertEqual(first.related_article_ids, second.related_article_ids)
        self.assertEqual(first.summary_article_ids, second.summary_article_ids)

    def test_fewer_than_two_embeddings_returns_empty_selection(self):
        """정상 embedding이 한 건뿐이면 실패 없이 빈 clustering 결과를 반환한다."""

        result = self._select(
            [self._article(1, source="A", importance=20)],
            [(1.0, 0.0)],
        )

        self.assertEqual(result.cluster_count, 0)
        self.assertEqual(result.topic_candidate_count, 0)
        self.assertEqual(result.selected_topic_count, 0)
        self.assertEqual(result.related_article_ids, [])
        self.assertEqual(result.summary_article_ids, [])

    def test_rejects_summary_limit_larger_than_related_limit(self):
        """Summary 근거 상한이 관련 기사 상한을 넘는 잘못된 3일 설정을 거부한다."""

        with self.assertRaisesRegex(
            ValueError,
            "max_summary_articles_per_topic cannot exceed",
        ):
            self._select(
                [
                    self._article(1, source="A", importance=20),
                    self._article(2, source="B", importance=19),
                ],
                [(1.0, 0.0), (1.0, 0.0)],
                max_related=1,
                max_summary=2,
            )

    def _select(
        self,
        articles,
        embeddings,
        *,
        max_topics=5,
        max_related=3,
        max_summary=2,
    ):
        """기사·vector fixture를 3일 선정 stage에 전달해 결과를 반환한다."""

        candidate_result = ThreeDayCandidateStageResult(
            articles_with_embeddings=list(zip(articles, embeddings)),
            missing_embeddings=[],
        )
        return cluster_and_select_three_day_topics(
            candidate_result,
            pipeline_context=self.context,
            similarity_threshold=0.95,
            max_topics=max_topics,
            max_related_articles_per_topic=max_related,
            max_summary_articles_per_topic=max_summary,
        )

    def _article(
        self,
        article_id,
        *,
        source,
        importance,
        title=None,
        url=None,
    ):
        """Grouping과 대표 후보 점수 계산에 필요한 최소 기사 fixture를 만든다."""

        published_at = self.context.window_end - timedelta(hours=article_id)
        return {
            "id": article_id,
            "source": source,
            "title": title or f"Article {article_id}",
            "summary": f"Detailed summary for article {article_id}. " * 10,
            "url": url or f"https://example.com/{article_id}",
            "source_category": "technology",
            "rule_category": "technology",
            "topic_category": "technology",
            "detected_language": "en",
            "importance_score": importance,
            "published_at": published_at,
            "created_at": published_at,
            "analysis_time": published_at,
        }


class RecordingThreeDaySummaryProvider:
    """3일 Summary 입력을 기록하고 지정 Topic만 실패시키는 가짜 provider다."""

    provider = "test-provider"
    model = "test-three-day-summary-v1"

    def __init__(self, *, failing_topic_id=None):
        """실패시킬 Topic ID와 입력 기록 목록을 초기화한다."""

        self.failing_topic_id = failing_topic_id
        self.inputs = []

    def summarize(self, topic_input):
        """입력을 기록하고 성공 시 저장 model에 필요한 고정 Summary를 반환한다."""

        self.inputs.append(topic_input)
        if topic_input["topic_candidate_id"] == self.failing_topic_id:
            raise RuntimeError("summary provider unavailable")
        return {
            "title_ko": f"3일 흐름 {topic_input['topic_candidate_id']}",
            "summary_ko": "최근 72시간의 변화와 여러 출처의 공통 내용을 요약했다.",
            "key_points": ["초기 보도", "후속 진행"],
            "keywords": ["흐름", "진행"],
            "confidence": 0.8,
        }


class RecordingThreeDayRepository:
    """Window 교체 호출과 전달 Topic을 기록하는 가짜 repository다."""

    def __init__(self):
        """교체 호출 목록을 초기화한다."""

        self.calls = []

    def replace_window_topics(self, **kwargs):
        """교체 인자를 기록하고 Topic 수만큼 고정 ID를 반환한다."""

        self.calls.append(kwargs)
        return [900 + index for index, _topic in enumerate(kwargs["topics"], start=1)]


class FakeSummaryResponse:
    """OpenAI provider 테스트에 사용할 고정 JSON 응답을 제공한다."""

    def raise_for_status(self):
        """HTTP 성공 응답처럼 아무 예외도 발생시키지 않는다."""

    def json(self):
        """Strict schema에 맞는 Summary output_text payload를 반환한다."""

        return {
            "output_text": (
                '{"title_ko":"3일 흐름","summary_ko":"시간 순서 요약",'
                '"key_points":["초기","후속"],"keywords":["흐름"],'
                '"confidence":0.9}'
            )
        }


class ThreeDayRawAndSummaryStageTests(unittest.TestCase):
    """선택 원문 확보, 3일 prompt, 실패 격리와 원자 저장 연결을 검증한다."""

    def setUp(self):
        """고정 72시간 context와 두 Topic 선정 결과를 준비한다."""

        self.context = resolve_three_day_pipeline_context(
            started_at_utc=datetime(2026, 6, 23, 3, tzinfo=timezone.utc),
        )
        self.topic_result = ThreeDayTopicSelectionResult(
            selected_topics=[
                self._topic("topic-one", [1, 2, 3]),
                self._topic("topic-two", [4, 5]),
            ],
            representative_article_ids=[1, 4],
            related_article_ids=[1, 2, 3, 4, 5],
            summary_article_ids=[1, 2, 4, 5],
            cluster_count=2,
            topic_candidate_count=2,
        )

    def test_raw_acquisition_reuses_and_extracts_only_summary_articles(self):
        """관련 기사 중 Summary 4건만 조회하고 누락 원문을 Topic별로 추출한다."""

        extraction_executor = Mock(
            side_effect=[
                [{"article_id": 2, "status": "success"}],
                [{"article_id": 4, "status": "failed"}],
            ]
        )
        raw_text_loader = Mock(
            side_effect=[
                {1: "stored one"},
                {1: "stored one", 2: "new two", 5: "stored five"},
            ]
        )

        result = acquire_three_day_topic_raw_texts(
            self.topic_result,
            {
                1: {"has_raw_text": True, "extraction_status": "success"},
                2: {"has_raw_text": False, "extraction_status": "pending"},
                3: {"has_raw_text": False, "extraction_status": "pending"},
                4: {"has_raw_text": False, "extraction_status": "pending"},
                5: {"has_raw_text": True, "extraction_status": "success"},
            },
            {},
            pipeline_context=self.context,
            execute=True,
            extraction_limit=5,
            extraction_executor=extraction_executor,
            raw_text_loader=raw_text_loader,
        )

        self.assertEqual(
            [call.args[0] for call in extraction_executor.call_args_list],
            [[2], [4]],
        )
        self.assertEqual(raw_text_loader.call_args_list[0].args[0], [1, 2, 4, 5])
        self.assertEqual(result.reused_article_ids, [1, 5])
        self.assertEqual(result.extracted_article_ids, [2])
        self.assertEqual(result.failed_article_ids, [4])
        self.assertEqual(result.missing_article_ids, [4])
        self.assertNotIn(3, result.article_raw_texts)

    def test_summary_input_has_time_flow_prompt_and_stable_versioned_hash(self):
        """기사 시각과 3일 지시문이 prompt/hash에 포함되고 순서에 안정적인지 확인한다."""

        topic = self.topic_result.selected_topics[0]
        summary_input = build_three_day_summary_input(
            topic,
            {1: "raw one", 2: "raw two"},
            max_raw_chars_per_article=100,
        )
        reordered = {
            **summary_input,
            "used_articles": list(reversed(summary_input["used_articles"])),
        }

        self.assertEqual(summary_input["prompt_version"], PROMPT_VERSION)
        self.assertEqual(summary_input["representative_article_id"], 1)
        self.assertTrue(
            all(article["analysis_time"] for article in summary_input["used_articles"])
        )
        self.assertIn("최근 72시간", summary_input["instruction"])
        prompt = build_three_day_summary_prompt(summary_input)
        self.assertIn("시간 순서의 변화", prompt)
        self.assertIn("불확실한 내용", prompt)
        self.assertIn(
            "제목에는 날짜, 연도, 월, 일, 요일, 기간과 시간 범위를 포함하지 않는다.",
            prompt,
        )
        self.assertIn("제목은 뉴스 내용과 핵심 주제만 표현한다.", prompt)
        self.assertEqual(
            build_three_day_summary_input_hash(summary_input),
            build_three_day_summary_input_hash(reordered),
        )

    @patch(
        "app.services.three_day_topic_pipeline.summary_persistence_stage.requests.post"
    )
    def test_openai_provider_sends_three_day_prompt_and_strict_schema(self, post):
        """실제 provider adapter가 Daily prompt 대신 3일 흐름 prompt를 전송한다."""

        post.return_value = FakeSummaryResponse()
        summary_input = build_three_day_summary_input(
            self.topic_result.selected_topics[0],
            {1: "raw one", 2: "raw two"},
            max_raw_chars_per_article=100,
        )

        result = ThreeDayOpenAISummaryProvider(
            api_key="test-key",
            model="gpt-5-nano",
        ).summarize(summary_input)

        request = post.call_args.kwargs
        self.assertIn("시간 순서의 변화", request["json"]["input"])
        self.assertIn(PROMPT_VERSION, request["json"]["input"])
        self.assertEqual(
            request["json"]["text"]["format"]["name"],
            "three_day_topic_summary",
        )
        self.assertTrue(request["json"]["text"]["format"]["strict"])
        self.assertEqual(result["summary_ko"], "시간 순서 요약")

    def test_topic_failure_is_isolated_and_success_subset_is_saved_atomically(self):
        """한 Topic provider 실패 시 성공 Topic만 한 번의 window 교체로 저장한다."""

        repository = RecordingThreeDayRepository()
        provider = RecordingThreeDaySummaryProvider(
            failing_topic_id="topic-one"
        )
        raw_result = ThreeDayRawAcquisitionResult(
            article_raw_texts={
                1: "raw one",
                2: "raw two",
                4: "raw four",
                5: "raw five",
            },
            reused_article_ids=[1, 2, 4, 5],
            extracted_article_ids=[],
            failed_article_ids=[],
            missing_article_ids=[],
            extraction_results=[],
        )

        result = summarize_and_persist_three_day_topics(
            self.topic_result,
            raw_result,
            pipeline_context=self.context,
            summary_provider=provider,
            repository=repository,
            run_id=77,
            execute=True,
            max_raw_chars_per_article=1000,
        )

        self.assertEqual(result.run_status, "partial_success")
        self.assertEqual(result.generated_topic_count, 1)
        self.assertEqual(result.saved_topic_count, 1)
        self.assertEqual(result.failed_topic_count, 1)
        self.assertEqual(len(repository.calls), 1)
        saved_topic = repository.calls[0]["topics"][0]
        self.assertEqual(saved_topic.topic_candidate_id, "topic-two")
        self.assertEqual(saved_topic.prompt_version, PROMPT_VERSION)
        self.assertEqual(
            [article.article_id for article in saved_topic.articles],
            [4, 5],
        )
        self.assertTrue(saved_topic.articles[0].is_representative)
        self.assertTrue(all(article.is_summary_evidence for article in saved_topic.articles))

    def test_topic_record_uses_sanitized_title_and_keyword_fallback(self):
        """기간뿐인 provider 제목을 keyword fallback으로 바꿔 record에 저장한다."""

        raw_result = ThreeDayRawAcquisitionResult(
            article_raw_texts={1: "raw one", 2: "raw two", 4: "raw four", 5: "raw five"},
            reused_article_ids=[1, 2, 4, 5],
            extracted_article_ids=[],
            failed_article_ids=[],
            missing_article_ids=[],
            extraction_results=[],
        )
        provider = RecordingThreeDaySummaryProvider()
        provider.summarize = Mock(
            return_value={
                "title_ko": "(월요일~일요일)",
                "summary_ko": "시간 순서 요약",
                "key_points": ["핵심"],
                "keywords": ["AI 반도체 투자"],
                "confidence": 0.8,
            }
        )

        repository = RecordingThreeDayRepository()
        result = summarize_and_persist_three_day_topics(
            self.topic_result,
            raw_result,
            pipeline_context=self.context,
            summary_provider=provider,
            repository=repository,
            run_id=79,
            execute=True,
            max_raw_chars_per_article=1000,
        )

        self.assertEqual(
            [topic.title_ko for topic in result.topics],
            ["AI 반도체 투자", "AI 반도체 투자"],
        )
        self.assertEqual(
            [topic.title_ko for topic in repository.calls[0]["topics"]],
            ["AI 반도체 투자", "AI 반도체 투자"],
        )

    def test_all_topic_failures_preserve_existing_window_results(self):
        """성공 Topic이 없는 실패 실행은 repository 교체를 호출하지 않는다."""

        repository = RecordingThreeDayRepository()
        raw_result = ThreeDayRawAcquisitionResult(
            article_raw_texts={2: "support only", 5: "support only"},
            reused_article_ids=[2, 5],
            extracted_article_ids=[],
            failed_article_ids=[],
            missing_article_ids=[1, 4],
            extraction_results=[],
        )

        result = summarize_and_persist_three_day_topics(
            self.topic_result,
            raw_result,
            pipeline_context=self.context,
            summary_provider=RecordingThreeDaySummaryProvider(),
            repository=repository,
            run_id=78,
            execute=True,
            max_raw_chars_per_article=1000,
        )

        self.assertEqual(result.run_status, "failed")
        self.assertEqual(result.failed_topic_count, 2)
        self.assertEqual(repository.calls, [])

    def test_empty_selection_replaces_window_with_empty_success_result(self):
        """정상 빈 clustering 결과는 기존 window를 빈 결과로 교체할 수 있다."""

        repository = RecordingThreeDayRepository()
        empty_result = ThreeDayTopicSelectionResult(
            selected_topics=[],
            representative_article_ids=[],
            related_article_ids=[],
            summary_article_ids=[],
            cluster_count=0,
            topic_candidate_count=0,
        )

        result = summarize_and_persist_three_day_topics(
            empty_result,
            ThreeDayRawAcquisitionResult({}, [], [], [], [], []),
            pipeline_context=self.context,
            summary_provider=RecordingThreeDaySummaryProvider(),
            repository=repository,
            run_id=79,
            execute=True,
            max_raw_chars_per_article=1000,
        )

        self.assertEqual(result.run_status, "success")
        self.assertEqual(result.saved_topic_count, 0)
        self.assertEqual(len(repository.calls), 1)
        self.assertEqual(repository.calls[0]["topics"], [])

    def _topic(self, topic_candidate_id, article_ids):
        """대표 rank와 기사 시각을 가진 3일 Topic fixture를 만든다."""

        articles = []
        for rank, article_id in enumerate(article_ids, start=1):
            analysis_time = self.context.window_start + timedelta(hours=article_id)
            articles.append(
                {
                    "id": article_id,
                    "title": f"Article {article_id}",
                    "source": f"Source {article_id}",
                    "published_at": analysis_time,
                    "analysis_time": analysis_time,
                    "representative_candidate_rank": rank,
                    "similarity_to_seed": round(1 - rank / 100, 2),
                }
            )
        return {
            "topic_candidate_id": topic_candidate_id,
            "article_count": len(articles),
            "source_count": len(articles),
            "articles": articles,
        }


if __name__ == "__main__":
    unittest.main()
