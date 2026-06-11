import json
import sys
from datetime import date
from pathlib import Path

from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts.generate_topic_summary_report import (
    create_database_engine,
    create_argument_parser,
    generate,
    get_articles,
    get_raw_texts,
    parse_args as parse_generation_args,
)


UPSERT_TOPIC_QUERY = text("""
    insert into topics (
        topic_date, topic_candidate_id, title_ko, summary_ko, key_points,
        keywords, confidence, provider, model, status, source_count,
        article_count, summary_input_hash
    ) values (
        :topic_date, :topic_candidate_id, :title_ko, :summary_ko,
        cast(:key_points as jsonb), cast(:keywords as jsonb), :confidence,
        :provider, :model, :status, :source_count, :article_count,
        :summary_input_hash
    )
    on conflict (summary_input_hash, provider, model) do update set
        topic_candidate_id = excluded.topic_candidate_id,
        title_ko = excluded.title_ko,
        summary_ko = excluded.summary_ko,
        key_points = excluded.key_points,
        keywords = excluded.keywords,
        confidence = excluded.confidence,
        provider = excluded.provider,
        model = excluded.model,
        status = excluded.status,
        source_count = excluded.source_count,
        article_count = excluded.article_count,
        updated_at = now()
    returning id
""")
DELETE_TOPIC_ARTICLES_QUERY = text(
    "delete from topic_articles where topic_id = :topic_id"
)
INSERT_TOPIC_ARTICLE_QUERY = text("""
    insert into topic_articles (topic_id, article_id, role, similarity_score)
    values (:topic_id, :article_id, :role, :similarity_score)
    on conflict (topic_id, article_id) do nothing
""")


def parse_args(argv=None):
    parser = create_argument_parser(
        description="Save topic summaries (dry-run by default).",
    )
    parser.add_argument("--execute", action="store_true")
    return parse_generation_args(argv, parser=parser)


def build_save_plan(generation_result: dict, args) -> dict:
    topics = []
    skipped = []
    for summary in generation_result["topic_summaries"]:
        if summary["status"] != "ready":
            skipped.append(
                {
                    "topic_candidate_id": summary["topic_candidate_id"],
                    "reason": "insufficient_raw_text",
                }
            )
            continue
        used_articles = [
            {
                "article_id": article["article_id"],
                "role": "representative",
                "similarity_score": None,
            }
            for article in summary["used_articles"]
        ]
        topics.append(
            {
                "topic_date": date.today(),
                "topic_candidate_id": summary["topic_candidate_id"],
                "title_ko": summary["title_ko"],
                "summary_ko": summary["summary_ko"],
                "key_points": summary["key_points"],
                "keywords": summary["keywords"],
                "confidence": summary["confidence"],
                "provider": summary["provider"],
                "model": summary["model"],
                "status": "draft",
                "source_count": summary["source_count"],
                "article_count": summary["article_count"],
                "summary_input_hash": summary["summary_input_hash"],
                "articles": used_articles,
                "save_status": "planned",
                "topic_id": None,
            }
        )
    return {
        "analysis": {
            "dry_run": not args.execute,
            "execute_requested": args.execute,
            "db_write_performed": False,
            "raw_extraction_performed": False,
            "provider": generation_result["analysis"]["provider"],
            "model": generation_result["analysis"]["model"],
            "topic_count": len(generation_result["topic_summaries"]),
            "save_candidate_count": len(topics),
            "saved_topic_count": 0,
            "skipped_topic_count": len(skipped),
            "linked_article_count": 0,
        },
        "topics": topics,
        "skipped_topics": skipped,
    }


def execute_save_plan(plan: dict, connection) -> dict:
    for topic in plan["topics"]:
        params = {
            **{key: value for key, value in topic.items() if key != "articles"},
            "key_points": json.dumps(topic["key_points"], ensure_ascii=False),
            "keywords": json.dumps(topic["keywords"], ensure_ascii=False),
        }
        params.pop("save_status")
        params.pop("topic_id")
        topic_id = connection.execute(UPSERT_TOPIC_QUERY, params).scalar_one()
        connection.execute(DELETE_TOPIC_ARTICLES_QUERY, {"topic_id": topic_id})
        for article in topic["articles"]:
            connection.execute(
                INSERT_TOPIC_ARTICLE_QUERY,
                {"topic_id": topic_id, **article},
            )
        topic["topic_id"] = topic_id
        topic["save_status"] = "saved"

    plan["analysis"]["db_write_performed"] = bool(plan["topics"])
    plan["analysis"]["saved_topic_count"] = len(plan["topics"])
    plan["analysis"]["linked_article_count"] = sum(
        len(topic["articles"]) for topic in plan["topics"]
    )
    return plan


def render_save_report(plan: dict) -> str:
    analysis = plan["analysis"]
    lines = [
        "# Topic summary save report",
        "",
        "## Summary",
        "",
        f"- Dry-run: `{str(analysis['dry_run']).lower()}`",
        f"- Execute requested: `{str(analysis['execute_requested']).lower()}`",
        f"- DB write performed: `{str(analysis['db_write_performed']).lower()}`",
        "- Raw extraction performed: `false`",
        f"- Provider/model: `{analysis['provider']}` / `{analysis['model']}`",
        f"- Topic count: {analysis['topic_count']}",
        f"- Save candidate count: {analysis['save_candidate_count']}",
        f"- Saved topic count: {analysis['saved_topic_count']}",
        f"- Skipped topic count: {analysis['skipped_topic_count']}",
        f"- Linked article count: {analysis['linked_article_count']}",
        "",
        "## Topics",
        "",
    ]
    for topic in plan["topics"]:
        lines.append(
            f"- `{topic['topic_candidate_id']}`: `{topic['save_status']}`, "
            f"topic_id=`{topic['topic_id']}`, articles={len(topic['articles'])}"
        )
    if not plan["topics"]:
        lines.append("- None")
    lines.extend(["", "## Skipped Topics", ""])
    for skipped in plan["skipped_topics"]:
        lines.append(
            f"- `{skipped['topic_candidate_id']}`: `{skipped['reason']}`"
        )
    if not plan["skipped_topics"]:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def main():
    args = parse_args()
    engine = create_database_engine()
    if args.execute:
        with engine.begin() as connection:
            result = _generate_with_connection(connection, args)
            plan = execute_save_plan(build_save_plan(result, args), connection)
    else:
        with engine.connect() as connection:
            connection.execute(text("set transaction read only"))
            result = _generate_with_connection(connection, args)
        plan = build_save_plan(result, args)

    if args.report_path:
        args.report_path.parent.mkdir(parents=True, exist_ok=True)
        args.report_path.write_text(render_save_report(plan), encoding="utf-8")
    print(json.dumps(plan, ensure_ascii=False, indent=2, default=str))


def _generate_with_connection(connection, args):
    rows = get_articles(connection, args)
    raw_texts = get_raw_texts(connection, (row["id"] for row in rows))
    return generate(rows, raw_texts, args)


if __name__ == "__main__":
    main()
