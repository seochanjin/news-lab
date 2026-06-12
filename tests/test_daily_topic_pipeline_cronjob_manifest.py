import unittest
from pathlib import Path


MANIFEST_PATH = Path("k8s/news-daily-topic-pipeline-cronjob.yaml")


class DailyTopicPipelineCronJobManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = MANIFEST_PATH.read_text(encoding="utf-8")

    def assertContainsAll(self, snippets):
        for snippet in snippets:
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, self.manifest)

    def test_schedule_and_job_safety_settings(self):
        self.assertContainsAll(
            [
                "apiVersion: batch/v1",
                "kind: CronJob",
                "name: news-daily-topic-pipeline",
                'schedule: "0 4 * * *"',
                'timeZone: "Asia/Seoul"',
                "concurrencyPolicy: Forbid",
                "successfulJobsHistoryLimit: 3",
                "failedJobsHistoryLimit: 3",
                "activeDeadlineSeconds: 1800",
                "backoffLimit: 1",
                "restartPolicy: Never",
                "workload: app",
            ]
        )

    def test_command_has_bounded_execute_configuration(self):
        self.assertIn(
            "- python\n"
            "                - -u\n"
            "                - scripts/run_daily_topic_pipeline.py",
            self.manifest,
        )
        self.assertContainsAll(
            [
                "- --window-hours\n                - \"24\"",
                "- --max-articles\n                - \"300\"",
                "- --similarity-threshold\n                - \"0.70\"",
                "- --max-topics\n                - \"3\"",
                "- --max-reference-topics\n                - \"10\"",
                "- --max-articles-per-topic\n                - \"3\"",
                "- --max-raw-chars-per-article\n                - \"3000\"",
                "- --use-embedding-provider",
                "- --use-summary-provider",
                "- --summary-model\n                - gpt-5-nano",
                "- --execute",
            ]
        )

    def test_reuses_existing_image_secret_and_security_patterns(self):
        self.assertContainsAll(
            [
                "image: seocj/news-api:latest",
                "allowPrivilegeEscalation: false",
                'drop: ["ALL"]',
                "type: RuntimeDefault",
                "- name: DATABASE_URL",
                "key: DATABASE_URL",
                "- name: OPENAI_EMBEDDING_API_KEY",
                "key: OPENAI_EMBEDDING_API_KEY",
                "- name: OPENAI_SUMMARY_API_KEY",
                "key: OPENAI_SUMMARY_API_KEY",
            ]
        )
        self.assertEqual(self.manifest.count("name: news-api-secret"), 3)


if __name__ == "__main__":
    unittest.main()
