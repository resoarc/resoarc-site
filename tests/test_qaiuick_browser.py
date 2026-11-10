# SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
# SPDX-License-Identifier: MIT
"""Browser acceptance tests of the five qAIUIck sample applications."""
from __future__ import annotations

import functools
import http.server
import pathlib
import threading
import unittest

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

ROOT = pathlib.Path(__file__).resolve().parents[1]
SITE = ROOT / "site"


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@unittest.skipUnless(sync_playwright, "Playwright is not installed")
class QaiuickBrowserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler = functools.partial(QuietHandler, directory=str(SITE))
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = "http://127.0.0.1:" + str(cls.server.server_address[1])
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)
        cls.context = cls.browser.new_context(
            viewport={"width": 390, "height": 844}, device_scale_factor=1
        )

    @classmethod
    def tearDownClass(cls):
        cls.context.close()
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()

    def open(self, slug):
        page = self.context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(self.base + "/tools/qaiuick-" + slug + "/", wait_until="networkidle")
        self.assertEqual(errors, [], "\n".join(errors))
        return page

    def test_default_content_source_tabs_and_mobile_width(self):
        counts = {
            "demo": (".q-list li", 3),
            "inventory": ("tbody tr", 5),
            "budget": (".q-list li", 5),
            "tickets": (".q-list li", 4),
            "customers": ("tbody tr", 5),
        }
        for slug, (selector, expected) in counts.items():
            with self.subTest(slug=slug):
                page = self.open(slug)
                try:
                    page.locator(selector).first.wait_for()
                    self.assertEqual(page.locator(selector).count(), expected)
                    page.locator('[data-q-source-code]').wait_for()
                    page.locator('[data-q-source-tab="html"]').click()
                    page.wait_for_function(
                        "() => document.querySelector('[data-q-source-code]').textContent.includes('<!doctype html>')"
                    )
                    page.locator('[data-q-source-tab="css"]').click()
                    page.wait_for_function(
                        "() => document.querySelector('[data-q-source-code]').textContent.includes('--q-primary')"
                    )
                    page.locator('[data-q-source-tab="js"]').click()
                    page.wait_for_function(
                        "() => document.querySelector('[data-q-source-code]').textContent.includes('quickApp')"
                    )
                    width = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
                    self.assertLessEqual(width, 2, "horizontal overflow on " + slug)
                finally:
                    page.close()

    def test_todo_seed_only_first_visit_and_reset(self):
        page = self.open("demo")
        try:
            self.assertEqual(page.locator(".q-list li").count(), 3)
            while page.locator('.q-list button[q-action="remove"]').count():
                page.locator('.q-list button[q-action="remove"]').first.click()
            self.assertEqual(page.locator(".q-list li").count(), 0)
            page.reload(wait_until="networkidle")
            self.assertEqual(page.locator(".q-list li").count(), 0)
            page.locator('button[q-action="reset"]').click()
            self.assertEqual(page.locator(".q-list li").count(), 3)
            page.locator('[q-model="draft"]').fill('<img src=x onerror=alert(1)>')
            page.locator('button[type="submit"]').click()
            page.wait_for_function("() => document.querySelectorAll('.q-list li').length === 4")
            self.assertEqual(page.locator(".q-list li img").count(), 0)
        finally:
            page.close()

    def test_inventory_updates(self):
        page = self.open("inventory")
        try:
            self.assertEqual(page.locator('[q-text="lowStock"]').inner_text(), "2")
            page.locator('button[q-action="restock"]').first.click()
            self.assertEqual(page.locator('tbody tr').first.locator('td').nth(2).inner_text(), "58")
            page.locator('[q-model="draft.name"]').fill("デモ用ケース")
            page.locator('button[type="submit"]').click()
            self.assertEqual(page.locator("tbody tr").count(), 6)
        finally:
            page.close()

    def test_budget_totals_ticket_progress_and_customer_filter(self):
        budget = self.open("budget")
        try:
            self.assertEqual(budget.locator('[q-text="total"]').inner_text(), "8,770 円")
            self.assertEqual(budget.locator('[q-text="foodTotal"]').inner_text(), "3,230 円")
        finally:
            budget.close()
        tickets = self.open("tickets")
        try:
            tickets.locator('button[q-action="advance"]').first.click()
            self.assertIn("対応中", tickets.locator(".q-list li").first.inner_text())
        finally:
            tickets.close()
        customers = self.open("customers")
        try:
            customers.locator('[q-model="query"]').fill("東京")
            self.assertEqual(customers.locator("tbody tr").count(), 2)
            customers.locator('[q-model="query"]').fill("")
            self.assertEqual(customers.locator("tbody tr").count(), 5)
        finally:
            customers.close()


if __name__ == "__main__":
    unittest.main()
