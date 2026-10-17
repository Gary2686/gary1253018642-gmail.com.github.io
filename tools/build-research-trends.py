#!/usr/bin/env python3
"""Render research-trends/index.html from the two data files.

    python3 tools/build-research-trends.py

Nothing in the generated page is hand-edited: data/research-trends.json comes
from the Notion notes (via tools/notion-to-research-trends.py) and
data/research-trends-notes.json holds the hand-written reading.  Every count,
bar and chart on the page is computed here, so the prose can never drift away
from the numbers.
"""
import html
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TPL = os.path.join(HERE, "research-trends", "template.html")
CSS = os.path.join(HERE, "research-trends", "style.css")
JS = os.path.join(HERE, "research-trends", "app.js")
DATA = os.path.join(ROOT, "data", "research-trends.json")
NOTES = os.path.join(ROOT, "data", "research-trends-notes.json")
OUT = os.path.join(ROOT, "research-trends", "index.html")

e = lambda s: html.escape(str(s), quote=True)


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------- data ------
d = json.loads(read(DATA))
notes = json.loads(read(NOTES))
items = d["items"]
themes = d["themes"]
journals = d["journals"]
calls = d["calls"]

years = sorted({i["date"][:4] for i in items})
y_prev, y_cur = years[0], years[-1]
by_year = {y: [i for i in items if i["date"][:4] == y] for y in years}


def share(theme, year):
    pool = by_year[year]
    return 100.0 * sum(theme in i["themes"] for i in pool) / len(pool)


stat = {}
for t in themes:
    k = t["key"]
    sub = [i for i in items if k in i["themes"]]
    stat[k] = {
        "n": len(sub),
        "journals": sorted({i["journal"] for i in sub}),
        "prev": share(k, y_prev),
        "cur": share(k, y_cur),
    }
order = sorted(themes, key=lambda t: -stat[t["key"]]["n"])
nmax = max(s["n"] for s in stat.values())

jtotal = {j: sum(1 for i in items if i["journal"] == j) for j in journals}
jorder = sorted([j for j in journals if jtotal[j]], key=lambda j: (-jtotal[j], j))
cellv = {(j, t["key"]): sum(1 for i in items
                            if i["journal"] == j and t["key"] in i["themes"])
         for j in jorder for t in themes}
cmax = max(cellv.values())

opens = [c for c in calls if c["open"]]
closed = [c for c in calls if not c["open"]]
# short column headers for the matrix; the full name stays in the tooltip
SHORT = {
    "agency": "Human–AI agency", "governance": "AI governance",
    "research": "Research & review", "methods": "Methods & theory",
    "platforms": "Platforms", "society": "Society & sustainability",
    "futures": "Digital futures", "impact": "Rigor & impact",
}

opens.sort(key=lambda c: c["deadline_iso"] or "9999")
closed.sort(key=lambda c: c["deadline_iso"] or "0000", reverse=True)


def split_editors(theme):
    """'Native IS Theories (Grover, Hassan)' -> title, editors."""
    m = re.match(r"^(.*?)\s*\(([^()]*(?:,|and)[^()]*)\)\s*$", theme)
    if m and len(m.group(2)) > 6:
        return m.group(1), m.group(2)
    return theme, ""


# -------------------------------------------------------------- blocks -----
stats_html = "\n".join([
    '      <div class="stat"><b>%d</b><span>editorials read</span></div>' % len(items),
    '      <div class="stat"><b>%d</b><span>journals tracked</span></div>' % len(jorder),
    '      <div class="stat"><b>%d</b><span>special issue calls open</span></div>' % len(opens),
    '      <div class="stat"><b>%d</b><span>research directions</span></div>' % len(themes),
])

tk = []
for n, t in enumerate(notes["takeaways"], 1):
    key = t["theme"]
    tk.append(
        '        <button type="button" class="tk" data-pick-theme="%s" data-reveal '
        'style="--c:var(--t-%s)">\n'
        '          <span class="tk-n">%02d</span>\n'
        '          <span class="tk-b"><strong>%s</strong><span>%s</span></span>\n'
        '          <span class="tk-go">%d \u2192</span>\n'
        '        </button>' % (e(key), e(key), n, e(t["title"]), e(t["en"]),
                               stat[key]["n"]))
