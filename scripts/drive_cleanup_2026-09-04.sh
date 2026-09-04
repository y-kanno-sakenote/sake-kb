#!/bin/zsh
# Drive 重複整理（2026-09-04 オーナー承認）。削除はせず「仮置き（月末削除）」へ移動するだけ。
# 冪等: 存在するものだけ動かし、移動先に同名があればスキップ（入れ子にしない）。重複PDFは移動前に正本と全件MD5照合し、1本でも違えば動かさない
set -u
D="$HOME/Library/CloudStorage/GoogleDrive-y.kanno@sakenote.net/マイドライブ/サケノテ"
P="$D/31.AI事業/5.アプリ開発/論文DB"
T="$D/仮置き（月末削除）/2026-09-04_重複整理"
[ -d "$D/31.AI事業" ] || { echo "Google Drive が見当たりません（未マウント）。中止"; exit 1; }
mkdir -p "$T"
mv_if(){ if [ ! -e "$1" ]; then echo "無し（済）: ${1#$D/}"; elif [ -e "$2" ]; then echo "移動先に既存あり・スキップ: ${2#$D/}"; else mv "$1" "$2" && echo "移動: ${1#$D/} → ${2#$D/}"; fi; }
# 正本と重複の全件MD5照合（ファイル一覧が一致し、全ハッシュが一致したときだけ 0 を返す）
same_tree(){ python3 - "$1" "$2" <<'PY'
import sys,os,hashlib
a,b=sys.argv[1],sys.argv[2]
if not os.path.isdir(b): sys.exit(0)   # 重複側が無い＝移動済み
def files(r): return sorted(os.path.relpath(os.path.join(d,f),r) for d,_,fs in os.walk(r) for f in fs if f!='.DS_Store')
fa,fb=files(a),files(b)
if fb and set(fb)-set(fa): print("正本に無いファイルが重複側にある:", list(set(fb)-set(fa))[:5]); sys.exit(2)
def h(p):
    m=hashlib.md5()
    with open(p,'rb') as f:
        for c in iter(lambda: f.read(1<<20), b''): m.update(c)
    return m.hexdigest()
bad=[f for f in fb if h(os.path.join(a,f))!=h(os.path.join(b,f))]
print(f"照合 {len(fb)}本 不一致 {len(bad)}本"); sys.exit(2 if bad else 0)
PY
}
C="$P/0_pdfs/日本醸造協会誌"
# 目次PDF（重複フォルダにだけあった1本）は論文DB直下へ救出
mv_if "$D/32.研究事業/日本醸造協会誌/論文リスト - リスト.pdf" "$P/論文リスト（PDF版）.pdf"
# 0_pdfs と同一（4,278本・MD5一致）の重複2箇所
for dup in "$P/8_reHP/1.corpus/1.rawdata/日本醸造協会誌" "$D/32.研究事業/日本醸造協会誌"; do
  if same_tree "$C" "$dup"; then
    case "$dup" in *8_reHP*) dst="$T/論文DB_8_reHP_1.corpus_1.rawdata_日本醸造協会誌（0_pdfsと同一の重複）";; *) dst="$T/32.研究事業_日本醸造協会誌（0_pdfsと同一の重複）";; esac
    mv_if "$dup" "$dst"
  else echo "MD5 不一致のため動かさない: ${dup#$D/}"; fi
done
rmdir "$P/8_reHP/1.corpus/1.rawdata" 2>/dev/null && echo "空フォルダ削除: 1.rawdata" || true
# 退避場・旧実験データ
mv_if "$P/_archive" "$T/論文DB__archive（役目を終えた退避場）"
mv_if "$P/8_reHP/2.5.tags/before_taxonomy_all" "$T/論文DB_8_reHP_2.5.tags_before_taxonomy_all（旧分類実験の中間データ）"
# 再生成できるもの（npm install / venv 作り直しで戻る）
mv_if "$D/31.AI事業/5.アプリ開発/FocusRoom/node_modules" "$T/FocusRoom_node_modules"
mv_if "$D/31.AI事業/5.アプリ開発/Cyber_Sake_Deck/cyber-brewer-mvp/node_modules" "$T/Cyber_Sake_Deck_node_modules"
mv_if "$P/8_reHP/6.hp/node_modules" "$T/論文DB_8_reHP_6.hp_node_modules"
mv_if "$P/.venv" "$T/論文DB_.venv"
mv_if "$P/JBSJ_P/.venv" "$T/論文DB_JBSJ_P_.venv"
echo "完了。仮置き（月末削除）/2026-09-04_重複整理 の中身:"; ls "$T"
