#!/usr/bin/env python3
"""Turn the Research Trends Notion export into the JSON the web page reads.

Input is the raw text of the Notion page (the `text` field of a notion-fetch
result, unescaped).  Output is data/research-trends.json.
"""
import datetime, json, re, sys

# The page keeps a rolling window. Anything older is dropped on every refresh,
# so the list never turns into an archive nobody reads.
KEEP_YEARS = 4

JOURNALS = {
    "ISR": "Information Systems Research",
    "MISQ": "MIS Quarterly",
    "JMIS": "Journal of Management Information Systems",
    "MS": "Management Science",
    "POM": "Production and Operations Management",
    "EJIS": "European Journal of Information Systems",
    "ISJ": "Information Systems Journal",
    "JAIS": "Journal of the Association for Information Systems",
    "JIT": "Journal of Information Technology",
    "JSIS": "Journal of Strategic Information Systems",
    "DSS": "Decision Support Systems",
    "I&M": "Information & Management",
    "I&O": "Information and Organization",
}

# Theme -> tag keywords.  A tag matches a theme when it contains one of these.
THEMES = [
    ("agency", "Human-AI agency", "人機能動性配置", [
        "human-ai collaboration", "human-ai interaction", "ai agency", "autonomy",
        "cognitive offloading", "overreliance", "algorithm aversion", "ai aversion",
        "human-computer symbiosis", "responsible augmentation", "automation",
        "ai consequences", "creativity", "ai trust and alignment", "agentic",
        "ai and operations", "genai and jobs", "future of work", "hybrid work",
        "deskilling", "adoption", "end users"]),
    ("governance", "AI governance & responsible AI", "AI 治理與負責任 AI", [
        "governance", "regulation", "responsible ai", "responsible tech",
        "responsible digital", "ethics", "eu ai act", "ai risk", "legal compliance",
        "policy", "fairness", "bias", "accountability", "enforcement",
        "bright internet", "cybersecurity", "privacy", "surveillance",
        "content moderation", "free speech", "data breaches", "platform security",
        "institutional trust", "misinformation", "social media harms",
        "critical infrastructure"]),
    ("research", "Research practice & peer review", "研究實踐與審稿規範", [
        "review practices", "research integrity", "peer review", "editorial policy",
        "journal policy", "ai-assisted analysis", "authorship", "research ethics",
        "submission", "desk rejection", "developmental reviewing", "guidelines",
        "scholarly writing", "academic writing", "editorial guidance",
        "editorial practice", "editorial decisions", "journal fit", "reflexivity",
        "positionality", "literature reviews", "grey literature", "review issue",
        "issue editorial", "editorial transition", "journal leadership",
        "journal governance"]),
    ("methods", "Methods & theory building", "方法與理論建構", [
        "methods", "theory", "research design", "evaluation criteria",
        "multimethod", "design science", "computational methods", "causal ml",
        "digital trace data", "conceptual clarity", "quantitative behavioral",
        "epistemic plurality", "context", "sociomateriality", "socio-technical",
        "sociotechnical", "behavioral is", "novelty", "framework",
        "cumulative knowledge", "interdisciplinarity"]),
    ("platforms", "Platforms & ecosystems", "數位平台與生態系", [
        "platform", "ecosystem", "complementors", "metaverse", "immersive",
        "sharing economy", "social media", "recommender", "decentralization",
        "blockchain", "digital twins", "internet of things", "business models",
        "enterprise systems", "digital innovation", "it innovation diffusion",
        "digital transformation", "strategizing", "global strategy"]),
    ("society", "Sustainability & societal impact", "永續與社會影響", [
        "societal impact", "sustainab", "green is", "inclusion", "equity",
        "global south", "decoloniality", "base of the pyramid", "digital development",
        "digital health", "health analytics", "ai in healthcare", "social value",
        "digital responsibility", "stakeholders", "is community",
        "global scholarship", "asia-pacific", "pacis"]),
    ("futures", "Digital futures", "數位未來與未來學", [
        "futures", "future", "hype", "emerging technologies", "digital turbulence",
        "value-reflexivity"]),
    ("impact", "Rigor, relevance & impact", "嚴謹・相關・影響力", [
        "rigor and relevance", "research impact", "practice engagement",
        "practitioner", "engaged scholarship", "policy impact", "research agenda",
        "discipline history", "discipline identity", "journal retrospective",
        "journal mission", "field evolution", "research trends", "is policy"]),
]

ITEM_RE = re.compile(r"^\*\*(\d+)\. (.+?)\*\*$")
META_RE = re.compile(
    r"^- 期刊 / Journal: (?P<j>.+?); 卷期 / Vol\(Issue\): (?P<v>.+?); 年月 / Date: (?P<d>.+?)\s*$")