takeaways_html = "\n".join(tk)

dirs = []
for t in order:
    k, s = t["key"], stat[t["key"]]
    delta = s["cur"] - s["prev"]
    cls = "up" if delta >= 2 else ("down" if delta <= -2 else "")
    arrow = "↗" if delta >= 2 else ("↘" if delta <= -2 else "→")
    dirs.append(
        '        <button type="button" class="dir" data-theme="%s" data-reveal '
        'aria-pressed="false" style="--c:var(--t-%s)">\n'
        '          <span class="dir-top"><i class="dot"></i><h3>%s</h3><span class="n">%d</span></span>\n'
        '          <span class="zh" lang="zh-Hant">%s</span>\n'
        '          <span class="bar"><i style="width:%.0f%%"></i></span>\n'
        '          <span class="foot">%d of %d journals · '
        '<span class="trend %s">%s %+.0f pts</span> vs %s</span>\n'
        '        </button>' % (e(k), e(k), e(t["en"]), s["n"], e(t["zh"]),
                               100.0 * s["n"] / nmax, len(s["journals"]), len(jorder),
                               cls, arrow, delta, y_prev))
dirs_html = "\n".join(dirs)

# ---- slope chart ----------------------------------------------------------
W, H = 820, 430
X1, X2 = 250, 540
TOP, BOT = 74, 396
DOM = 55.0
y = lambda v: BOT - (v / DOM) * (BOT - TOP)


def declutter(vals, gap=19.0):
    """Nudge label positions apart, keeping their order."""
    idx = sorted(range(len(vals)), key=lambda i: vals[i])
    out = list(vals)
    for n, i in enumerate(idx):
        if n and out[i] - out[idx[n - 1]] < gap:
            out[i] = out[idx[n - 1]] + gap
    shift = max(0.0, out[idx[-1]] - (H - 22))
    if shift:
        for i in idx:
            out[i] -= shift
    return out


ly = declutter([y(stat[t["key"]]["prev"]) for t in themes])
ry = declutter([y(stat[t["key"]]["cur"]) for t in themes])

svg = ['<svg viewBox="0 0 %d %d" role="img" aria-labelledby="slope-t slope-d">' % (W, H),
       '  <title id="slope-t">Share of each year\'s editorials by research direction</title>',
       '  <desc id="slope-d">%s</desc>' % e("; ".join(
           "%s %.0f%% in %s to %.0f%% in %s" % (t["en"], stat[t["key"]]["prev"], y_prev,
                                                stat[t["key"]]["cur"], y_cur)
           for t in order)),
       '  <line class="slope-rule" x1="%d" y1="%d" x2="%d" y2="%d"/>' % (X1, 42, X1, BOT + 10),
       '  <line class="slope-rule" x1="%d" y1="%d" x2="%d" y2="%d"/>' % (X2, 42, X2, BOT + 10),
       '  <text class="slope-axis" x="%d" y="%d" text-anchor="middle" fill="currentColor" '
       'opacity=".55">%s · n=%d</text>' % (X1, 30, y_prev, len(by_year[y_prev])),
       '  <text class="slope-axis" x="%d" y="%d" text-anchor="middle" fill="currentColor" '
       'opacity=".55">%s to date · n=%d</text>' % (X2, 30, y_cur, len(by_year[y_cur]))]

