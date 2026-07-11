# Backend Immutable Image GitOps Design

[Architecture index로 돌아가기](../ARCHITECTURE.md)

이 문서는 `news-api` Backend workload를 `latest` image 기준에서 full Git SHA
image 기준으로 전환하기 위한 현재 구조 조사와 설계 결정을 기록한다. 실제
workflow 구현, manifest tag 변경, Argo CD Sync, rollout, rollback과 restore는
후속 UNIT에서 별도로 수행한다.

## UNIT-01 조사 결과

### Backend image build workflow

현재 Backend image build workflow는 `.github/workflows/docker-build.yml` 하나다.

| 항목 | 현재 값 |
| --- | --- |
| Trigger | `main` branch push, `workflow_dispatch` |
| Path filter | `app/**`, `scripts/**`, `requirements.txt`, `Dockerfile`, `.github/workflows/docker-build.yml` |
| Runner | `ubuntu-latest` |
| Build action | `docker/build-push-action@v6` |
| Platform | `linux/arm64` |
| Push | `true` |
| SHA tag | `${{ secrets.DOCKERHUB_USERNAME }}/news-api:${{ github.sha }}` |
| Compatibility tag | `${{ secrets.DOCKERHUB_USERNAME }}/news-api:latest` |

`${{ github.sha }}`는 GitHub Actions event의 commit SHA이므로 `main` push에서는
merge 결과 commit을 가리킨다. Backend workflow는 이미 full Git SHA tag를
발행하도록 작성되어 있지만, Docker Hub에 특정 SHA tag가 실제 존재하는지는
후속 UNIT에서 `docker buildx imagetools inspect`로 확인해야 한다.

현재 workflow에는 repository-level `permissions`가 명시되어 있지 않다. 후속
workflow 변경에서는 Docker Hub login에 필요한 registry credential만 사용하고,
manifest PR 생성 job에만 `contents: write`와 `pull-requests: write`를 부여한다.

### Backend workload manifest

현재 `k8s/`의 Backend workload image reference는 모두 `seocj/news-api:latest`다.

| File | Resource | 현재 image |
| --- | --- | --- |
| `k8s/news-api.yaml` | `Deployment/news-api` | `seocj/news-api:latest` |
| `k8s/news-rss-collector-cronjob.yaml` | `CronJob/news-rss-collector` | `seocj/news-api:latest` |
| `k8s/news-daily-topic-pipeline-cronjob.yaml` | `CronJob/news-daily-topic-pipeline` | `seocj/news-api:latest` |
| `k8s/news-three-day-topic-pipeline-cronjob.yaml` | `CronJob/news-three-day-topic-pipeline` | `seocj/news-api:latest` |
| `k8s/news-weekly-topic-pipeline-cronjob.yaml` | `CronJob/news-weekly-topic-pipeline` | `seocj/news-api:latest` |

이번 task의 immutable image 전환 대상은 위 다섯 workload image reference다.
Service, Ingress, selector, port, probe, resource request/limit, CronJob schedule,
command, `suspend`, concurrency policy와 Secret reference는 변경 대상이 아니다.

### Argo CD 관리 범위

`k8s/argocd/news-api-application.yaml`의 `news-api` Application은 다음 source를
추적한다.

| 항목 | 값 |
| --- | --- |
| Repository | `https://github.com/seochanjin/news-lab.git` |
| Revision | `main` |
| Path | `k8s` |
| Recurse | `false` |
| Exclude | `cluster-issuer.yaml` |
| Destination | in-cluster Kubernetes API |
| Namespace | `default` |

Application manifest에는 `spec.syncPolicy.automated`가 없다. 따라서 automated
sync, automatic prune, automatic self-heal은 사용하지 않고 Manual Sync 정책을
유지한다.

`recurse: false`이므로 `k8s/argocd/`와 `k8s/monitoring/` 하위 파일은
`news-api` workload Application source에 포함되지 않는다. `cluster-issuer.yaml`
도 directory exclude로 제외된다. 따라서 관리 대상은 다음 일곱 resource로
제한한다.

