#!/usr/bin/env python3
"""『47都道府県・発酵文化百科』の頁つき構造化事実（data/hyakka/*.jsonl、Claude ビジョンで抽出・逐語ではない）→ SQLite に source_id=hyakka-hakko で差し替え投入。
1行 = 1事実 {file, spread, side, printed_page, prefecture, section, type, name, fact, confidence}。
pages の単位は「分割PDF / 見開き番号 / 左右」。引用は 印刷頁（printed_page）を優先し、無ければ見開き番号で行う。
非公開圏のデータ（図書館蔵書スキャン由来）。チャンク本文をゲーム・HPに転載しない。"""
import glob, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kbdb
from extract_books import chunk_text

BOOKS = {  # 引数 --book のキー → (source_id, 事実JSONLの置き場)
    "hakko": ("hyakka-hakko", os.path.join(kbdb.ROOT, "data", "hyakka")),
    "dentoshoku": ("hyakka-dentoshoku", os.path.join(kbdb.ROOT, "data", "hyakka_dentoshoku")),
    "chomiryo": ("hyakka-chomiryo", os.path.join(kbdb.ROOT, "data", "hyakka_chomiryo")),
}
SRC = "hyakka-hakko"
DIR = BOOKS["hakko"][1]
KEYS = ["file", "spread", "side", "printed_page", "prefecture", "section", "type", "name", "fact", "confidence"]

def load(d=None):
    rows = []
    for p in sorted(glob.glob(os.path.join(d or DIR, "*.jsonl"))):
        for n, line in enumerate(open(p, encoding="utf-8"), 1):
            line = line.strip()
            if not line: continue
            try: d = json.loads(line)
            except json.JSONDecodeError as e: print(f"!! {os.path.basename(p)}:{n} JSON不正 {e}", file=sys.stderr); continue
            miss = [k for k in KEYS if k not in d]
            if miss: print(f"!! {os.path.basename(p)}:{n} 欠けキー {miss}", file=sys.stderr); continue
            rows.append(d)
    return rows

def build(book="hakko", db_path=kbdb.DB):
    SRC, DIR = BOOKS[book]
    s = next((x for x in kbdb.read_sources() if x["source_id"] == SRC), None)
    if not s: sys.exit(f"sources.csv に {SRC} の行がない")
    rows = load(DIR)
    if not rows: sys.exit(f"{DIR}/*.jsonl が空")
    con = kbdb.connect(db_path); t0 = time.time()
    kbdb.clear_source(con, SRC); kbdb.upsert_source(con, s)
    groups = {}
    for d in rows: groups.setdefault((d["file"], int(d["spread"]), d["side"]), []).append(d)
    # 分割PDFの境界頁が2ファイルに重複スキャンされていることがある（同じ印刷頁が別 file に存在）。
    # 同じ printed_page が複数の file にあれば、事実件数の多い方を残し他を落とす（前付のローマ数字頁は printed_page が本文と衝突するので対象外）。
    by_page = {}
    for key, facts in groups.items():
        pp = next((x["printed_page"] for x in facts if x.get("printed_page") is not None), None)
        if pp is None or key[0].startswith("1.はじめに"): continue
        by_page.setdefault(int(pp), []).append(key)
    dropped = 0
    for pp, keys in by_page.items():
        files = {k[0] for k in keys}
        if len(files) < 2: continue
        keep = max(keys, key=lambda k: len(groups[k]))
        for k in keys:
            if k != keep and k[0] != keep[0]:
                dropped += len(groups.pop(k)); print(f"  境界重複を除外: p.{pp} {k[0]} 見開き{k[1]:03d}{k[2]}（{keep[0]} を採用）")
    if dropped: print(f"  重複除外 合計 {dropped} 件")
    n_chunks = 0
    for (f, sp, side), facts in sorted(groups.items()):
        part = f"{f}/見開き{sp:03d}{side}"
        pp = next((x["printed_page"] for x in facts if x.get("printed_page") is not None), None)
        lines = []
        for x in facts:
            tag = f"〔確度{x.get('confidence')}〕" if x.get("confidence") in ("medium", "low") else ""
            lines.append(f"【{x['prefecture']}｜{x['section']}】{x['type']}: {x['name']} — {x['fact']}{tag}")
        text = "\n".join(lines)
        page_no = int(pp) if pp is not None else 0
        con.execute("INSERT OR REPLACE INTO pages VALUES(?,?,?,?)", (SRC, part, page_no, text))
        for k, ch in enumerate(chunk_text(text)):
            con.execute("INSERT OR REPLACE INTO chunks(chunk_id,source_id,part,pdf_page,seq,text) VALUES(?,?,?,?,?,?)",
                        (f"{SRC}/{part}/p{page_no:04d}/{k}", SRC, part, page_no, k, ch)); n_chunks += 1
    con.commit(); con.close()
    print(f"{SRC:<18} facts={len(rows)} pages={len(groups)} chunks={n_chunks} elapsed={time.time()-t0:.1f}s")

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--book", choices=list(BOOKS), default="hakko")
    build(ap.parse_args().book)
