import json
import logging

from langchain_chroma import Chroma

from src.config import Settings
from src.llm_factory import embeddings
from src.models import RetrievedChunk
from src.rag.ingest import embedding_identity

MISSING_KB = "Knowledge base missing or incompatible. Run python scripts/ingest_kb.py --rebuild"


class Retriever:
    def __init__(self, settings: Settings, embedding=None):
        info = settings.chroma_dir / "index_info.json"
        if not info.exists():
            raise ValueError(MISSING_KB)
        metadata = json.loads(info.read_text(encoding="utf-8"))
        if (
            metadata["embedding"] != embedding_identity(settings)
            or metadata["collection"] != settings.collection_name
        ):
            raise ValueError(MISSING_KB)
        self.settings = settings
        self.store = Chroma(
            collection_name=settings.collection_name,
            persist_directory=str(settings.chroma_dir),
            embedding_function=embedding or embeddings(settings),
        )
        data = self.store.get()
        self.count = len(data["ids"])
        self.source_titles = {m["source_title"] for m in data["metadatas"]}
        if not self.count or len(self.source_titles) < 3:
            raise ValueError(MISSING_KB)

    def retrieve(self, query: str, planning=False) -> list[RetrievedChunk]:
        if planning:
            # Cover distinct itinerary needs instead of filling every slot with similar overviews.
            queries = [
                (query, 1),
                ("Singapore Chinatown Little India Geylang Serai culture cuisine", 1),
                ("Singapore indoor attractions museums", 1),
                ("Singapore cooled conservatories glass domes indoor children", 1),
                ("Singapore outdoor gardens family attractions", 1),
                ("Singapore getting around MRT bus transportation", 1),
            ]
            matches = []
            seen = set()
            for text, count in queries:
                selected = 0
                for doc, score in self.store.similarity_search_with_relevance_scores(
                    text, k=count + 2
                ):
                    key = (doc.metadata["source_id"], doc.page_content)
                    if key not in seen and len(doc.page_content.split()) >= 20:
                        seen.add(key)
                        matches.append((doc, score))
                        selected += 1
                        if selected == count:
                            break
        else:
            matches = self.store.similarity_search_with_relevance_scores(
                query, k=self.settings.rag_top_k
            )
        results = [
            RetrievedChunk(**doc.metadata, text=doc.page_content, relevance=score)
            for doc, score in matches
            if score >= self.settings.rag_min_relevance
        ]
        logging.info(
            "[RAG] retrieved=%d sources=%d", len(results), len({c.source_id for c in results})
        )
        return results