- `Deployment/news-api`
- `Service/news-api`
- `Ingress/news-api-ingress`
- `CronJob/news-rss-collector`
- `CronJob/news-daily-topic-pipeline`
- `CronJob/news-three-day-topic-pipeline`
- `CronJob/news-weekly-topic-pipeline`

Immutable image 전환 시 Argo CD diff는 위 resource 중 Deployment와 네 CronJob의
image tag 변경만 포함되어야 한다. `ClusterIssuer/letsencrypt-prod`, Secret,
Service, Ingress, Application spec, monitoring resource 변경은 이번 task의
diff에 포함하지 않는다.

## 확정 설계

### Image tag 정책

운영 manifest의 Backend image는 `seocj/news-api:<full-git-sha>` 형식으로
전환한다. `<full-git-sha>`는 40자리 lowercase hexadecimal Git commit SHA다.

`latest` tag는 Docker Hub 호환 목적의 보조 tag로 계속 발행할 수 있지만,
K3s workload manifest와 Argo CD desired state에서는 사용하지 않는다. Rollback
기준으로도 `latest`를 사용하지 않는다.

Deployment와 네 CronJob은 항상 동일한 full Git SHA tag를 사용한다. 서로 다른
SHA가 섞이면 API와 scheduled pipeline의 실행 코드가 달라지므로 manifest update
PR과 정적 검증에서 차단한다.

### Manifest update PR 방식

Image build workflow가 full Git SHA image build/push에 성공한 뒤 manifest update
job이 별도 branch와 PR을 생성한다. `main`에 직접 commit하거나 push하지 않는다.

후속 구현에서 사용할 기본 방식은 `peter-evans/create-pull-request` action이다.
이 action은 `GITHUB_TOKEN`으로 branch 생성과 PR 생성을 처리할 수 있어 별도 PAT를
새로 도입하지 않아도 된다. 필요한 repository setting에서 `GITHUB_TOKEN`의
workflow write 권한이 허용되어 있어야 하며, workflow file에는 job 단위로 다음
최소 권한만 부여한다.

- build job: repository content read와 Docker Hub login secret 사용
- manifest update job: `contents: write`, `pull-requests: write`

Manifest update branch 이름은 동일 SHA 재실행 시 같은 branch를 재사용하도록
`bot/update-news-api-image-${{ github.sha }}` 형식을 사용한다. PR title과 body에도
같은 full SHA를 기록한다. 같은 SHA에서 workflow를 재실행하면 기존 branch와 PR을
업데이트하거나 no-op 처리해 중복 PR 생성을 피한다.

Manifest update commit은 다섯 workload image reference만 같은 SHA로 바꾼다.
Commit message와 PR body에는 다음 추적 정보를 포함한다.

- source repository: `seochanjin/news-lab`
- source commit: full `${{ github.sha }}`
- image: `seocj/news-api:${{ github.sha }}`
- 대상 resource: `Deployment/news-api`와 네 CronJob

### Workflow sequencing

Manifest update는 image build가 성공한 뒤에만 실행한다. 같은 workflow 안에서는
manifest update job이 build job을 `needs`로 의존하게 한다. 별도 workflow로
분리할 경우에는 build workflow의 successful `workflow_run`에만 반응해야 한다.

초기 구현은 같은 workflow 안에서 `build`와 `update-manifest` job을 분리하는
방식이 가장 단순하다. 이렇게 하면 source commit SHA와 image tag가 같은
workflow context에서 유지되고, manifest update가 build 실패 뒤 실행될 위험을
줄일 수 있다.

### 정적 검증

후속 UNIT에서 manifest가 immutable image로 전환되면 다음 조건을 정적 검증한다.

- `k8s/` workload manifest에 `seocj/news-api:latest`가 없다.
- `Deployment/news-api`와 네 CronJob image가 모두 `seocj/news-api:<sha>` 형식이다.
- 다섯 image tag는 모두 같은 값이다.
- tag는 40자리 lowercase hexadecimal SHA다.
- YAML syntax가 유효하다.
- workflow에는 full `${{ github.sha }}` 또는 동등한 40자리 SHA source가 사용된다.
- manifest update는 build 성공 이후에만 실행된다.
- workflow permission은 필요한 job에만 제한된다.

