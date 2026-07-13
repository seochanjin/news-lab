"""Daily topic pipeline CronJob의 운영 인자와 안전 설정을 검증한다.

Manifest를 로컬에서 파싱해 schedule, 실행 상한, Secret 참조와 pod 보안 설정이
의도한 계약을 유지하는지 확인한다. Kubernetes object를 생성하거나 변경하지
않는다.
"""

import unittest
from pathlib import Path

import yaml


MANIFEST_PATH = Path("k8s/news-daily-topic-pipeline-cronjob.yaml")
API_MANIFEST_PATH = Path("k8s/news-api.yaml")
RSS_MANIFEST_PATH = Path("k8s/news-rss-collector-cronjob.yaml")
RAW_EXTRACTOR_MANIFEST_PATH = Path("k8s/news-raw-extractor-cronjob.yaml")


class DailyTopicPipelineCronJobManifestTests(unittest.TestCase):
    """Daily CronJob manifest가 bounded execute 계약을 따르는지 검증한다."""

    @classmethod
    def setUpClass(cls):
        """검증 대상 manifest와 중첩 spec을 한 번 파싱해 테스트 간 공유한다."""

        cls.manifest = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
        cls.spec = cls.manifest["spec"]
        cls.job_spec = cls.spec["jobTemplate"]["spec"]
        cls.pod_spec = cls.job_spec["template"]["spec"]
        cls.container = cls.pod_spec["containers"][0]

    def test_schedule_and_job_safety_settings(self):
        """Schedule, 동시 실행 차단과 Job/Pod 종료 정책이 유지되는지 확인한다."""

        self.assertEqual(self.manifest["apiVersion"], "batch/v1")
        self.assertEqual(self.manifest["kind"], "CronJob")
        self.assertEqual(
            self.manifest["metadata"]["name"],
            "news-daily-topic-pipeline",
        )
        self.assertEqual(self.spec["schedule"], "0 4 * * *")
        self.assertEqual(self.spec["timeZone"], "Asia/Seoul")
        self.assertEqual(self.spec["concurrencyPolicy"], "Forbid")
        self.assertEqual(self.spec["successfulJobsHistoryLimit"], 3)
        self.assertEqual(self.spec["failedJobsHistoryLimit"], 3)
        self.assertEqual(self.job_spec["activeDeadlineSeconds"], 1800)
        self.assertEqual(self.job_spec["backoffLimit"], 1)
        self.assertEqual(self.pod_spec["restartPolicy"], "Never")
        self.assertEqual(self.pod_spec["nodeSelector"], {"workload": "app"})

    def test_command_has_bounded_execute_configuration(self):
        """관련 기사 20건과 Summary 기사 3건 상한이 실행 명령에 포함되는지 확인한다."""

        command = self.container["command"]

        expected_command = [
            "python",
            "-u",
            "scripts/run_daily_topic_pipeline.py",
            "--window-hours",
            "24",
            "--max-articles",
            "300",
            "--similarity-threshold",
            "0.70",
            "--max-topics",
            "3",
            "--max-reference-topics",
            "10",
            "--max-related-articles-per-topic",
            "20",
            "--max-summary-articles-per-topic",
            "3",
            "--max-raw-chars-per-article",
            "3000",
            "--use-embedding-provider",
            "--use-summary-provider",
            "--summary-model",
            "gpt-5-nano",
            "--execute",
        ]

        self.assertEqual(command, expected_command)

    def test_reuses_existing_image_secret_and_security_patterns(self):
        """Immutable image와 Secret, 최소 권한 securityContext 재사용을 확인한다."""

        api_manifest = next(
            yaml.safe_load_all(API_MANIFEST_PATH.read_text(encoding="utf-8"))
        )
        api_container = api_manifest["spec"]["template"]["spec"]["containers"][0]

        self.assertRegex(
            self.container["image"],
            r"^seocj/news-api:[0-9a-f]{40}$",
        )
        self.assertEqual(self.container["image"], api_container["image"])
        self.assertEqual(
            self.container["securityContext"],
            {
                "allowPrivilegeEscalation": False,
                "capabilities": {"drop": ["ALL"]},
                "seccompProfile": {"type": "RuntimeDefault"},
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
                "OPENAI_EMBEDDING_API_KEY": {
                    "name": "news-api-secret",
                    "key": "OPENAI_EMBEDDING_API_KEY",
                },
                "OPENAI_SUMMARY_API_KEY": {
                    "name": "news-api-secret",
                    "key": "OPENAI_SUMMARY_API_KEY",
                },
            },
        )

    def test_pipeline_replaces_scheduled_raw_extractor(self):
        """Daily pipeline schedule과 제거된 raw extractor manifest 상태를 확인한다."""

        rss_manifest = yaml.safe_load(
            RSS_MANIFEST_PATH.read_text(encoding="utf-8")
        )

        self.assertFalse(RAW_EXTRACTOR_MANIFEST_PATH.exists())
        self.assertEqual(rss_manifest["spec"]["schedule"], "0 3 * * *")
        self.assertEqual(rss_manifest["spec"]["timeZone"], "Asia/Seoul")
        self.assertEqual(self.spec["schedule"], "0 4 * * *")
        self.assertEqual(self.spec["timeZone"], "Asia/Seoul")


if __name__ == "__main__":
    unittest.main()
