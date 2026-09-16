"""Real semantic model + persistent Chroma. First run downloads MiniLM (~80 MB)."""

import pytest

from src.config import Settings
from src.rag.ingest import load_chunks
from src.rag.retriever import Retriever


@pytest.mark.integration
def test_persisted_semantic_retrieval():
    settings = Settings()
    if not (settings.chroma_dir / "index_info.json").exists():
        pytest.skip("Run scripts/ingest_kb.py --rebuild for real-index integration tests")
    retriever = Retriever(settings)
    chunks = retriever.retrieve("indoor attractions museums gardens Marina Bay")
    assert chunks
    assert any("Marina" in chunk.text or "museum" in chunk.text.lower() for chunk in chunks)
    sources, _ = load_chunks()
    assert all(c.source_url in {s["url"] for s in sources} for c in chunks)
    assert len(retriever.source_titles) >= 3


@pytest.mark.integration
@pytest.mark.parametrize(
    "source_id,query",
    [
        (
            "visitsingapore_gardens",
            "Gardens by the Bay Supertrees rainwater solar energy OCBC Skyway",
        ),
        (
            "visitsingapore_national_gallery",
            "National Gallery Singapore Southeast Asian art collection",
        ),
    ],
)
def test_official_sources_retrievable(source_id, query):
    settings = Settings()
    if not (settings.chroma_dir / "index_info.json").exists():
        pytest.skip("Run scripts/ingest_kb.py for real-index integration tests")
    sources, _ = load_chunks()
    source = next(s for s in sources if s["id"] == source_id)
    chunks = Retriever(settings).retrieve(query)
    matching = [c for c in chunks if c.source_id == source_id]
    assert matching, "Official document must be retrieved by real semantic search"
    assert all(
        c.source_title == source["title"] and c.source_url == source["url"] for c in matching
    )
    assert all(c.content_format == "factual_summary" for c in matching)
