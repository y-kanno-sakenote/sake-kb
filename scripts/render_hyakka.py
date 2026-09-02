"""百科スキャン（見開き・90°回転）→ 正立 → 左右頁 PNG（長辺1600px）。使い方: <venv with Pillow>/bin/python scripts/render_hyakka.py <PDFフォルダ> <出力フォルダ>"""
import sys, os, glob, subprocess, re, time
from PIL import Image
B,O=sys.argv[1],sys.argv[2]; t0=time.time(); n=0
for pdf in sorted(glob.glob(B+"/*.pdf")):
    name=os.path.splitext(os.path.basename(pdf))[0]; d=os.path.join(O,name); os.makedirs(d,exist_ok=True)
    subprocess.run(["pdftocairo","-png","-r","110",pdf,os.path.join(d,"s")],check=True)
    for png in sorted(glob.glob(d+"/s-*.png")):
        k=int(re.search(r"s-(\d+)\.png",png).group(1)); im=Image.open(png).rotate(90,expand=True); w,h=im.size
        for side,(x0,x1) in (("L",(0,w//2)),("R",(w//2,w))):
            p=im.crop((x0,0,x1,h)); p.thumbnail((1600,1600)); p.save(os.path.join(d,f"{k:03d}{side}.png"))
        os.remove(png); n+=1
    print(name, "done", flush=True)
print(f"spreads={n} pages={len(glob.glob(O+'/*/*.png'))} {time.time()-t0:.0f}s")
