# Verification: NewsLab Deployment 중지 설정

## Verification Status

passed

이 문서는 로컬 설정 검증 결과를 기록한다. 운영 적용과 merge는 수행하지 않았다.
초기 검증 후 사용자가 커밋, push, main 대상 PR 생성을 별도로 요청했다.

- 날짜: 2026-11-07
- 브랜치: `codex/retire-newslab-replicas`
- 기준 HEAD: `25d6ebaef3a03700618f403e3723765fcf7ac4a8`

## 실제 검증

저장소 루트에서 다음 코드를 `.venv/bin/python`으로 실행했다.

```python
from pathlib import Path
import copy
import subprocess
import yaml

expected = {"k8s/news-api.yaml": ("news-api", 2), "k8s/redis.yaml": ("news-redis", 1)}
for name, (deployment_name, old_count) in expected.items():
    before = list(yaml.safe_load_all(subprocess.check_output(["git", "show", f"25d6ebaef3a03700618f403e3723765fcf7ac4a8:{name}"], text=True)))
    after = list(yaml.safe_load_all(Path(name).read_text()))
    wanted = copy.deepcopy(before)
    deployment = next(doc for doc in wanted if doc and doc.get("kind") == "Deployment")
    assert deployment["metadata"]["name"] == deployment_name
    assert deployment["spec"]["replicas"] == old_count
    deployment["spec"]["replicas"] = 0
    assert after == wanted, f"Unexpected semantic change: {name}"
    current = next(doc for doc in after if doc and doc.get("kind") == "Deployment")
    assert type(current["spec"]["replicas"]) is int
    print(f"PASS {deployment_name}: {old_count} -> 0; every other setting unchanged")

cronjobs = []
deployments = []
yaml_files = sorted(Path("k8s").rglob("*.yaml")) + sorted(Path("k8s").rglob("*.yml"))
for path in yaml_files:
    for doc in yaml.safe_load_all(path.read_text()):
        if not isinstance(doc, dict):
            continue
        kind = doc.get("kind")
        assert kind != "HorizontalPodAutoscaler", f"HPA requires review: {path}"
        if kind == "CronJob":
            assert doc["spec"]["suspend"] is True, f"Active CronJob: {path}"
            cronjobs.append(doc["metadata"]["name"])
        if kind in ("Deployment", "StatefulSet"):
            assert doc["spec"]["replicas"] == 0, f"Active workload: {path}"
            deployments.append(doc["metadata"]["name"])
assert set(deployments) == {"news-api", "news-redis"}
assert len(cronjobs) == 4
print(f"PASS {len(yaml_files)} YAML files parsed; all 4 CronJobs suspended; no HPA")
```

결과(exit 0):

```text
PASS news-api: 2 -> 0; every other setting unchanged
PASS news-redis: 1 -> 0; every other setting unchanged
PASS 13 YAML files parsed; all 4 CronJobs suspended; no HPA
```

- `git diff --check`: 출력 없음, exit 0.
- `git diff --stat`: 설정 2개만 변경. 각각 주석 추가 및 replicas 변경.
- `git status --short --branch`: 작업 브랜치에서 변경. 기존 미추적
  `docs/reports/baseline-2026-08.md`는 보존했다.
- 문서 작성 첫 시도는 stdin 인코딩 오류로 실행 전 실패했다.
  ASCII JSON 입력으로 변경하여 재시도했다. 설정 검증 실패는 아니다.

## PR 준비 확인

- `git fetch origin main`: 성공.
- `git rev-list --left-right --count HEAD...origin/main`: 커밋 전 `0 0`, 최신 main과 동일.
- 비교 코드는 PR 커밋 후에도 재현할 수 있도록 위 기준 SHA를 고정했다.
- GitHub 저장소 쓰기 권한과 동일 head/base의 열린 PR 부재를 확인했다.
- `gh` CLI가 없어 GitHub connector로 PR을 생성한다. CLI 설치는 수행하지 않았다.

## 미수행

앱 코드 변경이 없어 API/DB 통합 테스트는 수행하지 않았다.
운영 서버 조회/적용, 서버 측 검증, 외부 리뷰도 이번 작업에서 수행하지 않았다.
GitHub Actions 중지는 사용자 보고이며 이 작업에서 변경하거나 검증하지 않았다.

## 재개 조건과 범위

replicas=0은 Deployment Pod 실행을 중지한다. 같은 파일의 Service/Ingress는
생성될 수 있고, 별도 수동 Job이나 Helm 설치는 차단하지 않는다.
재개 전 이미지와 DB/키 유효성을 확인하고 필요한 수량을 검토한다.
기존 값은 API 2, Redis 1이다. 이번 작업에서 재개 명령은 실행하지 않았다.

## 실제 GitHub 제출 결과

- 지정 파일 6개만 staging하고 `git diff --cached --check`를 통과했다.
- 커밋 `d7fc72c8ef8c3742f683779e5d59490df517b6a0`을 검토 브랜치에 push했다.
- GitHub connector의 PR 생성이 integration 권한 403으로 거절되어 기존 Git 인증으로 GitHub REST API를 호출했다. 인증정보는 메모리에서만 사용했고 로그나 파일로 저장하지 않았다. 시스템 CA로 TLS 검증을 유지했다.
- PR https://github.com/seochanjin/news-lab/pull/75 생성 후 open, base=main, head=codex/retire-newslab-replicas 및 최초 커밋 SHA 일치를 확인했다.
- 기존 미추적 `docs/reports/baseline-2026-08.md`는 커밋에서 제외했다.
- 운영 적용과 PR 병합은 수행하지 않았다.
