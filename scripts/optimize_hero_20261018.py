#!/usr/bin/env python3
"""Optimize only TOP visual images without changing composition, attribution or layout."""
from pathlib import Path
from PIL import Image
root=Path(__file__).resolve().parents[1]/"site"
base=root/"assets"
photo=base/"hero-architecture.jpg"
with Image.open(photo) as source:
    img=source.convert("RGB")
    for w in (800,1600):
        ratio=w/img.width
        new=img.resize((w,round(img.height*ratio)),Image.Resampling.LANCZOS)
        out=base/f"hero-architecture-{w}.webp"
        new.save(out,format="WEBP",quality=78,method=6)
        print("GENERATED",out.name,"dims",new.size,"bytes",out.stat().st_size)
index=root/"index.html"
text=index.read_text(encoding="utf8")
old='<img src="/assets/hero-architecture.jpg" alt="近代的な建築物を見上げた写真" fetchpriority="high">'
new='<img src="/assets/hero-architecture.jpg" srcset="/assets/hero-architecture-800.webp 800w, /assets/hero-architecture-1600.webp 1600w" sizes="(max-width: 720px) 100vw, 51vw" width="1648" height="1200" alt="近代的な建築物を見上げた写真" fetchpriority="high" decoding="async">'
if new not in text:
    assert text.count(old)==1,("hero markup changed",text.count(old))
    index.write_text(text.replace(old,new,1),encoding="utf8",newline="")
    print("UPDATED_TOP_MARKUP")
else:print("TOP_ALREADY_OPTIMIZED")
