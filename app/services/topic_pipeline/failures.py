"""Topic 실패 사유를 run 이력에 남길 요약 문자열로 집계한다.

Topic별 실패는 지금까지 ``LOGGER.warning``으로만 남았다. Pod가 정리되면 사라지므로
``partial_success`` run의 원인을 나중에 확인할 방법이 없었다. 실제로 부분 실패
38.3%의 원인을 특정하는 데 Production SQL 조회 6회가 필요했고, 그마저도 사유를
직접 읽은 것이 아니라 다른 table에서 역추적한 결과였다.

run 이력 table의 ``error_message``는 1000자 상한이 있으므로 개별 사유를 모두
남기지 않는다. 사유별 건수만 집계해 어떤 유형이 지배적인지 판별할 수 있게 한다.
"""

MAX_ERROR_MESSAGE_LENGTH = 1000
MAX_REASON_LENGTH = 200


def summarize_topic_failure_reasons(
    failures,
    *,
    max_length: int = MAX_ERROR_MESSAGE_LENGTH,
) -> str | None:
    """Topic 실패 목록을 사유별 건수 요약으로 변환한다.

    실패가 없으면 None을 반환한다. 성공한 run의 ``error_message``를 빈 문자열로
    채우면 "사유가 없다"와 "사유를 기록하지 않았다"를 구분할 수 없기 때문이다.

    건수가 많은 사유부터 남긴다. 상한을 넘으면 남은 유형 수를 표시한다.
    지배적인 사유를 먼저 보여주는 것이 목적이므로 전부 남기려고 잘라내지 않는다.
    """

    if not failures:
        return None

    reason_counts = {}
    for failure in failures:
        reason = failure.get("error") or "unknown error"
        reason = " ".join(str(reason).split())
        reason = reason[:MAX_REASON_LENGTH]
        reason_counts[reason] = reason_counts.get(reason, 0) + 1

    ordered_reasons = sorted(
        reason_counts.items(),
        key=lambda item: (-item[1], item[0]),
    )

    kept_parts = []
    for reason, count in ordered_reasons:
        part = f"{reason} x{count}"
        remaining = len(ordered_reasons) - (len(kept_parts) + 1)
        candidate = "; ".join(kept_parts + [part])
        if remaining > 0:
            candidate = f"{candidate}; (+{remaining} more)"
        if len(candidate) > max_length:
            break
        kept_parts.append(part)

    if not kept_parts:
        # 사유 하나조차 상한을 넘는 경우다. 잘라서라도 남긴다.
        return ordered_reasons[0][0][:max_length]

    message = "; ".join(kept_parts)
    remaining = len(ordered_reasons) - len(kept_parts)
    if remaining > 0:
        message = f"{message}; (+{remaining} more)"

    # 생략 표시의 자릿수가 늘어나 상한을 1~2자 넘길 수 있으므로 마지막에 자른다.
    return message[:max_length]