for n, t in enumerate(themes):
    k, s = t["key"], stat[t["key"]]
    c = "var(--t-%s)" % k
    svg += [
        '  <g class="slope-g" data-theme="%s" tabindex="0" role="button" '
        'aria-label="%s, %.0f%% in %s, %.0f%% in %s">' % (
            e(k), e(t["en"]), s["prev"], y_prev, s["cur"], y_cur),
        '    <line class="slope-line" x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s"/>' % (
            X1, y(s["prev"]), X2, y(s["cur"]), c),
        '    <circle cx="%d" cy="%.1f" r="4.5" fill="%s"/>' % (X1, y(s["prev"]), c),
        '    <circle cx="%d" cy="%.1f" r="4.5" fill="%s"/>' % (X2, y(s["cur"]), c),
        '    <text class="slope-lab" x="%d" y="%.1f" text-anchor="end" fill="currentColor">%s</text>' % (
            X1 - 46, ly[n] + 4, e(t["en"])),
        '    <text class="slope-val" x="%d" y="%.1f" text-anchor="end" fill="%s">%.0f%%</text>' % (
            X1 - 12, ly[n] + 4, c, s["prev"]),
        '    <text class="slope-val" x="%d" y="%.1f" fill="%s">%.0f%%</text>' % (
            X2 + 12, ry[n] + 4, c, s["cur"]),
        '    <text class="slope-lab" x="%d" y="%.1f" fill="currentColor" opacity=".75">%s</text>' % (
            X2 + 52, ry[n] + 4, e(SHORT.get(k, t["en"]))),
        '  </g>']
svg.append('</svg>')
slope_html = "\n".join("        " + s for s in svg)

# ---- rising / fading ------------------------------------------------------
def rf_col(kind, title, icon, rows):
    out = ['      <div class="rf-col rf-%s" data-reveal>' % kind,
           '        <h3>%s%s</h3>' % (icon, e(title)),
           '        <ul>']
    for r in rows:
        out.append('          <li><b>%s</b> — %s <i>(%s)</i></li>' % (
            e(r["what"]), e(r["why"]), e(r["where"])))
    out += ['        </ul>', '      </div>']
    return "\n".join(out)


UP = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4">'
      '<path d="m4 17 6-6 4 4 6-7"/><path d="M15 8h5v5"/></svg>')
DOWN = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4">'
        '<path d="m4 7 6 6 4-4 6 7"/><path d="M15 16h5v-5"/></svg>')
risefall_html = (rf_col("up", "Editors are asking for more of this", UP, notes["rising"])
                 + "\n" + rf_col("down", "Editors are arguing against this", DOWN, notes["fading"]))

# ---- matrix ---------------------------------------------------------------
mx = ['      <table class="mx">',
      '        <caption class="skip">Editorials by journal and research direction</caption>',
      '        <thead><tr><th class="corner"><span class="skip">Journal</span></th>']
for t in order:
    mx.append('          <th scope="col" style="--c:var(--t-%s)"><button type="button" '
              'data-pick-theme="%s" title="%s">%s</button></th>' % (
                  e(t["key"]), e(t["key"]), e(t["en"]), e(SHORT.get(t["key"], t["en"]))))
mx.append('        </tr></thead>')
mx.append('        <tbody>')
for j in jorder:
    mx.append('          <tr><th scope="row"><button type="button" data-pick-journal="%s" '
              'title="%s">%s<small>%d</small></button></th>' % (
                  e(j), e(journals[j]), e(j), jtotal[j]))
    for t in order:
        v = cellv[(j, t["key"])]
        a = 0.0 if not v else 0.16 + 0.74 * (v / cmax)
        mx.append('            <td><button type="button" class="cell" data-v="%d" '
                  'data-journal="%s" data-theme="%s" style="--c:var(--t-%s);--a:%.2f" '
                  'aria-label="%s, %s: %d"><span class="fill"></span><span class="v">%s</span>'
                  '</button></td>' % (v, e(j), e(t["key"]), e(t["key"]), a,
                                      e(j), e(t["en"]), v, v or "·"))
    mx.append('          </tr>')
mx += ['        </tbody>', '      </table>',
       '      <p class="mx-legend">Fewer <span class="sw">'
       + "".join('<i style="opacity:%.2f"></i>' % o for o in (.2, .4, .6, .8, 1))
       + '</span> more editorials · click to filter</p>']
matrix_html = "\n".join(mx)

