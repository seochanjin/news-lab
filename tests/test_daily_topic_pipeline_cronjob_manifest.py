import unittest
from pathlib import Path

import yaml


MANIFEST_PATH = Path("k8s/news-daily-topic-pipeline-cronjob.yaml")


class DailyTopicPipelineCronJobManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
        cls.spec = cls.manifest["spec"]
        cls.job_spec = cls.spec["jobTemplate"]["spec"]
        cls.pod_spec = cls.job_spec["template"]["spec"]
        cls.container = cls.pod_spec["containers"][0]

    def test_schedule_and_job_safety_settings(self):
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
        command = self.container["command"]

        self.assertEqual(
            command[:3],
            ["python", "-u", "scripts/run_daily_topic_pipeline.py"],
        )
        for argument, value in (
            ("--window-hours", "24"),
            ("--max-articles", "300"),
            ("--similarity-threshold", "0.70"),
            ("--max-topics", "3"),
            ("--max-reference-topics", "10"),
            ("--max-articles-per-topic", "3"),
            ("--max-raw-chars-per-article", "3000"),
            ("--summary-model", "gpt-5-nano"),
        ):
            with self.subTest(argument=argument):
                index = command.index(argument)
                self.assertEqual(command[index + 1], value)
        for flag in (
            "--use-embedding-provider",
            "--use-summary-provider",
            "--execute",
        ):
            with self.subTest(flag=flag):
                self.assertIn(flag, command)

    def test_reuses_existing_image_secret_and_security_patterns(self):
        self.assertEqual(self.container["image"], "seocj/news-api:latest")
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


if __name__ == "__main__":
    unittest.main()
