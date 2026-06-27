"""기간별 Topic pipeline에서 공유하는 기사 선정과 read-only 처리 helper를 제공한다.

이 package는 Daily, 3일, 7일처럼 저장 테이블과 실행 정책이 다른 pipeline 사이에
공통으로 사용할 수 있는 작은 처리 단위를 둔다. Topic 정렬과 관련·Summary 근거
기사 ID 선정, 기사 window 조회와 저장된 article embedding 검증을 담당하며,
provider 호출, clustering, DB 쓰기, migration 적용은 수행하지 않는다.
"""

from .selection import (
    attach_article_urls,
    selected_topic_article_ids,
    summary_topic_article_ids,
    topic_selection_key,
)

__all__ = [
    "attach_article_urls",
    "selected_topic_article_ids",
    "summary_topic_article_ids",
    "topic_selection_key",
]
