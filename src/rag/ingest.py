import hashlib
import json

import yaml
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from src.config import ROOT, Settings
from src.llm_factory import embeddings


def load_chunks(manifest=ROOT / "data/source_manifest.yaml"):
    sources = yaml.safe_load(manifest.read_text(encoding="utf-8"))["sources"]
    chunks = []
    headers = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")]
    )
    # MiniLM truncates at 256 wordpieces, so use smaller chunks for this embedding model.
    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=180, chunk_overlap=30
    )
    for source in sources:
        raw = (ROOT / source["local_file"]).read_text(encoding="utf-8")
        for section in headers.split_text(raw):
            meta = dict(
                source_id=source["id"],
                source_title=source["title"],
                source_url=source["url"],
                document_type="travel_knowledge",
                section=" / ".join(section.metadata.values()) or source["title"],
                publisher=source.get("publisher", "Wikivoyage contributors"),
                content_format=source.get("content_format", "adapted_snapshot"),
                license=source["license"],
                retrieved_at=source["retrieved_at"],
            )
            chunks.extend(
                splitter.split_documents(
                    [Document(page_content=section.page_content, metadata=meta)]
                )
            )
    if len({s["id"] for s in sources}) < 3 or not chunks:
        raise ValueError("Provide at least three nonempty Singapore travel resources.")
    return sources, chunks


def embedding_identity(settings):
    return (
        "all-MiniLM-L6-v2"
        if settings.embedding_provider == "local"
        else settings.openai_embedding_model
    )


def ingest(settings: Settings, rebuild=False, embedding=None):
    sources, chunks = load_chunks()
    model = embedding or embeddings(settings)
    store = Chroma(
        collection_name=settings.collection_name,
        persist_directory=str(settings.chroma_dir),
        embedding_function=model,
        collection_metadata={"hnsw:space": "cosine"},
    )
    if rebuild:
        store.reset_collection()
    ids = [
        hashlib.sha256(
            (json.dumps(c.metadata, sort_keys=True) + c.page_content).encode()
        ).hexdigest()
        for c in chunks
    ]
    # Upsert stable IDs and remove obsolete chunks, so updates cannot accumulate stale facts.
    for offset in range(0, len(chunks), 64):
        store.add_documents(chunks[offset : offset + 64], ids=ids[offset : offset + 64])
    stale = set(store.get()["ids"]) - set(ids)
    if stale:
        store.delete(ids=list(stale))
    settings.chroma_dir.mkdir(parents=True, exist_ok=True)
    (settings.chroma_dir / "index_info.json").write_text(
        json.dumps(
            {
                "embedding": embedding_identity(settings),
                "collection": settings.collection_name,
                "source_count": len(sources),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Documents: {len(sources)}; chunks: {len(ids)}")
    for source in sources:
        print(source["title"])
    print(f"Persistence directory: {settings.chroma_dir}")
    return store
