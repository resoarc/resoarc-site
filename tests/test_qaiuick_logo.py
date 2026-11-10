# SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
# SPDX-License-Identifier: MIT
"""Verify that the approved orbit logo is used consistently and stays legible."""
from __future__ import annotations

import functools
import hashlib
import http.server
import pathlib
import threading
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
LOGO = "/assets/qaiuick-beta/logo-orbit-20261110.webp"
SHA256 = "ebbe7cae1276fad66d56e7b9d60e48c8978465b7f605b76b7847e35b926352f1"

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


class LogoReferencesTest(unittest.TestCase):
    def test_logo_hash_references_and_old_asset_preserved(self):
        current = SITE / LOGO.lstrip("/")
        self.assertEqual(hashlib.sha256(current.read_bytes()).hexdigest(), SHA256)
        self.assertTrue((SITE / "assets/qaiuick-beta/hero.webp").is_file())
        page = (SITE / "products/web/qaiuick/index.html").read_text("utf-8")
        catalog = (SITE / "products/web/index.html").read_text("utf-8")
        self.assertEqual(page.count(LOGO), 3)
        self.assertEqual(catalog.count(LOGO), 1)
        self.assertNotIn("/assets/qaiuick-beta/hero.webp", page + catalog)


@unittest.skipUnless(sync_playwright, "Playwright unavailable")
class LogoBrowserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(
            ("127.0.0.1", 0),
            functools.partial(Quiet, directory=str(SITE)))
        cls.server.daemon_threads = True
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()

    def test_desktop_and_mobile_logo_without_cropping(self):
        for width in (390, 768, 1440):
            with self.subTest(width=width):
                page = self.browser.new_page(viewport={"width": width, "height": 900})
                response = page.goto(
                    f"http://127.0.0.1:{self.server.server_port}/products/web/qaiuick/",
                    wait_until="networkidle")
                self.assertEqual(response.status, 200)
                logo = page.locator("img.qai-cosmic")
                self.assertEqual(logo.evaluate("(img) => img.naturalWidth"), 1080)
                self.assertEqual(logo.evaluate("(img) => img.naturalHeight"), 487)
                self.assertEqual(logo.evaluate("(img) => getComputedStyle(img).objectFit"),
                                 "contain")
                self.assertLessEqual(
                    page.evaluate("document.documentElement.scrollWidth-innerWidth"), 2)
                page.close()

    def test_catalog_card_uses_same_image(self):
        page = self.browser.new_page(viewport={"width": 390, "height": 844})
        response = page.goto(
            f"http://127.0.0.1:{self.server.server_port}/products/web/",
            wait_until="networkidle")
        self.assertEqual(response.status, 200)
        logo = page.locator("img.qai-catalog-logo")
        self.assertEqual(logo.evaluate("(img) => img.naturalWidth"), 1080)
        self.assertEqual(logo.evaluate("(img) => getComputedStyle(img).objectFit"),
                         "contain")
        page.close()


if __name__ == "__main__":
    unittest.main()
