"""SQLite スキーマと共通操作。chunks_fts は chunks を外部コンテンツにした FTS5（本文を二重に持たない）。"""
import os, sqlite3
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "sake_kb.sqlite")
DRIVE = "/Users/ymacmini/Library/CloudStorage/GoogleDrive-y.kanno@sakenote.net/マイドライブ/サケノテ"
SCHEMA = """
CREATE TABLE IF NOT EXISTS sources(source_id TEXT PRIMARY KEY, title, publisher, year, edition, type, tier, drive_path, note, extract_mode);
CREATE TABLE IF NOT EXISTS docs(source_id, part, title, authors, year INTEGER, vol INTEGER, no INTEGER, page_start INTEGER, page_end INTEGER, url, PRIMARY KEY(source_id, part));
CREATE TABLE IF NOT EXISTS pages(source_id, part, pdf_page INTEGER, text, PRIMARY KEY(source_id, part, pdf_page));
CREATE TABLE IF NOT EXISTS chunks(id INTEGER PRIMARY KEY, chunk_id TEXT UNIQUE, source_id, part, pdf_page INTEGER, seq INTEGER, text);
CREATE INDEX IF NOT EXISTS chunks_src ON chunks(source_id);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(text, content='chunks', content_rowid='id', tokenize='trigram');
CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text); END;
CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES('delete', old.id, old.text); END;
CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
  INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES('delete', old.id, old.text);
  INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text); END;
"""

def connect(db_path=DB):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    con = sqlite3.connect(db_path)
    con.executescript("PRAGMA journal_mode=WAL; PRAGMA synchronous=OFF;" + SCHEMA)
    return con

def clear_source(con, source_id):
    """ソース単位で差し替える（他ソースは触らない）。"""
    for t in ("chunks", "pages", "docs", "sources"):
        con.execute(f"DELETE FROM {t} WHERE source_id=?", (source_id,))

def upsert_source(con, s: dict):
    cols = ["source_id", "title", "publisher", "year", "edition", "type", "tier", "drive_path", "note", "extract_mode"]
    con.execute(f"INSERT OR REPLACE INTO sources({','.join(cols)}) VALUES({','.join('?'*len(cols))})", [s.get(c) for c in cols])

def read_sources():
    import csv
    with open(os.path.join(ROOT, "sources.csv"), encoding="utf-8") as f:
        return list(csv.DictReader(f))