# ---- calls ----------------------------------------------------------------
cl = []
for c in opens:
    title, eds = split_editors(c["theme"])
    due = c["deadline_iso"] or ""
    cl.append(
        '        <article class="call"%s data-reveal>\n'
        '          <div class="call-top"><span class="jbadge">%s</span>'
        '<span class="due">%s</span></div>\n'
        '          <h3><a href="%s" target="_blank" rel="noopener">%s</a></h3>\n'
        '          %s\n'
        '          <p class="cd">%s</p>\n'
        '        </article>' % (
            ' data-due="%s"' % e(due) if due else "", e(c["journal"]),
            e(c["deadline"] if not due else due), e(c["url"]), e(title),
            '<p class="ed">Guest editors: %s</p>' % e(eds) if eds else "",
            e(c["deadline"] if not due else "Deadline %s" % c["deadline"])))
calls_html = "\n".join(cl)

cz = []
for c in closed:
    title, _ = split_editors(c["theme"])
    cz.append('          <li><time>%s</time><span><span class="jbadge">%s</span> '
              '<a href="%s" target="_blank" rel="noopener">%s</a></span></li>' % (
                  e(c["deadline_iso"] or "—"), e(c["journal"]), e(c["url"]), e(title)))
closed_html = "\n".join(cz)

# ---- item list ------------------------------------------------------------
tzh = {t["key"]: t["en"] for t in themes}
rows = sorted(items, key=lambda i: (i["date"], i["journal"]), reverse=True)
il = []
for i in rows:
    blob = " ".join([i["title"], i["authors"], " ".join(i["tags"]),
                     journals.get(i["journal"], ""), i["journal"]]).lower()
    dots = "".join('<i style="--c:var(--t-%s)" title="%s"></i>' % (e(k), e(tzh[k]))
                   for k in i["themes"])
    il.append(
        '        <li class="item" data-journal="%s" data-year="%s" data-themes="%s" '
        'data-text="%s">\n'
        '          <span class="jbadge">%s</span>\n'
        '          <time datetime="%s">%s</time>\n'
        '          <a href="%s" target="_blank" rel="noopener">%s</a>\n'
        '          <span class="tdots" aria-hidden="true">%s</span>\n'
        '        </li>' % (
            e(i["journal"]), e(i["date"][:4]), e(" ".join(i["themes"])), e(blob),
            e(i["journal"]), e(i["date"]), e(i["date"]),
            e(i["url"]), e(i["title"]), dots))
items_html = "\n".join(il)

# ---- JSON-LD --------------------------------------------------------------
PAGE = "https://gary2686.github.io/research-trends/"
ld = {
    "@context": "https://schema.org",
    "@graph": [
        {
            "@type": "CollectionPage",
            "@id": PAGE + "#webpage",
            "url": PAGE,
            "name": "Research Trends — What Information Systems Editors Are Asking For",
            "description": ("A quarterly reading of %d editorials and %d special issue calls from %d "
                            "information systems journals, reduced to %d research directions."
                            % (len(items), len(calls), len(jorder), len(themes))),
            "inLanguage": ["en", "zh-Hant"],
            "dateModified": d["updated"],
            "isPartOf": {"@id": "https://gary2686.github.io/#website"},
            "author": {"@id": "https://gary2686.github.io/#person"},
            "about": [{"@type": "Thing", "name": t["en"]} for t in order],
            "mainEntity": {"@id": PAGE + "#directions"},
        },
        {
            "@type": "ItemList",
            "@id": PAGE + "#directions",
            "name": "Research directions IS editors are asking for",
            "numberOfItems": len(order),
            "itemListOrder": "https://schema.org/ItemListOrderDescending",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": n,
                    "item": {
                        "@type": "DefinedTerm",
                        "name": t["en"],
                        "alternateName": t["zh"],
                        "description": ("Raised in %d of %d editorials across %d journals; %.0f%% of %s "
                                        "editorials versus %.0f%% of %s."
                                        % (stat[t["key"]]["n"], len(items),
                                           len(stat[t["key"]]["journals"]),
                                           stat[t["key"]]["cur"], y_cur,
                                           stat[t["key"]]["prev"], y_prev)),
                        "inDefinedTermSet": {"@type": "DefinedTermSet",
                                             "name": "Research Trends directions"},
                    },
                } for n, t in enumerate(order, 1)
            ],
        },
        {
            "@type": "Dataset",
            "@id": PAGE + "#dataset",
            "name": "Research Trends",
            "description": ("Editorials and special issue calls for papers from %d information systems "
                            "journals, each coded with research direction tags." % len(jorder)),
            "url": PAGE,
            "temporalCoverage": "/".join(d["coverage"]),
            "dateModified": d["updated"],
            "creator": {"@id": "https://gary2686.github.io/#person"},
            "license": "https://creativecommons.org/licenses/by/4.0/",
            "isAccessibleForFree": True,
            "variableMeasured": [t["en"] for t in order],
            "distribution": {
                "@type": "DataDownload",
                "encodingFormat": "application/json",
                "contentUrl": "https://gary2686.github.io/data/research-trends.json",
            },
        },
    ],
}

