#!/usr/bin/env python3
"""全国市販酒類調査 平成29年度（nta-shihanshu-h29）の -layout テキストから、清酒の県別平均表（参考資料①〜④）を JSON にする。
出力: data/exports/seishu_pref_h29.json  {種類: {県: {n,alc,smv,ext,acid,amino,amakara,notan}, '全国': {...}}}
甘辛度は報告書の注記どおり「大きいほど甘口」、濃淡度は「大きいほど濃醇」。"""
import re, json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent)); import kbdb
SRC = pathlib.Path(kbdb.DRIVE) / '読み物/日本酒資料/国税庁_最新/全国市販酒類調査_平成29年度/text/全国市販酒類調査_平成29年度.txt'
PREFS = ['北海道','青森','岩手','宮城','秋田','山形','福島','茨城','栃木','群馬','埼玉','千葉','東京','神奈川','新潟','富山','石川','福井','山梨','長野','岐阜','静岡','愛知','三重','滋賀','京都','大阪','兵庫','奈良','和歌山','鳥取','島根','岡山','広島','山口','徳島','香川','愛媛','高知','福岡','佐賀','長崎','熊本','大分','宮崎','鹿児島','沖縄']
ROW = re.compile(r'\s*(\S+?)\s+(\d+)\s+([\d.]+)\s+(-?[\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s*$')
L = SRC.read_text(encoding='utf-8').split('\n')
out = {}
for kind in ['一般酒', '吟醸酒', '純米酒', '本醸造酒']:
    starts = [k for k, l in enumerate(L) if f'{kind}の成分分析等結果（平均値・県別）' in l]
    tbl = {}
    for i in starts:
        for l in L[i + 1:]:
            if '成分分析等結果（平均値・県別）' in l and l is not L[i]: break
            m = ROW.match(l)
            if not m: continue
            name = m.group(1); p = '東京' if name == '東京都' else re.sub(r'[県府]$', '', name)
            if p in PREFS or name == '全国':
                key = '全国' if name == '全国' else p
                tbl[key] = dict(n=int(m.group(2)), alc=float(m.group(3)), smv=float(m.group(4)), ext=float(m.group(5)), acid=float(m.group(6)), amino=float(m.group(7)), amakara=float(m.group(8)), notan=float(m.group(9)))
        if len(tbl) > 30: break
    out[kind] = tbl
    print(kind, len([k for k in tbl if k != '全国']), '県', '全国=', tbl.get('全国'), file=sys.stderr)
dst = pathlib.Path(__file__).parent.parent / 'data/exports/seishu_pref_h29.json'
json.dump(out, open(dst, 'w'), ensure_ascii=False, indent=0); print(dst)
