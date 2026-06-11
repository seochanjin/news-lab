"""Topic summary input, provider, and report helpers."""

import hashlib
import json
import math
import re
from collections import Counter
from collections.abc import Mapping, Sequence

import requests


DEFAULT_SUMMARY_MODEL = "gpt-5-nano"
SUPPORTED_SUMMARY_MODELS = {"gpt-5-nano", "gpt-5-mini"}
WORD_PATTERN = re.compile(r"[A-Za-z0-9가-힣]{2,}")


def build_topic_summary_inputs(
    topics: Sequence[dict],
    raw_texts: Mapping[int, str],
    *,
    max_topics: int,
    max_articles_per_topic: int,
    max_raw_chars_per_article: int,
) -> list[dict]:
    summary_inputs = []
    for original_order, topic in enumerate(topics):
        used_articles = []
        for article in topic["articles"]:
            raw_text = (raw_texts.get(article["id"]) or "").strip()
            if not raw_text:
                continue
            used_articles.append(
                {
                    "article_id": article["id"],
                    "title": article.get("title"),
                    "source": article.get("source"),
                    "raw_text_length": len(raw_text),
                    "raw_text": raw_text[:max_raw_chars_per_article],
                }
            )
            if len(used_articles) >= max_articles_per_topic:
                break

        summary_inputs.append(
            {
                "topic_candidate_id": topic["topic_candidate_id"],
                "status": "ready" if used_articles else "insufficient_raw_text",
                "source_count": len(
                    {
                        article["source"]
                        for article in used_articles
                        if article.get("source")
                    }
                ),
                "article_count": len(used_articles),
                "used_articles": used_articles,
                "_original_order": original_order,
            }
        )
    summary_inputs.sort(key=_summary_input_priority)
    return [
        {key: value for key, value in topic_input.items() if key != "_original_order"}
        for topic_input in summary_inputs[:max_topics]
    ]


class DeterministicSummaryProvider:
    provider = "deterministic"
    model = "deterministic-summary-v1"

    def summarize(self, topic_input: dict) -> dict:
        articles = topic_input["used_articles"]
        titles = [article["title"] or "제목 없음" for article in articles]
        sources = [article["source"] or "출처 미상" for article in articles]
        keywords = _keywords(titles)
        title = titles[0]
        summary = (
            f"이 주제는 '{title}'을 중심으로 {len(articles)}개 기사와 "
            f"{len(set(sources))}개 출처의 원문을 검토한 deterministic 요약입니다."
        )
        key_points = [
            f"{article['source'] or '출처 미상'}: "
            f"{article['title'] or '제목 없음'}"
            for article in articles
        ]
        return {
            "title_ko": f"주제 요약: {title}",
            "summary_ko": summary,
            "key_points": key_points,
            "keywords": keywords,
            "confidence": round(min(0.5 + 0.1 * len(articles), 0.8), 2),
        }


class OpenAISummaryProvider:
    provider = "openai"
    endpoint = "https://api.openai.com/v1/responses"

    def __init__(self, *, api_key: str, model: str = DEFAULT_SUMMARY_MODEL):
        if not api_key:
            raise ValueError("api_key is required")
        if model not in SUPPORTED_SUMMARY_MODELS:
            raise ValueError(f"unsupported summary model: {model}")
        self.api_key = api_key
        self.model = model

    def summarize(self, topic_input: dict) -> dict:
        response = requests.post(
            self.endpoint,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "input": _provider_prompt(topic_input),
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": "topic_summary",
                        "strict": True,
                        "schema": _summary_schema(),
                    }
                },
            },
            timeout=90,
        )
        response.raise_for_status()
        return parse_provider_response(response.json())


def summarize_topic_inputs(
    summary_inputs: Sequence[dict],
    provider,
) -> list[dict]:
    summaries = []
    for topic_input in summary_inputs:
        public_input = _public_topic_input(topic_input)
        public_input["summary_input_hash"] = build_summary_input_hash(topic_input)
        if topic_input["status"] == "insufficient_raw_text":
            summaries.append(
                {
                    **public_input,
                    "title_ko": None,
                    "summary_ko": None,
                    "key_points": [],
                    "keywords": [],
                    "confidence": 0.0,
                    "provider": provider.provider,
                    "model": provider.model,
                }
            )
            continue
        summary = provider.summarize(topic_input)
        summaries.append(
            {
                **public_input,
                **summary,
                "provider": provider.provider,
                "model": provider.model,
            }
        )
    return summaries


