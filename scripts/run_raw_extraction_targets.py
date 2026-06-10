import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts.analyze_raw_extraction_targets import (
    DEFAULT_MAX_CANDIDATES_PER_TOPIC,
    DEFAULT_MAX_TARGETS_PER_TOPIC,
    DEFAULT_SIMILARITY_THRESHOLD,
    analyze,
    get_raw_extraction_states,
)
from scripts.analyze_topic_groups import (
    DEFAULT_MAX_ARTICLES,
    SUPPORTED_WINDOWS,
    create_database_engine,
    get_articles,
)


MAX_EXECUTION_LIMIT = 5


def parse_args(argv=None):
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Raw extraction target execution planner (dry-run by default).",
    )
    window_group = parser.add_mutually_exclusive_group()
    window_group.add_argument(
        "--window-hours",
        type=int,
        choices=SUPPORTED_WINDOWS,
        default=24,
    )
    window_group.add_argument("--all", action="store_true")
    parser.add_argument(
        "--time-basis",
        choices=("published", "created"),
        default="published",
    )
    parser.add_argument("--max-articles", type=int, default=None)
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=DEFAULT_SIMILARITY_THRESHOLD,
    )
    parser.add_argument(
        "--max-candidates-per-topic",
        type=int,
        default=DEFAULT_MAX_CANDIDATES_PER_TOPIC,
    )
    parser.add_argument(
        "--max-targets-per-topic",
        type=int,
        default=DEFAULT_MAX_TARGETS_PER_TOPIC,
    )
    parser.add_argument("--limit", type=int)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--report-path", type=Path)
    args = parser.parse_args(argv)

    if args.max_articles is not None and args.max_articles <= 0:
        parser.error("--max-articles must be greater than zero")
    if not 0 <= args.similarity_threshold <= 1:
        parser.error("--similarity-threshold must be between zero and one")
    if args.max_candidates_per_topic <= 0:
        parser.error("--max-candidates-per-topic must be greater than zero")
    if not 1 <= args.max_targets_per_topic <= 3:
        parser.error("--max-targets-per-topic must be between 1 and 3")
    if args.limit is not None and not 1 <= args.limit <= MAX_EXECUTION_LIMIT:
        parser.error(f"--limit must be between 1 and {MAX_EXECUTION_LIMIT}")
    if args.execute and args.limit is None:
        parser.error("--execute requires an explicit --limit")

    args.effective_max_articles = args.max_articles or DEFAULT_MAX_ARTICLES
    args.use_embedding_provider = False
    return args


def build_execution_candidates(target_result, *, limit=None):
    candidates = []
    for topic in target_result["topic_candidates"]:
        for article in topic["articles"]:
            if article["extraction_target_status"] != "target":
                continue
            candidates.append(
                {
                    "article_id": article["id"],
                    "title": article["title"],
                    "source": article["source"],
                    "topic_candidate_id": topic["topic_candidate_id"],
                    "raw_extraction_status": article["raw_extraction_status"],
                    "decision_reason": article["extraction_target_reason"],
                    "execution_status": "planned",
                }
            )
    return candidates[:limit] if limit is not None else candidates


def build_execution_plan(target_result, args):
    candidates = build_execution_candidates(target_result, limit=args.limit)
    return {
        "analysis": {
            "dry_run": not args.execute,
            "execute_requested": args.execute,
            "limit": args.limit,
            "target_candidate_count": target_result["analysis"][
                "extraction_target_count"
            ],
            "execution_candidate_count": len(candidates),
            "raw_extraction_performed": False,
            "db_write_performed": False,
        },
        "target_analysis": target_result["analysis"],
        "execution_candidates": candidates,
        "execution_results": [],
    }


def execute_plan(plan, executor=None):
    if not plan["execution_candidates"]:
        return plan
    if executor is None:
        from scripts.extract_raw_articles import extract_selected_article_ids

        executor = extract_selected_article_ids

    results = executor(
        [candidate["article_id"] for candidate in plan["execution_candidates"]],
        limit=plan["analysis"]["limit"],
    )
    plan["analysis"]["raw_extraction_performed"] = True
    plan["analysis"]["db_write_performed"] = True
    plan["execution_results"] = results
    return plan


def run(rows, raw_states, args, provider=None, executor=None):
    target_result = analyze(rows, raw_states, args, provider=provider)
    plan = build_execution_plan(target_result, args)
    if args.execute:
        return execute_plan(plan, executor=executor)
    return plan


def render_execution_report(plan):
    analysis = plan["analysis"]
    lines = [
        "# Raw extraction target execution plan",
        "",
        "## Warning",
        "",
        "- Human review status: **Pending**",
        "- This report is not an approval to execute raw extraction.",
        "- Actual execution requires explicit human approval and `--execute --limit`.",
        "",
        "## Summary",
        "",
        f"- Dry-run: `{str(analysis['dry_run']).lower()}`",
        f"- Execute requested: `{str(analysis['execute_requested']).lower()}`",
        f"- Limit: `{analysis['limit']}`",
        f"- Target candidate count: {analysis['target_candidate_count']}",
        f"- Execution candidate count: {analysis['execution_candidate_count']}",
        f"- Raw extraction performed: `{str(analysis['raw_extraction_performed']).lower()}`",
        f"- DB write performed: `{str(analysis['db_write_performed']).lower()}`",
        "",
        "## Execution Candidates",
        "",
        "| Article ID | Topic ID | Title | Source | Raw Status | Decision Reason |",
        "| ---: | --- | --- | --- | --- | --- |",
    ]
    for candidate in plan["execution_candidates"]:
        lines.append(
            f"| {candidate['article_id']} "
            f"| {_escape(candidate['topic_candidate_id'])} "
            f"| {_escape(candidate['title'])} "
            f"| {_escape(candidate['source'])} "
            f"| {_escape(candidate['raw_extraction_status'])} "
            f"| {_escape(candidate['decision_reason'])} |"
        )
    if not plan["execution_candidates"]:
        lines.append("|  |  | None |  |  |  |")

    lines.extend(["", "## Execution Results", ""])
    if plan["execution_results"]:
        for result in plan["execution_results"]:
            lines.append(
                f"- Article {result['article_id']}: `{result['status']}`"
                + (
                    f" - {_escape(result.get('error_message'))}"
                    if result.get("error_message")
                    else ""
                )
            )
    else:
        lines.append("- None (dry-run execution plan only).")
    lines.append("")
    return "\n".join(lines)


def _escape(value):
    return str(value or "").replace("|", "\\|").replace("\n", " ")


def main():
    args = parse_args()
    engine = create_database_engine()
    with engine.connect() as connection:
        connection.execute(text("set transaction read only"))
        rows = get_articles(connection, args)
        raw_states = get_raw_extraction_states(
            connection,
            (row["id"] for row in rows),
        )

    target_result = analyze(rows, raw_states, args)
    result = build_execution_plan(target_result, args)
    if args.report_path:
        args.report_path.parent.mkdir(parents=True, exist_ok=True)
        args.report_path.write_text(render_execution_report(result), encoding="utf-8")
    if args.execute:
        result = execute_plan(result)
    if args.report_path:
        args.report_path.write_text(render_execution_report(result), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
