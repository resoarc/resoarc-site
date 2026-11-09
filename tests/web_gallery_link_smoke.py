#!/usr/bin/env python3
"""Public WEB tools must show no more than one relevant screenshot link per card."""
from pathlib import Path
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = frozenset({
    "kintone-app-diff",
    "kintone-import-check",
    "kintone-bulk-preview",
    "kintone-permission-audit",
    "kintone-duplicates",
    "kintone-lookup-audit",
    "kintone-cross-aggregate",
    "kintone-print-report",
})

class Cards(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.cards = []
        self.in_card = False

    def handle_starttag(self, tag, attrs):
        props = dict(attrs)
        classes = set(props.get("class", "").split())
        if tag == "article" and "product-card" in classes:
            assert not self.in_card, "nested catalog card"
            self.cards.append({"tools": [], "screens": []})
            self.in_card = True
        if tag == "a" and self.in_card:
            href = props.get("href", "")
            if "product-cta" in classes:
                self.cards[-1]["tools"].append(href)
            if "tool-gallery-link" in classes:
                self.cards[-1]["screens"].append(href)

    def handle_endtag(self, tag):
        if tag == "article" and self.in_card:
            self.in_card = False

def main():
    index = ROOT / "site/products/web/index.html"
    parser = Cards()
    parser.feed(index.read_text(encoding="utf-8"))
    assert len(parser.cards) == 10, "Expected all 10 published WEB tools"
    n = 0
    for card in parser.cards:
        assert len(card["tools"]) == 1, card
        tool = card["tools"][0]
        assert tool.startswith("/tools/") and tool.endswith("/"), tool
        slug = tool.split("/")[-2]
        expected = [f"/products/web/screens/#{slug}"] if slug in EXPECTED else []
        assert card["screens"] == expected, (slug, card["screens"], expected)
        if expected:
            assert (ROOT / f"site/assets/tool-screens/{slug}.webp").is_file(), slug
            n += 1
    assert n == len(EXPECTED) == 8
    print("WEB_GALLERY_LINK_SMOKE_PASS: 10 cards, 8 unique mapped screenshot links")

if __name__ == "__main__":
    main()
