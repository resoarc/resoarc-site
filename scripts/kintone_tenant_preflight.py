#!/usr/bin/env python3
"""Read-only kintone test-tenant gate.

All settings come from environment variables. Does not perform record writes,
does not save API tokens or record values, and does not emit app names.
Run ONLY against a dedicated ResoArc test app with least-privilege API token.
"""
from __future__ import annotations
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter

ALLOWED_HOST_SUFFIXES=('.cybozu.com','.kintone.com')
class AcceptanceError(RuntimeError): pass

def validate_env(environ):
    base=environ.get('RESOARC_KINTONE_TEST_BASE','').strip().rstrip('/')
    app=environ.get('RESOARC_KINTONE_TEST_APP','')
    token=environ.get('RESOARC_KINTONE_TEST_READ_TOKEN','')
    if not (base and app and token):
        raise AcceptanceError('専用テスト環境の設定が不足しています。環境への接続試験は未実施です。')
    url=urllib.parse.urlsplit(base)
    host=(url.hostname or '').lower()
    if url.scheme!='https' or url.username or url.password or url.port or url.query or url.fragment or url.path:
        raise AcceptanceError('テスト環境のURLは https://テナント の形式で指定してください')
    if not any(host.endswith(suffix) and len(host)>len(suffix) for suffix in ALLOWED_HOST_SUFFIXES):
        raise AcceptanceError('cybozu.com / kintone.comのテスト用テナントに限定します')
    if not app.isascii() or not app.isdecimal() or int(app)<1 or int(app)>2**31:
        raise AcceptanceError('テストアプリIDは正の整数を指定してください')
    if not token.strip() or '\n' in token or '\r' in token:
        raise AcceptanceError('読み取り専用のAPIトークンを指定してください')
    return base,int(app),token

def get_json(base,app,token,path,extra=None,opener=None):
    query={'app':str(app)}
    query.update(extra or {})
    endpoint=base+'/k/v1/'+path+'.json?'+urllib.parse.urlencode(query)
    req=urllib.request.Request(endpoint,headers={'X-Cybozu-API-Token':token,'Accept':'application/json'},method='GET')
    try:
        if opener is None:
            response=urllib.request.urlopen(req,timeout=15)
        else:
            response=opener(req)
        with response:
            data=response.read(1024*1024+1)
        if len(data)>1024*1024:raise AcceptanceError('テスト応答が1MiBを超えたため停止しました')
        return json.loads(data.decode('utf8'))
    except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError) as error:
        # Do not echo URLs, credentials, or raw response bodies.
        code=error.code if isinstance(error,urllib.error.HTTPError) else 'network'
        raise AcceptanceError(f'テストAPIへのGETが失敗しました（{path}, {code}）。権限と接続を確認してください') from None
    except (ValueError,UnicodeDecodeError) as error:
        raise AcceptanceError(f'{path} のJSONを解釈できません') from None

def inspect(base,app,token,opener=None):
    fields=get_json(base,app,token,'app/form/fields',opener=opener)
    if not isinstance(fields,dict) or not isinstance(fields.get('properties'),dict) or not fields['properties']:
        raise AcceptanceError('フォーム情報を取得できません。アプリ管理権限を確認してください')
    # Only the current test app's 1st record is inspected. Never print values.
    records=get_json(base,app,token,'records',{'query':'limit 1','fields[0]':'$id'},opener=opener)
    if not isinstance(records,dict) or not isinstance(records.get('records'),list):
        raise AcceptanceError('レコード閲覧情報を取得できません')
    field_types=Counter(x.get('type','UNKNOWN') for x in fields['properties'].values() if isinstance(x,dict))
    return {'test_app_id':app,'read_only':True,'field_count':len(fields['properties']),
            'field_types':dict(sorted(field_types.items())),
            'sample_record_present':bool(records['records']),
            'checked':'form fields and one record via GET only',
            'not_tested':['plugin installation','field write/edit rights','event behavior','mobile UI','concurrency','other plugin conflicts']}

def main():
    try:
        base,app,token=validate_env(os.environ)
        result=inspect(base,app,token)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        print('RESOARC_TENANT_READ_ONLY_PREFLIGHT_PASS')
        return 0
    except AcceptanceError as error:
        print('RESOARC_TENANT_READ_ONLY_PREFLIGHT_NOT_APPROVED: '+str(error),file=sys.stderr)
        return 2

if __name__=='__main__':sys.exit(main())
