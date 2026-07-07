# NewsLab README 한글 표기 및 용어 정합성 개선

## 작업 목적

- README를 국내 독자가 자연스럽게 읽을 수 있도록 한국어 중심으로 정리한다.
- 기술명, 코드, 명령어, 파일 경로, API endpoint, 실제 리소스명은 원문으로 유지한다.
- 기존 데이터 파이프라인, 인프라, 운영 원칙의 사실관계를 바꾸지 않는다.

## 기존 문제

- README의 주요 section heading과 설명 문장이 영어 중심으로 남아 있었다.
- `Topic`, `backend`, `Architecture`, `Data Pipeline`, `Observability` 등 일반 설명 용어가 한글과 영어로 혼용되어 있었다.
- 사람 승인 기반 운영 원칙은 설명되어 있었지만 `Human-in-the-loop` 용어의 한국어 의미가 함께 제시되지 않았다.

## 변경 내용

- 운영 서비스, 데이터 파이프라인, 아키텍처, 인프라와 배포, 관측성, agent workflow, 문서, 로컬 개발 section을 한국어 중심으로 정리했다.
- `Topic`은 최초 1회 `토픽(Topic)`으로 설명하고 이후에는 `토픽` 중심으로 정리했다.
- `Human-in-the-loop`은 `사람 승인 기반(Human-in-the-loop)`으로 설명했다.
- 기술명과 제품명, 운영 URL, 아키텍처 이미지 참조, 실제 리소스명은 유지했다.

## 테스트

- README heading과 일반 설명 영어 표현 잔존 여부를 `rg`로 확인했다.
- 기술명과 운영 URL, 아키텍처 이미지 참조, 오래된 도메인 미포함 여부를 `rg`로 확인했다.
- `docs/ARCHITECTURE.md`, `docs/RUNBOOK.md`, `docs/images/newslab-architecture.png` 파일 존재를 확인했다.
- `git diff --check`로 Markdown 공백과 diff 형식 오류가 없음을 확인했다.
- `git diff --name-only -- app scripts k8s db .github Dockerfile docker-compose.yml requirements.txt`로 scope 밖 코드와 인프라 변경이 없음을 확인했다.
- 상세 command와 결과는 `docs/verification/fix-readme-korean-localization.md`에 기록했다.

## 운영 반영

- 운영 반영 없음.
- Production rollout, deployment, Supabase SQL, production verification은 수행하지 않았다.

## 확인 결과

- README의 주요 heading과 일반 설명 문장이 한국어 중심으로 정리됐다.
- 운영 URL, 이미지 경로와 대체 텍스트, 데이터 파이프라인 구조, K3s 노드와 리소스 설명의 핵심 사실관계는 유지됐다.
- 애플리케이션 코드, DB, API, K3s manifest, GitHub Actions workflow, Dockerfile, dependency는 변경하지 않았다.

## 이번 단계의 의미

- README의 채용용 가독성을 높이면서 운영 증거와 상세 문서 링크를 유지했다.
- 자동 CD나 관측성 수준을 과장하지 않고 사람이 통제하는 운영 원칙을 유지했다.

## 다음 단계

- Review가 필요한 경우 `docs/verification/fix-readme-korean-localization.md`의 실제 검증 결과를 기준으로 진행한다.
