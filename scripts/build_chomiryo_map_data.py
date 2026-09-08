import re,pathlib,json,collections,sys
PREFS=['北海道','青森','岩手','宮城','秋田','山形','福島','茨城','栃木','群馬','埼玉','千葉','東京','神奈川','新潟','富山','石川','福井','山梨','長野','岐阜','静岡','愛知','三重','滋賀','京都','大阪','兵庫','奈良','和歌山','鳥取','島根','岡山','広島','山口','徳島','香川','愛媛','高知','福岡','佐賀','長崎','熊本','大分','宮崎','鹿児島','沖縄']
def short(p): return '東京' if p.startswith('東京') else re.sub(r'[県府]$','',p)
def num(x):
    try: return float(x.replace(',',''))
    except: return 0.0
data={p:{} for p in PREFS}
for l in pathlib.Path('data/exports/shoyu_pref_type_2024.md').read_text().split('\n'):
    c=[x.strip() for x in l.strip('|').split('|')]
    if len(c)==9 and c[0] in PREFS:
        sh=[num(x) for x in c[2:7]]
        data[c[0]]['shoyu']={'total':int(num(c[1])),'koi':sh[0],'usu':sh[1],'tamari':sh[2],'sai':sh[3],'shiro':sh[4]}
rows=[]
for l in pathlib.Path('docs/chomiryo_jbsj_extract.md').read_text().split('\n'):
    c=[x.strip() for x in l.strip('|').split('|')]
    if len(c)>=7 and re.fullmatch(r'Q\d+',c[1]): rows.append(dict(pref=c[0],q=c[1],fact=c[2],quote=c[3],src=c[4],note=c[5],verdict=c[6]))
for r in rows:
    if r['q']=='Q6' and short(r['pref']) in data and r['verdict']!='根拠なし':
        f=r['fact']
        # qa 2026-09-08: 調合を先に判定（山梨=米麦調合）。複数原料の併記（／）や「一意に定まらない」注記は断定しない
        if f.startswith(('米麦','調合')): base='調合'   # 先頭が調合のときだけ（「麦味噌（＋調合味噌…）」は麦）
        elif '／' in f or '一意' in r['note']: base='—'
        else: base='米' if f.startswith('米') else '麦' if f.startswith(('麦','大麦')) else '豆' if f.startswith('豆') else '—'
        data[short(r['pref'])]['miso']={'base':base,'fact':f,'quote':r['quote'].strip('「」')[:90],'src':r['src'].replace('論文「','').rstrip('」'),'verdict':r['verdict']}
cnt=collections.defaultdict(collections.Counter); ex={}
for l in open('data/exports/chomiryo_by_pref.jsonl'):
    d=json.loads(l); p=short(d['prefecture'])
    for t in d['tags']:
        if t.startswith('味噌:') and t.split(':')[1] in('米味噌','麦味噌','豆味噌'):
            b=t.split(':')[1][0]; cnt[p][b]+=1; ex.setdefault((p,b),(d['name'],d['fact'][:70],d['source'],d['printed_page']))
for p in PREFS:
    if 'miso' not in data[p]:
        # 百科は「主体/主流/中心/多い」を含む記述だけ根拠にする（店が扱う銘柄などの言及は主流の根拠にしない）
        cands=[(b,ex[(p,b)]) for b,_ in cnt[p].most_common() if re.search('主体|主流|中心|多い|多く',ex[(p,b)][1])]
        if cands:
            b,e=cands[0]
            data[p]['miso']={'base':b,'fact':f'百科の記述（{e[0]}）','quote':e[1],'src':f'{e[2]} p.{e[3]}','verdict':'百科'}
        else: data[p]['miso']={'base':'—','fact':'台帳内に県単位の記述なし','quote':'','src':'','verdict':'根拠なし'}
# qa 2026-09-08: 原文に県名が無い地方（四国太平洋側・北陸〜山口の日本海側）は県に展開しない。地方名は行政区分が確定しているものだけ
REG={'九州全域':['福岡','佐賀','長崎','熊本','大分','宮崎','鹿児島'],'中国地方':['鳥取','島根','岡山','広島','山口'],'東北':['青森','岩手','宮城','秋田','山形','福島']}
ama={p:[] for p in PREFS}
for r in rows:
    if r['q']!='Q2' or '聞かない' in r['fact'] or '甘塩' in r['fact']: continue   # 甘塩=食塩分の話で甘口とは別軸
    key=r['pref'].strip('（）'); targets=[]
    for k,v in REG.items():
        if k in key: targets+=v
    targets+=[short(x) for x in re.split('[・,、]',key) if short(x) in PREFS]
    for p in set(targets): ama[p].append({'fact':r['fact'][:40],'quote':r['quote'].strip('「」')[:90],'src':r['src'].replace('論文「','').rstrip('」'),'verdict':r['verdict'],'scope':key})
for p in PREFS:
    lv=max([2 if a['verdict']=='裏取れた' else 1 for a in ama[p]],default=0)
    data[p]['amakuchi']={'level':lv,'refs':ama[p]}

# 清酒の甘辛（全国市販酒類調査 平成29年度・一般酒・県別トリム平均）
try:
    sj=json.load(open('data/exports/seishu_pref_h29.json'))['一般酒']
    for p in PREFS: data[p]['seishu']=sj.get(p)
    data['_seishu_zenkoku']=sj.get('全国')
except FileNotFoundError: pass
json.dump(data,open(sys.argv[1],'w'),ensure_ascii=False)
P=[data[p] for p in PREFS]
print('miso base:',collections.Counter(d['miso']['base'] for d in P))
print('miso verdict:',collections.Counter(d['miso']['verdict'] for d in P))
print('amakuchi level:',collections.Counter(d['amakuchi']['level'] for d in P))
print('seishu:',sum(1 for d in P if d.get('seishu')),'県')
print('shoyu missing:',[p for p in PREFS if 'shoyu' not in data[p]])
print({p:data[p]['miso']['base'] for p in ['福井','大阪','愛知','大分','長野','島根','香川']})
print('usu>=20:',[p for p in PREFS if data[p]['shoyu']['usu']>=20],'tamari>=5:',[p for p in PREFS if data[p]['shoyu']['tamari']>=5],'shiro>=1:',[p for p in PREFS if data[p]['shoyu']['shiro']>=1])
