# Knowledge base attribution and reuse

The three Wikivoyage Markdown snapshots in `raw/` are adapted from the articles linked in
`source_manifest.yaml`, by Wikivoyage contributors. They are distributed under
[Creative Commons Attribution-ShareAlike 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
Author histories are available via the History tab on each original article.
Changes: HTML/navigation/images/tables removed; headings and text converted to Markdown.
Retrieval timestamps are in the manifest. The text remains a dated community guide,
not a source of live prices, entry rules, opening hours, weather, or exchange rates.

[Wikivoyage reuse policy](https://en.wikivoyage.org/wiki/Wikivoyage:Copyleft) reviewed
on 2026-09-11.

Two additional documents, `visitsingapore_gardens.md` and
`visitsingapore_national_gallery.md`, contain concise original factual summaries
checked on 2026-09-15 against Singapore Tourism Board's official VisitSingapore pages.
They are assignment-authored summaries, not downloaded full articles or verbatim STB
excerpts. The original page titles and canonical URLs are recorded in the manifest.
No photographs, logos, promotional prose, ticket prices or opening hours are bundled
from those pages. Website content remains subject to
[VisitSingapore's terms](https://www.visitsingapore.com/terms-of-use/) and is not
relicensed as CC BY-SA. Only the Wikivoyage adaptations carry that attribution/license.
The knowledge base now uses five documents from two publishers.

Refresh Wikivoyage explicitly with `python scripts/fetch_sources.py`, review changes,
then rebuild. The fetcher skips official factual summaries: review their linked pages,
edit only supported facts and update the manifest review date before re-ingesting.
There is no scraping during a user request. Attribution and this license must accompany
redistributed KB adaptations, including extracted passages.
