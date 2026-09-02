#!/usr/bin/env python3
"""data/jbsj_corpus.jsonl（export_jbsj_corpus.py の出力）→ 正規化 → SQLite に source_id=jbsj として差し替え投入。標準ライブラリのみ。
論文本文には頁区切りが無いので pdf_page=0（論文単位）。引用は docs の 巻(号)・頁範囲 で行う。"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kbdb
from extract_books import normalize_page, chunk_text

SRC = "jbsj"
JSONL = os.path.join(kbdb.ROOT, "data", "jbsj_corpus.jsonl")

def build(db_path=kbdb.DB):
    s = next((x for x in kbdb.read_sources() if x["source_id"] == SRC), None)
    if not s: sys.exit("sources.csv に jbsj の行がない")
    if not os.path.exists(JSONL): sys.exit(f"{JSONL} がない。先に ../jbsj/.venv/bin/python scripts/export_jbsj_corpus.py")
    con = kbdb.connect(db_path); t0 = time.time()
    kbdb.clear_source(con, SRC); kbdb.upsert_source(con, s)
    n_docs = n_chunks = n_chars = 0
    with open(JSONL, encoding="utf-8") as f:
        for line in f:
            d = json.loads(line); part = os.path.splitext(d["file_name"])[0]
            text = normalize_page(d["text"])
            con.execute("INSERT INTO docs VALUES(?,?,?,?,?,?,?,?,?,?)",
                        (SRC, part, d["title"], d["authors"], d["year"], d["vol"], d["no"], d["page_start"], d["page_end"], d["url"]))
            con.execute("INSERT INTO pages VALUES(?,?,?,?)", (SRC, part, 0, text))
            rows = [(f"{SRC}/{part}/p0000/{k}", SRC, part, 0, k, ch) for k, ch in enumerate(chunk_text(text))]
            con.executemany("INSERT INTO chunks(chunk_id,source_id,part,pdf_page,seq,text) VALUES(?,?,?,?,?,?)", rows)
            n_docs += 1; n_chunks += len(rows); n_chars += len(text)
            if n_docs % 1000 == 0: con.commit(); print(f"  {n_docs} docs…", flush=True)
    con.commit(); con.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('optimize')"); con.commit(); con.close()
    print(f"{SRC:<18} docs={n_docs} chars={n_chars:,} chunks={n_chunks:,} elapsed={time.time()-t0:.0f}s")

if __name__ == "__main__":
    build()
