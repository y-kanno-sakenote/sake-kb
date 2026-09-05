# sake-kb — 日本酒・醸造 知識ベース（単一知識層）

各プロジェクトが日本酒・醸造の「事実」を取り込むときの唯一の参照口。
**引用（出典＋頁）が付かない記述は事実として扱わない**。

## 構成
- `sources.csv` … 出典台帳（人が管理）。信頼階層 T1=公的機関・学会・教科書 / T2=業界団体・実査済み蔵元HP / T3=二次資料（不採用）
- `scripts/kbdb.py` … スキーマ（sources / docs / pages / chunks / chunks_fts）。ソース単位で差し替え可能
- `scripts/extract_books.py` … Drive の自炊本PDF → 正規化 → SQLite（type=教科書/試験問題 の行だけ）
- `scripts/export_jbsj_corpus.py` … jbsj の corpus.parquet＋書誌 → `data/jbsj_corpus.jsonl`（**../jbsj/.venv で実行**。parquet読みにpyarrowが要るため）
- `scripts/ingest_hyakka.py` … `data/hyakka/*.jsonl`（Claude Sonnet のビジョンで抽出した頁つき事実。git外・非公開）→ source_id=hyakka-hakko
- `scripts/ingest_papers.py` … 論文を **元PDFから頁単位で** 抽出して source_id=jbsj で投入（書誌と退避用本文は上の JSONL）。印刷頁＝開始ページ＋pdf_page−1。PDF頁数と書誌の頁範囲が一致した論文だけ印刷頁を確定（docs.page_ok=1）、それ以外は corpus 本文を頁なし（pdf_page=0）で投入
- `scripts/kb.py` … 検索CLI。`python3 scripts/kb.py "酒母 温度" -k 5` で出典＋頁つきに返す
- `data/manifest_books.json`, `data/jbsj_corpus.jsonl.manifest.json` … 取り込み元の md5・件数（機械が書く）

依存: Python 標準ライブラリのみ ＋ poppler（`pdftotext`, `pdfinfo`）。

## 頁番号について
本: `pdf_page` は PDF 内の通し頁（1始まり）で印刷頁とは一致しない。引用は「source_id / part / pdf_page」。
論文: 引用は「誌名 巻(号) 年 pp.範囲 p.印刷頁 著者「題名」」。page_ok=0 の論文は頁なし。

## 現在の範囲
| source_id | 内容 | 単位 | チャンク |
|---|---|---|---|
| akahon / aohon / nihonshu-no-moto / kanno-hyokashi / ginou-kentei | 自炊本5冊 | PDF頁 | 約2,000 |
| jbsj | 日本醸造協会誌 本文 4,278本（1988〜） | PDF頁（印刷頁つき引用、4,268本で確定） | 約68,400 |
| nta-* | 国税庁資料6件（調査研究2005・アクションプラン2000・経営改善2004・こうじ菌2021・概況R7・酒のしおりR8 Excel数表） | PDF頁／Excelシート | 約1,250 |
| nta-hyoji-kijun | 清酒の製法品質表示基準（平成元年国税庁告示第8号・最終改正 令和4年告示第30号）の告示本文＋国税庁「概要」 | HTML本文1頁×2 | 14 |
| shuzeiho / shuzeiho-sekourei | 酒税法 第1〜3条（清酒の定義・アルコール分22度未満ほか）／酒税法施行令 第2条（清酒の原料）。e-Gov法令検索 | 条文テキスト1頁ずつ | 9 |
| hyakka-hakko | 47都道府県・発酵文化百科（2021・丸善出版）の**頁つき構造化事実**4,987件（逐語ではない） | 書籍頁 | 約460 |
| hyakka-dentoshoku | 47都道府県・伝統食百科（2009・丸善）の頁つき構造化事実 6,173件 | 書籍頁 | 約570 |
| nrib-jitsu-moromi | 酒類総合研究所 実もろみDB 42件（引用専用・FTS未取り込み。実体は dev/nihonshu-intro/data/nrib_moromi_42_full.json） |
| hyakka-chomiryo | 47都道府県・伝統調味料百科（丸善出版 2013）の頁つき構造化事実 4,154件 | 書籍頁 | 約400 |
| nrib-kouen44-koji / nrib-kouen46-sulfate | 酒類総合研究所 講演会要旨2本（第44回2008「麹の品質は予測できるか」小林健／第46回2010「硫酸塩添加仕込によるアミノ酸の少ない酒造り」日下一尊） | PDF頁（各2頁） | 12 |
| nrib-patent-2010-98996 | 公開特許公報 特開2010-98996「麹の製造方法」（出願人 酒類総合研究所・発明者 小林健・2010公開） | PDF頁（10頁） | 23 |
| nrib-db-kaisetsu | 清酒製造支援データベースの解説文9ページ（硫酸塩添加仕込の仕込例／清酒発酵の制御ルール＋品温・グルコース・アミノ酸／麹菌の呼吸活性・ATP・エネルギーチャージ／製麹条件と麹の品質） | HTML本文を1ファイルに結合（1頁扱い） | 7 |

