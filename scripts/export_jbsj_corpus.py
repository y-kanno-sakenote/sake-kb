#!/usr/bin/env python3
"""jbsj の corpus.parquet（本文）と app_db.parquet（書誌）を結合して data/jbsj_corpus.jsonl に書き出す。
parquet 読み出しに pyarrow が要るので **jbsj の .venv で実行**する（sake-kb 本体は標準ライブラリのみ）:
  ../jbsj/.venv/bin/python scripts/export_jbsj_corpus.py"""
import hashlib, json, os, sys
import pandas as pd
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = "/Users/ymacmini/Library/CloudStorage/GoogleDrive-y.kanno@sakenote.net/マイドライブ/サケノテ/31.AI事業/5.アプリ開発/論文DB/8_reHP/1.corpus/corpus.parquet"
META = os.path.join(ROOT, "..", "jbsj", "data", "app_db.parquet")
OUT = os.path.join(ROOT, "data", "jbsj_corpus.jsonl")
c = pd.read_parquet(CORPUS, columns=["file_name", "rel_path", "source", "full_text"])
m = pd.read_parquet(META, columns=["file_name", "発行年", "巻数", "号数", "開始ページ", "終了ページ", "論文タイトル", "著者", "HPリンク先"])
m = m.drop_duplicates("file_name")
j = c.merge(m, on="file_name", how="left")
assert len(j) == len(c), "書誌と本文の結合で行数が変わった"
print("書誌欠け:", {k: int(j[k].isna().sum()) for k in ["論文タイトル", "著者", "発行年", "巻数", "号数", "開始ページ", "終了ページ", "HPリンク先"]})
def I(v):
    try: return int(v)
    except (TypeError, ValueError): return None
def S(v): return None if pd.isna(v) else str(v)
def md5(p): return hashlib.md5(open(p, "rb").read()).hexdigest()
with open(OUT, "w", encoding="utf-8") as f:
    for r in j.itertuples(index=False):
        f.write(json.dumps({"file_name": r.file_name, "rel_path": r.rel_path, "ocr": r.source, "title": S(r.論文タイトル) or r.file_name, "authors": S(r.著者),
                            "year": I(r.発行年), "vol": I(r.巻数), "no": I(r.号数), "page_start": I(r.開始ページ), "page_end": I(r.終了ページ),
                            "url": S(r.HPリンク先), "text": r.full_text}, ensure_ascii=False) + "\n")
json.dump({"corpus_parquet": CORPUS, "corpus_md5": md5(CORPUS), "meta_parquet": os.path.abspath(META), "meta_md5": md5(META), "rows": len(j)},
          open(OUT + ".manifest.json", "w"), ensure_ascii=False, indent=1)
print("rows", len(j), "->", OUT)