### Argo CD 승인 gate

Manifest update PR merge 후 사람이 Argo CD `news-api` Application을 refresh하고
diff를 확인한다. 기대 상태는 다음이다.

- Application sync policy는 Manual이다.
- Application은 `OutOfSync`를 감지한다.
- diff는 `Deployment/news-api`와 네 CronJob의 image tag 변경으로 제한된다.
- Service, Ingress, Secret, `ClusterIssuer`, Application spec, CronJob schedule,
  command, selector, port, resource 값의 변경은 없어야 한다.

Manual Sync는 사람이 diff를 승인한 뒤에만 실행한다. Agent는 `argocd app sync`,
`kubectl rollout`, `kubectl apply`, rollback/restore 변경 명령을 자동 실행하지
않는다.

### Rollback과 restore 기준

이전 정상 SHA는 다음 조건을 모두 만족하는 revision에서 고른다.

- Docker Hub에 `seocj/news-api:<sha>` image가 존재한다.
- image manifest에 `linux/arm64` platform이 포함된다.
- 해당 SHA가 운영에서 `Synced`, `Healthy`, Deployment rollout 성공,
  Pod image 일치와 production `/health` 정상으로 확인된 기록이 있다.
- DB schema, Secret, ConfigMap, CronJob command와 호환된다.

Controlled rollback은 이전 정상 SHA로 manifest update PR을 만들고 사람이 merge,
Argo CD diff 확인, Manual Sync, rollout과 `/health` 확인을 수행하는 방식으로
진행한다. Restore도 같은 방식으로 최신 SHA를 다시 manifest에 반영한다.

Rollback과 restore 결과는 실제 실행 command, Git revision, image tag, Argo CD
Sync result, running Pod image, CronJob image와 `/health` 결과가 있을 때만
Verification에 완료로 기록한다.

## UNIT-01에서 변경하지 않는 범위

UNIT-01은 조사와 설계 확정만 수행한다. 다음은 후속 UNIT에서 다룬다.

- GitHub Actions workflow 구현 변경
- Kubernetes workload image tag 변경
- Docker Hub image 존재 확인
- Argo CD refresh, diff, Manual Sync
- K3s rollout, running Pod image 확인
- production `/health` 확인
- controlled rollback과 restore 실행

## UNIT-02 구현 결과

UNIT-02에서는 `.github/workflows/docker-build.yml`의 Backend image build/push
job만 수정했다. Manifest update branch/PR 생성, Kubernetes workload image tag
변경, Docker Hub image 조회, Argo CD diff/Sync와 운영 rollout은 후속 UNIT 범위로
남겼다.

변경한 build/push 정책은 다음과 같다.

- Workflow 권한을 repository contents read-only인 `contents: read`로 명시했다.
- Docker Hub 대상 image repository를 `seocj/news-api`로 고정했다.
- Build 전에 `GITHUB_SHA`가 40자리 lowercase hexadecimal Git SHA인지 검증한다.
- `docker/build-push-action@v6`는 `linux/arm64` image를 build/push한다.
- Primary tag는 `seocj/news-api:${{ github.sha }}`이며, `latest`는 Docker Hub
  호환용 보조 tag로만 계속 발행한다.

이 변경은 GitHub Actions build job의 source commit과 Docker image tag를 같은
full Git SHA로 연결한다. K3s workload manifest는 아직 `latest`를 사용하므로,
운영 desired state의 immutable image 전환은 UNIT-04에서 별도로 수행한다.

## UNIT-03 구현 결과

UNIT-03에서는 `.github/workflows/docker-build.yml`에 image build 성공 이후
Kubernetes manifest image tag 갱신 branch와 PR을 생성하는 `update-manifest` job을
추가했다. Kubernetes workload manifest의 현재 image 값을 직접 변경하는 작업은
UNIT-04 범위로 남겼다.

변경한 manifest update 정책은 다음과 같다.

- `update-manifest` job은 `needs: build`로 image build/push 성공 이후에만
  실행되며, `main` branch context에서만 manifest PR을 만든다.
