#!/usr/bin/env python3
"""検索CLI: python3 scripts/kb.py "酒母 温度" -k 5 [--source akahon] [--full]
空白区切りはAND。3文字以上の語は FTS5(trigram, bm25)、2文字以下の語は LIKE で補う（trigramは3文字未満を引けない）。"""
import argparse, os, sqlite3
DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "sake_kb.sqlite")
COLS = ["chunk_id", "source_id", "title", "part", "pdf_page", "text", "score"]

def search(query: str, k=5, source=None, db=DB):
    terms = [t for t in query.split() if t]
    if not terms: return []
    long_t = [t for t in terms if len(t) >= 3]; short_t = [t for t in terms if len(t) < 3]
    con = sqlite3.connect(db)
    where, args = [], []
    if long_t:
        base = """SELECT c.chunk_id, c.source_id, s.title, c.part, c.pdf_page, c.text, bm25(chunks_fts) AS score
                  FROM chunks_fts JOIN chunks c ON c.chunk_id = chunks_fts.chunk_id JOIN sources s USING(source_id)
                  WHERE chunks_fts MATCH ?"""
        args.append(" AND ".join('"' + t.replace('"', '""') + '"' for t in long_t))
    else:
        base = """SELECT c.chunk_id, c.source_id, s.title, c.part, c.pdf_page, c.text, 0.0 AS score
                  FROM chunks c JOIN sources s USING(source_id) WHERE 1=1"""
    for t in short_t:
        where.append("c.text LIKE ?"); args.append(f"%{t}%")
    if source:
        where.append("c.source_id = ?"); args.append(source)
    sql = base + "".join(" AND " + w for w in where)
    rows = [dict(zip(COLS, r)) for r in con.execute(sql, args)]
    con.close()
    if not long_t:  # 出現回数の多い順（LIKEのみのとき）
        for r in rows: r["score"] = -sum(r["text"].count(t) for t in short_t)
    rows.sort(key=lambda r: r["score"])
    return rows[:k]

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("query"); ap.add_argument("-k", type=int, default=5)
    ap.add_argument("--source"); ap.add_argument("--full", action="store_true")
    a = ap.parse_args()
    for r in search(a.query, a.k, a.source):
        body = r["text"] if a.full else r["text"][:160].replace("\n", " ") + ("…" if len(r["text"]) > 160 else "")
        print(f"[{r['title']} / {r['part']} / p.{r['pdf_page']}] ({r['chunk_id']})\n  {body}\n")
