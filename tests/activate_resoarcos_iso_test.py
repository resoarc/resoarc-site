import contextlib
import hashlib
import io
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import activate_resoarcos_iso as m

class PublishTest(unittest.TestCase):
    def test_preview_link_requires_verified_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp)
            (root/"site"/"os").mkdir(parents=True)
            (root/"site"/"downloads").mkdir(parents=True)
            source=b"source zip test"
            (root/"site"/"downloads"/"resoarcos-pc-v0.1.0-dev-source.zip").write_bytes(source)
            oldsum="a"*64
            html=('<p>現在公開できるのはソースコードと検証記録です。ISOイメージは生成・検証済みですが、ファイル配布先の整備が必要なため、このサイトからのISOダウンロードはまだ提供していません。</p>'
                  '<span>配布準備中</span><span>本番非推奨</span>'
                  '<a class="product-cta" href="#verification">検証状況を見る <span aria-hidden="true">↓</span></a>'
                  f'<p>ローカル検証でのISO SHA-256：<code>{oldsum}</code></p>')
            page=root/"site"/"os"/"index.html"
            page.write_text(html,encoding="utf8")
            iso_url=f"https://github.com/{m.REPO}/releases/download/{m.TAG}/{m.ASSET}"
            sums_url="https://github.com/example/SHA256SUMS"
            data={
                "tag_name":m.TAG,"prerelease":True,"draft":False,
                "assets":[
                    {"name":m.ASSET,"size":610000000,"browser_download_url":iso_url},
                    {"name":"SHA256SUMS","size":100,"browser_download_url":sums_url},
                    {"name":"source.zip","size":len(source),"browser_download_url":"https://github.com/example/source.zip"}]}
            def fake_get(url):
                if url.endswith("/releases/tags/"+m.TAG):return json.dumps(data).encode()
                if url==sums_url:return (("b"*64)+"  "+m.ASSET+"\n").encode()
                raise AssertionError(url)
            with patch.object(m,"ROOT",root),patch.object(m,"PAGE",page),patch.object(m,"EXPECTED_SOURCE",hashlib.sha256(source).hexdigest()),patch.object(m,"get",side_effect=fake_get):
                with patch.object(sys,"argv",["script"]):
                    with contextlib.redirect_stdout(io.StringIO()):m.main()
                self.assertEqual(page.read_text(encoding="utf8"),html)
                with patch.object(sys,"argv",["script","--apply"]):
                    with contextlib.redirect_stdout(io.StringIO()):m.main()
                self.assertIn(iso_url,page.read_text(encoding="utf8"))
                self.assertIn("公開ISO SHA-256",page.read_text(encoding="utf8"))
                self.assertNotIn("配布準備中",page.read_text(encoding="utf8"))
                data["prerelease"]=False
                with patch.object(sys,"argv",["script","--apply"]):
                    with self.assertRaises(AssertionError):
                        m.main()

if __name__=="__main__":
    unittest.main()
