from scripts.acceptance import missing_knowledge_disclosed


def test_missing_knowledge_requires_explicit_disclosure():
    entity = "Merlion Moon Observatory"
    assert missing_knowledge_disclosed(
        "### Knowledge-base limitations\nThe knowledge base does not contain any place called "
        + entity,
        entity,
    )
    assert not missing_knowledge_disclosed(entity + " has space exhibits.", entity)
    assert not missing_knowledge_disclosed(
        "### Knowledge-base limitations\nThe knowledge base does not list current ticket prices.",
        entity,
    )
