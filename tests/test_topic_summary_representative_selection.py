"""Summary 대표 기사 선정이 원문 확보 여부를 반영하는지 검증한다.

clustering 대표(``representative_candidate_rank`` 1)는 기사 유사도로 정해지므로
원문 확보 여부와 무관하다. Summary 대표는 요약의 근거이므로 원문이 있어야 한다.
기존 구현은 후자에 전자를 그대로 사용해, rank 1 기사의 원문 추출이 실패하면
같은 Topic의 다른 근거 기사에 원문이 남아 있어도 Topic 전체가 폐기됐다.
"""

import unittest

from app.services.topic_pipeline import pick_summary_representative_article_id
from app.services.three_day_topic_pipeline.summary_persistence_stage import (
    build_three_day_summary_input,
)
from app.services.weekly_topic_pipeline.summary_persistence_stage import (
    build_weekly_summary_input,
)


def make_article(article_id, rank, published_at="2026-08-20T00:00:00+00:00"):
    return {
        "id": article_id,
        "title": f"title {article_id}",
        "source": "Al Jazeera",
        "published_at": published_at,
        "representative_candidate_rank": rank,
    }


def make_used(article_id):
    return {"article_id": article_id}


class PickSummaryRepresentativeTests(unittest.TestCase):
    """공유 선정 함수의 rank 우선순위와 경계 동작을 고정한다."""

    def setUp(self):
        self.topic_articles = [
            make_article(11, 1),
            make_article(22, 2),
            make_article(33, 3),
        ]

    def test_rank1의_원문이_있으면_rank1을_그대로_고른다(self):
        """기존 동작을 바꾸지 않는다."""

        used_articles = [make_used(11), make_used(22)]

        result = pick_summary_representative_article_id(
            self.topic_articles,
            used_articles,
        )

        self.assertEqual(result, 11)

    def test_rank1의_원문이_없으면_rank2로_승격한다(self):
        """이번 수정의 핵심이다. 이전에는 Topic 전체가 폐기됐다."""

        used_articles = [make_used(22), make_used(33)]

        result = pick_summary_representative_article_id(
            self.topic_articles,
            used_articles,
        )

        self.assertEqual(result, 22)

    def test_rank_순서를_건너뛰지_않는다(self):
        """rank 3만 남아도 더 낮은 rank를 먼저 찾은 뒤 선택한다."""

        used_articles = [make_used(33)]

        result = pick_summary_representative_article_id(
            self.topic_articles,
            used_articles,
        )

        self.assertEqual(result, 33)

    def test_원문이_하나도_없으면_None을_반환한다(self):
        """근거가 없으면 대표도 없다. 호출부가 Topic을 실패로 처리한다."""

        result = pick_summary_representative_article_id(self.topic_articles, [])

        self.assertIsNone(result)

    def test_rank가_없는_기사만_원문을_가지면_그_기사를_쓴다(self):
        """rank 부여 대상이 아니어도 근거로 쓰였다면 대표가 될 수 있다."""

        topic_articles = [make_article(11, 1), make_article(44, None)]
        used_articles = [make_used(44)]

        result = pick_summary_representative_article_id(topic_articles, used_articles)

        self.assertEqual(result, 44)


class ThreeDaySummaryInputRepresentativeTests(unittest.TestCase):
    """3일 pipeline의 Summary 입력 구성에서 폴백이 실제로 동작하는지 확인한다."""

    def setUp(self):
        self.topic = {
            "topic_candidate_id": "topic-1",
            "articles": [
                make_article(11, 1),
                make_article(22, 2, published_at="2026-08-20T01:00:00+00:00"),
            ],
        }

    def test_대표_기사_원문이_없어도_다른_근거로_대표를_정한다(self):
        """영상 포스트가 rank 1로 뽑힌 실제 실패 상황이다."""

        summary_input = build_three_day_summary_input(
            self.topic,
            {22: "raw two"},
            max_raw_chars_per_article=100,
        )

        self.assertEqual(summary_input["representative_article_id"], 22)
        used_ids = [
            article["article_id"] for article in summary_input["used_articles"]
        ]
        self.assertEqual(used_ids, [22])

    def test_원문이_하나도_없으면_대표가_없다(self):
        """근거가 전무한 Topic은 여전히 폐기 대상이다."""

        summary_input = build_three_day_summary_input(
            self.topic,
            {},
            max_raw_chars_per_article=100,
        )

        self.assertIsNone(summary_input["representative_article_id"])
        self.assertEqual(summary_input["used_articles"], [])


class WeeklySummaryInputRepresentativeTests(unittest.TestCase):
    """7일 pipeline도 같은 폴백을 사용하는지 확인한다."""

    def setUp(self):
        self.topic = {
            "topic_candidate_id": "topic-1",
            "week_start": "2026-08-17",
            "week_end": "2026-08-23",
            "articles": [
                make_article(11, 1),
                make_article(22, 2, published_at="2026-08-20T01:00:00+00:00"),
            ],
        }

    def test_대표_기사_원문이_없어도_다른_근거로_대표를_정한다(self):
        summary_input = build_weekly_summary_input(
            self.topic,
            {22: "raw two"},
            max_raw_chars_per_article=100,
        )

        self.assertEqual(summary_input["representative_article_id"], 22)

    def test_원문이_하나도_없으면_대표가_없다(self):
        summary_input = build_weekly_summary_input(
            self.topic,
            {},
            max_raw_chars_per_article=100,
        )

        self.assertIsNone(summary_input["representative_article_id"])


if __name__ == "__main__":
    unittest.main()
