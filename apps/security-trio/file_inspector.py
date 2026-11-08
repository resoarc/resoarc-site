"""File Inspector: static read-only indicators, never executing inspected files."""
from __future__ import annotations

import os
import re
import threading
import zipfile
from pathlib import Path

from common import Finding, ScanResult, is_cancelled, safe_name, sha256, validate_paths, walk_files, zip_preflight

APP_NAME = "ResoArc File Inspector"
MAX_FILE_SIZE = 2 * 1024 ** 3
MAX_ZIP_ENTRIES = 2500
MAX_RELS_BYTES = 128 * 1024
LNK_HEADER = bytes.fromhex("4c0000000114020000000000c000000000000046")
OLE_HEADER = bytes.fromhex("d0cf11e0a1b11ae1")
EXECUTABLE_EXTENSIONS = {
    ".exe", ".scr", ".com", ".pif", ".bat", ".cmd", ".ps1",
    ".vbs", ".vbe", ".js", ".jse", ".wsf", ".hta", ".lnk", ".msi",
}
DOC_EXTENSIONS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".jpg", ".jpeg", ".png", ".txt", ".zip"}
EXPECTED_TYPES = {
    ".pdf": {"PDF"}, ".jpg": {"JPEG"}, ".jpeg": {"JPEG"}, ".png": {"PNG"},
    ".docx": {"ZIP"}, ".xlsx": {"ZIP"}, ".pptx": {"ZIP"},
    ".docm": {"ZIP"}, ".xlsm": {"ZIP"}, ".pptm": {"ZIP"},
    ".doc": {"OLE"}, ".xls": {"OLE"}, ".ppt": {"OLE"}, ".zip": {"ZIP"},
}
PDF_FLAGS = (b"/JavaScript", b"/OpenAction", b"/Launch", b"/EmbeddedFile", b"/AA ")
COMMANDS = ("powershell", "pwsh", "mshta", "wscript", "cscript", "cmd.exe")
ENCODED_COMMAND = re.compile(r"(?i)(?:-enc(?:odedcommand)?\s+|frombase64string\s*\()")
BIDI = ("\u202e", "\u202d", "\u2066", "\u2067", "\u2068")


def file_type(head: bytes) -> str:
    if head.startswith(LNK_HEADER):
        return "LNK"
    if head.startswith(b"MZ") and len(head) >= 64:
        offset = int.from_bytes(head[0x3c:0x40], "little")
        return "PE" if 0 <= offset <= len(head) - 4 and head[offset:offset+4] == b"PE\0\0" else "DOS"
    if head[:5] == b"%PDF-" or b"%PDF-" in head[:1024]:
        return "PDF"
    if head.startswith(OLE_HEADER):
        return "OLE"
    if head.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
        return "ZIP"
    if head.startswith(b"\x7fELF"):
        return "ELF"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    if head[:3] == b"\xff\xd8\xff":
        return "JPEG"
    return "UNKNOWN"


