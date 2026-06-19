import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATION = REPO_ROOT / "db" / "migrations" / "006_create_article_embeddings.sql"


class ArticleEmbeddingMigrationTests(unittest.TestCase):
    def test_migration_defines_pgvector_table_and_constraints(self):
        sql = MIGRATION.read_text(encoding="utf-8").lower()

        self.assertIn("create extension if not exists vector", sql)
        self.assertIn("create table if not exists article_embeddings", sql)
        self.assertIn("article_id bigint", sql)
        self.assertIn("references articles(id) on delete cascade", sql)
        self.assertIn("embedding vector(1536)", sql)
        self.assertIn("dimension integer not null check (dimension = 1536)", sql)
        self.assertIn(
            "unique (article_id, provider, model, source_text_type)",
            sql,
        )
        self.assertNotIn("using hnsw", sql)
        self.assertNotIn("using ivfflat", sql)


if __name__ == "__main__":
    unittest.main()
