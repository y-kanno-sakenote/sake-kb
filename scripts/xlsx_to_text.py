#!/usr/bin/env python3
"""xlsx を標準ライブラリだけでシート別 .txt に書き出す（sake-kb 取り込み用）。
ふりがな（rPh）は捨てる。1行目に「シート表題（書誌・ファイル名・シート名）」を付ける（酒のしおり Excel の前例に合わせる）。
使い方: xlsx_to_text.py <xlsx> <出力dir> "<書誌ラベル>" """
import sys, zipfile, re, pathlib, xml.etree.ElementTree as ET
M = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'

def shared_strings(z):
    if 'xl/sharedStrings.xml' not in z.namelist(): return []
    out = []
    for si in ET.fromstring(z.read('xl/sharedStrings.xml')):
        parts = []
        for el in si:
            if el.tag == M + 't': parts.append(el.text or '')
            elif el.tag == M + 'r':
                t = el.find(M + 't'); parts.append(t.text or '' if t is not None else '')
            # rPh（ふりがな）は無視
        out.append(''.join(parts))
    return out

def fmt(v):
    try:
        f = float(v)
        return str(int(f)) if f.is_integer() else f'{f:.1f}'
    except ValueError: return v

def main(xlsx, outdir, label):
    z = zipfile.ZipFile(xlsx); ss = shared_strings(z)
    wb = ET.fromstring(z.read('xl/workbook.xml'))
    rels = {r.get('Id'): r.get('Target') for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
    outdir = pathlib.Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    for n, s in enumerate(wb.find(M + 'sheets'), start=1):
        name = s.get('name'); tgt = rels[s.get(R + 'id')]
        p = tgt if tgt.startswith('xl/') else 'xl/' + tgt.lstrip('/')
        root = ET.fromstring(z.read(p)); lines = []
        for row in root.find(M + 'sheetData'):
            cells = []
            for c in row:
                v = c.find(M + 'v')
                if v is None or v.text is None: continue
                val = ss[int(v.text)] if c.get('t') == 's' else fmt(v.text)
                val = re.sub(r'\s+', ' ', val).strip()
                if val: cells.append(val)
            if cells: lines.append(' | '.join(cells))
        if len(lines) < 2: continue
        title = lines[0]
        body = [f'{title}（{label}・{pathlib.Path(xlsx).name}・シート「{name}」）'] + lines[1:]
        fn = outdir / f'{n:02d}_{re.sub(r"[/\\\\:*?\"<>|（）()〔〕 ]", "_", name)[:40]}.txt'
        fn.write_text('\n'.join(body) + '\n', encoding='utf-8')
        print(fn.name, len(lines), 'rows')

if __name__ == '__main__':
    main(*sys.argv[1:4])