def build_summary_input_hash(topic_input: dict) -> str:
    payload = sorted(
        (
            {
                "article_id": article["article_id"],
                "raw_text": article["raw_text"],
            }
            for article in topic_input["used_articles"]
        ),
        key=lambda item: (item["article_id"], item["raw_text"]),
    )
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def parse_provider_response(payload: dict) -> dict:
    output_text = payload.get("output_text")
    if not output_text:
        for output in payload.get("output", []):
            for content in output.get("content", []):
                if content.get("type") == "output_text" and content.get("text"):
                    output_text = content["text"]
                    break
            if output_text:
                break
    if not output_text:
        raise ValueError("summary provider response did not contain output text")

    result = json.loads(output_text)
    if not isinstance(result, dict):
        raise ValueError("summary provider response must be a JSON object")

    required = {"title_ko", "summary_ko", "key_points", "keywords", "confidence"}
    missing = required - result.keys()
    if missing:
        raise ValueError(f"summary provider response missing fields: {sorted(missing)}")
    for field in ("title_ko", "summary_ko"):
        if not isinstance(result[field], str):
            raise ValueError(f"summary provider field `{field}` must be a string")
    for field in ("key_points", "keywords"):
        if not isinstance(result[field], list) or not all(
            isinstance(value, str) for value in result[field]
        ):
            raise ValueError(
                f"summary provider field `{field}` must be a list of strings"
            )

    confidence = result["confidence"]
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise ValueError("summary provider field `confidence` must be a number")
    confidence = float(confidence)
    if not math.isfinite(confidence):
        raise ValueError("summary provider field `confidence` must be finite")
    if not 0 <= confidence <= 1:
        raise ValueError("summary provider field `confidence` must be between 0 and 1")
    result["confidence"] = confidence
    return result


def render_topic_summary_report(result: dict) -> str:
    analysis = result["analysis"]
    lines = [
        "# Raw text topic summary report",
        "",
        "## Summary",
        "",
        "- Human review status: **Pending**",
        f"- Provider/model: `{analysis['provider']}` / `{analysis['model']}`",
        f"- Topic count: {analysis['topic_count']}",
        f"- Summarized topic count: {analysis['summarized_topic_count']}",
        f"- Insufficient raw text topic count: {analysis['insufficient_raw_text_topic_count']}",
        "- DB write performed: `false`",
        "- Raw extraction performed: `false`",
        "",
        "## Topic Summaries",
        "",
    ]
    for summary in result["topic_summaries"]:
        lines.extend(_render_topic_summary(summary))
    if not result["topic_summaries"]:
        lines.extend(["- None", ""])
    lines.extend(
        [
            "## Notes",
            "",
            "- Summary outputs are report-only and are not stored in the database.",
            "- Raw extraction was not run while generating this report.",
            "",
        ]
    )
    return "\n".join(lines)


def _render_topic_summary(summary: dict) -> list[str]:
    lines = [
        f"### {summary['topic_candidate_id']}",
        "",
        f"- Status: `{summary['status']}`",
        f"- Provider/model: `{summary['provider']}` / `{summary['model']}`",
        f"- Source count: {summary['source_count']}",
        f"- Article count: {summary['article_count']}",
    ]
    if summary["status"] == "insufficient_raw_text":
        lines.extend(["- Summary: `insufficient_raw_text`", ""])
        return lines

    lines.extend(
        [
            f"- Title: {_escape(summary['title_ko'])}",
            f"- Summary: {_escape(summary['summary_ko'])}",
            f"- Confidence: {summary['confidence']:.2f}",
            f"- Keywords: `{', '.join(summary['keywords'])}`",
            "",
            "#### Key Points",
            "",
        ]
    )
    lines.extend(f"- {_escape(point)}" for point in summary["key_points"])
    lines.extend(
        [
            "",
            "#### Used Articles",
            "",
            "| Article ID | Title | Source | Raw Text Length |",
            "| ---: | --- | --- | ---: |",
        ]
    )
    for article in summary["used_articles"]:
        lines.append(
            f"| {article['article_id']} | {_escape(article['title'])} "
            f"| {_escape(article['source'])} | {article['raw_text_length']} |"
        )
    lines.append("")
    return lines


def _keywords(titles: Sequence[str]) -> list[str]:
    counts = Counter(
        word.casefold()
        for title in titles
        for word in WORD_PATTERN.findall(title or "")
    )
    return [word for word, _ in counts.most_common(5)]


def _public_topic_input(topic_input: dict) -> dict:
    return {
        **{key: value for key, value in topic_input.items() if key != "used_articles"},
        "used_articles": [
            {key: value for key, value in article.items() if key != "raw_text"}
            for article in topic_input["used_articles"]
        ],
    }


def _summary_input_priority(topic_input: dict) -> tuple:
    return (
        topic_input["status"] != "ready",
        -topic_input["article_count"],
        -topic_input["source_count"],
        topic_input["_original_order"],
        topic_input["topic_candidate_id"],
    )


def _provider_prompt(topic_input: dict) -> str:
    return (
        "다음 뉴스 원문을 바탕으로 한국어 topic summary를 작성하세요. "
        "사실을 추가하지 말고 JSON schema에 맞춰 응답하세요.\n"
        + json.dumps(topic_input, ensure_ascii=False, default=str)
    )


def _summary_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "title_ko": {"type": "string"},
            "summary_ko": {"type": "string"},
            "key_points": {"type": "array", "items": {"type": "string"}},
            "keywords": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": "number"},
        },
        "required": [
            "title_ko",
            "summary_ko",
            "key_points",
            "keywords",
            "confidence",
        ],
        "additionalProperties": False,
    }


def _escape(value) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")
