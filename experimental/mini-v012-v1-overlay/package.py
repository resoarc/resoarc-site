"""Produce signed Kintone plugin packages from ResoArc sources.

Legacy Kintone plugin ZIP layout: contents.zip, PUBKEY (RSA-SPKI DER),
SIGNATURE (RSASSA-PKCS1-v1_5 with SHA1 over contents.zip).
Private signing keys stay outside public source/distribution.
"""
from pathlib import Path
import io,zipfile,json,hashlib,base64
from cryptography.hazmat.primitives.asymmetric import rsa,padding
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.exceptions import InvalidSignature
ROOT=Path(__file__).parent; PRIVATE=ROOT/'private'; RELEASE=ROOT/'release'; PLUGINS=ROOT/'plugins'
def build():
    catalog=json.loads((ROOT/'catalog.json').read_text(encoding='utf-8'))
    pins={x['slug']:x['public_key_sha256'] for x in json.loads((ROOT/'release-manifest.json').read_text(encoding='utf-8'))}
    if len(catalog)!=18 or len(pins)!=18:raise RuntimeError('Expected 18 original plugin keys')
    approved_keys={}
    for row in catalog:
        slug=row['slug'];keyfile=PRIVATE/(slug+'.pem')
        if not row['implemented'] or not keyfile.is_file():
            raise RuntimeError('Missing ORIGINAL signing key for '+slug+'; no output was created')
        key=serialization.load_pem_private_key(keyfile.read_bytes(),password=None)
        pub=key.public_key().public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo)
        if hashlib.sha256(pub).hexdigest()!=pins[slug]:
            raise RuntimeError('Signing key mismatch for '+slug+'; release blocked')
        approved_keys[slug]=key
    RELEASE.mkdir(exist_ok=True)
    results=[]
    for row in catalog:
        slug=row['slug'];src=PLUGINS/slug;keyfile=PRIVATE/(slug+'.pem')
        if not row['implemented']:raise RuntimeError('Runtime missing: '+slug)
        priv=approved_keys[slug]
        public=priv.public_key().public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo)
        members=sorted(p for p in src.rglob('*') if p.is_file())
        contents=io.BytesIO()
        with zipfile.ZipFile(contents,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as out:
            for p in members:
                path=str(p.relative_to(src)).replace('\\','/')
                out.writestr(path,p.read_bytes())
        contents_blob=contents.getvalue()
        signature=priv.sign(contents_blob,padding.PKCS1v15(),hashes.SHA1())
        dest=RELEASE/('resoarc-'+slug+'-v0.1.2-beta.zip')
        with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_STORED) as out:
            out.writestr('contents.zip',contents_blob)
            out.writestr('PUBKEY',public)
            out.writestr('SIGNATURE',signature)
        with zipfile.ZipFile(dest) as f:
            assert set(f.namelist())=={'contents.zip','PUBKEY','SIGNATURE'}
            priv.public_key().verify(f.read('SIGNATURE'),f.read('contents.zip'),padding.PKCS1v15(),hashes.SHA1())
            with zipfile.ZipFile(io.BytesIO(f.read('contents.zip'))) as nested:
                assert 'manifest.json' in nested.namelist()
                manifest=json.loads(nested.read('manifest.json'))
                assert all(x in nested.namelist() for x in [manifest['icon'],*manifest['desktop']['js'],manifest['config']['html'],*manifest['config']['js'],*manifest['config']['css']])
        results.append({'slug':slug,'bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'public_key_sha256':hashlib.sha256(public).hexdigest()})
    (ROOT/'release-manifest.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Signed and verified',len(results),'plugins;',sum(x['bytes'] for x in results),'bytes')
if __name__=='__main__':build()
