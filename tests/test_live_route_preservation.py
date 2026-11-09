import importlib.util
import tempfile
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "scripts" / "verify_live_route_preservation.py"
spec = importlib.util.spec_from_file_location("route_guard", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def sitemap(*paths):
    rows = "".join(f"<url><loc>https://resoarc.com{p}</loc></url>" for p in paths)
    return ('<?xml version="1.0" encoding="UTF-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            + rows + '</urlset>').encode("utf-8")


class RoutePreservationTests(unittest.TestCase):
    def test_preserved_and_added_routes(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            for route in ("", "tools/csv"):
                p = base / route / "index.html"
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("test", encoding="utf-8")
            dropped, absent_files = module.validate_candidate(
                sitemap("/", "/tools/csv/"),
                sitemap("/", "/tools/csv/", "/en/"),
                base)
            self.assertFalse(dropped)
            self.assertFalse(absent_files)

    def test_missing_live_route_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            dropped, absent_files = module.validate_candidate(
                sitemap("/", "/security/weather/"), sitemap("/"), Path(d))
            self.assertEqual(dropped, {"/security/weather/"})
            self.assertEqual(absent_files, {"/"})

    def test_missing_file_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            dropped, absent_files = module.validate_candidate(
                sitemap("/", "/os/"), sitemap("/", "/os/"), Path(d))
            self.assertFalse(dropped)
            self.assertEqual(absent_files, {"/", "/os/"})

    def test_nonproject_host_rejected(self):
        self.assertRaises(ValueError, module.get_routes,
                          sitemap("/").replace(b"resoarc.com", b"example.com"))

    def test_path_traversal_rejected(self):
        self.assertRaises(ValueError, module.get_routes, sitemap("/", "/abc/../"))
        self.assertRaises(ValueError, module.get_routes, sitemap("/", "/%2e%2e/"))

    def test_bad_xml_rejected(self):
        self.assertRaises(Exception, module.get_routes, b"<urlset broken")

    def test_empty_rejected(self):
        self.assertRaises(ValueError, module.get_routes, sitemap("/not-root/"))


if __name__ == "__main__":
    unittest.main()
