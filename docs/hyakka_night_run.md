# 百科の夜間抽出 手順書（スケジュールタスクが読む）

前提: `data/hyakka_img/<book>/` に正立済み頁画像がある（`scripts/render_hyakka.py` で生成済み）。book は dentoshoku（伝統食百科・成瀬宇平 著）／chomiryo（伝統調味料百科・成瀬宇平 著）。

1. `python3 scripts/hyakka_batches.py --book <book>` でバッチ計画を得る（done=true は飛ばす）
2. `docs/hyakka_extract_prompt.md` の雛形を各バッチで埋め、Sonnet サブエージェントを **同時8本まで** 背景起動。完了通知を待って次を投入（1バッチ 約9万トークン・3〜6分）
3. 全バッチ完了後: JSONL を検証（全行 JSON、見開き番号の欠けなし）。欠けたバッチだけ再実行
4. `python3 scripts/ingest_hyakka.py --book <book>` で SQLite に投入。`python3 scripts/kb.py "<その本に出てきそうな語>" --source hyakka-<book>` で1件引けることを確認
5. 奥付（type=書誌）から発行年月日・版・ISBN を読み、`sources.csv` の該当行の year/edition と備考を埋める（推測で埋めない。無ければ「要確認」のまま）
6. 検証係（subagent_type=qa）に無作為3頁の画像突合を依頼（誤り率・脱落・頁番号一致、20行以内）
7. `git add -A && git commit -m "<book> 百科の頁つき事実を取り込み"`（data/ は git 外なので scripts/sources.csv/README の差分だけ）
8. 事実 JSONL を Drive `31.AI事業/5.アプリ開発/sake-kb_data/<book>_facts_<日付>/` に退避
9. Vault `📤受け渡し/<当日>.md` の「## 💡 今日やったこと」に1行（件数・誤り率・所要トークン）

やらないこと: 逐語書き起こし／Haiku での抽出／本文のゲーム・HPへの転載。
