import unittest
from pathlib import Path
from html.parser import HTMLParser
ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.urls=[]
    def handle_starttag(self, tag, attrs):
        for key,value in attrs:
            if key in ("href","src") and value:self.urls.append(value)
class CommunitySiteTest(unittest.TestCase):
    def test_pages_and_navigation(self):
        for page in ("community/index.html","en/index.html"):
            text=(SITE/page).read_text(encoding="utf-8")
            self.assertIn('href="/os/"',text)
            self.assertIn('<main id="main">',text)
            self.assertNotIn("????",text)
            parser=Links();parser.feed(text)
            for ref in parser.urls:
                if ref.startswith("/") and not ref.startswith("//"):
                    target=SITE/ref.lstrip("/")
                    if ref.endswith("/") or target.is_dir(): target=target/"index.html"
                    self.assertTrue(target.is_file(),ref)
        self.assertIn('lang="en"',(SITE/"en/index.html").read_text(encoding="utf-8"))
        self.assertIn("参加・活動",(SITE/"community/index.html").read_text(encoding="utf-8"))
    def test_community_discoverable(self):
        for name in ("index.html","project/index.html"):
            self.assertIn('href="/community/"',(SITE/name).read_text(encoding="utf-8"))
        sitemap=(SITE/"sitemap.xml").read_text(encoding="utf-8")
        self.assertIn("https://resoarc.com/community/",sitemap)
        self.assertIn("https://resoarc.com/en/",sitemap)
    def test_privacy_notice(self):
        p=(SITE/"privacy/index.html").read_text(encoding="utf-8")
        self.assertIn("任意の集計機能",p)
        self.assertIn("Cookie",p)
if __name__=="__main__":unittest.main()
