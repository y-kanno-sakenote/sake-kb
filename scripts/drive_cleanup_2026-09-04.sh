#!/bin/zsh
# Drive 重複整理（2026-09-04 オーナー承認）。削除はせず「仮置き（月末削除）」へ移動するだけ。何度実行しても安全（存在するものだけ動かす）
set -u
D="$HOME/Library/CloudStorage/GoogleDrive-y.kanno@sakenote.net/マイドライブ/サケノテ"
P="$D/31.AI事業/5.アプリ開発/論文DB"
T="$D/仮置き（月末削除）/2026-09-04_重複整理"
mkdir -p "$T"
mv_if(){ if [ -e "$1" ]; then mv "$1" "$2" && echo "移動: ${1#$D/} → ${2#$D/}"; else echo "無し（済）: ${1#$D/}"; fi; }
# 目次PDF（重複フォルダにだけあった1本）は論文DB直下へ救出
mv_if "$D/32.研究事業/日本醸造協会誌/論文リスト - リスト.pdf" "$P/論文リスト（PDF版）.pdf"
# 0_pdfs と同一（4,278本・MD5一致）の重複2箇所
mv_if "$P/8_reHP/1.corpus/1.rawdata/日本醸造協会誌" "$T/論文DB_8_reHP_1.corpus_1.rawdata_日本醸造協会誌（0_pdfsと同一の重複）"
mv_if "$D/32.研究事業/日本醸造協会誌" "$T/32.研究事業_日本醸造協会誌（0_pdfsと同一の重複）"
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
