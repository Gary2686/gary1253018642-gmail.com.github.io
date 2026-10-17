#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monthly calibration check for the publication list.

Reports, without changing anything:

  1. Dead links      - every external link on the page, by HTTP status.
  2. Metadata drift  - for each DOI on the page, what CrossRef now says about
                       the year, volume, issue and pages, where that differs
                       from the page. This is how an "online first" article
                       being assigned to an issue shows up.
  3. Possibly missing work - items CrossRef and ORCID associate with the ORCID
                       iD that no entry on the page seems to match.

What it cannot see: a manuscript moving from under review to revision or
acceptance leaves no public trace, so those statuses stay a manual edit.

    python3 tools/check-publications.py            # check the live site
    python3 tools/check-publications.py index.html # check a local file
"""
import html as H
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

SITE = "https://gary2686.github.io/"
ORCID = "0009-0008-4725-2623"
UA = "GaryYehSiteCheck/1.0 (+%s; mailto:gary1253018642@gmail.com)" % SITE
TAGS = re.compile(r"<[^>]+>")


def fetch(url, accept=None, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    if accept:
        req.add_header("Accept", accept)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


DOI_RE = re.compile(r'doi\.org/(10\.[^\s"<>]+)')


def check_link(url, timeout=25):
    """-> (verdict, detail). verdict is ok | dead | blocked | unreachable."""
    m = DOI_RE.search(url)
    if m:
        # Ask the DOI system itself. Following through to the publisher only
        # measures whether that publisher tolerates robots.
        doi = m.group(1).rstrip(".")
        try:
            raw = fetch("https://doi.org/api/handles/" + doi, timeout=timeout)
            code = json.loads(raw).get("responseCode")
            if code == 1:
                return "ok", "DOI registered"
            return "dead", "DOI not registered (handle responseCode %s)" % code
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return "dead", ("DOI not registered yet \u2014 the publisher has "
                                "not deposited it with the DOI system")
            return "unreachable", "handle API HTTP %d" % e.code
        except Exception as e:
            return "unreachable", type(e).__name__

    for attempt in (1, 2):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return "ok", str(r.status)
        except urllib.error.HTTPError as e:
            if e.code in (401, 403, 405, 429):
                return "blocked", "HTTP %d (bot protection, not necessarily broken)" % e.code
            return "dead", "HTTP %d" % e.code
        except Exception as e:
            if attempt == 2:
                return "unreachable", type(e).__name__
            time.sleep(2)


def text(s):
    return re.sub(r"\s+", " ", H.unescape(TAGS.sub("", s))).strip()


def norm(s):
    return re.sub(r"[^a-z0-9一-鿿]+", "", H.unescape(s).lower())


# ---------------------------------------------------------------- the page

def read_page(src):
    if src and os.path.exists(src):
        return io.open(src, encoding="utf-8").read()
    return fetch(src or SITE)


def publications(page):
    out = []
    for m in re.finditer(r"<li\b([^>]*)>(.*?)</li>", page, re.S):
        attrs, inner = m.group(1), m.group(2)
        if "data-type=" not in attrs:
            continue
        body = text(inner)
        em = re.search(r"<em>(.*?)</em>", inner, re.S)
        st = re.search(r'<span class="status-tag[^"]*">(.*?)</span>', inner, re.S)
        out.append({
            "type": re.search(r'data-type="([^"]*)"', attrs).group(1),
            "year": (re.search(r'data-year="([^"]*)"', attrs) or [None, None])[1]
                    if re.search(r'data-year="([^"]*)"', attrs) else None,
            "text": body,
            "venue": text(em.group(1)) if em else "",
            "status": text(st.group(1)) if st else "",
            "dois": re.findall(r"doi\.org/(10\.[^\"\s<]+)", inner),
            "links": re.findall(r'href="(https?://[^"]+)"', inner),
        })
    return out


def all_links(page):
    seen, out = set(), []
    for u in re.findall(r'<a\b[^>]*href="(https?://[^"]+)"', page):
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


# ------------------------------------------------------------- the registries

def crossref(doi):
    try:
        return json.loads(fetch("https://api.crossref.org/works/" + doi))["message"]
    except Exception:
        return None


def crossref_by_orcid():
    try:
        d = json.loads(fetch(
            "https://api.crossref.org/works?filter=orcid:%s&rows=100" % ORCID))
        return d["message"]["items"]
    except Exception:
        return []


def orcid_works():
    try:
        d = json.loads(fetch("https://pub.orcid.org/v3.0/%s/works" % ORCID,
                             accept="application/json"))
    except Exception:
        return []
    out = []
    for g in d.get("group", []):
        s = g["work-summary"][0]
        ids = {e["external-id-type"]: e["external-id-value"]
               for e in (g.get("external-ids") or {}).get("external-id", [])}
        out.append({
            "title": s["title"]["title"]["value"],
            "year": ((s.get("publication-date") or {}).get("year") or {}).get("value"),
            "doi": ids.get("doi", ""),
            "type": s.get("type", ""),
        })
    return out


def year_of(msg):
    for k in ("published-print", "published-online", "issued"):
        p = (msg.get(k) or {}).get("date-parts") or []
        if p and p[0] and p[0][0]:
            return str(p[0][0])
    return None


# ------------------------------------------------------------------- report

def main():
    src = sys.argv[1] if len(sys.argv) > 1 else None
    page = read_page(src)
    pubs = publications(page)
    links = all_links(page)
    print("# Publication calibration — %s\n" % time.strftime("%Y-%m-%d"))
    print("Checked %d publications and %d distinct links on %s.\n"
          % (len(pubs), len(links), src or SITE))

    # 1 ---------------------------------------------------------- dead links
    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(check_link, links))
    buckets = {"ok": [], "dead": [], "blocked": [], "unreachable": []}
    for u, (v, d) in zip(links, results):
        buckets[v].append((u, d))

    print("## 1. Links\n")
    if buckets["dead"]:
        print("**%d broken — these need fixing:**\n" % len(buckets["dead"]))
        for u, d in buckets["dead"]:
            print("- `%s` — %s" % (u, d))
        print()
    else:
        print("No broken links.\n")
    if buckets["unreachable"]:
        print("Could not reach (may be a timeout at their end, worth an eyeball):\n")
        for u, d in buckets["unreachable"]:
            print("- `%s` — %s" % (u, d))
        print()
    if buckets["blocked"]:
        print("%d link(s) refuse automated requests, so they cannot be verified "
              "here; they usually work in a browser:\n" % len(buckets["blocked"]))
        for u, d in buckets["blocked"]:
            print("- `%s` — %s" % (u, d))
        print()
    print("%d of %d verified reachable.\n" % (len(buckets["ok"]), len(links)))

    # 2 ------------------------------------------------------ metadata drift
    print("## 2. Registry metadata vs the page\n")
    site_dois = sorted({d.rstrip(".") for p in pubs for d in p["dois"]})
    drift = []
    for doi in site_dois:
        msg = crossref(doi)
        if msg is None:
            drift.append((doi, "not in CrossRef (not registered yet, or a non-CrossRef agency)", ""))
            continue
        entry = next((p for p in pubs if any(doi in d for d in p["dois"])), None)
        body = entry["text"] if entry else ""
        notes = []
        y = year_of(msg)
        if y and entry and entry["year"] and y != entry["year"]:
            notes.append("year: page says %s, CrossRef says %s" % (entry["year"], y))
        vol, iss, pg = msg.get("volume"), msg.get("issue"), msg.get("page")
        if vol and vol not in body:
            notes.append("volume %s not on the page" % vol)
        if pg and pg.replace("-", "–") not in body and pg not in body:
            notes.append("pages %s not on the page" % pg)
        if iss and ("(%s)" % iss) not in body:
            notes.append("issue %s not on the page" % iss)
        if notes:
            drift.append((doi, "; ".join(notes),
                          (msg.get("title") or [""])[0][:60]))
    if drift:
        for doi, note, title in drift:
            print("- `%s` %s\n  - %s" % (doi, ("— " + title) if title else "", note))
    else:
        print("All %d DOIs on the page agree with CrossRef." % len(site_dois))
    print()

    # 3 --------------------------------------------------- work not on the page
    print("## 3. Work in the registries that the page may be missing\n")
    page_norm = norm(page)
    found = []
    for it in crossref_by_orcid():
        t = (it.get("title") or [""])[0]
        found.append({"title": H.unescape(t), "doi": it.get("DOI", ""),
                      "year": year_of(it), "src": "CrossRef"})
    for w in orcid_works():
        found.append({"title": H.unescape(w["title"]), "doi": w["doi"],
                      "year": w["year"], "src": "ORCID"})

    missing, seen = [], set()
    for f in found:
        key = (f["doi"] or norm(f["title"]))[:80]
        if key in seen:
            continue
        seen.add(key)
        on_page = (f["doi"] and f["doi"].lower() in page.lower()) or \
                  (norm(f["title"])[:45] in page_norm)
        if not on_page:
            missing.append(f)
    if missing:
        print("%d item(s) with no obvious match on the page:\n" % len(missing))
        for f in missing:
            print("- **%s** (%s, %s)\n  - `%s`"
                  % (f["title"][:90], f["year"], f["src"], f["doi"] or "no DOI"))
        print("\nA preprint posting of a paper already listed is normal; "
              "it only needs adding if you want the preprint linked.")
    else:
        print("Nothing in CrossRef or ORCID is missing from the page.")
    print()

    # 4 ------------------------------------------------------------- manual
    inreview = [p for p in pubs if p["status"] and "通過" not in p["status"]]
    print("## 4. Statuses only you can confirm\n")
    print("No public source reports these; check them against your inboxes:\n")
    for p in inreview:
        print("- **%s** — %s" % (p["status"], p["venue"] or p["text"][:60]))


if __name__ == "__main__":
    main()
