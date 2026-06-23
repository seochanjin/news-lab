"""3일 Topic CronJob manifest의 schedule, 실행 계약과 안전 설정을 검증한다.

로컬 YAML만 파싱해 Daily 이후 독립 실행, bounded CLI 인자, 기존 image·Secret
재사용과 pod 보안 설정을 확인한다. Kubernetes object를 생성하거나 변경하지
않는다.
"""

import unittest
from pathlib import Path

import yaml


MANIFEST_PATH = Path("k8s/news-three-day-topic-pipeline-cronjob.yaml")
DAILY_MANIFEST_PATH = Path("k8s/news-daily-topic-pipeline-cronjob.yaml")


class ThreeDayTopicPipelineCronJobManifestTests(unittest.TestCase):
    """3일 CronJob이 독립적인 72시간 execute 계약을 따르는지 검증한다."""

    @classmethod
    def setUpClass(cls):
        """검증 대상 manifest와 중첩 spec을 한 번 파싱해 테스트 간 공유한다."""

        cls.manifest = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
        cls.spec = cls.manifest["spec"]
        cls.job_spec = cls.spec["jobTemplate"]["spec"]
        cls.pod_spec = cls.job_spec["template"]["spec"]
        cls.container = cls.pod_spec["containers"][0]

    def test_schedule_runs_after_daily_with_job_safety_limits(self):
        """서울 05시 schedule과 동시 실행·재시도·실행 시간 제한을 확인한다."""

        daily = yaml.safe_load(DAILY_MANIFEST_PATH.read_text(encoding="utf-8"))

        self.assertEqual(self.manifest["apiVersion"], "batch/v1")
        self.assertEqual(self.manifest["kind"], "CronJob")
        self.assertEqual(
            self.manifest["metadata"]["name"],
            "news-three-day-topic-pipeline",
        )
        self.assertEqual(daily["spec"]["schedule"], "0 4 * * *")
        self.assertEqual(self.spec["schedule"], "0 5 * * *")
        self.assertEqual(self.spec["timeZone"], "Asia/Seoul")
        self.assertEqual(self.spec["concurrencyPolicy"], "Forbid")
        self.assertEqual(self.spec["successfulJobsHistoryLimit"], 3)
        self.assertEqual(self.spec["failedJobsHistoryLimit"], 3)
        self.assertEqual(self.job_spec["activeDeadlineSeconds"], 1800)
        self.assertEqual(self.job_spec["backoffLimit"], 1)
        self.assertEqual(self.pod_spec["restartPolicy"], "Never")

    def test_command_uses_explicit_three_day_entrypoint_and_bounds(self):
        """전용 script, 72시간과 독립 기사·Topic 상한이 command에 포함되는지 확인한다."""

        self.assertEqual(
            self.container["command"],
            [
                "python",
                "-u",
                "scripts/run_three_day_topic_pipeline.py",
                "--window-hours",
                "72",
                "--max-articles",
                "500",
                "--similarity-threshold",
                "0.70",
                "--max-topics",
                "5",
                "--max-related-articles-per-topic",
                "20",
                "--max-summary-articles-per-topic",
                "3",
                "--max-raw-chars-per-article",
                "3000",
                "--use-summary-provider",
                "--summary-model",
                "gpt-5-nano",
                "--execute",
            ],
        )
        self.assertNotIn("--use-embedding-provider", self.container["command"])

    def test_reuses_image_database_and_summary_secret_without_embedding_key(self):
        """기존 image·Secret과 보안·resource 패턴을 필요한 환경 변수만 재사용한다."""

        self.assertEqual(self.container["image"], "seocj/news-api:latest")
        self.assertEqual(
            self.container["securityContext"],
            {
                "allowPrivilegeEscalation": False,
                "capabilities": {"drop": ["ALL"]},
                "seccompProfile": {"type": "RuntimeDefault"},
            },
        )
        self.assertEqual(
            self.container["resources"],
            {
                "requests": {"cpu": "100m", "memory": "128Mi"},
                "limits": {"cpu": "500m", "memory": "512Mi"},
            },
        )
        secret_refs = {
            item["name"]: item["valueFrom"]["secretKeyRef"]
            for item in self.container["env"]
        }
        self.assertEqual(
            secret_refs,
            {
                "DATABASE_URL": {
                    "name": "news-api-secret",
                    "key": "DATABASE_URL",
                },
                "OPENAI_SUMMARY_API_KEY": {
                    "name": "news-api-secret",
                    "key": "OPENAI_SUMMARY_API_KEY",
                },
            },
        )


if __name__ == "__main__":
    unittest.main()
