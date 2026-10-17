# IS Editorial Watch — how the page is built

`/editorial-watch/` is generated. **Never edit `editorial-watch/index.html` by
hand**; the next build overwrites it.

```
Notion page  ──(1)──▶  data/editorial-watch.json   ──┐
                                                     ├──(3)──▶  editorial-watch/index.html
data/editorial-watch-notes.json  (hand-written)  ────┘
```

## Quarterly refresh

1. **Read Notion.** Open the
   [IS Editorial Watch notes](https://app.notion.com/p/3fc65a04846a81ecb6cbf6d723de47f8)
   and make sure the quarter's editorials and calls are in. Corrections belong
   there first, not here — Notion is the source of truth.
2. **Export and parse.** Save the whole page as plain text, then:
   ```
   python3 tools/notion-to-editorial-json.py <exported.md> data/editorial-watch.json
   ```
   The script prints a report. Check `untagged: 0` and `no url: 0`; anything
   else means an item's format drifted and the parser needs a look.
3. **Rewrite the reading.** `data/editorial-watch-notes.json` holds the four
   takeaways and the rising/fading lists. This is the only hand-written content
   on the page, and the only part that can go stale silently. Every number it
   quotes must match what step 4 prints.
4. **Build.**
   ```
   python3 tools/build-editorial-watch.py
   ```
   It rebuilds the page, recomputes every count, bar and chart, and syncs the
   three numbers in the teaser card on the profile page. It refuses to finish
   if a template slot is unfilled or the teaser card has moved.
5. **Look at it**, then commit both data files, the page and `index.html`.

## Why there is no cron for this

The quarterly GitHub Action (`.github/workflows/publication-check.yml`) cannot
do steps 1 to 3: it has no Notion credentials, and the reading in step 3 is a
judgment call. What it does instead is run `tools/check-editorial-watch.py`,
which says how stale the snapshot is and lists the calls for papers closing
before the next run. Giving the runner a Notion integration token would
automate steps 1 and 2; step 3 would still be manual.

## Files

| Path | What it is |
| --- | --- |
| `template.html` | page skeleton, `{{SLOT}}` placeholders |
| `style.css` | page styles; the design tokens are copied from `index.html` on purpose |
| `app.js` | theme toggle, scroll reveal, deadline countdowns, the shared filter |
| `../build-editorial-watch.py` | assembles all of the above |
| `../notion-to-editorial-json.py` | Notion export → JSON, including direction-tag mapping |
| `../check-editorial-watch.py` | the quarterly staleness and deadline reminder |
