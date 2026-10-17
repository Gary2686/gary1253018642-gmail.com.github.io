#!/usr/bin/env python3
"""Quarterly reminder for the IS Editorial Watch page.

Runs on GitHub's runner next to check-publications.py.  It cannot refresh the
page by itself — the source is a Notion page, and the runner has no Notion
credentials — so it does the two things it honestly can: say how stale the
snapshot is, and name the calls for papers that fall due before the next
quarterly run.

Prints markdown on stdout.  Exit status is always 0; this is a report.
"""
import datetime
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "editorial-watch.json")
NOTES = "https://app.notion.com/p/3fc65a04846a81ecb6cbf6d723de47f8"

QUARTER = 91  # days until the next scheduled run


def main():
    today = datetime.date.today()
    with open(DATA, encoding="utf-8") as f:
        d = json.load(f)

    try:
        read_on = datetime.date.fromisoformat(d["updated"])
        age = (today - read_on).days
    except ValueError:
        read_on, age = None, None

    print("")
    print("---")
    print("")
    print("# IS Editorial Watch")
    print("")
    if age is None:
        print("- 快照日期無法解析（`data/editorial-watch.json` 的 `updated`）。")
    elif age <= QUARTER + 7:
        print("- 快照讀取日 %s，距今 %d 天，仍在一季之內。" % (read_on, age))
    else:
        print("- **快照已過期**：上次讀取是 %s，距今 %d 天（超過一季）。" % (read_on, age))

    horizon = today + datetime.timedelta(days=QUARTER)
    due = []
    for c in d.get("calls", []):
        if not c.get("open") or not c.get("deadline_iso"):
            continue
        day = datetime.date.fromisoformat(c["deadline_iso"])
        if day <= horizon:
            due.append((day, c))
    due.sort()

    print("")
    print("## 下一季之前截稿的專刊徵稿")
    print("")
    if not due:
        print("本季沒有徵稿截止。")
    else:
        for day, c in due:
            left = (day - today).days
            state = "**已截稿**" if left < 0 else ("剩 %d 天" % left)
            print("- %s · %s — %s（%s）" % (day, c["journal"], c["theme"], state))
            if c.get("url"):
                print("  - %s" % c["url"])

    print("")
    print("## 要更新時怎麼做")
    print("")
    print("1. 開 [IS Editorial Watch 的 Notion 筆記](%s)，確認本季的 editorial 與徵稿已經補齊。" % NOTES)
    print("2. 把整頁內容存成文字檔，跑 `python3 tools/notion-to-editorial-json.py <檔案> "
          "data/editorial-watch.json`。")
    print("3. 重寫 `data/editorial-watch-notes.json`（四則重點、rising / fading），這是唯一手寫的部分。")
    print("4. 跑 `python3 tools/build-editorial-watch.py`，它會重建 "
          "`editorial-watch/index.html` 並同步首頁卡片上的數字。")
    print("5. 確認頁面沒問題後再 commit；產生出來的頁面不要手改。")


main()