def _check_zip(path: Path, out: ScanResult):
    preflight = zip_preflight(path, max_entries=MAX_ZIP_ENTRIES)
    if preflight:
        out.skipped += 1
        out.truncated = True
        rule = "ZIP項目数が過大" if "項目数が上限" in preflight else "ZIP中央ディレクトリの制限"
        out.add(Finding("中", rule, safe_name(path.name),
                        preflight, "入力を小さく分けるか、専門ツールで確認してください。"))
        return
    try:
        with zipfile.ZipFile(path, "r") as archive:
            info = archive.infolist()
            if len(info) > MAX_ZIP_ENTRIES:
                out.truncated = True
                out.skipped += len(info) - MAX_ZIP_ENTRIES
                out.add(Finding("中", "ZIP項目数が過大", safe_name(path.name),
                                f"内部項目 {len(info)} 件。上限超過のため詳細を検査できません。"))
                return
            total = sum(x.file_size for x in info)
            compressed = sum(max(1, x.compress_size) for x in info)
            if total > 512 * 1024 * 1024 or (total > 20 * 1024 * 1024 and total > 100 * compressed):
                out.skipped += 1
                out.add(Finding("高", "ZIPの異常な容量膨張", safe_name(path.name),
                                "展開時に非常に大きくなる可能性があります。", "不用意に展開しないでください。"))
                return
            names = [x.filename.replace("\\", "/") for x in info]
            # An arbitrary ZIP renamed to .docx/.xlsx/.pptx is not a valid
            # Office document. Check expected OPC package structure from names,
            # without loading or executing embedded content.
            ext = path.suffix.lower()
            expected_parts = {
                ".docx": "word/document.xml", ".docm": "word/document.xml",
                ".xlsx": "xl/workbook.xml", ".xlsm": "xl/workbook.xml",
                ".pptx": "ppt/presentation.xml", ".pptm": "ppt/presentation.xml",
            }
            if ext in expected_parts:
                members = set(names)
                if "[Content_Types].xml" not in members or expected_parts[ext] not in members:
                    out.add(Finding("中", "Office内部構造の不一致", safe_name(path.name),
                                    "Office文書に必要な構造が見つかりません。単なるZIPの偽装か、破損したファイルの可能性があります。",
                                    "Officeで開く前に入手元を確認してください。"))
            if any(x.startswith("/") or ".." in x.split("/") or re.match(r"^[a-zA-Z]:", x) for x in names):
                out.add(Finding("中", "ZIP内の危険なパス", safe_name(path.name),
                                "内部ファイル名にディレクトリ逸脱を示唆する記述があります。"))
            encrypted_count = sum(bool(x.flag_bits & 1) for x in info)
            if encrypted_count:
                out.skipped += encrypted_count
                out.add(Finding("情報", "ZIP内に暗号化項目", safe_name(path.name),
                                "暗号化項目の内部は検査できません。"))
            # Only inspect archive metadata. Never open or execute its contents.
            embedded_exec = sum(Path(n).suffix.lower() in EXECUTABLE_EXTENSIONS
                                for n in names if not n.endswith("/"))
            if embedded_exec:
                out.add(Finding("中", "ZIP内に実行可能な形式", safe_name(path.name),
                                f"ZIP内部に実行ファイル・スクリプト形式が {embedded_exec} 件あります。",
                                "添付元を確認し、不明なファイルは実行しないでください。"))
            if any(n.lower().endswith("/vbaproject.bin") for n in names):
                out.add(Finding("高", "Office VBAマクロを含む", safe_name(path.name),
                                "ZIP内部でVBAマクロ用のファイルを検出しました。",
                                "マクロは実行せず送信元を確認してください。"))
            for item in info:
                if not item.filename.lower().endswith(".rels") or item.file_size > MAX_RELS_BYTES or item.flag_bits & 1:
                    continue
                try:
                    with archive.open(item, "r") as stream:
                        xml = stream.read(MAX_RELS_BYTES + 1)
                    # External hyperlinks are commonplace in legitimate Office
                    # files. They are *not* equivalent to external templates or
                    # remotely loaded objects. Inspect bounded relationship tags
                    # without parsing external XML entities.
                    for rel in re.finditer(rb"(?is)<(?:[A-Za-z0-9_]+:)?Relationship\b[^>]{0,8192}>", xml):
                        tag = rel.group(0)
                        if not re.search(rb"(?i)\bTargetMode\s*=\s*['\"]\s*External\s*['\"]", tag):
                            continue
                        if re.search(rb"(?i)\bType\s*=\s*['\"][^'\"]*/hyperlink['\"]", tag):
                            continue
                        out.add(Finding("中", "Office外部参照", safe_name(path.name),
                                        "外部テンプレートやオブジェクト等の読み込みを示す関係定義を検出しました。",
                                        "不明な外部コンテンツの読み込みを許可しないでください。"))
                        break
                    else:
                        continue
                    break
                except (OSError, ValueError, RuntimeError, EOFError, zipfile.BadZipFile):
                    out.skipped += 1
                    continue
    except (OSError, ValueError, RuntimeError, EOFError, zipfile.BadZipFile):
        out.skipped += 1
        out.truncated = True
        out.add(Finding("情報", "ZIP形式の解析失敗", safe_name(path.name),
                        "ZIPとして完全に解析できません。検査結果は不完全です。"))


def _mark_of_web(path: Path) -> int | None:
    if os.name != "nt":
        return None
    try:
        with open(str(path) + ":Zone.Identifier", "rb") as stream:
            meta = stream.read(2048).decode("ascii", "ignore")
        m = re.search(r"(?m)^ZoneId=(\d+)\s*$", meta)
        return int(m.group(1)) if m else None
    except (OSError, ValueError):
        return None


