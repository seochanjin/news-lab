"""7일 Topic context, 후보 조회와 재클러스터링 선정 계약을 검증한다.

가짜 SQLAlchemy connection만 사용해 직전 완료 주간 계산, 명시 주간 재처리 범위,
후보 상한과 정렬, metadata/hash/vector 검증 및 누락 통계를 확인한다. 선정
stage는 메모리 fixture만 사용해 최소 기사·출처 조건, 대표·관련·Summary 근거
기사 선택을 검증한다. 실제 DB 쓰기나 embedding provider·외부 API 호출은
수행하지 않는다.
"""

import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import Mock, patch

from app.services.weekly_topic_pipeline import (
    PROMPT_VERSION,
    WeeklyCandidateStageResult,
    WeeklyOpenAISummaryProvider,
    WeeklyPipelineContext,
    WeeklyTopicProcessingResult,
    WeeklyRawAcquisitionResult,
    cluster_and_select_weekly_topics,
    acquire_weekly_topic_raw_texts,
    build_weekly_summary_input,
    build_weekly_summary_input_hash,
    build_weekly_summary_prompt,
    load_weekly_candidates,
    resolve_weekly_pipeline_context,
    summarize_and_persist_weekly_topics,
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


class WeeklyPipelineContextTests(unittest.TestCase):
    """서울 기준 완료 주간과 재현 가능한 UTC 7일 범위 계산을 확인한다."""

    def test_default_execution_uses_previous_completed_monday_to_sunday_week(self):
        """월요일 00:30 실행이 직전 월요일-일요일 주간으로 한 번만 해석된다."""

        context = resolve_weekly_pipeline_context(
            started_at_utc=datetime(2026, 6, 21, 15, 30, tzinfo=timezone.utc),
        )

        self.assertEqual(context.week_start, date(2026, 6, 15))
        self.assertEqual(context.week_end, date(2026, 6, 21))
        self.assertEqual(
            context.window_start,
            datetime(2026, 6, 14, 15, tzinfo=timezone.utc),
        )
        self.assertEqual(
            context.window_end,
            datetime(2026, 6, 21, 15, tzinfo=timezone.utc),
        )
        self.assertEqual(context.window_end - context.window_start, timedelta(days=7))
        self.assertEqual(context.window_source, "started_at")

    def test_explicit_week_start_resolves_same_week_independent_of_run_time(self):
        """명시 주간 시작일이 실행 시각과 무관하게 같은 주간 window를 만든다."""

        context = resolve_weekly_pipeline_context(
            started_at_utc=datetime(2026, 7, 10, 2, tzinfo=timezone.utc),
            week_start=date(2026, 6, 15),
        )

        self.assertEqual(context.week_start, date(2026, 6, 15))
        self.assertEqual(context.week_end, date(2026, 6, 21))
        self.assertEqual(
            context.window_start,
            datetime(2026, 6, 14, 15, tzinfo=timezone.utc),
        )
        self.assertEqual(
            context.window_end,
            datetime(2026, 6, 21, 15, tzinfo=timezone.utc),
        )
        self.assertEqual(context.window_source, "explicit_week_start")

    def test_non_monday_week_start_and_naive_started_at_are_rejected(self):
        """재처리 날짜와 실행 시각 오류가 환경별 범위 차이로 이어지지 않게 한다."""

        with self.assertRaisesRegex(ValueError, "week_start must be a Monday"):
            resolve_weekly_pipeline_context(
                started_at_utc=datetime(2026, 7, 10, 2, tzinfo=timezone.utc),
                week_start=date(2026, 6, 16),
            )

        with self.assertRaisesRegex(
            ValueError,
            "started_at_utc must be timezone-aware",
        ):
            resolve_weekly_pipeline_context(
                started_at_utc=datetime(2026, 7, 10, 2),
            )

    def test_shifted_noon_to_noon_week_window_is_rejected(self):
        """날짜만 맞는 월요일 정오~다음 월요일 정오 window를 거부한다."""

        with self.assertRaisesRegex(
            ValueError,
            "weekly topic window must start at Monday 00:00",
        ):
            WeeklyPipelineContext(
                week_start=date(2026, 6, 15),
                week_end=date(2026, 6, 21),
                business_timezone="Asia/Seoul",
                started_at_utc=datetime(2026, 6, 21, 15, 30, tzinfo=timezone.utc),
                started_at_local=datetime(
                    2026,
                    6,
                    22,
                    0,
                    30,
                    tzinfo=timezone(timedelta(hours=9)),
                ),
                window_start=datetime(
                    2026,
                    6,
                    15,
                    12,
                    tzinfo=timezone(timedelta(hours=9)),
                ),
                window_end=datetime(
                    2026,
                    6,
                    22,
                    12,
                    tzinfo=timezone(timedelta(hours=9)),
                ),
                window_days=7,
                window_source="test",
            )


class WeeklyCandidateStageTests(unittest.TestCase):
    """주간 후보 조회와 저장 embedding 검증·누락 분류를 확인한다."""

    def setUp(self):
        """고정 주간 context와 기사 row 생성 기준 시각을 준비한다."""

        self.context = resolve_weekly_pipeline_context(
            started_at_utc=datetime(2026, 6, 21, 15, 30, tzinfo=timezone.utc),
        )
        self.analysis_time = self.context.window_end - timedelta(hours=1)

    def test_query_uses_shared_week_window_and_candidate_limit(self):
        """기사 조회가 context 경계와 상한을 bind하고 embedding 조회는 후보만 사용한다."""

        article = self._article(1, title="기사", summary="요약")
        connection = FakeConnection(
            [article],
            [self._embedding(article)],
        )

        result = load_weekly_candidates(
            connection,
            pipeline_context=self.context,
            max_articles=700,
            dimension=3,
        )

        candidate_sql, candidate_params = connection.calls[0]
        self.assertIn(
            "coalesce(a.published_at, a.created_at) >= :window_start",
            candidate_sql,
        )
        self.assertIn(
            "coalesce(a.published_at, a.created_at) < :window_end",
            candidate_sql,
        )
        self.assertIn("a.id desc", candidate_sql)
        self.assertEqual(candidate_params["window_start"], self.context.window_start)
        self.assertEqual(candidate_params["window_end"], self.context.window_end)
        self.assertEqual(candidate_params["max_articles"], 700)
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

        result = load_weekly_candidates(
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

        result = load_weekly_candidates(
            connection,
            pipeline_context=self.context,
            max_articles=10,
            dimension=3,
        )

        self.assertEqual(len(connection.calls), 1)
        self.assertEqual(result.candidate_count, 0)
        self.assertEqual(result.embedding_count, 0)
        self.assertEqual(result.missing_embedding_count, 0)

    def test_candidate_result_rejects_duplicate_article_ids(self):
        """정상·누락 결과 사이에 같은 기사 ID가 섞이는 회귀를 차단한다."""

        article = self._article(1, title="중복", summary="요약")

        with self.assertRaisesRegex(ValueError, "candidate article IDs"):
            WeeklyCandidateStageResult(
                articles_with_embeddings=[(article, (0.1, 0.2, 0.3))],
                missing_embeddings=[{"article_id": 1, "reason": "missing_row"}],
            )

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
                    load_weekly_candidates(
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


class WeeklyTopicSelectionStageTests(unittest.TestCase):
    """주간 재클러스터링과 대표·관련·Summary 근거 기사 선정 정책을 확인한다."""

    def setUp(self):
        """완료된 주간 context와 기사 시각 fixture 기준을 준비한다."""

        self.context = resolve_weekly_pipeline_context(
            started_at_utc=datetime(2026, 6, 21, 15, 30, tzinfo=timezone.utc),
        )

    def test_filters_clusters_by_minimum_article_and_source_count(self):
        """5개 기사·2개 출처 조건을 통과한 군집만 주간 Topic 후보로 남긴다."""

        articles = [
            self._article(1, source="A", importance=20),
            self._article(2, source="A", importance=19),
            self._article(3, source="B", importance=18),
            self._article(4, source="B", importance=17),
            self._article(5, source="C", importance=16),
            self._article(6, source="D", importance=15),
            self._article(7, source="D", importance=14),
            self._article(8, source="D", importance=13),
            self._article(9, source="D", importance=12),
            self._article(10, source="D", importance=11),
            self._article(11, source="E", importance=10),
            self._article(12, source="F", importance=9),
            self._article(13, source="G", importance=8),
            self._article(14, source="H", importance=7),
        ]
        embeddings = [
            (1.0, 0.0),
            (0.99, 0.01),
            (0.98, 0.02),
            (0.97, 0.03),
            (0.96, 0.04),
            (0.0, 1.0),
            (0.01, 0.99),
            (0.02, 0.98),
            (0.03, 0.97),
            (0.04, 0.96),
            (-1.0, 0.0),
            (-0.99, 0.01),
            (-0.98, 0.02),
            (-0.97, 0.03),
        ]

        result = self._select(articles, embeddings, max_topics=5)

        self.assertEqual(result.cluster_count, 3)
        self.assertEqual(result.topic_candidate_count, 1)
        self.assertEqual(result.selected_topic_count, 1)
        self.assertEqual(result.selected_topics[0]["article_count"], 5)
        self.assertEqual(result.selected_topics[0]["source_count"], 3)
        self.assertEqual(set(result.related_article_ids), {1, 2, 3, 4, 5})

    def test_selects_related_and_source_diverse_summary_evidence_deterministically(self):
        """관련 기사 상한과 source 다양성을 적용하고 대표 기사를 근거에 포함한다."""

        articles = [
            self._article(1, source="A", importance=20),
            self._article(2, source="A", importance=19),
            self._article(3, source="A", importance=18),
            self._article(4, source="A", importance=17),
            self._article(5, source="A", importance=16),
            self._article(6, source="B", importance=15),
            self._article(7, source="C", importance=14),
        ]
        embeddings = [(1.0, 0.0)] * len(articles)

        first = self._select(
            articles,
            embeddings,
            max_related=7,
            max_summary=5,
        )
        second = self._select(
            articles,
            embeddings,
            max_related=7,
            max_summary=5,
        )

        self.assertEqual(first.representative_article_ids, [1])
        self.assertEqual(len(first.related_article_ids), 7)
        self.assertEqual(first.summary_article_ids[:3], [1, 6, 7])
        self.assertEqual(len(first.summary_article_ids), 5)
        self.assertTrue(
            set(first.summary_article_ids).issubset(first.related_article_ids)
        )
        self.assertEqual(first.related_article_ids, second.related_article_ids)
        self.assertEqual(first.summary_article_ids, second.summary_article_ids)

    def test_summary_evidence_drops_duplicate_urls_and_titles(self):
        """동일 URL·정규화 제목 중복은 Summary 근거 기사에서 제외한다."""

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
            self._article(4, source="D", importance=17),
            self._article(5, source="E", importance=16),
        ]

        result = self._select(
            articles,
            [(1.0, 0.0)] * len(articles),
            max_related=5,
            max_summary=5,
        )

        self.assertEqual(result.summary_article_ids, [1, 4, 5])

    def test_fewer_than_five_embeddings_returns_empty_selection(self):
        """정상 embedding이 5건 미만이면 실패 없이 빈 clustering 결과를 반환한다."""

        result = self._select(
            [
                self._article(1, source="A", importance=20),
                self._article(2, source="B", importance=19),
                self._article(3, source="C", importance=18),
                self._article(4, source="D", importance=17),
            ],
            [(1.0, 0.0)] * 4,
        )

        self.assertEqual(result.cluster_count, 0)
        self.assertEqual(result.topic_candidate_count, 0)
        self.assertEqual(result.selected_topic_count, 0)
        self.assertEqual(result.related_article_ids, [])
        self.assertEqual(result.summary_article_ids, [])

    def test_rejects_weekly_selection_limits_outside_policy(self):
        """주간 관련 기사·Summary 근거 상한이 정책을 벗어나면 거부한다."""

        articles = [
            self._article(index, source="A", importance=20 - index)
            for index in range(1, 6)
        ]
        embeddings = [(1.0, 0.0)] * 5

        with self.assertRaisesRegex(
            ValueError,
            "max_related_articles_per_topic must be at least weekly minimum",
        ):
            self._select(
                articles,
                embeddings,
                max_related=4,
            )

        with self.assertRaisesRegex(
            ValueError,
            "max_summary_articles_per_topic cannot exceed 5",
        ):
            self._select(
                articles,
                embeddings,
                max_related=6,
                max_summary=6,
            )

    def _select(
        self,
        articles,
        embeddings,
        *,
        max_topics=5,
        max_related=5,
        max_summary=5,
    ):
        """기사·vector fixture를 주간 선정 stage에 전달해 결과를 반환한다."""

        candidate_result = WeeklyCandidateStageResult(
            articles_with_embeddings=list(zip(articles, embeddings)),
            missing_embeddings=[],
        )
        return cluster_and_select_weekly_topics(
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
            "summary": f"Detailed summary for weekly article {article_id}. " * 10,
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


class RecordingWeeklySummaryProvider:
    """주간 Summary 입력을 기록하고 지정 Topic만 실패시키는 가짜 provider다."""

    provider = "test-provider"
    model = "test-weekly-summary-v1"

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
            "title_ko": f"주간 흐름 {topic_input['topic_candidate_id']}",
            "summary_ko": "지난 월요일부터 일요일까지의 변화와 공통 쟁점을 요약했다.",
            "key_points": ["초기 전개", "반복 쟁점", "주말 변화"],
            "keywords": ["주간", "흐름"],
            "confidence": 0.82,
        }


class RecordingWeeklyRepository:
    """Window 교체 호출과 전달 Topic을 기록하는 가짜 repository다."""

    def __init__(self):
        """교체 호출 목록을 초기화한다."""

        self.calls = []

    def replace_window_topics(self, **kwargs):
        """교체 인자를 기록하고 Topic 수만큼 고정 ID를 반환한다."""

        self.calls.append(kwargs)
        return [1900 + index for index, _topic in enumerate(kwargs["topics"], start=1)]


class FakeSummaryResponse:
    """OpenAI provider 테스트에 사용할 고정 JSON 응답을 제공한다."""

    def raise_for_status(self):
        """HTTP 성공 응답처럼 아무 예외도 발생시키지 않는다."""

    def json(self):
        """Strict schema에 맞는 Summary output_text payload를 반환한다."""

        return {
            "output_text": (
                '{"title_ko":"주간 흐름","summary_ko":"주간 순서 요약",'
                '"key_points":["초기","반복","후속"],"keywords":["주간"],'
                '"confidence":0.91}'
            )
        }


class WeeklyRawAndSummaryStageTests(unittest.TestCase):
    """선택 원문 확보, 주간 prompt, 실패 격리와 원자 저장 연결을 검증한다."""

    def setUp(self):
        """완료 주간 context와 두 Topic 선정 결과를 준비한다."""

        self.context = resolve_weekly_pipeline_context(
            started_at_utc=datetime(2026, 6, 21, 15, 30, tzinfo=timezone.utc),
        )
        self.topic_result = self._topic_result()

    def test_raw_acquisition_reuses_extracts_and_keeps_fallback_related_text(self):
        """관련 기사 원문을 조회하되 지연 추출은 Summary 후보에만 수행한다."""

        extraction_executor = Mock(
            side_effect=[
                [{"article_id": 2, "status": "success"}],
                [{"article_id": 5, "status": "failed"}],
            ]
        )
        raw_text_loader = Mock(
            side_effect=[
                {
                    1: "stored one",
                    6: "fallback six",
                    7: "stored seven",
                    8: "stored eight",
                    9: "stored nine",
                    10: "stored ten",
                    11: "stored eleven",
                },
                {
                    1: "stored one",
                    2: "new two",
                    6: "fallback six",
                    7: "stored seven",
                    8: "stored eight",
                    9: "stored nine",
                    10: "stored ten",
                    11: "stored eleven",
                },
            ]
        )

        result = acquire_weekly_topic_raw_texts(
            self.topic_result,
            {
                1: {"has_raw_text": True, "extraction_status": "success"},
                2: {"has_raw_text": False, "extraction_status": "pending"},
                3: {"has_raw_text": False, "extraction_status": "failed"},
                4: {"has_raw_text": False, "extraction_status": "failed"},
                5: {"has_raw_text": False, "extraction_status": "pending"},
                6: {"has_raw_text": True, "extraction_status": "success"},
            },
            {},
            pipeline_context=self.context,
            execute=True,
            extraction_limit=1,
            extraction_executor=extraction_executor,
            raw_text_loader=raw_text_loader,
        )

        self.assertEqual(raw_text_loader.call_args_list[0].args[0], list(range(1, 12)))
        self.assertEqual(
            [call.args[0] for call in extraction_executor.call_args_list],
            [[2], [5]],
        )
        self.assertEqual(result.extracted_article_ids, [2])
        self.assertEqual(result.failed_article_ids, [5])
        self.assertEqual(result.missing_article_ids, [3, 4])
        self.assertIn(6, result.article_raw_texts)

    def test_raw_acquisition_merges_preloaded_and_loader_raw_texts(self):
        """Partial loader 결과가 기존 원문을 지우지 않고 같은 ID는 loader 값을 우선한다."""

        raw_text_loader = Mock(return_value={2: "loader two", 6: "loader six"})

        result = acquire_weekly_topic_raw_texts(
            self.topic_result,
            {},
            {1: "existing one", 2: "existing two"},
            pipeline_context=self.context,
            execute=False,
            extraction_limit=5,
            raw_text_loader=raw_text_loader,
        )

        self.assertEqual(result.article_raw_texts[1], "existing one")
        self.assertEqual(result.article_raw_texts[2], "loader two")
        self.assertEqual(result.article_raw_texts[6], "loader six")
        self.assertIn(1, result.reused_article_ids)
        self.assertIn(6, result.reused_article_ids)

    def test_raw_acquisition_result_rejects_overlapping_status_buckets(self):
        """하나의 기사가 reused와 failed 같은 서로 다른 상태에 동시에 들어가지 못한다."""

        with self.assertRaisesRegex(ValueError, "mutually exclusive"):
            WeeklyRawAcquisitionResult(
                article_raw_texts={1: "raw"},
                reused_article_ids=[1],
                extracted_article_ids=[],
                failed_article_ids=[1],
                missing_article_ids=[],
                extraction_results=[],
            )

        with self.assertRaisesRegex(ValueError, "mutually exclusive"):
            WeeklyRawAcquisitionResult(
                article_raw_texts={},
                reused_article_ids=[],
                extracted_article_ids=[2],
                failed_article_ids=[],
                missing_article_ids=[2],
                extraction_results=[],
            )

    def test_raw_acquisition_result_rejects_raw_text_state_contradictions(self):
        """원문 map과 missing/available 상태가 서로 모순되는 결과를 차단한다."""

        with self.assertRaisesRegex(ValueError, "cannot be failed or missing"):
            WeeklyRawAcquisitionResult(
                article_raw_texts={3: "raw"},
                reused_article_ids=[],
                extracted_article_ids=[],
                failed_article_ids=[],
                missing_article_ids=[3],
                extraction_results=[],
            )

        with self.assertRaisesRegex(ValueError, "must have raw text"):
            WeeklyRawAcquisitionResult(
                article_raw_texts={},
                reused_article_ids=[4],
                extracted_article_ids=[],
                failed_article_ids=[],
                missing_article_ids=[],
                extraction_results=[],
            )

    def test_summary_input_uses_weekly_prompt_hash_and_fallback_article(self):
        """원문 없는 Summary 후보 대신 다음 관련 기사 원문을 주간 입력에 포함한다."""

        topic = self.topic_result.selected_topics[0]
        summary_input = build_weekly_summary_input(
            topic,
            {
                1: "raw one",
                2: "raw two",
                3: "raw three",
                4: "raw four",
                6: "fallback six",
            },
            max_raw_chars_per_article=100,
        )
        reordered = {
            **summary_input,
            "used_articles": list(reversed(summary_input["used_articles"])),
        }

        self.assertEqual(summary_input["prompt_version"], PROMPT_VERSION)
        self.assertEqual(summary_input["representative_article_id"], 1)
        self.assertEqual(
            {article["article_id"] for article in summary_input["used_articles"]},
            {1, 2, 3, 4, 6},
        )
        self.assertIn("지난 월요일부터 일요일", summary_input["instruction"])
        prompt = build_weekly_summary_prompt(summary_input)
        self.assertIn("주간 뉴스 흐름", prompt)
        self.assertIn("반복해서 등장한 쟁점", prompt)
        self.assertEqual(
            build_weekly_summary_input_hash(summary_input),
            build_weekly_summary_input_hash(reordered),
        )

    @patch("app.services.weekly_topic_pipeline.summary_persistence_stage.requests.post")
    def test_openai_provider_sends_weekly_prompt_and_strict_schema(self, post):
        """실제 provider adapter가 Daily·3일 prompt 대신 주간 흐름 prompt를 전송한다."""

        post.return_value = FakeSummaryResponse()
        summary_input = build_weekly_summary_input(
            self.topic_result.selected_topics[0],
            {index: f"raw {index}" for index in range(1, 6)},
            max_raw_chars_per_article=100,
        )

        result = WeeklyOpenAISummaryProvider(
            api_key="test-key",
            model="gpt-5-nano",
        ).summarize(summary_input)

        request = post.call_args.kwargs
        self.assertIn("주간 뉴스 흐름", request["json"]["input"])
        self.assertIn(PROMPT_VERSION, request["json"]["input"])
        self.assertEqual(
            request["json"]["text"]["format"]["name"],
            "weekly_topic_summary",
        )
        self.assertTrue(request["json"]["text"]["format"]["strict"])
        self.assertEqual(result["summary_ko"], "주간 순서 요약")

    def test_topic_failure_is_isolated_and_success_subset_is_saved_atomically(self):
        """한 Topic provider 실패 시 성공 Topic만 한 번의 window 교체로 저장한다."""

        repository = RecordingWeeklyRepository()
        provider = RecordingWeeklySummaryProvider(failing_topic_id="weekly-one")
        raw_result = WeeklyRawAcquisitionResult(
            article_raw_texts={
                1: "raw one",
                2: "raw two",
                3: "raw three",
                4: "raw four",
                5: "raw five",
                7: "raw seven",
                8: "raw eight",
                9: "raw nine",
                10: "raw ten",
                11: "raw eleven",
            },
            reused_article_ids=[1, 2, 3, 4, 5, 7, 8, 9, 10, 11],
            extracted_article_ids=[],
            failed_article_ids=[],
            missing_article_ids=[],
            extraction_results=[],
        )

        result = summarize_and_persist_weekly_topics(
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
        self.assertEqual(saved_topic.topic_candidate_id, "weekly-two")
        self.assertEqual(saved_topic.prompt_version, PROMPT_VERSION)
        self.assertEqual([article.article_id for article in saved_topic.articles], [7, 8, 9, 10, 11])
        self.assertTrue(saved_topic.articles[0].is_representative)
        self.assertTrue(all(article.is_summary_evidence for article in saved_topic.articles))

    def test_all_topic_failures_preserve_existing_window_results(self):
        """성공 Topic이 없는 실패 실행은 repository 교체를 호출하지 않는다."""

        repository = RecordingWeeklyRepository()
        raw_result = WeeklyRawAcquisitionResult(
            article_raw_texts={2: "support only", 8: "support only"},
            reused_article_ids=[2, 8],
            extracted_article_ids=[],
            failed_article_ids=[],
            missing_article_ids=[1, 7],
            extraction_results=[],
        )

        result = summarize_and_persist_weekly_topics(
            self.topic_result,
            raw_result,
            pipeline_context=self.context,
            summary_provider=RecordingWeeklySummaryProvider(),
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

        repository = RecordingWeeklyRepository()
        empty_result = type(self.topic_result)(
            selected_topics=[],
            representative_article_ids=[],
            related_article_ids=[],
            summary_article_ids=[],
            cluster_count=0,
            topic_candidate_count=0,
        )

        result = summarize_and_persist_weekly_topics(
            empty_result,
            WeeklyRawAcquisitionResult({}, [], [], [], [], []),
            pipeline_context=self.context,
            summary_provider=RecordingWeeklySummaryProvider(),
            repository=repository,
            run_id=79,
            execute=True,
            max_raw_chars_per_article=1000,
        )

        self.assertEqual(result.run_status, "success")
        self.assertEqual(result.saved_topic_count, 0)
        self.assertEqual(len(repository.calls), 1)
        self.assertEqual(repository.calls[0]["topics"], [])

    def test_processing_result_rejects_status_count_contradictions(self):
        """run_status와 저장·실패 Topic count가 모순되는 최종 결과를 거부한다."""

        invalid_cases = [
            (
                {
                    "topics": [],
                    "generated_topic_count": 0,
                    "saved_topic_count": 0,
                    "failed_topic_count": 1,
                    "saved_topic_ids": [],
                    "failures": [{"topic_candidate_id": "one"}],
                    "run_status": "success",
                },
                "success run cannot include failed topics",
            ),
            (
                {
                    "topics": [],
                    "generated_topic_count": 0,
                    "saved_topic_count": 0,
                    "failed_topic_count": 1,
                    "saved_topic_ids": [],
                    "failures": [{"topic_candidate_id": "one"}],
                    "run_status": "partial_success",
                },
                "partial_success run requires saved and failed topics",
            ),
            (
                {
                    "topics": [],
                    "generated_topic_count": 0,
                    "saved_topic_count": 1,
                    "failed_topic_count": 0,
                    "saved_topic_ids": [1901],
                    "failures": [],
                    "run_status": "failed",
                },
                "saved_topic_count cannot exceed generated topics",
            ),
        ]
        for kwargs, message in invalid_cases:
            with self.subTest(run_status=kwargs["run_status"]):
                with self.assertRaisesRegex(ValueError, message):
                    WeeklyTopicProcessingResult(**kwargs)

    def test_processing_result_accepts_success_partial_failed_and_empty_success(self):
        """정상 성공, 정상 부분 성공, 전체 실패와 빈 성공 결과 계약을 유지한다."""

        valid_cases = [
            {
                "topics": [],
                "generated_topic_count": 0,
                "saved_topic_count": 0,
                "failed_topic_count": 0,
                "saved_topic_ids": [],
                "failures": [],
                "run_status": "success",
            },
            {
                "topics": ["topic"],
                "generated_topic_count": 1,
                "saved_topic_count": 1,
                "failed_topic_count": 0,
                "saved_topic_ids": [1901],
                "failures": [],
                "run_status": "success",
            },
            {
                "topics": ["topic"],
                "generated_topic_count": 1,
                "saved_topic_count": 1,
                "failed_topic_count": 1,
                "saved_topic_ids": [1901],
                "failures": [{"topic_candidate_id": "failed"}],
                "run_status": "partial_success",
            },
            {
                "topics": [],
                "generated_topic_count": 0,
                "saved_topic_count": 0,
                "failed_topic_count": 1,
                "saved_topic_ids": [],
                "failures": [{"topic_candidate_id": "failed"}],
                "run_status": "failed",
            },
        ]

        for kwargs in valid_cases:
            with self.subTest(run_status=kwargs["run_status"]):
                self.assertEqual(
                    WeeklyTopicProcessingResult(**kwargs).run_status,
                    kwargs["run_status"],
                )

    def _topic_result(self):
        """두 개의 주간 Topic fixture를 포함한 선정 결과를 만든다."""

        from app.services.weekly_topic_pipeline import WeeklyTopicSelectionResult

        return WeeklyTopicSelectionResult(
            selected_topics=[
                self._topic("weekly-one", list(range(1, 7))),
                self._topic("weekly-two", list(range(7, 12))),
            ],
            representative_article_ids=[1, 7],
            related_article_ids=list(range(1, 12)),
            summary_article_ids=[1, 2, 3, 4, 5, 7, 8, 9, 10, 11],
            cluster_count=2,
            topic_candidate_count=2,
        )

    def _topic(self, topic_candidate_id, article_ids):
        """대표 rank와 기사 시각을 가진 주간 Topic fixture를 만든다."""

        articles = []
        for rank, article_id in enumerate(article_ids, start=1):
            analysis_time = self.context.window_start + timedelta(hours=article_id)
            articles.append(
                {
                    "id": article_id,
                    "source": f"Source {article_id % 3}",
                    "title": f"Weekly article {article_id}",
                    "url": f"https://example.com/weekly/{article_id}",
                    "published_at": analysis_time,
                    "analysis_time": analysis_time,
                    "representative_candidate_rank": rank,
                    "similarity_to_seed": 1.0 - (rank * 0.01),
                }
            )
        return {
            "topic_candidate_id": topic_candidate_id,
            "articles": articles,
            "article_count": len(articles),
            "source_count": 3,
        }


if __name__ == "__main__":
    unittest.main()
