# sake-kb
- 思想は `../../template/owner_context.md`（コピー禁止）。共通規定は作業フォルダ直下の CLAUDE.md
- 聖域: 出典台帳 `sources.csv` にない資料は取り込まない。T3（二次資料）は不採用。引用なき記述は事実として扱わない
- 依存を増やさない（標準ライブラリ＋poppler）。ベクトル化は FTS5 の取りこぼし率を実測してから
- `data/*.sqlite` は生成物（git管理外）。再生成は `python3 scripts/extract_books.py`