def scan(paths, progress=None, cancel: threading.Event | None = None) -> ScanResult:
    result = ScanResult(APP_NAME)
    hash_records = []
    for index, path in enumerate(walk_files(validate_paths(paths, result), limit=501, cancel=cancel)):
        if index >= 500:
            result.truncated = True
            result.errors.append("走査対象の件数が上限(500)を超えたため途中で停止しました。")
            break
        if is_cancelled(cancel):
            break
        name = safe_name(path.name)
        if progress:
            progress(name)
        try:
            size = path.stat().st_size
            if size > MAX_FILE_SIZE:
                result.skipped += 1
                result.errors.append(f"{name}: 2 GiBを超えるため除外しました。")
                continue
            with path.open("rb") as stream:
                head = stream.read(2 * 1024 * 1024)
            kind = file_type(head)
            ext = path.suffix.lower()
            result.scanned += 1
            digest = sha256(path, cancel)
            if digest:
                hash_records.append({"file": name, "sha256": digest, "bytes": size, "detected_type": kind})
            if kind == "OLE":
                result.add(Finding("情報", "旧Office/OLE形式", name,
                                   "古い複合文書形式です。内部マクロの解析は対象外です。",
                                   "マクロを有効にせず送信元を確認してください。"))
                if ext in (".docx", ".xlsx", ".pptx"):
                    result.add(Finding("中", "Officeの拡張子と実形式が不一致", name,
                                       "新しいOffice形式の拡張子ですが内部はOLE形式です。"))
            if kind in ("PE", "DOS") and ext in DOC_EXTENSIONS:
                result.add(Finding("高", "拡張子と実行形式の不一致", name,
                                   f"文書・画像に見えますが内部は{kind}形式です。",
                                   "開かずに送信元を確認してください。"))
            if kind == "LNK" and ext != ".lnk":
                result.add(Finding("高", "ショートカット偽装", name,
                                   "拡張子と異なりWindowsショートカット形式です。"))
            if kind == "ZIP" and ext in (".pdf", ".png", ".jpg", ".jpeg"):
                result.add(Finding("中", "拡張子とZIP形式の不一致", name,
                                   "文書・画像ではなくZIP形式を検出しました。"))
            # Known signatures conflicting with expected extension types.
            # UNKNOWN alone is not strong enough evidence to issue a warning.
            expected = EXPECTED_TYPES.get(ext)
            if expected and kind not in expected and kind not in ("UNKNOWN", "DOS", "PE"):
                already_reported = ((kind == "ZIP" and ext in (".pdf", ".png", ".jpg", ".jpeg")) or
                                    (kind == "OLE" and ext in (".docx", ".xlsx", ".pptx")))
                if not already_reported:
                    result.add(Finding("中", "拡張子と実形式が不一致", name,
                                       f"拡張子は{ext}ですが、内部は{kind}形式です。",
                                       "開く前にファイルの入手元を確認してください。"))
            if re.search(r"(?i)\.(?:pdf|docx?|xlsx?|jpe?g|png|txt|zip)\.(?:exe|scr|bat|cmd|js|vbs|lnk|ps1)$", path.name):
                result.add(Finding("高", "二重拡張子", name,
                                   "文書・画像に見せた実行可能な拡張子です。"))
            if any(ch in path.name for ch in BIDI):
                result.add(Finding("高", "文字方向制御による偽装", name,
                                   "表示上のファイル名を誤認させる可能性があります。"))
            if ext in EXECUTABLE_EXTENSIONS:
                result.add(Finding("情報", "実行可能・スクリプト形式", name,
                                   "実行・スクリプトに使用される拡張子です。これだけでは悪意は判定できません。"))
            if kind == "PDF" and any(marker in head for marker in PDF_FLAGS):
                result.add(Finding("中", "PDFに能動的な構造の兆候", name,
                                   "自動動作・スクリプト・埋め込みを示唆する文字列があります。",
                                   "保護されたビューアで扱い、送信元を確認してください。"))
            if kind == "LNK":
                lower = head.lower()
                if any(c.encode("ascii") in lower or c.encode("utf-16le") in lower for c in COMMANDS):
                    result.add(Finding("高", "LNK内のコマンド起動文字列", name,
                                       "スクリプトやコマンド処理の起動文字列を検出しました。"))
            if ext in (".ps1", ".bat", ".cmd", ".js", ".vbs", ".hta"):
                if ENCODED_COMMAND.search(head.decode("utf-8", errors="ignore")[:100_000]):
                    result.add(Finding("中", "エンコードコマンドの兆候", name,
                                       "エンコードされたコマンドの実行を示唆します。"))
            if kind == "ZIP":
                _check_zip(path, result)
            zone = _mark_of_web(path)
            if zone in (3, 4):
                result.add(Finding("情報", "インターネット由来", name,
                                   f"WindowsのZone.IdentifierにZoneId={zone}が記録されています。"))
        except (OSError, ValueError, PermissionError, OverflowError):
            result.errors.append(f"{name}: 読み取れませんでした。")
    if result.scanned == 0:
        result.errors.append("解析できるファイルがありませんでした。")
    result.metrics = {
        "files": hash_records,
        "max_files": 500, "max_size_gib": 2, "cancelled": is_cancelled(cancel),
        "disclaimer": "静的な兆候を表示します。マルウェア有無の判定は行いません。",
    }
    return result