# -------------------------------------------------------------- render -----
out = read(TPL)
repl = {
    "STYLE": read(CSS).strip(),
    "SCRIPT": read(JS).strip(),
    "JSONLD": json.dumps(ld, ensure_ascii=False, indent=2),
    "STATS": stats_html,
    "TAKEAWAYS": takeaways_html,
    "DIRS": dirs_html,
    "SLOPE": slope_html,
    "RISEFALL": risefall_html,
    "MATRIX": matrix_html,
    "CALLS": calls_html,
    "CLOSED": closed_html,
    "ITEMS": items_html,
    "N_ITEMS": str(len(items)),
    "N_CALLS": str(len(calls)),
    "N_OPEN": str(len(opens)),
    "N_CLOSED": str(len(closed)),
    "N_JOURNALS": str(len(jorder)),
    "COVERAGE": " to ".join(d["coverage"]),
    "UPDATED": d["updated"],
    "Y_PREV": y_prev,
    "Y_CUR": y_cur,
    "MONTH_CUR": max(i["date"] for i in by_year[y_cur])[5:7].lstrip("0"),
    "WINDOW": str(d.get("window_years", 4)),
    "SOURCE": d["source"],
    "JOURNAL_LIST": ", ".join("%s (%s)" % (journals[j], j) for j in jorder),
}
for k, v in repl.items():
    out = out.replace("{{%s}}" % k, v)

left = re.findall(r"\{\{[A-Z_]+\}\}", out)
if left:
    raise SystemExit("unfilled slots: %s" % sorted(set(left)))

with open(OUT, "w", encoding="utf-8") as f:
    f.write(out)

# Keep the teaser on the profile page honest: it quotes three counts.
HOME = os.path.join(ROOT, "index.html")
home = read(HOME)
teaser = ('<b>%d</b> editorials \u00b7 <b>%d</b> journals \u00b7 <b>%d</b> calls open'
          % (len(items), len(jorder), len(opens)))
home2, n = re.subn(r'(<span class="watch-stats">\s*)(.*?)(\s*</span>)',
                   lambda m: m.group(1) + teaser + m.group(3), home, flags=re.S)
if n != 1:
    raise SystemExit("index.html: expected exactly one .watch-stats span, found %d" % n)
if home2 != home:
    with open(HOME, "w", encoding="utf-8") as f:
        f.write(home2)
    print("updated index.html teaser counts")

print("wrote %s (%.1f KB)" % (os.path.relpath(OUT, ROOT), len(out) / 1024.0))
print("  %d editorials · %d journals · %d open calls · %d directions"
      % (len(items), len(jorder), len(opens), len(themes)))
for t in order:
    s = stat[t["key"]]
    print("  %-34s n=%2d  %s %4.1f%% -> %s %4.1f%%"
          % (t["en"], s["n"], y_prev, s["prev"], y_cur, s["cur"]))
