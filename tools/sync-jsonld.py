#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Re-generate the publication list inside index.html's JSON-LD from the page itself.

Run this after adding, editing or removing a <li> in #journal-list, #conf-list or
#case-list so that what search engines and AI assistants read stays in sync with
what a human reads:

    python3 tools/sync-jsonld.py

Each publication <li> needs two attributes, which this script also repairs:
    data-type="journal" | "conference" | "case"
    data-year="2026"        (parsed from the (YYYY) in the entry)
Two optional attributes are preserved as written, so add them by hand on new
entries:
    data-topics="hai genai ..."   drives the charts and the theme filters
        valid keys: hai  genai  dx  sustain  urban  method
    data-authors="Name|Name|..."   drives the co-authorship network; use the
        same spelling as the existing entries so people merge into one node
"""
import html as H
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'index.html')
BASE = "https://gary2686.github.io/gary1253018642-gmail.com.github.io/"
PERSON = BASE + "#person"

LISTS = [('journal-list', 'journal'), ('conf-list', 'conference'), ('case-list', 'case')]
TAGS = re.compile(r'<[^>]+>')


def strip(s):
    return re.sub(r'\s+', ' ', H.unescape(TAGS.sub('', s))).strip()


def parse(inner, kind):
    plain = strip(inner)
    ym = re.search(r'\((\d{4})\)', plain)
    year = ym.group(1) if ym else ''

    em = re.search(r'<em>(.*?)</em>', inner, re.S)
    venue = strip(em.group(1)) if em else ''

    title = ''
    if em:
        seg = strip(inner[:em.start()])
        m = re.search(r'\(\d{4}\)\.\s*(.+?)\.\s*$', seg)
        if m:
            title = m.group(1).strip()
    if not title:
        m = re.search(r'\(\d{4}\)。(.+?)。《(.+?)》', plain)
        if m:
            title, venue = m.group(1).strip(), m.group(2).strip()
    if not title:
        m = re.search(r'<a[^>]*>(.*?)</a>\s*《(.+?)》', inner, re.S)
        if m:
            title, venue = strip(m.group(1)), strip(m.group(2))
    if not title:
        title = plain

    authors = re.split(r'\s*\(\d{4}\)', plain, maxsplit=1)[0].strip()
    lm = re.search(r'href="(https?://[^"]+)"', inner)
    sm = re.search(r'<span class="status-tag[^"]*">(.*?)</span>', inner, re.S)

    return {'title': title, 'authors': authors, 'year': year, 'venue': venue,
            'url': lm.group(1) if lm else '', 'status': strip(sm.group(1)) if sm else '',
            'kind': kind}


def node(r):
    n = {
        "@type": "ScholarlyArticle" if r['kind'] != 'case' else "Article",
        "name": r['title'],
        "author": {"@id": PERSON},
        "description": "%s (%s). %s. %s" % (r['authors'], r['year'], r['title'], r['venue']),
    }
    if r['year']:
        n["datePublished"] = r['year']
    if r['venue']:
        n["isPartOf"] = {"@type": "Periodical" if r['kind'] == 'journal' else "CreativeWork",
                         "name": r['venue']}
    if r['url']:
        n["url"] = r['url']
        if 'doi.org/' in r['url']:
            n["identifier"] = r['url'].split('doi.org/', 1)[1]
    if r['status']:
        n["creativeWorkStatus"] = r['status']
    return n


def main():
    src = io.open(PAGE, encoding='utf-8').read()
    records = []

    for list_id, kind in LISTS:
        m = re.search(r'(<ol class="pub-list" id="%s">)(.*?)(</ol>)' % list_id, src, re.S)
        if not m:
            sys.exit("could not find #" + list_id)
        body = m.group(2)
        rebuilt = []
        for li in re.finditer(r'<li\b[^>]*>(.*?)</li>', body, re.S):
            rec = parse(li.group(1), kind)
            records.append(rec)
            attrs = ' data-type="%s"' % kind
            if rec['year']:
                attrs += ' data-year="%s"' % rec['year']
            for carry in ('data-topics', 'data-authors'):
                keep = re.search(carry + r'="([^"]*)"', li.group(0))
                if keep:
                    attrs += ' %s="%s"' % (carry, keep.group(1))
            rebuilt.append('          <li%s>%s</li>' % (attrs, li.group(1)))
        src = src[:m.start()] + m.group(1) + '\n' + '\n'.join(rebuilt) + '\n        ' + m.group(3) + src[m.end():]

    jm = re.search(r'(<script type="application/ld\+json">\n)(.*?)(\n</script>)', src, re.S)
    if not jm:
        sys.exit("could not find the JSON-LD block")
    data = json.loads(jm.group(2))

    for n in data['@graph']:
        if n.get('@type') == 'ItemList':
            n['numberOfItems'] = len(records)
            n['itemListElement'] = [
                {"@type": "ListItem", "position": i + 1, "item": node(r)}
                for i, r in enumerate(records)
            ]
            break
    else:
        sys.exit("no ItemList node in the JSON-LD")

    src = src[:jm.start()] + jm.group(1) + json.dumps(data, ensure_ascii=False, indent=2) + jm.group(3) + src[jm.end():]
    io.open(PAGE, 'w', encoding='utf-8').write(src)
    print("synced %d publications into the JSON-LD" % len(records))


if __name__ == '__main__':
    main()
