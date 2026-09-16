from unittest.mock import Mock

import pytest
from langchain_core.documents import Document

from src.config import Settings
from src.rag.citation import source_markdown, unique_sources
from src.rag.ingest import load_chunks
from src.rag.retriever import Retriever


def test_all_sources_and_metadata():
    sources, chunks = load_chunks()
    assert len(sources) >= 3
    assert len(chunks) > 10
    for chunk in chunks:
        assert all(
            chunk.metadata[k]
            for k in ["source_id", "source_title", "source_url", "section", "document_type"]
        )


def test_retrieval_metadata_and_irrelevance():
    retriever = object.__new__(Retriever)
    retriever.settings = Settings(_env_file=None)
    retriever.store = Mock()
    _, chunks = load_chunks()
    retriever.store.similarity_search_with_relevance_scores.return_value = [
        (chunks[0], 0.8),
        (chunks[0], 0.7),
        (Document(page_content="unrelated"), 0.1),
    ]
    results = retriever.retrieve("attractions")
    assert results[0].source_url == chunks[0].metadata["source_url"]
    assert results[0].source_title
    assert len(unique_sources(results)) == 1
    retriever.store.similarity_search_with_relevance_scores.return_value = []
    assert retriever.retrieve("unsupported") == []


def test_missing_store(tmp_path):
    with pytest.raises(ValueError, match="ingest_kb.py"):
        Retriever(Settings(_env_file=None, chroma_dir=tmp_path))


def test_official_source_summaries_preserve_provenance():
    sources, chunks = load_chunks()
    official = [s for s in sources if s["id"].startswith("visitsingapore_")]
    assert len(official) == 2
    for source in official:
        selected = [c for c in chunks if c.metadata["source_id"] == source["id"]]
        assert selected
        retriever = object.__new__(Retriever)
        retriever.settings = Settings(_env_file=None)
        retriever.store = Mock()
        retriever.store.similarity_search_with_relevance_scores.return_value = [
            (c, 0.9) for c in selected
        ]
        results = retriever.retrieve(source["title"])
        for result in results:
            assert result.source_title == source["title"]
            assert result.source_url == source["url"]
            assert result.content_format == "factual_summary"
            assert result.publisher == source["publisher"]
            assert result.retrieved_at == source["retrieved_at"]
        rendered = source_markdown(unique_sources(results))
        assert "assignment factual summary of official source" in rendered
        assert source["url"] in rendered


def test_refresh_does_not_overwrite_reviewed_summaries(monkeypatch, tmp_path):
    import yaml

    from scripts import fetch_sources

    source = {
        "title": "Reviewed official summary",
        "refresh_mode": "manual_review",
        "local_file": "data/raw/summary.md",
    }
    data = tmp_path / "data"
    (data / "raw").mkdir(parents=True)
    summary = data / "raw/summary.md"
    summary.write_text("Reviewed facts", encoding="utf-8")
    (data / "source_manifest.yaml").write_text(yaml.safe_dump({"sources": [source]}))
    monkeypatch.setattr(fetch_sources, "ROOT", tmp_path)
    http = Mock(side_effect=AssertionError("Must not scrape reviewed summaries"))
    monkeypatch.setattr(fetch_sources.httpx, "get", http)
    fetch_sources.main()
    http.assert_not_called()
    assert summary.read_text(encoding="utf-8") == "Reviewed facts"
