#!/usr/bin/env python3
"""百科jsonl（伝統調味料百科・伝統食百科）から調味料の県別事実を機械抽出する。
LLMを通さない。出力: data/exports/chomiryo_by_pref.jsonl, chomiryo_counts.md
問いの定義は docs/chomiryo_questions.md。"""
import json, glob, re, collections, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = {'hyakka-chomiryo': 'data/hyakka_chomiryo', 'hyakka-dentoshoku': 'data/hyakka_dentoshoku', 'hyakka-hakko': 'data/hyakka'}
PREFS = ['北海道','青森県','岩手県','宮城県','秋田県','山形県','福島県','茨城県','栃木県','群馬県','埼玉県','千葉県','東京都','神奈川県','新潟県','富山県','石川県','福井県','山梨県','長野県','岐阜県','静岡県','愛知県','三重県','滋賀県','京都府','大阪府','兵庫県','奈良県','和歌山県','鳥取県','島根県','岡山県','広島県','山口県','徳島県','香川県','愛媛県','高知県','福岡県','佐賀県','長崎県','熊本県','大分県','宮崎県','鹿児島県','沖縄県']
BARE = {p.rstrip('県府都'): p for p in PREFS}; BARE['北海道'] = '北海道'
ISLANDS = {'伊豆大島':'東京都','父島':'東京都','青ヶ島':'東京都','五島列島(中通島)':'長崎県','対馬':'長崎県','天草':'熊本県','天附島(牛深)':'熊本県','通貝島':'熊本県',
 '上蒲刈島':'広島県','仙酔島':'広島県','下甑島':'鹿児島県','宝島':'鹿児島県','小宝島':'鹿児島県','奄美大島':'鹿児島県','加計呂麻島':'鹿児島県','徳之島':'鹿児島県','与論島':'鹿児島県',
 '沖縄本島':'沖縄県','与那国島':'沖縄県','石垣島':'沖縄県','粟国島':'沖縄県','久米島':'沖縄県','宮古島':'沖縄県'}
SEASONING = {'醤油': r'醤油|しょうゆ|しょう油|正油', '味噌': r'味噌|みそ|ミソ', '酢': r'(?<![調])酢', 'みりん': r'みりん|味醂', '塩': r'(?<![醤味])塩(?!辛)', '魚醤': r'魚醤|しょっつる|いしる|いしり|いかなご醤油'}
TAGS = {'醤油': {'濃口': r'濃口|こいくち', '淡口': r'淡口|薄口|うすくち', 'たまり': r'たまり|溜', '白醤油': r'白醤油|白しょうゆ', '再仕込': r'再仕込', '甘口': r'甘口|甘い|甘み|甘味', '減塩': r'減塩|薄塩'},
        '味噌': {'米味噌': r'米味噌|米みそ|米麹|米こうじ', '麦味噌': r'麦味噌|麦みそ|麦麹|麦こうじ', '豆味噌': r'(?<!納)豆味噌|(?<!納)豆みそ|八丁|豆麹', '赤': r'赤味噌|赤みそ|赤色', '白': r'白味噌|白みそ|西京', '甘口': r'甘口|甘い|甘み|甘味', '辛口': r'辛口|辛み'}}

def norm_pref(p):
    if not p: return None
    p = p.strip().replace('(', '（').replace(')', '）')
    if p in PREFS: return p
    if p in BARE: return BARE[p]
    return ISLANDS.get(p.replace('（','(').replace('）',')'))

rows, counts, tagc, dropped = [], collections.Counter(), collections.Counter(), collections.Counter()
for sid, d in SRC.items():
    for f in sorted(glob.glob(str(ROOT / d / '*.jsonl'))):
        for l in open(f):
            try: r = json.loads(l)
            except json.JSONDecodeError: continue
            if r.get('confidence') != 'high' or r.get('type') == '書誌': dropped['low/書誌'] += 1; continue
            pref = norm_pref(r.get('prefecture'))
            if not pref: dropped['県なし'] += 1; continue
            text = f"{r.get('name','')} {r.get('fact','')}"
            seas = [s for s, rx in SEASONING.items() if re.search(rx, text)]
            if not seas: continue
            # 他県名混入の除外（qa 2026-09-08 の指摘を反映）: 「東京都」は「京都」に当たるので先に潰す。
            # 自県名が本文にあれば併記（例「長崎・大分の麦味噌」）として採用し、他県名だけの行を落とす。
            t2 = text.replace('東京都', '東京')
            bare = lambda q: q if q == '北海道' else q[:-1]
            if bare(pref) not in t2:
                # 固有名詞・時代語の一部（福岡醤油店・宮崎本店・奈良時代 等）は他県名扱いしない（qa 2回目の指摘）
                others = [q for q in PREFS if q != pref and re.search(re.escape(bare(q)) + r'(?!本店|醤油店|商店|屋|時代|漬)', t2)]
                if others: dropped['他県名混入'] += 1; continue
            tags = sorted({f'{s}:{t}' for s in seas if s in TAGS for t, rx in TAGS[s].items() if re.search(rx, text)})
            rows.append({'source': sid, 'printed_page': r['printed_page'], 'prefecture': pref, 'type': r['type'], 'name': r['name'], 'fact': r['fact'], 'seasoning': seas, 'tags': tags})
            for s in seas: counts[(pref, s)] += 1
            for t in tags: tagc[(pref, t)] += 1

out = ROOT / 'data/exports'; out.mkdir(exist_ok=True)
with open(out / 'chomiryo_by_pref.jsonl', 'w') as w:
    for r in rows: w.write(json.dumps(r, ensure_ascii=False) + '\n')
S = list(SEASONING)
md = ['# 調味料 県別件数（百科2冊・high のみ・機械抽出）', '', f'元: {sum(len(list(open(f))) for d in SRC.values() for f in glob.glob(str(ROOT/d/"*.jsonl")))}件 → 採用 {len(rows)}件（除外: {dict(dropped)}）', '',
      '| 県 | ' + ' | '.join(S) + ' | 醤油タグ | 味噌タグ |', '|' + '---|' * (len(S) + 3)]
for p in PREFS:
    st = lambda s: ', '.join(f'{t.split(":")[1]}{n}' for (pp, t), n in sorted(tagc.items(), key=lambda x: -x[1]) if pp == p and t.startswith(s + ':')) or '—'
    md.append(f'| {p} | ' + ' | '.join(str(counts[(p, s)] or '—') for s in S) + f' | {st("醤油")} | {st("味噌")} |')
md.append('| **計** | ' + ' | '.join(str(sum(n for (pp, s), n in counts.items() if s == ss)) for ss in S) + ' | | |')
(out / 'chomiryo_counts.md').write_text('\n'.join(md) + '\n')
print(f'rows={len(rows)} dropped={dict(dropped)} -> {out}')