再生成: `../jbsj/.venv/bin/python scripts/export_jbsj_corpus.py && python3 scripts/extract_books.py && python3 scripts/ingest_papers.py`（export 約10秒・本 約2秒・論文は元PDF 4,278本を8並列で約13分、DB約720MB）。旧誌（日本釀造協會雜誌 2,162本）は**取り込み停止中**（2026-09-04 オーナー判断：Drive 側の整理が先。可読性・出典付与は docs/backlog_2026-09-03.md で確認済み、パイロット data/pilot_kyushi.sqlite）。他誌論文は所在未確認。

## 既知の癖（実測済み）
- 自炊本5冊のみ OCRの固定誤字を補正: 疏→酛、膠→醪（本5冊には誤読以外の用例なし）。論文は正字を持ち疏水・膠原線維などがあるので補正しない。他の誤字は未補正
- 『日本酒の基』と醸造協会誌の論文は2段組のため `pdftotext -raw`（default だと左右の行が混ざり空行だらけになる）。他4冊は default
- FTS5 trigram は2文字語を引けないので kb.py は2文字以下を LIKE で補う
- 柱（章題ヘッダ）や数表のOCR断片チャンクが約3%混在。引用時は `--full` で前後を確認する
- 論文の書誌欠け2件（100_112、84_183 (1)）は「書誌未登録」と表示。84_183 (1) は 84_183 の重複ダウンロード（上流 jbsj 側の問題）
- 百科3種はスキャンが90°回転しているので正立させてから左右頁に分割（scratchpad の render_hyakka.py 相当）。逐語転記は著作権上しない。事実は Sonnet で抽出（Haiku は数値・県名の誤りが多く不採用）
- 表示基準・法令の .txt は全角スペースが正規化で消える（例「七　清酒　次に掲げる…」→「七清酒次に掲げる…」）。検索・引用には支障ないが、逐語で写すときは Drive の `表示基準_酒税法/原本/`（取得元HTML・e-Gov JSON）を見る
- 酒のしおりの PDF（令和3〜8年版）は埋め込みフォントの ToUnicode 欠落で全頁文字化け。数表は Excel から取る

- NRIB 清酒製造支援DB（2026-09-05取得）: サイトは初回GETでセッションcookieを発行するので `curl -c/-b -L`（cookie無しのurllib・WebFetchは302ループ）。PDF3本はいずれもテキスト抽出可（画像PDFではない）だが、特許公報の1頁目の書誌欄（出願人・発明者・出願番号）だけは画像なので本文には入らない（台帳noteに転記済み）。講演会要旨2本は本文中に図が入るためグラフの軸ラベル断片（「製成酒のアミノ酸度」など）が数チャンク混じる。解説文.txt は .txt 扱いで全チャンクに1行目「NRIB 清酒製造支援データベース 解説文（2026-09-05取得）」が前置される（表示基準・法令と同じ癖）。図の画像と `/koji/seikiku/data_select` の計算ツール（表・フォーム）は取り込み対象外

- 既知の癖（2026-09-05 検証係）: `.txt` 入力は数表用に「頁1行目を全チャンクに前置」するため、告示本文・概要は全チャンクが「清酒」「表示基準」で当たる（ソース内ノイズ。`--source` なしの検索では bm25 で薄まる）。

- 異体字（2026-09-05）: DB は原文どおりで「麴」（旧字）が jbsj 538・国税庁こうじ菌資料26・NRIB 46回要旨1チャンクにある。`kb.py` が検索語の 麹↔麴 を自動展開して両方を引く（逐語引用は原文の字を使う）。

## 裏取りを係に頼むとき
`docs/verification_prompt.md` の5条（原文引用・逆接保持・矛盾の定義・機械集計・出典形式）を委任文に貼る。流れは 検証表 → qa係の抜き取り → 本体訂正 → 反映はオーナー判断。前例: `dev/kamoshite_pon/docs/prefecture_verification.md`、`dev/seishu-musou/docs/sim_constants_verification.md`。
