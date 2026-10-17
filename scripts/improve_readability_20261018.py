#!/usr/bin/env python3
"""Improve genuine text readability and accessibility semantics across ResoArc.
Do not relax CSP to game Lighthouse's blocked Cloudflare analytics finding.
"""
from pathlib import Path
root=Path(__file__).resolve().parents[1]/"site"
old='aria-label="ResoArc トップページ"'
new='aria-label="ResoArc OPEN TECHNOLOGY PROJECT トップページ"'
changed=[]
for f in sorted(root.rglob("*.html")):
    s=f.read_text(encoding="utf8")
    if old in s:
        f.write_text(s.replace(old,new),encoding="utf8",newline="")
        changed.append(f.relative_to(root).as_posix())
print("BRAND_ACCESSIBLE_LABELS",len(changed),changed[:10])
css=root/"assets/recognition-20261017.css"
text=css.read_text(encoding="utf8")
marker="/* ResoArc verified readability improvements, 2026-10-18 */"
style=r"""
/* ResoArc verified readability improvements, 2026-10-18 */
/* Contrast targets: 4.5:1 minimum for informative small text. */
.hero-footnote {color:#4c6378;}
.rec-hub-framed .rec-hub-card-eyebrow {color:#496177;}
.rec-hub-framed .rec-dense-card .rec-hub-grade small,
.rec-hub-framed .rec-dense-card .rec-hub-live small {color:#4b6377;}
.rec-hub-framed .rec-hub-state-pending {color:#455d70;}
.quick-intro small {color:#425e53;}
.quick-nav a small {color:#4d6379;}
.kicker-jp {color:#4c647a;}
.list-note > span {color:#4b6376;}
.updates-items .no-more a {color:#4c6379;}
@media (max-width: 720px) {
  /* Avoid illegible 9-11px labels, especially in card descriptions. */
  .rec-hub-framed .rec-dense-card > p {font-size:13px; line-height:1.65;}
  .rec-hub-framed .rec-hub-note {font-size:12.5px;line-height:1.75;}
  .rec-hub-framed .rec-dense-card .rec-hub-card-eyebrow {font-size:11.5px;letter-spacing:.04em;}
  .rec-hub-framed .rec-dense-card .rec-hub-grade small,
  .rec-hub-framed .rec-dense-card .rec-hub-live small,
  .rec-hub-framed .rec-hub-state {font-size:11.5px;}
  .list-note > span {font-size:12.5px;}
  .footer-bottom {font-size:12px;}
  .hero-topline {font-size:11.5px;}
  .kicker-jp {font-size:12px;}
  .rec-eyebrow {font-size:12px;}
  .quick-intro small,.quick-nav a small {font-size:12px;}
}
"""
if marker not in text:
    css.write_text(text.rstrip()+"\n"+style,encoding="utf8",newline="")
    print("CSS_IMPROVED")
else: print("CSS_EXISTS")
