# PR 초안: NewsLab API와 Redis를 replicas 0으로 보관

운영 종료 후에도 배포 파일을 다시 적용하면 API 2개와 Redis 1개가 실행될 수 있었다.
두 Deployment의 replicas를 0으로 바꿔 저장소도 중지 상태로 맞춘다.
이미지, Service, Ingress, Secret 참조와 CronJob suspend 설정은 유지한다.

검증: [verification](../verification/codex-retire-newslab-replicas.md)에 기록한
YAML 13개 파싱, replicas 외 설정 동일, CronJob 4개 중지, HPA 부재, 공백 검사 통과.

사용자 요청으로 main 대상 PR을 준비한다. 이 PR 작업에는 운영 적용이나 병합이 포함되지 않는다.
