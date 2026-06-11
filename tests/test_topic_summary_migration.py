import unittest
from pathlib import Path


MIGRATION = Path("db/migrations/005_create_topics_tables.sql")


class TopicSummaryMigrationTests(unittest.TestCase):
    def test_migration_defines_topic_tables_constraints_and_indexes(self):
        sql = MIGRATION.read_text(encoding="utf-8").lower()

        self.assertIn("create table if not exists topics", sql)
        self.assertIn("create table if not exists topic_articles", sql)
        self.assertIn("references topics(id)", sql)
        self.assertIn("references articles(id)", sql)
        self.assertIn("unique (summary_input_hash, provider, model)", sql)
        self.assertIn("unique (topic_id, article_id)", sql)
        self.assertIn("idx_topics_topic_date", sql)
        self.assertIn("idx_topic_articles_topic_id", sql)


if __name__ == "__main__":
    unittest.main()
