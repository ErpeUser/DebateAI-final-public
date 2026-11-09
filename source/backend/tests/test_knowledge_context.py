import asyncio
import unittest
import uuid
import json
from types import SimpleNamespace

import numpy as np
from sqlalchemy.dialects import postgresql

from app.services.knowledge_context import (
    FastEmbedContextIndex,
    KnowledgeSection,
    build_postgres_fts_statement,
    prepare_knowledge_record_embeddings,
    retrieve_knowledge_record_context,
    select_knowledge_record_context,
    select_context_sections,
)


class _EmbeddingModel:
    def __init__(self, vectors):
        self.vectors = vectors
        self.batches = []

    def embed(self, texts):
        values = list(texts)
        self.batches.append(values)
        return [np.asarray(self.vectors[value], dtype=np.float32) for value in values]


class KnowledgeContextTests(unittest.TestCase):
    def test_semantic_ranking_is_independent_from_lexical_candidates(self):
        query = "Wie sinkt der CO2-Ausstoss?"
        sections = [
            KnowledgeSection("lexical", "### Worttreffer\nCO2 wird nur erwaehnt."),
            KnowledgeSection("semantic", "### Wirkung\nWeniger Emissionen durch Waermepumpen."),
        ]
        model = _EmbeddingModel({
            query: [0.0, 1.0],
            sections[0].text: [1.0, 0.0],
            sections[1].text: [0.0, 1.0],
        })
        index = FastEmbedContextIndex(model=model, model_version="test-model@1")

        ranking = index.semantic_ranking(sections, query, limit=1)

        self.assertEqual(["semantic"], ranking)

    def test_large_context_fuses_postgres_and_fastembed_rankings(self):
        sections = [f"### Thema {index}\nAllgemeiner Inhalt {index}." for index in range(9)]
        sections.append("### Preismodell\nDie Kosten betragen zehn Euro.")
        query = "Was ist der Preis?"
        vectors = {query: [0.0, 1.0]}
        vectors.update({section: [1.0, 0.0] for section in sections})
        vectors[sections[-1]] = [0.0, 1.0]
        selected = select_context_sections(
            "\n\n".join(sections),
            query,
            budget=120,
            lexical_ranking=["section:0"],
            index=FastEmbedContextIndex(
                model=_EmbeddingModel(vectors),
                model_version="test-model@1",
            ),
        )
        self.assertIn("Preismodell", selected)
        self.assertIn("Kosten", selected)

    def test_embedding_cache_reuses_only_matching_model_dimension_and_content_hash(self):
        query = "Frage"
        original = KnowledgeSection("record-1", "### Titel\nAlter Inhalt")
        changed = KnowledgeSection("record-1", "### Titel\nNeuer Inhalt")
        model = _EmbeddingModel({
            query: [1.0, 0.0],
            original.text: [1.0, 0.0],
            changed.text: [0.0, 1.0],
        })
        index = FastEmbedContextIndex(model=model, model_version="test-model@1")

        index.semantic_ranking([original], query, limit=1)
        first = index.cache_metadata("record-1")
        index.semantic_ranking([original], query, limit=1)
        index.semantic_ranking([changed], query, limit=1)
        second = index.cache_metadata("record-1")

        document_batches = [batch for batch in model.batches if batch != [query]]
        self.assertEqual([[original.text], [changed.text]], document_batches)
        self.assertEqual("test-model@1", first["model_version"])
        self.assertEqual(2, first["dimension"])
        self.assertNotEqual(first["content_hash"], second["content_hash"])

    def test_postgres_fts_statement_uses_german_fallback_and_authorized_ids(self):
        allowed_id = uuid.UUID("11111111-1111-1111-1111-111111111111")

        statement = build_postgres_fts_statement(
            [allowed_id],
            "Kosten fuer Waermepumpen",
            limit=7,
        )
        sql = str(statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )).casefold()

        self.assertIn("to_tsvector", sql)
        self.assertIn("websearch_to_tsquery", sql)
        self.assertIn("ts_rank_cd", sql)
        self.assertIn("to_regconfig('german')", sql)
        self.assertIn("to_regconfig('simple')", sql)
        self.assertIn(str(allowed_id), sql)
        self.assertIn("knowledge_records.active is true", sql)

    def test_record_embedding_metadata_is_reused_and_preserves_source_fields(self):
        query = "Welche Wirkung hat das?"
        record = SimpleNamespace(
            id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            title="Dossierquelle",
            body="Waermepumpen verringern Emissionen.",
            active=True,
            meta=json.dumps({"origin": "Studie.pdf", "independent_evidence": True}),
        )
        rendered = "### Dossierquelle [local document; private/local; origin: Studie.pdf]\nWaermepumpen verringern Emissionen."
        first_model = _EmbeddingModel({query: [0.0, 1.0], rendered: [0.0, 1.0]})
        first_index = FastEmbedContextIndex(model=first_model, model_version="test-model@1")

        selected = select_knowledge_record_context(
            [record], query, lexical_ranking=[], index=first_index
        )
        stored = json.loads(record.meta)
        second_model = _EmbeddingModel({query: [0.0, 1.0]})
        second_index = FastEmbedContextIndex(model=second_model, model_version="test-model@1")
        selected_again = select_knowledge_record_context(
            [record], query, lexical_ranking=[], index=second_index
        )

        self.assertIn("Studie.pdf", selected)
        self.assertEqual(selected, selected_again)
        self.assertEqual("Studie.pdf", stored["origin"])
        self.assertEqual("test-model@1", stored["retrieval_embedding"]["model_version"])
        self.assertEqual([[query]], second_model.batches)

    def test_record_context_preserves_page_reference(self):
        query = "Welche Wirkung hat das?"
        record = SimpleNamespace(
            id=uuid.UUID("44444444-4444-4444-4444-444444444444"),
            title="Dossierquelle",
            body="Waermepumpen verringern Emissionen.",
            active=True,
            meta=json.dumps({
                "origin": "Studie.pdf",
                "page_reference": "S. 12-13",
                "independent_evidence": True,
            }),
        )
        rendered = (
            "### Dossierquelle [local document; private/local; "
            "origin: Studie.pdf; page: S. 12-13]\n"
            "Waermepumpen verringern Emissionen."
        )
        index = FastEmbedContextIndex(
            model=_EmbeddingModel({query: [0.0, 1.0], rendered: [0.0, 1.0]}),
            model_version="test-model@1",
        )

        selected = select_knowledge_record_context(
            [record], query, lexical_ranking=[], index=index
        )

        self.assertIn("page: S. 12-13", selected)

    def test_record_selection_excludes_inactive_or_unapproved_input(self):
        query = "Frage"
        inactive = SimpleNamespace(
            id=uuid.uuid4(), title="Geloescht", body="Darf nicht erscheinen",
            active=False, meta="{}",
        )

        selected = select_knowledge_record_context(
            [inactive],
            query,
            lexical_ranking=[str(inactive.id)],
            index=FastEmbedContextIndex(
                model=_EmbeddingModel({query: [1.0, 0.0]}),
                model_version="test-model@1",
            ),
        )

        self.assertEqual("", selected)

    def test_import_embedding_preparation_reuses_hash_and_refreshes_changed_body(self):
        record = SimpleNamespace(
            id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
            title="Unterlage", body="Erste Fassung", active=True,
            meta=json.dumps({"origin": "Unterlage.txt"}),
        )
        first_render = (
            "### Unterlage [user position; not independent evidence; "
            "private/local; origin: Unterlage.txt]\nErste Fassung"
        )
        second_render = first_render.replace("Erste Fassung", "Zweite Fassung")
        model = _EmbeddingModel({
            first_render: [1.0, 0.0],
            second_render: [0.0, 1.0],
        })
        index = FastEmbedContextIndex(model=model, model_version="test-model@1")

        self.assertEqual(1, prepare_knowledge_record_embeddings([record], index=index))
        self.assertEqual(0, prepare_knowledge_record_embeddings([record], index=index))
        record.body = "Zweite Fassung"
        self.assertEqual(1, prepare_knowledge_record_embeddings([record], index=index))

        self.assertEqual([[first_render], [second_render]], model.batches)

    def test_retrieval_composes_postgres_ranking_with_fastembed_context(self):
        query = "Welche Wirkung hat das?"
        record = SimpleNamespace(
            id=uuid.UUID("55555555-5555-5555-5555-555555555555"),
            title="Unterlage",
            body="Waermepumpen verringern Emissionen.",
            active=True,
            meta="{}",
        )
        rendered = (
            "### Unterlage [user position; not independent evidence; "
            "private/local; origin: Unterlage]\n"
            "Waermepumpen verringern Emissionen."
        )

        class _Rows:
            @staticmethod
            def all():
                return [(record.id, 0.8)]

        class _Db:
            def __init__(self):
                self.execute_count = 0

            async def execute(self, _statement):
                self.execute_count += 1
                return _Rows()

        db = _Db()
        selected = asyncio.run(retrieve_knowledge_record_context(
            db,
            [record],
            query,
            index=FastEmbedContextIndex(
                model=_EmbeddingModel({query: [0.0, 1.0], rendered: [0.0, 1.0]}),
                model_version="test-model@1",
            ),
        ))

        self.assertEqual(1, db.execute_count)
        self.assertIn("Waermepumpen", selected)

    def test_small_context_preserves_author_order(self):
        value = "### Erste\nA\n\n### Zweite\nB"
        self.assertTrue(select_context_sections(value, "Zweite").startswith("### Erste"))

    def test_small_context_uses_semantic_ranking_when_an_index_is_available(self):
        first = "### Worttreffer\nDie Unterlage nennt nur das Thema."
        second = "### Wirkung\nWaermepumpen senken den Energieverbrauch."
        query = "Wie sinkt der Verbrauch?"
        model = _EmbeddingModel({
            query: [0.0, 1.0],
            first: [1.0, 0.0],
            second: [0.0, 1.0],
        })

        selected = select_context_sections(
            f"{first}\n\n{second}",
            query,
            budget=len(second),
            lexical_ranking=[],
            index=FastEmbedContextIndex(
                model=model,
                model_version="test-model@1",
            ),
        )

        self.assertEqual(second, selected)


if __name__ == "__main__":
    unittest.main()
