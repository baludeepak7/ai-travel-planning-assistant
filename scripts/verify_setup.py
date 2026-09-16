import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import Settings
from src.mcp_client.client import MCPClient
from src.rag.retriever import Retriever


async def verify():
    failures = 0
    if sys.version_info < (3, 12):
        print("[FAIL] Use Python 3.12 or newer.")
        failures += 1
    else:
        print("[OK] Python environment")
    settings = Settings()
    try:
        settings.validate_llm()
        print("[OK] LLM configuration (credentials are not authenticated by this check)")
    except ValueError as exc:
        print(f"[FAIL] {exc}")
        failures += 1
    try:
        retriever = Retriever(settings)
        print(f"[OK] Vector database: {retriever.count} chunks")
        print(f"[OK] Knowledge sources: {len(retriever.source_titles)}")
    except Exception:
        print("[FAIL] Build compatible vector DB: python scripts/ingest_kb.py --rebuild")
        failures += 1
    client = MCPClient()
    try:
        await client.initialize()
    except RuntimeError as exc:
        print(f"[FAIL] {exc}")
        failures += 1
    for name, status in client.status.items():
        print(f"[{'OK' if status == 'Connected' else 'FAIL'}] MCP {name} tool: {status}")
    print("READY" if not failures else "NOT READY — fix the failures above.")
    return failures == 0


if __name__ == "__main__":
    sys.exit(0 if asyncio.run(verify()) else 1)
