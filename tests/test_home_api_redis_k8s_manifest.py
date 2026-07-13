"""Home API Redis 운영 manifest와 Argo CD 수동 반영 경계를 검증한다.

이 테스트는 로컬 YAML만 파싱해 `news-api`의 Redis 환경 변수, `news-redis`
Deployment/Service, Argo CD Manual Sync 정책을 확인한다. Kubernetes object를
생성하거나 변경하지 않으며, 운영 Secret 값도 읽지 않는다.
"""

import unittest
from pathlib import Path

import yaml


NEWS_API_MANIFEST_PATH = Path("k8s/news-api.yaml")
REDIS_MANIFEST_PATH = Path("k8s/redis.yaml")
ARGOCD_APPLICATION_PATH = Path("k8s/argocd/news-api-application.yaml")


def load_yaml_documents(path):
    """여러 Kubernetes YAML document를 입력 순서대로 파싱해 반환한다."""

    return list(yaml.safe_load_all(path.read_text(encoding="utf-8")))


class HomeApiRedisK8sManifestTests(unittest.TestCase):
    """Home API Redis cache를 위한 운영 manifest 계약을 회귀 검증한다."""

    @classmethod
    def setUpClass(cls):
        """검증 대상 manifest를 한 번 파싱해 테스트 간 공유한다."""

        cls.news_api_documents = load_yaml_documents(NEWS_API_MANIFEST_PATH)
        cls.news_api_deployment = cls.news_api_documents[0]
        cls.news_api_container = cls.news_api_deployment["spec"]["template"][
            "spec"
        ]["containers"][0]
        cls.redis_documents = load_yaml_documents(REDIS_MANIFEST_PATH)
        cls.redis_deployment = cls.redis_documents[0]
        cls.redis_service = cls.redis_documents[1]
        cls.redis_container = cls.redis_deployment["spec"]["template"]["spec"][
            "containers"
        ][0]
        cls.argocd_application = yaml.safe_load(
            ARGOCD_APPLICATION_PATH.read_text(encoding="utf-8")
        )

    def test_news_api_uses_redis_cache_configuration(self):
        """API Deployment가 Redis URL, TTL, timeout과 immutable image 기준을 유지한다."""

        env_by_name = {
            item["name"]: item
            for item in self.news_api_container["env"]
        }

        self.assertEqual(self.news_api_deployment["metadata"]["name"], "news-api")
        self.assertEqual(self.news_api_deployment["spec"]["replicas"], 2)
        self.assertEqual(
            self.news_api_deployment["spec"]["template"]["spec"]["nodeSelector"],
            {"workload": "app"},
        )
        self.assertRegex(
            self.news_api_container["image"],
            r"^seocj/news-api:[0-9a-f]{40}$",
        )
        self.assertEqual(
            env_by_name["DATABASE_URL"]["valueFrom"]["secretKeyRef"],
            {"name": "news-api-secret", "key": "DATABASE_URL"},
        )
        self.assertEqual(
            env_by_name["REDIS_URL"]["value"],
            "redis://news-redis:6379/0",
        )
        self.assertEqual(env_by_name["HOME_TOPICS_CACHE_TTL_SECONDS"]["value"], "60")
        self.assertEqual(env_by_name["REDIS_TIMEOUT_SECONDS"]["value"], "0.05")

    def test_redis_deployment_is_ephemeral_and_bounded(self):
        """Redis Deployment가 persistence 없이 bounded resource로 실행되는지 확인한다."""

        pod_spec = self.redis_deployment["spec"]["template"]["spec"]

        self.assertEqual(self.redis_deployment["metadata"]["name"], "news-redis")
        self.assertEqual(self.redis_deployment["spec"]["replicas"], 1)
        self.assertEqual(pod_spec["nodeSelector"], {"workload": "app"})
        self.assertEqual(self.redis_container["name"], "redis")
        self.assertEqual(self.redis_container["image"], "redis:7.2-alpine")
        self.assertEqual(
            self.redis_container["args"],
            [
                "redis-server",
                "--save",
                "",
                "--appendonly",
                "no",
                "--maxmemory",
                "96mb",
                "--maxmemory-policy",
                "allkeys-lru",
            ],
        )
        self.assertEqual(
            self.redis_container["resources"],
            {
                "requests": {"cpu": "50m", "memory": "64Mi"},
                "limits": {"cpu": "250m", "memory": "128Mi"},
            },
        )

    def test_redis_service_is_cluster_internal(self):
        """Redis Service가 ClusterIP 기본 동작으로 API Pod 내부 접근만 제공한다."""

        self.assertEqual(self.redis_service["kind"], "Service")
        self.assertEqual(self.redis_service["metadata"]["name"], "news-redis")
        self.assertEqual(self.redis_service["spec"]["selector"], {"app": "news-redis"})
        self.assertEqual(
            self.redis_service["spec"]["ports"],
            [{"port": 6379, "targetPort": 6379}],
        )
        self.assertNotIn("type", self.redis_service["spec"])

    def test_argocd_application_keeps_manual_sync_boundary(self):
        """Argo CD Application이 k8s top-level manifest만 읽고 자동 Sync를 쓰지 않는다."""

        spec = self.argocd_application["spec"]

        self.assertEqual(spec["source"]["path"], "k8s")
        self.assertEqual(spec["source"]["targetRevision"], "main")
        self.assertFalse(spec["source"]["directory"]["recurse"])
        self.assertEqual(
            spec["source"]["directory"]["exclude"],
            "cluster-issuer.yaml",
        )
        self.assertNotIn("syncPolicy", spec)


if __name__ == "__main__":
    unittest.main()
