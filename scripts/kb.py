#!/usr/bin/env python3
"""検索CLI: python3 scripts/kb.py "酒母 温度" -k 5 [--source akahon|jbsj] [--full]
空白区切りはAND。3文字以上の語は FTS5(trigram, bm25)、2文字以下の語は LIKE で補う（trigramは3文字未満を引けない）。"""
import argparse, os, sqlite3
DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "sake_kb.sqlite")
COLS = ["chunk_id", "source_id", "title", "part", "pdf_page", "text", "score", "doc_title", "authors", "year", "vol", "no", "page_start", "page_end", "url", "page_ok"]
SEL = """c.chunk_id, c.source_id, s.title, c.part, c.pdf_page, c.text, {score},
         d.title, d.authors, d.year, d.vol, d.no, d.page_start, d.page_end, d.url, d.page_ok"""

# 異体字の展開：DB は原文どおり（麴＝旧字を使う論文・資料が約560チャンク）なので、検索側で両方を引く
VARIANTS = {"麹": "麴", "麴": "麹"}
def variants(t: str):
    out = {t}
    for a, b in VARIANTS.items():
        if a in t: out.add(t.replace(a, b))
    return sorted(out)

def search(query: str, k=5, source=None, db=DB):
    terms = [t for t in query.split() if t]
    if not terms: return []
    long_t = [t for t in terms if len(t) >= 3]; short_t = [t for t in terms if len(t) < 3]
    con = sqlite3.connect(db); where, args = [], []
    joins = "JOIN sources s ON s.source_id=c.source_id LEFT JOIN docs d ON d.source_id=c.source_id AND d.part=c.part"
    if long_t:
        base = f"SELECT {SEL.format(score='bm25(chunks_fts)')} FROM chunks_fts JOIN chunks c ON c.id=chunks_fts.rowid {joins} WHERE chunks_fts MATCH ?"
        args.append(" AND ".join("(" + " OR ".join('"' + v.replace('"', '""') + '"' for v in variants(t)) + ")" for t in long_t))
    else:
        base = f"SELECT {SEL.format(score='0.0')} FROM chunks c {joins} WHERE 1=1"
    for t in short_t:
        vs = variants(t); where.append("(" + " OR ".join("c.text LIKE ?" for _ in vs) + ")"); args.extend(f"%{v}%" for v in vs)
    if source: where.append("c.source_id = ?"); args.append(source)
    rows = [dict(zip(COLS, r)) for r in con.execute(base + "".join(" AND " + w for w in where), args)]
    con.close()
    if not long_t:
        for r in rows: r["score"] = -sum(r["text"].count(v) for t in short_t for v in variants(t))
    rows.sort(key=lambda r: r["score"])
    return rows[:k]

def cite(r):
    """引用表記。論文は 誌名 巻(号) 年 頁範囲 著者「題名」、本は 題名 / 分割ファイル / PDF頁。"""
    if r["doc_title"]:
        if r["vol"] is None or r["year"] is None:   # 書誌欠け（上流 app_db に無い論文）
            return f"{r['title']} 書誌未登録 {r['part']}"
        pg = f" p.{r['page_start'] + r['pdf_page'] - 1}" if r["page_ok"] and r["pdf_page"] else ""
        return f"{r['title']} {r['vol']}({r['no']}) {r['year']} pp.{r['page_start']}-{r['page_end']}{pg} {r['authors'] or '著者不明'}「{r['doc_title']}」"
    return f"{r['title']} / {r['part']}" + (f" / p.{r['pdf_page']}" if r["pdf_page"] else "")   # 頁不明（前付・欠落）は見開きだけで引用

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("query"); ap.add_argument("-k", type=int, default=5)
    ap.add_argument("--source"); ap.add_argument("--full", action="store_true")
    a = ap.parse_args()
    hits = search(a.query, a.k, a.source)
    if not hits: print("0件")
    terms = [t for t in a.query.split() if t]
    for r in hits:
        if a.full: body = r["text"]
        else:
            lines = r["text"].split("\n")
            hit_lines = [l for l in lines if any(t in l for t in terms)] if len(lines) > 1 else []
            body = (" / ".join(hit_lines[:2])[:200] + ("…" if len(hit_lines) > 2 else "")) if hit_lines else r["text"][:160].replace("\n", " ") + ("…" if len(r["text"]) > 160 else "")
        print(f"[{cite(r)}] ({r['chunk_id']})\n  {body}\n")
