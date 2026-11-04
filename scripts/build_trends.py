#!/usr/bin/env python3
"""RECODE WEEKLY 보고서 HTML 에서 홈페이지 TRENDS 탭이 읽을 JSON 을 뽑는다.

왜: 홈페이지(recode.re.kr/TRENDS)는 주보를 '서지와 링크'만 보여 준다 — **한글 번역 초록은 싣지 않는다**
(2026-11-04 사용자 결정). 출판사 초록의 번역을 공개 게시하는 저작권 위험을 피하면서 동향은 그대로 전한다.
그래서 보고서에서 에디터 노트와 논문 서지(제목·한글 제목·저널·IF·저자·연도·PubMed/원문 링크)만 가려 담는다.

무엇을 넣지 않나: `div.korean-abstract`(번역 초록) 전체. 이 스크립트는 그 칸을 읽지도 않는다.

쓰는 곳: `--out` 에 `index.json`(호 목록 + 에디터 노트)과 호마다 `<stamp>.json`(서지)을 쓴다.
홈페이지 블록 JS 가 이 둘만 읽는다. 보고서 HTML 자체는 공개 홈페이지에서 불러오지 않는다.

**이미 만들어 둔 호는 다시 만들지 않는다**(`--rebuild` 로만 강제). 옛 호의 IF 를 `fix_if.py` 로 바로잡아
두었기 때문이다 — 다시 파싱하면 보고서 HTML 의 틀린 IF 로 되돌아간다. 색인은 늘 디스크의 호 파일로 다시 만든다.

사용:
  python3 build_trends.py --reports <주보저장소>/reports --index <주보저장소>/web/reports.json --out <출력폴더>
  python3 build_trends.py --reports ... --out ... --rebuild   # 전부 다시 파싱(IF 교정은 날아간다)
"""
import argparse
import datetime as dt
import html as htmllib
import json
import re
from pathlib import Path

PAPER_RE = re.compile(r'<div class="paper (\w+)-if">(.*?)(?=<div class="paper |</section>)', re.S)
TITLE_RE = re.compile(r'<h3 class="paper-title">\s*(\d+)\.\s*(.*?)</h3>', re.S)
KO_RE = re.compile(r'<div class="korean-title">\s*&rarr;|<div class="korean-title">\s*→\s*(.*?)</div>', re.S)
KOT_RE = re.compile(r'<div class="korean-title">\s*(?:→|&rarr;)?\s*(.*?)</div>', re.S)
IF_RE = re.compile(r'<span class="badge if-badge">IF\s*([\d.]+)</span>')
JOURNAL_RE = re.compile(r'<span class="badge journal-badge">(.*?)</span>', re.S)
META_RE = re.compile(r'<div class="meta-info">\s*(.*?)\s*</div>', re.S)
AUTH_RE = re.compile(r'^(.*?)\s*\((\d{4}(?:-\d{2}(?:-\d{2})?)?)\)\s*(?:\||$)', re.S)
LINK_RE = re.compile(r'<a href="([^"]+)"[^>]*>(.*?)</a>', re.S)
BRIEF_RE = re.compile(r'<li[^>]*>(.*?)</li>', re.S)
NOTE_RE = re.compile(r'에디터 노트</h2>(.*?)</section>', re.S)
EMBED_RE = re.compile(r'<script type="application/json" id="recode-meta">(.*?)</script>', re.S)
SECTION_RE = re.compile(r'<h2 class="section-title">(.*?)</h2>(.*?)</section>', re.S)


def text(s):
    """태그를 걷고 엔티티를 풀어 한 줄로."""
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def links_of(markup):
    """meta-info / brief 항목의 링크 → (pubmed, fulltext, oa)."""
    pubmed = fulltext = None
    oa = False
    for href, label in LINK_RE.findall(markup):
        lab = text(label)
        if "pubmed" in href.lower():
            pubmed = href
        elif "PubMed" in lab:
            pubmed = href
        else:
            fulltext = htmllib.unescape(href)
            oa = "무료" in lab
    return pubmed, fulltext, oa


def parse_detailed(chunk):
    """자세히 실린 논문 한 편 — 번역 초록은 건드리지 않는다."""
    t = TITLE_RE.search(chunk)
    if not t:
        return None
    ko = KOT_RE.search(chunk)
    iff = IF_RE.search(chunk)
    jr = JOURNAL_RE.search(chunk)
    mi = META_RE.search(chunk)
    authors = year = ""
    pubmed = fulltext = None
    oa = False
    if mi:
        head = mi.group(1).split("|")[0]
        a = AUTH_RE.search(text(head) + " |")
        if a:
            authors, year = text(a.group(1)), a.group(2)
        else:
            authors = text(head)
        pubmed, fulltext, oa = links_of(mi.group(1))
    return {"n": int(t.group(1)), "title": text(t.group(2)),
            "title_ko": text(ko.group(1)) if ko else "",
            "if": float(iff.group(1)) if iff else None,
            "journal": text(jr.group(1)) if jr else "",
            "authors": authors, "year": year,
            "pubmed": pubmed, "fulltext": fulltext, "oa": oa, "detailed": True}


