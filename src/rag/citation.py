from src.models import Source


def unique_sources(chunks):
    return list(
        {
            c.source_url: Source(**c.model_dump(exclude={"text", "relevance"})) for c in chunks
        }.values()
    )


def source_markdown(sources):
    lines = []
    for source in sources:
        details = []
        if source.publisher:
            details.append(source.publisher)
        if source.content_format == "factual_summary":
            details.append("assignment factual summary of official source")
        if source.license:
            details.append(source.license)
        if source.retrieved_at:
            details.append(f"reviewed/retrieved {source.retrieved_at}")
        suffix = " — " + "; ".join(details) if details else ""
        lines.append(f"- [{source.source_title}]({source.source_url}){suffix}")
    return "\n".join(lines)
