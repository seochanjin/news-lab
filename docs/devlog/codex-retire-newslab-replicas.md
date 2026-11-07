# Devlog: NewsLab 종료 상태를 배포 설정에 반영

- API replicas 2 → 0, Redis replicas 1 → 0으로 변경했다.
- 주석에 종료 목적과 기존 수량을 남겼다.
- YAML 의미 비교로 replicas 외 설정이 동일함을 확인했다.
- CronJob 4개의 suspend=true 유지 및 HPA 부재를 확인했다.
- 실제 결과: [verification](../verification/codex-retire-newslab-replicas.md).
- 운영 서버는 변경하지 않았다. 로컬 검증 뒤 사용자에게 커밋, push, main 대상 PR 생성 요청을 받았다.
