#!/usr/bin/env python3
"""醸造協会誌の論文を **元PDFから頁単位で** 抽出して SQLite に source_id=jbsj として差し替え投入。標準ライブラリ＋poppler。
- 書誌と本文の退避用テキストは data/jbsj_corpus.jsonl（export_jbsj_corpus.py の出力）
- 本文は Drive 論文DB/0_pdfs の PDF を pdftotext -raw で頁ごとに取る（2段組なので default だと左右の行が混ざり空行だらけになる。実測済み。OCR済み120本は ocr_out/ 配下）
- 印刷頁 = 開始ページ + pdf_page - 1。PDF頁数 == 終了-開始+1 を満たす論文だけ印刷頁を確定（docs.page_ok=1）。
  満たさない／PDFが無い論文は corpus の本文を頁なし（pdf_page=0）で入れる
使い方: python3 scripts/ingest_papers.py [--limit N] [--workers 8]"""
import argparse, json, os, re, subprocess, sys, time
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kbdb
from extract_books import normalize_page, chunk_text

SRC = "jbsj"
JSONL = os.path.join(kbdb.ROOT, "data", "jbsj_corpus.jsonl")
MANIFEST = os.path.join(kbdb.ROOT, "data", "manifest_papers.json")
PDF_ROOT = os.path.join(kbdb.DRIVE, "31.AI事業/5.アプリ開発/論文DB/0_pdfs")

def pdf_path(d):
    base = os.path.join(PDF_ROOT, "ocr_out") if d["ocr"] == "ocr" else PDF_ROOT
    p = os.path.join(base, d["rel_path"])
    return p if os.path.exists(p) else None

def extract(d):
    """1論文分。戻り: (part, pages:list[str] or None, reason)"""
    p = pdf_path(d)
    if not p: return d["file_name"], None, "pdf_missing"
    try:
        txt = subprocess.run(["pdftotext", "-enc", "UTF-8", "-raw", p, "-"], capture_output=True, text=True, check=True, timeout=120).stdout
    except Exception as e:
        return d["file_name"], None, f"pdftotext_error:{type(e).__name__}"
    pages = txt.split("\f")
    if pages and not pages[-1].strip(): pages = pages[:-1]
    rng = (d["page_end"] or 0) - (d["page_start"] or 0) + 1
    if d["page_start"] is None: return d["file_name"], None, "no_bib"
    if len(pages) != rng: return d["file_name"], None, f"page_mismatch:{len(pages)}!={rng}"
    norm = [normalize_page(pg, ocr_fix=False) for pg in pages]
    if sum(map(len, norm)) < 200: return d["file_name"], None, "too_short"
    return d["file_name"], norm, "ok"

def build(limit=None, workers=8, db_path=kbdb.DB):
    s = next((x for x in kbdb.read_sources() if x["source_id"] == SRC), None)
    if not s: sys.exit("sources.csv に jbsj の行がない")
    if not os.path.exists(JSONL): sys.exit(f"{JSONL} がない。先に ../jbsj/.venv/bin/python scripts/export_jbsj_corpus.py")
    docs = [json.loads(l) for l in open(JSONL, encoding="utf-8")]
    if limit: docs = docs[:limit]
    t0 = time.time(); results = {}
    with ProcessPoolExecutor(workers) as ex:
        for i, (fn, pages, reason) in enumerate(ex.map(extract, docs, chunksize=8), 1):
            results[fn] = (pages, reason)
            if i % 500 == 0: print(f"  extracted {i}/{len(docs)} {time.time()-t0:.0f}s", flush=True)
    con = kbdb.connect(db_path)
    con.execute("ALTER TABLE docs ADD COLUMN page_ok INTEGER DEFAULT 0") if "page_ok" not in [r[1] for r in con.execute("PRAGMA table_info(docs)")] else None
    kbdb.clear_source(con, SRC); kbdb.upsert_source(con, s)
    n_chunks = n_chars = n_paged = 0; reasons = {}
    for d in docs:
        part = os.path.splitext(d["file_name"])[0]
        pages, reason = results[d["file_name"]]
        reasons[reason] = reasons.get(reason, 0) + 1
        if pages is None: pages = {0: normalize_page(d["text"], ocr_fix=False)}
        else: pages = dict(enumerate(pages, start=1)); n_paged += 1
        con.execute("INSERT INTO docs(source_id,part,title,authors,year,vol,no,page_start,page_end,url,page_ok) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (SRC, part, d["title"], d["authors"], d["year"], d["vol"], d["no"], d["page_start"], d["page_end"], d["url"], int(reason == "ok")))
        rows = []
        for pg, text in pages.items():
            if not text.strip(): continue
            con.execute("INSERT INTO pages VALUES(?,?,?,?)", (SRC, part, pg, text))
            rows += [(f"{SRC}/{part}/p{pg:04d}/{k}", SRC, part, pg, k, ch) for k, ch in enumerate(chunk_text(text))]
            n_chars += len(text)
        con.executemany("INSERT INTO chunks(chunk_id,source_id,part,pdf_page,seq,text) VALUES(?,?,?,?,?,?)", rows)
        n_chunks += len(rows)
    con.commit(); con.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('optimize')"); con.commit(); con.close()
    json.dump({"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "docs": len(docs), "paged_docs": n_paged, "chunks": n_chunks, "chars": n_chars,
               "reasons": reasons, "failed": sorted(fn for fn, (p, r) in results.items() if p is None)},
              open(MANIFEST, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{SRC:<18} docs={len(docs)} paged={n_paged} chars={n_chars:,} chunks={n_chunks:,} reasons={reasons} elapsed={time.time()-t0:.0f}s")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--limit", type=int); ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args(); build(a.limit, a.workers)
