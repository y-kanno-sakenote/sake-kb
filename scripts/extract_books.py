#!/usr/bin/env python3
"""自炊本PDF → 正規化テキスト → SQLite（pages / chunks / FTS5）。標準ライブラリ＋poppler のみ。"""
import csv, glob, hashlib, json, os, re, sqlite3, subprocess, sys, time
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRIVE = "/Users/ymacmini/Library/CloudStorage/GoogleDrive-y.kanno@sakenote.net/マイドライブ/サケノテ"
DB = os.path.join(ROOT, "data", "sake_kb.sqlite")
MANIFEST = os.path.join(ROOT, "data", "manifest.json")
CHUNK_MAX = 800

NA = r"[^\x00-\x7f]"            # 非ASCII（日本語）
RE_SP_NA_NA = re.compile(rf"(?<={NA})[^\S\n]+(?={NA})")
RE_SP_NA_D = re.compile(rf"(?<={NA})[^\S\n]+(?=[0-9])")
RE_SP_D_NA = re.compile(rf"(?<=[0-9])[^\S\n]+(?={NA})")
RE_PAGENO = re.compile(r"^[\s\d\-–—・.]*$")
RE_SP_NA_P = re.compile(rf"(?<={NA})[^\S\n]+(?=[,.):;])")   # 「が , その」型
RE_SP_P_NA = re.compile(rf"(?<=[,(])[^\S\n]+(?={NA})")

# OCRの固定誤字（JIS第2水準の醸造用字が別字に読まれる）。コーパス実測で誤読以外の用例が無いことを確認済み（疏水・膠質は0件）
OCR_FIX = str.maketrans({"疏": "酛", "膠": "醪"})

def normalize_line(s: str) -> str:
    s = s.strip().translate(OCR_FIX)
    s = RE_SP_NA_NA.sub("", s)
    s = RE_SP_NA_NA.sub("", s)  # 3連続以上の隙間を潰すため2回
    s = RE_SP_NA_D.sub("", s)
    s = RE_SP_D_NA.sub("", s)
    s = RE_SP_NA_P.sub("", s)
    s = RE_SP_P_NA.sub("", s)
    return s

def normalize_page(raw: str) -> str:
    """行を段落に畳む。日本語同士の改行は連結、空行は段落区切り。数字だけの行（頁番号）は捨てる。"""
    paras, buf = [], ""
    for line in raw.split("\n"):
        ln = normalize_line(line)
        if not ln or RE_PAGENO.match(ln):
            if buf: paras.append(buf); buf = ""
            continue
        if buf and re.search(rf"{NA}$", buf) and re.match(NA, ln):
            buf += ln
        else:
            buf = (buf + " " + ln) if buf else ln
    if buf: paras.append(buf)
    return "\n".join(paras)

def chunk_text(text: str, limit=CHUNK_MAX):
    """段落を積み、limitを超えたら「。」境界で切る。"""
    out, cur = [], ""
    for para in text.split("\n"):
        while len(para) > limit:
            cut = para.rfind("。", 0, limit)
            cut = cut + 1 if cut > limit // 2 else limit
            if cur: out.append(cur); cur = ""
            out.append(para[:cut]); para = para[cut:]
        if len(cur) + len(para) + 1 > limit and cur:
            out.append(cur); cur = para
        else:
            cur = (cur + "\n" + para) if cur else para
    if cur: out.append(cur)
    return [c for c in out if c.strip()]

def pdf_pages(path: str, mode="default"):
    """mode=raw はコンテンツ順（2段組の本で左右の行が混ざるのを防ぐ。単段の本では default の方が安定）"""
    args = ["-raw"] if mode == "raw" else []
    txt = subprocess.run(["pdftotext", "-enc", "UTF-8", *args, path, "-"], capture_output=True, text=True, check=True).stdout
    pages = txt.split("\f")
    if pages and not pages[-1].strip(): pages = pages[:-1]
    return pages

def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

def resolve_files(drive_path: str):
    pat = os.path.join(DRIVE, drive_path)
    files = sorted(glob.glob(pat))
    # 原本/ と結合版 日本酒の基.pdf は除外
    return [f for f in files if "/原本/" not in f and os.path.basename(f) != "日本酒の基.pdf"]

def build(db_path=DB):
    if os.path.exists(db_path): os.remove(db_path)
    con = sqlite3.connect(db_path)
    con.executescript("""
    CREATE TABLE sources(source_id TEXT PRIMARY KEY, title, publisher, year, edition, type, tier, drive_path, note, extract_mode);
    CREATE TABLE pages(source_id, part, pdf_page INTEGER, text, PRIMARY KEY(source_id, part, pdf_page));
    CREATE TABLE chunks(chunk_id TEXT PRIMARY KEY, source_id, part, pdf_page INTEGER, seq INTEGER, text);
    CREATE VIRTUAL TABLE chunks_fts USING fts5(text, chunk_id UNINDEXED, tokenize='trigram');
    """)
    manifest = {"generated_at": datetime.now().isoformat(timespec="seconds"), "chunk_max": CHUNK_MAX, "files": []}
    with open(os.path.join(ROOT, "sources.csv"), encoding="utf-8") as f:
        srcs = list(csv.DictReader(f))
    t0 = time.time()
    for s in srcs:
        con.execute("INSERT INTO sources VALUES(?,?,?,?,?,?,?,?,?,?)", [s[k] for k in s])
        files = resolve_files(s["drive_path"])
        if not files: print(f"!! {s['source_id']}: ファイルなし {s['drive_path']}", file=sys.stderr); continue
        n_chunks = n_chars = n_pages = 0
        for path in files:
            part = os.path.splitext(os.path.basename(path))[0]
            pages = pdf_pages(path, s.get("extract_mode") or "default")
            fchars = 0
            for i, raw in enumerate(pages, start=1):
                text = normalize_page(raw)
                if not text.strip(): continue
                con.execute("INSERT INTO pages VALUES(?,?,?,?)", (s["source_id"], part, i, text))
                for k, ch in enumerate(chunk_text(text)):
                    cid = f"{s['source_id']}/{part}/p{i:04d}/{k}"
                    con.execute("INSERT INTO chunks VALUES(?,?,?,?,?,?)", (cid, s["source_id"], part, i, k, ch))
                    con.execute("INSERT INTO chunks_fts(text, chunk_id) VALUES(?,?)", (ch, cid))
                    n_chunks += 1
                fchars += len(text)
            n_pages += len(pages); n_chars += fchars
            manifest["files"].append({"source_id": s["source_id"], "part": part, "path": os.path.relpath(path, DRIVE),
                                      "md5": md5(path), "pages": len(pages), "chars": fchars})
        print(f"{s['source_id']:<18} files={len(files):>2} pages={n_pages:>4} chars={n_chars:>9,} chunks={n_chunks:>5}")
    con.commit(); con.close()
    manifest["elapsed_sec"] = round(time.time() - t0, 1)
    json.dump(manifest, open(MANIFEST, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"done {manifest['elapsed_sec']}s -> {db_path}")

if __name__ == "__main__":
    build()
