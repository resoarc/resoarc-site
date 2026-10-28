"""Private OFFLINE Cowrie lab data snapshot/restore with bounded SHA-256 audit.

Not a production backup tool. No external network, archiving of actual user
telemetry, automatic repair or deletion of real services. Use only in the
disposable trial directory owned by cowrie_recreate_recovery.py.
"""
import hashlib
import os
from pathlib import Path
import shutil
import stat

MAX_FILES=512
MAX_BYTES=8*1024*1024
COWRIE_UID=999

def manifest(root):
    root=Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("missing or symlinked private var root")
    entries={}
    bytes_seen=0
    for folder, directories, files in os.walk(root,followlinks=False):
        for name in directories:
            entry=Path(folder)/name
            if entry.is_symlink() or not entry.is_dir():
                raise ValueError("symlink/non-directory in var tree")
        for name in files:
            path=Path(folder)/name
            st=path.lstat()
            if not stat.S_ISREG(st.st_mode) or st.st_nlink!=1:
                raise ValueError("symlink, hardlink or special file in var")
            if st.st_size>MAX_BYTES or bytes_seen+st.st_size>MAX_BYTES:
                raise ValueError("unbounded private var")
            if len(entries)>=MAX_FILES:
                raise ValueError("too many private data files")
            h=hashlib.sha256()
            with path.open("rb") as f:
                while True:
                    data=f.read(65536)
                    if not data:break
                    h.update(data)
            if path.stat().st_size!=st.st_size:
                raise ValueError("var data changed during capture")
            key=path.relative_to(root).as_posix()
            entries[key]={"size":st.st_size,"sha256":h.hexdigest()}
            bytes_seen+=st.st_size
    if not entries or "log/cowrie/cowrie.json" not in entries:
        raise ValueError("Cowrie JSON evidence missing")
    return entries

def copy_verified(source, destination, expected=None, owner=None):
    src=Path(source);dst=Path(destination)
    if dst.exists() or dst.is_symlink():
        raise ValueError("refusing to overwrite pre-existing data")
    original=manifest(src)
    if expected is not None and original!=expected:
        raise ValueError("untrusted/tampered backup manifest")
    try:
        shutil.copytree(src,dst,symlinks=False)
        if owner is not None:
            for folder, dirs, files in os.walk(dst):
                os.chown(folder,owner,owner)
                for f in files:os.chown(os.path.join(folder,f),owner,owner)
        if manifest(dst)!=original:
            raise ValueError("backup restore copy integrity differs")
    except Exception:
        if dst.exists() and not dst.is_symlink():shutil.rmtree(dst)
        raise
    return original
