from __future__ import annotations
import importlib.util
import io
import json
import unittest
from pathlib import Path
from urllib.error import HTTPError
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('preflight',ROOT/'scripts/kintone_tenant_preflight.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
BASE='https://example.cybozu.com'
TOKEN='FAKE_READ_ONLY_TEST_TOKEN'

class PreflightTests(unittest.TestCase):
    def test_credentials_required_and_never_default_to_real_tenant(self):
        with self.assertRaisesRegex(module.AcceptanceError,'不足'):
            module.validate_env({})
    def test_refuses_http_foreign_hosts_and_url_credentials(self):
        for base in ('http://example.cybozu.com','https://example.evil.invalid','https://example.cybozu.com@attacker.com','https://example.cybozu.com:8443','https://example.cybozu.com/path'):
            with self.subTest(base=base),self.assertRaises(module.AcceptanceError):
                module.validate_env({'RESOARC_KINTONE_TEST_BASE':base,'RESOARC_KINTONE_TEST_APP':'42','RESOARC_KINTONE_TEST_READ_TOKEN':TOKEN})
    def test_positive_app_and_no_header_injection(self):
        for app in ('0','-1','NaN','1.2','4294967296',' 7'):
            with self.subTest(app=app),self.assertRaises(module.AcceptanceError):
                module.validate_env({'RESOARC_KINTONE_TEST_BASE':BASE,'RESOARC_KINTONE_TEST_APP':app,'RESOARC_KINTONE_TEST_READ_TOKEN':TOKEN})
        with self.assertRaises(module.AcceptanceError):
            module.validate_env({'RESOARC_KINTONE_TEST_BASE':BASE,'RESOARC_KINTONE_TEST_APP':'42','RESOARC_KINTONE_TEST_READ_TOKEN':'abcd\nX-Injected: true'})
    def test_success_is_get_only_and_does_not_return_values_or_token(self):
        seen=[]
        def opener(req):
            seen.append(req)
            self.assertEqual(req.get_method(),'GET')
            self.assertIn('x-cybozu-api-token',dict((k.lower(),v) for k,v in req.header_items()))
            if '/form/fields.json' in req.full_url:
                return io.BytesIO(json.dumps({'properties':{'Name':{'type':'SINGLE_LINE_TEXT'},'Status':{'type':'DROP_DOWN'}}}).encode())
            if '/records.json' in req.full_url:
                return io.BytesIO(b'{"records":[{"$id":{"value":"3"},"SECRET":{"value":"DO_NOT_DISCLOSE"}}]}')
            self.fail('unexpected url')
        result=module.inspect(BASE,42,TOKEN,opener=opener)
        self.assertEqual(len(seen),2)
        self.assertEqual(result['field_count'],2)
        self.assertTrue(result['sample_record_present'])
        self.assertIn('plugin installation',result['not_tested'])
        self.assertNotIn('DO_NOT_DISCLOSE',json.dumps(result))
        self.assertNotIn(TOKEN,json.dumps(result))
    def test_network_failure_has_no_raw_credentials(self):
        def denied(req):raise HTTPError(req.full_url,403,'access denied',{},None)
        with self.assertRaises(module.AcceptanceError) as cm:
            module.inspect(BASE,42,TOKEN,opener=denied)
        self.assertIn('403',str(cm.exception))
        self.assertNotIn(TOKEN,str(cm.exception))
        self.assertNotIn(BASE,str(cm.exception))
    def test_missing_schema_fails(self):
        def empty(req):return io.BytesIO(b'{"properties":{}}')
        with self.assertRaisesRegex(module.AcceptanceError,'フォーム情報'):
            module.inspect(BASE,42,TOKEN,opener=empty)

if __name__=='__main__':unittest.main()
