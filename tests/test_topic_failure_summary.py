"""Topic 실패 사유 집계가 run 이력의 1000자 상한 안에서 동작하는지 검증한다.

실패 사유는 지금까지 로그로만 남아 Pod 정리와 함께 사라졌다. run 이력에 남기되
개별 사유를 모두 적지 않고 사유별 건수만 집계한다.
"""

import unittest

from app.services.topic_pipeline import summarize_topic_failure_reasons
from app.services.topic_pipeline.failures import (
    MAX_ERROR_MESSAGE_LENGTH,
    MAX_REASON_LENGTH,
)


def make_failure(error, topic_candidate_id="topic-1"):
    """Topic 처리 단계가 기록하는 실패 항목 형태를 만든다."""

    return {"topic_candidate_id": topic_candidate_id, "error": error}


class SummarizeTopicFailureReasonsTests(unittest.TestCase):
    """집계 규칙과 상한 처리를 고정한다."""

    def test_실패가_없으면_None을_반환한다(self):
        """성공한 run의 error_message를 빈 문자열로 채우지 않는다."""

        self.assertIsNone(summarize_topic_failure_reasons([]))
        self.assertIsNone(summarize_topic_failure_reasons(None))

    def test_같은_사유를_건수로_묶는다(self):
        """유형별 건수만 남기므로 같은 사유는 하나로 합쳐진다."""

        failures = [
            make_failure("ValueError: representative article raw text is required"),
            make_failure("ValueError: representative article raw text is required"),
            make_failure("ValueError: insufficient raw text"),
        ]

        result = summarize_topic_failure_reasons(failures)

        self.assertEqual(
            result,
            "ValueError: representative article raw text is required x2; "
            "ValueError: insufficient raw text x1",
        )

    def test_건수가_많은_사유를_먼저_적는다(self):
        """어떤 유형이 지배적인지 먼저 보이는 것이 목적이다."""

        failures = [make_failure("rare")] + [make_failure("common")] * 3

        result = summarize_topic_failure_reasons(failures)

        self.assertTrue(result.startswith("common x3"))

    def test_공백을_정규화한다(self):
        """줄바꿈이 섞인 예외 메시지가 한 줄로 남게 한다."""

        failures = [make_failure("line one\n   line two")]

        result = summarize_topic_failure_reasons(failures)

        self.assertEqual(result, "line one line two x1")

    def test_사유가_없으면_unknown_error로_적는다(self):
        """error 키가 비어 있어도 건수는 남긴다."""

        failures = [{"topic_candidate_id": "topic-1"}]

        result = summarize_topic_failure_reasons(failures)

        self.assertEqual(result, "unknown error x1")

    def test_긴_사유는_잘라서_적는다(self):
        """provider 응답 본문이 통째로 들어오는 경우를 방어한다."""

        failures = [make_failure("x" * 500)]

        result = summarize_topic_failure_reasons(failures)

        self.assertEqual(result, "x" * MAX_REASON_LENGTH + " x1")

    def test_사유_유형이_많으면_상한_안에서_생략한다(self):
        """1000자를 넘기면 run 종료 model 검증에서 예외가 난다."""

        failures = [make_failure(f"reason {index:03d} " + "y" * 100) for index in range(40)]

        result = summarize_topic_failure_reasons(failures)

        self.assertLessEqual(len(result), MAX_ERROR_MESSAGE_LENGTH)
        self.assertIn("more)", result)

    def test_사유_하나가_상한을_넘어도_잘라서_남긴다(self):
        """아무것도 남기지 않는 것보다 잘라서라도 남기는 편이 낫다."""

        failures = [make_failure("z" * 100)]

        result = summarize_topic_failure_reasons(failures, max_length=20)

        self.assertEqual(len(result), 20)
        self.assertEqual(result, "z" * 20)


if __name__ == "__main__":
    unittest.main()
