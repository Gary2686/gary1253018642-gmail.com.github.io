# Research Trends — how the page is built

`/research-trends/` is generated. **Never edit `research-trends/index.html` by
hand**; the next build overwrites it.

```
Notion page  ──(1)──▶  data/research-trends.json   ──┐
                                                     ├──(3)──▶  research-trends/index.html
data/research-trends-notes.json  (hand-written)  ────┘
```

## Quarterly refresh

1. **Read Notion.** Open the
   [Research Trends notes](https://app.notion.com/p/3fc65a04846a81ecb6cbf6d723de47f8)
   and make sure the quarter's editorials and calls are in. Corrections belong
   there first, not here — Notion is the source of truth.
2. **Export and parse.** Save the whole page as plain text, then:
   ```
   python3 tools/notion-to-research-trends.py <exported.md> data/research-trends.json
   ```
   The script prints a report. Check `untagged: 0` and `no url: 0`; anything
   else means an item's format drifted and the parser needs a look. It also
   prints the window line: the page keeps a **rolling four-year window**
   (`KEEP_YEARS` in that script) and drops anything older on every refresh, so
   old editorials disappear by themselves — never curate that by hand.
3. **Rewrite the reading.** `data/research-trends-notes.json` holds the four
   shifts and the rising/fading lists. This is the only hand-written content on
   the page, and the only part that can go stale silently. Keep every line
   short — the page is meant to be scanned — and make sure any number it quotes
   matches what step 4 prints.
4. **Build.**
   ```
   python3 tools/build-research-trends.py
   ```
   It rebuilds the page, recomputes every count, bar and chart, and syncs the
   three numbers in the teaser card on the profile page. It refuses to finish
   if a template slot is unfilled or the teaser card has moved.
5. **Look at it**, then commit both data files, the page and `index.html`.

## Why there is no cron for this

The quarterly GitHub Action (`.github/workflows/publication-check.yml`) cannot
do steps 1 to 3: it has no Notion credentials, and the reading in step 3 is a
judgment call. What it does instead is run `tools/check-research-trends.py`,
which says how stale the snapshot is and lists the calls for papers closing
before the next run. Giving the runner a Notion integration token would
automate steps 1 and 2; step 3 would still be manual.

## Files

| Path | What it is |
| --- | --- |
| `template.html` | page skeleton, `{{SLOT}}` placeholders |
| `style.css` | page styles; the design tokens are copied from `index.html` on purpose |
| `app.js` | theme toggle, scroll reveal, deadline countdowns, the shared filter |
| `../build-research-trends.py` | assembles all of the above |
| `../notion-to-research-trends.py` | Notion export → JSON, including direction-tag mapping |
| `../check-research-trends.py` | the quarterly staleness and deadline reminder |

`/editorial-watch/` is a redirect stub left behind from the page's first name.
It can go once nothing links to it.
