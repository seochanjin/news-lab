"""Daily topic pipeline report rendering."""


def render_report(result):
    analysis = result["analysis"]
    lines = [
        "# Daily topic pipeline report",
        "",
        "## Summary",
        "",
        f"- Dry-run: `{str(analysis['dry_run']).lower()}`",
        f"- Execute requested: `{str(analysis['execute_requested']).lower()}`",
        f"- Window hours: {analysis['window_hours']}",
        f"- Article count: {analysis['article_count']}",
        f"- Candidate articles: {analysis['candidate_articles']}",
        f"- Embedding created/updated/reused/failed: {analysis['embedding_created']} / {analysis['embedding_updated']} / {analysis['embedding_reused']} / {analysis['embedding_failed']}",
        f"- Clustering input count: {analysis['clustering_input_count']}",
        f"- Cluster count: {analysis['cluster_count']}",
        f"- Topic candidate count: {analysis['topic_candidate_count']}",
        f"- Selected topic count: {analysis['selected_topic_count']}",
        f"- Topic count: {analysis['topic_count']}",
        f"- Reference topic count: {analysis['reference_topic_count']}",
        f"- Selected article IDs: `{analysis['selected_article_ids']}`",
        f"- Selected article count: {analysis['selected_article_count']}",
        "- Topic ordering: `article_count desc, source_count desc, average similarity desc, latest published_at desc, topic_candidate_id asc`",
        f"- Embedding provider/model: `{analysis['embedding_provider']}` / `{analysis['embedding_model']}`",
        f"- Summary provider/model: `{analysis['summary_provider']}` / `{analysis['summary_model']}`",
        f"- Raw extraction performed: `{str(analysis['raw_extraction_performed']).lower()}`",
        f"- Raw extraction success/failure: {analysis['raw_extraction_success_count']} / {analysis['raw_extraction_failed_count']}",
        f"- Raw reused/extracted/failed/missing: {analysis['raw_reused_count']} / {analysis['raw_extracted_count']} / {analysis['raw_failed_count']} / {analysis['raw_missing_count']}",
        f"- Topic generated/saved/skipped/failed: {analysis['generated_topic_count']} / {analysis['saved_topic_count']} / {analysis['skipped_topic_count']} / {analysis['failed_topic_count']}",
        f"- Pipeline date/timezone: `{analysis['pipeline_date']}` / `{analysis['business_timezone']}`",
        f"- Pipeline date source: `{analysis['pipeline_date_source']}`",
        f"- DB write performed: `{str(analysis['db_write_performed']).lower()}`",
        f"- Pipeline elapsed seconds: {analysis['pipeline_elapsed_seconds']}",
        "",
        "## Selected Topics",
        "",
    ]
    summaries_by_topic = {
        summary["topic_candidate_id"]: summary
        for summary in result["topic_summaries"]
    }
    for topic in result["topics"]:
        lines.extend(
            _render_report_topic(
                topic,
                summary=summaries_by_topic.get(topic["topic_candidate_id"]),
            )
        )
    if not result["topics"]:
        lines.extend(["- None", ""])
    lines.extend(
        [
            "## Reference Candidates",
            "",
            "These candidates were outside `--max-topics` and are shown only for human review.",
            "They are not raw extraction, summary provider, or DB save targets.",
            "",
        ]
    )
    for topic in result["reference_topics"]:
        lines.extend(_render_report_topic(topic, reference=True))
    if not result["reference_topics"]:
        lines.extend(["- None", ""])
    lines.extend(
        [
            "## Safety",
            "",
            "- Embedding vectors and topic candidate intermediate results are memory-only.",
            "- Actual raw extraction and DB writes require explicit `--execute`.",
            "- Provider calls require explicit provider flags and API keys.",
            "",
        ]
    )
    return "\n".join(lines)


def _render_report_topic(topic, *, summary=None, reference=False):
    article_id_label = "Article IDs" if reference else "Selected article IDs"
    lines = [
        f"### {topic['topic_candidate_id']}",
        "",
        f"- Article count: {topic['article_count']}",
        f"- Source count: {topic['source_count']}",
    ]
    if reference:
        lines.append("- Reason: outside max-topics")
    lines.extend(
        [
            f"- {article_id_label}: `{topic['selected_article_ids']}`",
            f"- Similarity scores: `{topic['similarity_scores']}`",
            "",
            "#### Selected Articles" if not reference else "#### Reference Articles",
            "",
            "| role | article_id | similarity | source | published_at | title | url |",
            "| --- | ---: | ---: | --- | --- | --- | --- |",
        ]
    )
    for article in topic["articles"]:
        lines.append(
            f"| {_escape(article['role'])} "
            f"| {article['article_id']} "
            f"| {_format_similarity(article['similarity_score'])} "
            f"| {_escape(article['source'])} "
            f"| {_escape(article['published_at'])} "
            f"| {_escape(article['title'])} "
            f"| {_escape(article['url'])} |"
        )
    lines.append("")
    if summary is not None:
        lines.extend(
            [
                "#### Generated Summary",
                "",
                f"- Status: `{summary['status']}`",
                f"- title_ko: {_escape(summary['title_ko'])}",
                f"- summary_ko: {_escape(summary['summary_ko'])}",
                "- key_points:",
            ]
        )
        lines.extend(f"  - {_escape(point)}" for point in summary["key_points"])
        lines.extend(
            [
                f"- keywords: `{', '.join(summary['keywords'])}`",
                "",
            ]
        )
    return lines


def _format_similarity(value):
    return "" if value is None else f"{float(value):.4f}"


def _escape(value):
    return str(value or "").replace("|", "\\|").replace("\n", " ")
