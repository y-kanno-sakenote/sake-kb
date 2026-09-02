# sake-kb — 日本酒・醸造 知識ベース（単一知識層）

各プロジェクトが日本酒・醸造の「事実」を取り込むときの唯一の参照口。
**引用（出典＋頁）が付かない記述は事実として扱わない**。

## 構成
- `sources.csv` … 出典台帳（人が管理）。信頼階層 T1=公的機関・学会・教科書 / T2=業界団体・実査済み蔵元HP / T3=二次資料（不採用）
- `scripts/kbdb.py` … スキーマ（sources / docs / pages / chunks / chunks_fts）。ソース単位で差し替え可能
- `scripts/extract_books.py` … Drive の自炊本PDF → 正規化 → SQLite（type=教科書/試験問題 の行だけ）
- `scripts/export_jbsj_corpus.py` … jbsj の corpus.parquet＋書誌 → `data/jbsj_corpus.jsonl`（**../jbsj/.venv で実行**。parquet読みにpyarrowが要るため）
- `scripts/ingest_papers.py` … その JSONL → SQLite に source_id=jbsj で投入（論文単位。pdf_page=0）
- `scripts/kb.py` … 検索CLI。`python3 scripts/kb.py "酒母 温度" -k 5` で出典＋頁つきに返す
- `data/manifest_books.json`, `data/jbsj_corpus.jsonl.manifest.json` … 取り込み元の md5・件数（機械が書く）

依存: Python 標準ライブラリのみ ＋ poppler（`pdftotext`, `pdfinfo`）。

## 頁番号について
`pdf_page` は PDF 内の通し頁（1始まり）で、本の印刷頁番号とは一致しない。引用は「source_id / part / pdf_page」で行う。

## 現在の範囲
| source_id | 内容 | 単位 | チャンク |
|---|---|---|---|
| akahon / aohon / nihonshu-no-moto / kanno-hyokashi / ginou-kentei | 自炊本5冊 | PDF頁 | 約2,000 |
| jbsj | 日本醸造協会誌 本文 4,278本（1988〜） | 論文（頁区切りなし） | 約59,800 |

再生成: `../jbsj/.venv/bin/python scripts/export_jbsj_corpus.py && python3 scripts/extract_books.py && python3 scripts/ingest_papers.py`（合計30秒弱、DB約440MB）。旧誌（日本釀造協會雜誌 2,162本）・他誌論文は次段。

## 既知の癖（実測済み）
- OCRの固定誤字を正規化で補正: 疏→酛、膠→醪（コーパス内に誤読以外の用例なし）。他の誤字は未補正
- 『日本酒の基』は2段組のため `extract_mode=raw`（他4冊は default。sources.csv で指定）
- FTS5 trigram は2文字語を引けないので kb.py は2文字以下を LIKE で補う
- 柱（章題ヘッダ）や数表のOCR断片チャンクが約3%混在。引用時は `--full` で前後を確認する
