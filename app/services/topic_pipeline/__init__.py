"""기간별 Topic pipeline이 공유하는 순수 기사 선정 helper를 공개한다.

Daily와 3일 pipeline의 clustering 이후 Topic 정렬, 관련 기사 ID 수집과 Summary
근거 기사 중복 제거 정책을 한 구현으로 유지한다. 이 package는 provider 호출,
원문 조회, 파일 또는 DB 쓰기를 수행하지 않는다.
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
