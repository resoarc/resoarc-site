#!/usr/bin/env python3
"""Browser check: homepage Information follows changes in /releases/ automatically."""
from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import threading
from html import unescape

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
RELEASES = (ROOT / "site/releases/index.html").read_text(encoding="utf-8")


class SilentHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def main() -> None:
    assert "connect-src 'self'" in (ROOT / "site/_headers").read_text(encoding="utf-8")
    match = re.search(r'<div class="release-entry">.*?<h2>(.*?)</h2>', RELEASES, re.S)
    assert match, "no release history heading"
    first_title = unescape(re.sub(r'<[^>]+>', '', match.group(1)))
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(SilentHandler, directory=str(ROOT / "site"))
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch(headless=True)
            except Exception:
                browser = playwright.chromium.launch(headless=True, channel="msedge")
            try:
                for width in (1440, 390):
                    page = browser.new_page(viewport={"width": width, "height": 880})
                    page.goto(f"http://127.0.0.1:{server.server_port}/")
                    page.wait_for_function(
                        "(title) => document.querySelector('.update-row strong')?.textContent.includes(title)",
                        arg=first_title, timeout=15000,
                    )
                    assert page.locator(".updates-items .update-row").count() == 3
                    assert page.locator(".updates-items a[href='/releases/']").count() == 1
                    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                    assert page.locator(".update-row a").first.get_attribute("href").startswith("/")
                    page.close()

                # A new release note must become the TOP lead without editing the homepage.
                new_entry = (
                    '<div class="release-entry"><div>'
                    '<time datetime="2026-10-17">2026.10.17</time>'
                    '<span>TEST</span></div><div>'
                    '<h2>回帰検証用の最新ニュース</h2>'
                    '<p><a href="/products/web/">Webツールへ</a></p></div></div>'
                )
                changed = RELEASES.replace(
                    '<div class="release-entry">', new_entry + '<div class="release-entry">', 1
                )
                page = browser.new_page()
                page.route(
                    "**/releases/",
                    lambda route: route.fulfill(
                        status=200, content_type="text/html; charset=utf-8", body=changed
                    ),
                )
                page.goto(f"http://127.0.0.1:{server.server_port}/")
                page.wait_for_function(
                    "() => document.querySelector('.update-row strong')?.textContent.includes('回帰検証用')",
                    timeout=15000,
                )
                assert page.locator(".update-row").count() == 3
                assert page.locator(".update-row a").first.get_attribute("href") == "/products/web/"
                page.close()
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
    print("TOP_RELEASE_NEWS_SYNC_PASS: desktop, mobile, simulated release insertion")


if __name__ == "__main__":
    main()
