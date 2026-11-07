# Task: NewsLab 종료 상태를 Deployment에 반영

## Goal

운영이 종료된 NewsLab의 저장소 설정도 중지 상태로 맞춘다. 배포 파일을 다시
적용하더라도 API와 Redis Pod가 실행되지 않도록 replicas를 0으로 명시한다.

## Scope / Allowed changes

- `k8s/news-api.yaml`: news-api replicas 2 → 0, 종료 및 재개 주석.
- `k8s/redis.yaml`: news-redis replicas 1 → 0, 종료 및 재개 주석.
- 이 브랜치의 `docs/tasks`, `docs/verification`, `docs/pr`, `docs/devlog` 문서.

## Do not change

- 앱 코드, 이미지, 환경 변수, Secret 참조, Service, Ingress, 리소스 제한.
- CronJob 4개의 기존 suspend=true, monitoring Helm values 및 공용 인프라.
- Supabase 데이터, GameProbe, `.env`, credentials, 기존 미추적 보고서.
- 운영 서버 적용 및 merge.
- web/exporter는 각자의 저장소에서 같은 작업 단위로 별도 변경하며 이 저장소에서 수정하지 않는다.

## Test commands

- `.venv/bin/python`과 PyYAML로 YAML을 읽고 HEAD와 비교한다.
  Deployment의 spec.replicas만 0으로 바뀌고 다른 문서는 동일해야 한다.
- 같은 검사에서 CronJob 4개의 suspend=true와 HPA 부재를 확인한다.
- `git diff --check`, `git diff --stat`, `git status --short --branch`.
- 최종 검사 코드는 verification에 실제 결과와 함께 보관한다.

## Acceptance criteria

- [x] API와 Redis replicas가 정수 0이다.
- [x] replicas 이외 설정이 HEAD와 동일하다.
- [x] CronJob suspend=true 유지 및 로컬 YAML 검증 통과.
- [x] 검증 결과와 재개 조건을 문서화했다.

## Notes

- 2026-11-07 사용자가 각 레포 replicas를 0으로 변경하도록 요청했다.
- 최초 요청은 Kubernetes manifest의 로컬 수정 승인이다.
- 후속 사용자 요청 "pr 올려줘"에 따라 이 변경의 커밋, push, main 대상 PR 생성이 승인되었다. 병합과 운영 변경은 포함하지 않는다.
- 기존 docs/tasks/main.md가 가리키는 기능 작업과 미추적 baseline 보고서는 수정하지 않는다.
- replicas=0은 이 Deployment의 Pod 실행을 막는다. Service/Ingress 생성이나 별도 수동 Job, Helm 설치를 막는 설정은 아니다.
- 재개는 별도 승인 작업이다. 이미지와 DB/키를 확인하고 API 2, Redis 1 등 필요한 수를 검토한 뒤 배포한다.

## Result

- 변경 파일: k8s/news-api.yaml, k8s/redis.yaml 및 이 브랜치 task/verification/pr/devlog 문서 4개.
- 실행: Python/PyYAML의 HEAD 의미 비교 및 YAML 13개 파싱, git diff --check/stat/status.
- 결과: API 2→0, Redis 1→0 외 설정 동일; CronJob 4개 suspend=true, HPA 없음.
- 미수행: 운영 적용, merge, 외부 리뷰. 후속 승인 범위는 로컬 검증을 마친 변경의 커밋, push, PR 생성이다.
- 주의: replicas=0은 Deployment Pod만 중지하며 Service/Ingress 생성이나 별도 Helm 설치를 차단하지 않는다.

## PR

- 사용자 추가 승인에 따라 커밋과 push를 완료했다.
- main 대상 PR: https://github.com/seochanjin/news-lab/pull/75
- 최초 설정 커밋: `d7fc72c8ef8c3742f683779e5d59490df517b6a0`.
- 병합과 운영 적용은 수행하지 않았다.
