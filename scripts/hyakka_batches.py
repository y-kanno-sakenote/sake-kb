#!/usr/bin/env python3
"""百科の抽出バッチ計画を JSON で出す。使い方: python3 scripts/hyakka_batches.py --book dentoshoku [--per 3]
出力: [{"file":"4.関東","spreads":[1,2,3],"images":[...絶対パス...],"out":"<jsonl絶対パス>"}, ...]
既に out が存在し、かつ中身に対象見開きが全部あるバッチは "done": true を付ける（再実行時のスキップ用）。"""
import argparse, glob, json, os, re, unicodedata
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOOKS = {"hakko": ("hyakka", "発酵文化百科"), "dentoshoku": ("hyakka_dentoshoku", "伝統食百科"), "chomiryo": ("hyakka_chomiryo", "伝統調味料百科")}

def plan(book, per=3):
    data_dir, title = BOOKS[book]
    img_root = os.path.join(ROOT, "data", "hyakka_img", book)
    out_dir = os.path.join(ROOT, "data", data_dir)
    batches = []
    for d in sorted(glob.glob(os.path.join(img_root, "*")), key=lambda p: [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", os.path.basename(p))]):
        fname = unicodedata.normalize("NFC", os.path.basename(d))
        spreads = sorted({int(os.path.basename(p)[:3]) for p in glob.glob(os.path.join(d, "*.png"))})
        for i in range(0, len(spreads), per):
            chunk = spreads[i:i + per]
            if len(spreads) - (i + per) == 1: chunk = spreads[i:]   # 端数1見開きは前のバッチに吸収
            imgs = [os.path.join(d, f"{k:03d}{side}.png") for k in chunk for side in ("R", "L")]
            out = os.path.join(out_dir, f"{fname}_{chunk[0]:03d}-{chunk[-1]:03d}.jsonl")
            done = False
            if os.path.exists(out):
                have = set()
                for line in open(out, encoding="utf-8"):
                    if line.strip():
                        try: have.add(int(json.loads(line)["spread"]))
                        except Exception: pass
                done = set(chunk) <= have or (os.path.getsize(out) > 0 and len(have) >= max(1, len(chunk) - 1))
            batches.append({"file": fname, "spreads": chunk, "images": imgs, "out": out, "done": done})
            if chunk[-1] == spreads[-1]: break
    return {"book": book, "title": title, "batches": batches}

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--book", choices=list(BOOKS), required=True); ap.add_argument("--per", type=int, default=3)
    print(json.dumps(plan(ap.parse_args().book, ap.parse_args().per), ensure_ascii=False, indent=1))
