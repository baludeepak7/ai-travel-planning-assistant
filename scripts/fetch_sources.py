"""Explicit, one-time refresh of licensed Wikivoyage text; never run during chat."""

import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
import yaml
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import ROOT


def main():
    manifest = ROOT / "data/source_manifest.yaml"
    data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    for source in data["sources"]:
        if source.get("refresh_mode") == "manual_review":
            print(f"Manual review required to refresh factual summary: {source['title']}")
            continue
        response = httpx.get(
            source["url"],
            follow_redirects=True,
            timeout=30,
            headers={"User-Agent": "SingaporeTravelAssignment/1.0 (KB snapshot)"},
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        article = max(
            soup.select(".mw-parser-output"), key=lambda node: len(node.get_text()), default=None
        )
        if article is None:
            raise ValueError(f"Article content not found: {source['url']}")
        for node in article.select("script, style, table, .mw-editsection, .navbox, .metadata"):
            node.decompose()
        lines = []
        for node in article.find_all(["h2", "h3", "h4", "p", "li"]):
            if node.name == "li" and node.find_parent("li"):
                continue
            text = node.get_text(" ", strip=True)
            if text:
                prefix = "#" * (int(node.name[1]) if node.name.startswith("h") else 0)
                lines.append(f"{prefix} {text}".strip())
        if sum(map(len, lines)) < 1000:
            raise ValueError("Unexpectedly short source; refusing to replace snapshot")
        path = ROOT / source["local_file"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n\n".join(lines), encoding="utf-8")
        source["retrieved_at"] = datetime.now(timezone.utc).isoformat()
        print(f"Saved {source['title']}: {len(lines)} paragraphs")
    manifest.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


if __name__ == "__main__":
    main()
