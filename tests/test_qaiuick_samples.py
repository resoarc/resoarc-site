# SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
# SPDX-License-Identifier: MIT
"""Static and behavioral quality gates for qAIUIck live examples."""
from __future__ import annotations

import html.parser
import pathlib
import re
import shutil
import subprocess
import unittest
from urllib.parse import urlsplit

ROOT = pathlib.Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
SLUGS = ("demo", "inventory", "budget", "tickets", "customers")
SOURCE_JS = {
    "demo": "demo.js",
    "inventory": "examples/inventory.js",
    "budget": "examples/budget.js",
    "tickets": "examples/tickets.js",
    "customers": "examples/customers.js",
}


class Parser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.sources = []
        self.anchors = []
        self.scripts = []
        self.styles = []
        self.inputs = []
        self.tabs = []
        self.current = []

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if tag == "a":
            self.anchors.append(data.get("href", ""))
        if tag == "script":
            self.scripts.append(data)
        if tag == "link" and data.get("rel") == "stylesheet":
            self.styles.append(data.get("href", ""))
        if "data-q-source" in data:
            self.sources.append(data)
        if "data-q-source-tab" in data:
            self.tabs.append(data["data-q-source-tab"])
        if "q-model" in data:
            self.inputs.append(data["q-model"])
        if "aria-current" in data:
            self.current.append(data["aria-current"])


def get_page(slug):
    name = "qaiuick-demo" if slug == "demo" else "qaiuick-" + slug
    return SITE / "tools" / name / "index.html"


class SampleGalleryTest(unittest.TestCase):
    def test_all_five_pages_and_gallery_links(self):
        home = (SITE / "products/web/qaiuick/index.html").read_text("utf-8")
        catalog = (SITE / "products/web/index.html").read_text("utf-8")
        self.assertIn('id="samples"', home)
        self.assertIn('/assets/qaiuick-beta/hero.webp', catalog)
        self.assertIn('qai-web-card', catalog)
        for slug in SLUGS:
            path = get_page(slug)
            self.assertTrue(path.is_file(), path)
            url = "/tools/" + path.parent.name + "/"
            self.assertIn(url, home)
            self.assertIn(url, (SITE / "sitemap.xml").read_text("utf-8"))
            self.assertIn(path.relative_to(ROOT).as_posix(),
                          (ROOT / "docs/RELEASED_PRODUCT_GUIDES.md").read_text("utf-8"))

    def test_source_viewers_reference_real_local_files(self):
        for slug in SLUGS:
            with self.subTest(slug=slug):
                parser = Parser()
                parser.feed(get_page(slug).read_text("utf-8"))
                self.assertEqual(len(parser.sources), 1)
                self.assertEqual(set(parser.tabs), {"html", "css", "js"})
                self.assertIn("/assets/qaiuick-beta/source-viewer.js",
                              [row.get("src") for row in parser.scripts])
                self.assertEqual(parser.current, ["page"])
                source = parser.sources[0]
                for field in ("data-source-html", "data-source-css", "data-source-js"):
                    for ref in source[field].split(","):
                        self.assertTrue(ref.startswith("/"), ref)
                        self.assertNotIn("..", ref)
                        self.assertTrue((SITE / ref.lstrip("/")).is_file(), ref)
                self.assertEqual(source["data-source-html"],
                                 "/tools/" + get_page(slug).parent.name + "/index.html")
                self.assertIn(SOURCE_JS[slug], source["data-source-js"])

    def test_no_inline_executable_script_or_event_handlers(self):
        for slug in SLUGS:
            page = get_page(slug).read_text("utf-8")
            self.assertNotRegex(page, r"\son[a-z]+\s*=", "Inline event handlers prohibited")
            self.assertNotRegex(page, r"<script(?![^>]*\bsrc=)[^>]*>", "Inline scripts prohibited")
            self.assertNotRegex(page, r"\sstyle\s*=", "CSP-disallowed inline styles prohibited")
            self.assertIn("q-submit=", page)
            self.assertIn("q-model=", page)
            self.assertIn("q-action=", page)
            self.assertIn("q-each=", page)

    def test_source_viewer_is_text_only(self):
        viewer = (SITE / "assets/qaiuick-beta/source-viewer.js").read_text("utf-8")
        self.assertIn("code.textContent", viewer)
        self.assertNotIn("innerHTML", viewer)
        self.assertNotIn("eval(", viewer)
        self.assertIn("credentials: 'omit'", viewer)
        self.assertIn("response.ok", viewer)

    def test_examples_have_seed_and_reset_without_remote_api(self):
        base = SITE / "assets/qaiuick-beta"
        files = [base / SOURCE_JS[x] for x in SLUGS]
        for f in files:
            with self.subTest(file=f.name):
                content = f.read_text("utf-8")
                self.assertIn("quickApp", content)
                self.assertIn("sample:", content)
                self.assertNotIn("fetch(", content)
                self.assertIn("quickApp({", content)
                self.assertIn("sample:", content)

    @unittest.skipUnless(shutil.which("node"), "Node.js not present")
    def test_seed_once_does_not_repopulate_deleted_items(self):
        module = (SITE / "assets/qaiuick-beta/examples/sample-data.js").as_uri()
        script = f"""
import assert from 'node:assert/strict';
import {{ seedOnce, resetSamples, storageKey }} from {module!r};
const cache = new Map();
globalThis.localStorage = {{
  getItem: k => cache.has(k) ? cache.get(k) : null,
  setItem: (k,v) => cache.set(k,v),
}};
const ns='example-testing';
const key=storageKey(ns);
let rows=[];
const store={{
  list: async()=>rows.map(x=>({{...x}})),
  save: async x=>{{rows.push({{...x}});cache.set(key,JSON.stringify(rows));}},
  remove: async id=>{{rows=rows.filter(x=>x.id!==id);cache.set(key,JSON.stringify(rows));}},
}};
const examples=[{{id:'one',title:'Example 1'}},{{id:'two',title:'Example 2'}}];
assert.equal((await seedOnce(store,ns,examples)).length,2);
await store.remove('one');await store.remove('two');
assert.equal((await seedOnce(store,ns,examples)).length,0);
assert.equal((await resetSamples(store,examples)).length,2);
console.log('QAIUICK_SEED_BEHAVIOR_PASS');
"""
        run = subprocess.run(
            ["node", "--input-type=module", "-e", script],
            text=True, capture_output=True, cwd=ROOT, timeout=25,
        )
        self.assertEqual(run.returncode, 0, run.stdout + "\n" + run.stderr)
        self.assertIn("QAIUICK_SEED_BEHAVIOR_PASS", run.stdout)


if __name__ == "__main__":
    unittest.main()
