import unittest

from app.utils.article_embedding_storage import (
    build_article_embedding_input,
    find_similar_article_embeddings,
    hash_source_text,
    store_article_embedding,
)


class FakeMappings:
    def __init__(self, *, first=None, rows=None):
        self._first = first
        self._rows = rows or []

    def first(self):
        return self._first

    def all(self):
        return self._rows


class FakeResult:
    def __init__(self, *, first=None, rows=None):
        self._mappings = FakeMappings(first=first, rows=rows)

    def mappings(self):
        return self._mappings


class FakeConnection:
    def __init__(
        self,
        *,
        existing=None,
        similarity_rows=None,
        upsert_inserted=True,
    ):
        self.existing = existing
        self.similarity_rows = similarity_rows or []
        self.upsert_inserted = upsert_inserted
        self.calls = []

    def execute(self, statement, params):
        sql = str(statement)
        self.calls.append((sql, params))
        if "select id, source_text_hash" in sql:
            return FakeResult(first=self.existing)
        if "as similarity" in sql:
            return FakeResult(rows=self.similarity_rows)
        if "on conflict" in sql:
            return FakeResult(first={"inserted": self.upsert_inserted})
        return FakeResult()


class FakeProvider:
    def __init__(self, *, model="test-model", embedding=None):
        self.model = model
        self.embedding = embedding or [0.1, 0.2, 0.3]
        self.calls = []

    def embed(self, texts):
        self.calls.append(list(texts))
        return [self.embedding]


class ArticleEmbeddingStorageTests(unittest.TestCase):
    def test_normalizes_title_and_summary_whitespace(self):
        result = build_article_embedding_input(
            title="  AI\n  startup ",
            summary="New\t model\nreleased",
        )

        self.assertEqual(
            result,
            "title: AI startup\nsummary: New model released",
        )

    def test_missing_summary_uses_title_only(self):
        result = build_article_embedding_input(title="Article", summary=None)

        self.assertEqual(result, "title: Article")

    def test_same_input_has_same_hash_and_content_change_changes_hash(self):
        first = build_article_embedding_input(title="AI  news", summary="Today")
        equivalent = build_article_embedding_input(
            title="AI\nnews",
            summary="Today",
        )
        changed = build_article_embedding_input(title="AI news", summary="Tomorrow")

        self.assertEqual(hash_source_text(first), hash_source_text(equivalent))
        self.assertNotEqual(hash_source_text(first), hash_source_text(changed))

    def test_same_hash_reuses_without_provider_call(self):
        source_text = build_article_embedding_input(title="Article", summary="Summary")
        connection = FakeConnection(
            existing={"id": 10, "source_text_hash": hash_source_text(source_text)}
        )
        provider = FakeProvider()

        result = store_article_embedding(
            connection,
            article={"id": 1, "title": "Article", "summary": "Summary"},
            embedding_provider=provider,
            expected_dimension=3,
        )

        self.assertEqual(result.status, "reused")
        self.assertEqual(provider.calls, [])
        self.assertEqual(len(connection.calls), 1)

    def test_new_embedding_is_inserted(self):
        connection = FakeConnection()
        provider = FakeProvider()

        result = store_article_embedding(
            connection,
            article={"id": 1, "title": "Article", "summary": "Summary"},
            embedding_provider=provider,
            expected_dimension=3,
        )

        self.assertEqual(result.status, "created")
        self.assertEqual(len(provider.calls), 1)
        self.assertIn("insert into article_embeddings", connection.calls[-1][0])
        self.assertIn(
            "on conflict (article_id, provider, model, source_text_type)",
            connection.calls[-1][0],
        )
        self.assertIn("embedding = excluded.embedding", connection.calls[-1][0])
        self.assertIn("dimension = excluded.dimension", connection.calls[-1][0])
        self.assertIn(
            "source_text_hash = excluded.source_text_hash",
            connection.calls[-1][0],
        )
        self.assertIn("updated_at = now()", connection.calls[-1][0])
        self.assertEqual(connection.calls[-1][1]["embedding"], "[0.1,0.2,0.3]")

    def test_changed_input_updates_existing_embedding(self):
        connection = FakeConnection(
            existing={"id": 10, "source_text_hash": "old-hash"},
            upsert_inserted=False,
        )
        provider = FakeProvider()

        result = store_article_embedding(
            connection,
            article={"id": 1, "title": "Changed", "summary": "Summary"},
            embedding_provider=provider,
            expected_dimension=3,
        )

        self.assertEqual(result.status, "updated")
        self.assertIn("on conflict", connection.calls[-1][0])

    def test_insert_race_returns_updated_instead_of_unique_error(self):
        connection = FakeConnection(upsert_inserted=False)
        provider = FakeProvider()

        result = store_article_embedding(
            connection,
            article={"id": 1, "title": "Article", "summary": "Summary"},
            embedding_provider=provider,
            expected_dimension=3,
        )

        self.assertEqual(result.status, "updated")
        self.assertEqual(len(provider.calls), 1)
        self.assertIn("on conflict", connection.calls[-1][0])

    def test_model_is_part_of_existing_embedding_lookup(self):
        connection = FakeConnection()
        provider = FakeProvider(model="new-model")

        result = store_article_embedding(
            connection,
            article={"id": 1, "title": "Article", "summary": "Summary"},
            embedding_provider=provider,
            expected_dimension=3,
        )

        self.assertEqual(result.status, "created")
        self.assertEqual(connection.calls[0][1]["model"], "new-model")
        self.assertEqual(connection.calls[-1][1]["model"], "new-model")

    def test_source_text_type_is_part_of_existing_embedding_lookup(self):
        connection = FakeConnection()
        provider = FakeProvider()

        result = store_article_embedding(
            connection,
            article={"id": 1, "title": "Article", "summary": "Summary"},
            embedding_provider=provider,
            source_text_type="title_only",
            expected_dimension=3,
        )

        self.assertEqual(result.status, "created")
        self.assertEqual(connection.calls[0][1]["source_text_type"], "title_only")
        self.assertEqual(connection.calls[-1][1]["source_text_type"], "title_only")

    def test_dimension_mismatch_stops_before_write(self):
        connection = FakeConnection()
        provider = FakeProvider(embedding=[0.1, 0.2])

        with self.assertRaisesRegex(ValueError, "dimension mismatch"):
            store_article_embedding(
                connection,
                article={"id": 1, "title": "Article", "summary": "Summary"},
                embedding_provider=provider,
                expected_dimension=3,
            )

        self.assertEqual(len(connection.calls), 1)

    def test_similarity_query_filters_compatible_embeddings(self):
        rows = [{"article_id": 2, "similarity": 0.9}]
        connection = FakeConnection(similarity_rows=rows)

        result = find_similar_article_embeddings(
            connection,
            embedding=[0.1, 0.2, 0.3],
            provider="openai",
            model="test-model",
            dimension=3,
            source_text_type="title_summary",
            exclude_article_id=1,
            limit=3,
        )

        self.assertEqual(result, rows)
        sql, params = connection.calls[0]
        self.assertIn("embedding <=>", sql)
        self.assertEqual(params["provider"], "openai")
        self.assertEqual(params["model"], "test-model")
        self.assertEqual(params["dimension"], 3)
        self.assertEqual(params["source_text_type"], "title_summary")


if __name__ == "__main__":
    unittest.main()