- `build` job 권한은 `contents: read`로 유지하고, `update-manifest` job에만
  `contents: write`, `pull-requests: write`를 부여했다.
- manifest 갱신 script는 `GITHUB_SHA`가 40자리 lowercase hexadecimal SHA인지
  확인한 뒤 `Deployment/news-api`와 네 CronJob manifest의 `seocj/news-api:*`
  image reference를 모두 `seocj/news-api:${{ github.sha }}`로 갱신한다.
- 같은 job 안에서 다섯 workload image 수, tag 일치, full SHA 형식과 workflow
  SHA 일치를 검증한다.
- `peter-evans/create-pull-request@v6`가
  `bot/update-news-api-image-${{ github.sha }}` branch를 사용해 `main` 대상 PR을
  생성한다. 같은 SHA workflow 재실행은 같은 branch를 재사용해 중복 PR 생성을
  줄인다.
- PR 제목, commit message와 body에는 source commit, image, 대상 resource 목록을
  기록해 application code PR merge commit과 manifest update PR을 추적할 수 있게
  했다.

이 변경은 manifest update branch와 PR 생성 workflow만 구현한다. 실제 Docker Hub
image 존재 확인, manifest PR merge, Argo CD OutOfSync/diff, Manual Sync, rollout,
production `/health`, rollback/restore 검증은 후속 UNIT 또는 사람이 수행할
검증으로 남아 있다.

## UNIT-04 구현 결과

UNIT-04에서는 K8s Backend workload manifest의 desired image를 `latest`에서
동일한 full Git SHA tag로 전환했다. 기준 SHA는 현재 브랜치 HEAD인
`5cbb040f3efe858c7a898ddae611f00ad1d2aeb5`다.

전환 대상은 다음 다섯 workload image reference로 제한했다.

| File | Resource | image |
| --- | --- | --- |
| `k8s/news-api.yaml` | `Deployment/news-api` | `seocj/news-api:5cbb040f3efe858c7a898ddae611f00ad1d2aeb5` |
| `k8s/news-rss-collector-cronjob.yaml` | `CronJob/news-rss-collector` | `seocj/news-api:5cbb040f3efe858c7a898ddae611f00ad1d2aeb5` |
| `k8s/news-daily-topic-pipeline-cronjob.yaml` | `CronJob/news-daily-topic-pipeline` | `seocj/news-api:5cbb040f3efe858c7a898ddae611f00ad1d2aeb5` |
| `k8s/news-three-day-topic-pipeline-cronjob.yaml` | `CronJob/news-three-day-topic-pipeline` | `seocj/news-api:5cbb040f3efe858c7a898ddae611f00ad1d2aeb5` |
| `k8s/news-weekly-topic-pipeline-cronjob.yaml` | `CronJob/news-weekly-topic-pipeline` | `seocj/news-api:5cbb040f3efe858c7a898ddae611f00ad1d2aeb5` |

Service, Ingress, selector, port, probe, resource request/limit, CronJob schedule,
command, `suspend`, concurrency policy와 Secret reference는 변경하지 않았다.

로컬 정적 검증에서 다음을 확인했다.

- `k8s/` workload manifest에 `seocj/news-api:latest`가 남아 있지 않다.
- `Deployment/news-api`와 네 CronJob이 모두 같은 SHA image를 사용한다.
- tag는 40자리 lowercase hexadecimal SHA다.
- `k8s/*.yaml` YAML syntax가 유효하다.
- `.github/workflows/docker-build.yml`은 full `${{ github.sha }}` image tag,
  `needs: build`, `github.ref == 'refs/heads/main'`, `contents: write`,
  `pull-requests: write`와 `peter-evans/create-pull-request@v6`를 유지한다.

`actionlint`는 현재 로컬 환경에 설치되어 있지 않아 실행하지 못했다. Docker Hub
image 존재와 ARM64 platform, manifest PR merge, Argo CD OutOfSync/diff, Manual
Sync, rollout, production `/health`, controlled rollback/restore는 후속 UNIT 또는
사람이 수행할 검증으로 남아 있다.