def parse_brief(item):
    """'그 밖의 논문' 한 줄 — 제목 / 저널 · IF · 링크."""
    head = item.split("<br>")[0]
    tail = item[len(head):]
    meta = text(re.sub(r"<a .*?</a>", "", tail))
    journal, iff = meta, None
    m = re.search(r"^(.*?)\s*·?\s*IF\s*([\d.]+)", meta)
    if m:
        journal, iff = m.group(1).strip(" ·"), float(m.group(2))
    pubmed, fulltext, oa = links_of(tail)
    return {"n": None, "title": text(head), "title_ko": "", "if": iff, "journal": journal,
            "authors": "", "year": "", "pubmed": pubmed, "fulltext": fulltext, "oa": oa, "detailed": False}


def parse_report(markup):
    """보고서 HTML → {note, sections[]}. 번역 초록은 담지 않는다."""
    note = ""
    em = EMBED_RE.search(markup)
    if em:
        try:
            note = (json.loads(em.group(1)) or {}).get("editor_note") or ""
        except json.JSONDecodeError:
            note = ""
    if not note:
        n = NOTE_RE.search(markup)
        note = text(n.group(1)) if n else ""

    sections = []
    for head, body in SECTION_RE.findall(markup):
        name = text(head)
        if "에디터" in name:
            continue
        papers = [p for p in (parse_detailed(c) for _, c in PAPER_RE.findall(body + "</section>")) if p]
        if not papers and "<li" in body:
            papers = [parse_brief(i) for i in BRIEF_RE.findall(body)]
            papers = [p for p in papers if p["title"]]
        if papers:
            sections.append({"name": name, "papers": papers})
    return {"note": note, "sections": sections}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reports", required=True, help="주보 저장소의 reports/ 폴더")
    ap.add_argument("--index", help="web/reports.json (호 제목·날짜). 없으면 파일 이름에서 날짜를 읽는다")
    ap.add_argument("--out", required=True)
    ap.add_argument("--rebuild", action="store_true", help="이미 만든 호도 다시 파싱한다(IF 교정이 날아간다)")
    a = ap.parse_args()

    reports = Path(a.reports)
    out = Path(a.out)
    (out).mkdir(parents=True, exist_ok=True)

    titles = {}
    if a.index and Path(a.index).exists():
        idx = json.loads(Path(a.index).read_text(encoding="utf-8"))
        for r in idx.get("reports", idx if isinstance(idx, list) else []):
            titles[r["filename"]] = (r.get("date"), r.get("title"))

    made, kept, empty = [], 0, []
    for f in sorted(reports.glob("recode_weekly_*.html"), reverse=True):
        stamp = f.stem.replace("recode_weekly_", "")
        target = out / f"{stamp}.json"
        if target.exists() and not a.rebuild:
            kept += 1
            continue
        date, title = titles.get(f.name, (None, None))
        if not date:
            date = f"{stamp[0:4]}-{stamp[4:6]}-{stamp[6:8]}"
            title = f"RECODE WEEKLY {date.replace('-', '.')}"
        d = parse_report(f.read_text(encoding="utf-8"))
        if not any(s["papers"] for s in d["sections"]):
            empty.append(f.name)
            continue
        target.write_text(json.dumps(
            {"stamp": stamp, "date": date, "title": title, "note": d["note"], "sections": d["sections"]},
            ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        made.append(stamp)

    # 색인은 늘 디스크에 있는 호 파일로 다시 만든다 — 같은 날 여러 번 만든 호는 마지막 것만(대시보드와 같은 규칙)
    issues, seen = [], set()
    for p in sorted(out.glob("*.json"), key=lambda x: x.name, reverse=True):
        if p.name == "index.json":
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        if d["date"] in seen:
            continue
        seen.add(d["date"])
        issues.append({"stamp": d["stamp"], "date": d["date"], "title": d["title"], "note": d["note"],
                       "total": sum(len(s["papers"]) for s in d["sections"]),
                       "top": [p2["title_ko"] or p2["title"] for s in d["sections"] for p2 in s["papers"][:3]][:3]})
    (out / "index.json").write_text(json.dumps(
        {"generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "issues": issues},
        ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(json.dumps({"issues": len(issues), "new": len(made), "kept": kept, "empty": empty,
                      "papers": sum(i["total"] for i in issues)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