def themes_for(tags):
    hit = []
    low = [t.lower() for t in tags]
    for key, en, zh, words in THEMES:
        if any(w in t for t in low for w in words):
            hit.append(key)
    return hit


def parse(text):
    lines = text.split("\n")
    items, cur, journal = [], None, None
    for ln in lines:
        h = re.match(r"^### (.+?) \((.+?)\)\s*$", ln)
        if h and h.group(2) in JOURNALS:
            journal = h.group(2)
        m = ITEM_RE.match(ln)
        if m and journal:
            cur = {"title": m.group(2).strip(), "journal": journal,
                   "tags": [], "note": "", "url": "", "authors": ""}
            items.append(cur)
            continue
        if cur is None:
            continue
        mm = META_RE.match(ln)
        if mm:
            cur["journal"] = mm.group("j").strip()
            cur["vol"] = mm.group("v").strip()
            raw = mm.group("d").strip()
            cur["date"] = raw[:7]
            cur["date_note"] = raw[7:].strip(" ()") or ""
            continue
        if ln.startswith("- 作者 / Authors:"):
            cur["authors"] = ln.split(":", 1)[1].strip()
            continue
        if ln.startswith("- DOI:"):
            u = re.search(r"\((https?://[^)]+)\)", ln)
            if u:
                cur["url"] = u.group(1)
            continue
        if ln.startswith("- URL:") and not cur["url"]:
            u = re.search(r"\((https?://[^)]+)\)", ln)
            if u:
                cur["url"] = u.group(1)
            continue
        if ln.startswith("- Key points"):
            body = ln.split(":", 1)[1].strip()
            first = re.split(r"(?<=[.!?])\s", body)[0]
            cur["note"] = first.strip()
            continue
        if ln.startswith("- 研究方向標籤"):
            tags = ln.split(":", 1)[1]
            cur["tags"] = [t.strip() for t in tags.split(";") if t.strip()]
            cur["themes"] = themes_for(cur["tags"])
            continue
    return items


def parse_calls(text):
    """The calls-for-papers table."""
    block = text.split("## 近期 Special Issue 徵稿")[1].split("## Editorial 清單")[0]
    rows, cells = [], []
    for ln in block.split("\n"):
        ln = ln.strip()
        if ln == "<tr>":
            cells = []
        elif ln.startswith("<td>"):
            cells.append(re.sub(r"</?td>", "", ln).strip())
        elif ln == "</tr>" and len(cells) == 5:
            rows.append(cells)
    out = []
    for j, theme, deadline, status, url in rows[1:]:
        u = re.search(r"\((https?://[^)]+)\)", url)
        iso = re.findall(r"\d{4}-\d{2}-\d{2}", deadline)
        out.append({
            "journal": j, "theme": theme, "deadline": deadline,
            "deadline_iso": iso[-1] if iso else "",
            "open": status.lower().startswith("open"),
            "status": status, "url": u.group(1) if u else "",
        })
    return out


def main():
    text = open(sys.argv[1]).read()
    items = parse(text)
    calls = parse_calls(text)

    cutoff = datetime.date.today().year - (KEEP_YEARS - 1)
    dropped = [i for i in items if int(i["date"][:4]) < cutoff]
    items = [i for i in items if int(i["date"][:4]) >= cutoff]
    cov = re.search(r"Coverage: (\S+) to (\S+)", text)
    upd = re.search(r"Last updated: (\S+)", text)
    data = {
        "updated": upd.group(1) if upd else "",
        "coverage": [cov.group(1), cov.group(2)] if cov else [],
        "source": "https://app.notion.com/p/3fc65a04846a81ecb6cbf6d723de47f8",
        "window_years": KEEP_YEARS,
        "window_from": str(cutoff),
        "journals": JOURNALS,
        "themes": [{"key": k, "en": e, "zh": z} for k, e, z, _ in THEMES],
        "items": items,
        "calls": calls,
    }
    json.dump(data, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
    # a quick console report so mis-parses are obvious
    print("items", len(items), "calls", len(calls), "open", sum(c["open"] for c in calls))
    print("window: %d- (last %d years); dropped %d older item(s)%s"
          % (cutoff, KEEP_YEARS, len(dropped),
             ": " + ", ".join(sorted({i["date"][:4] for i in dropped})) if dropped else ""))
    bad = [i for i in items if not i.get("themes")]
    print("untagged:", len(bad))
    for i in bad:
        print("   ", i["journal"], i["title"][:60], "|", "; ".join(i["tags"]))
    from collections import Counter
    c = Counter(t for i in items for t in i.get("themes", []))
    for k, e, z, _ in THEMES:
        print("%-12s %s" % (k, c[k]))
    miss = [i for i in items if not i["url"]]
    print("no url:", len(miss))
    print("no note:", len([i for i in items if not i["note"]]))


main()
