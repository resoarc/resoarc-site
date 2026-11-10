"""Secret Scout: offline secret exposure triage, always redacting matched values."""
from __future__ import annotations

import re
import threading
import zipfile
from pathlib import Path, PurePosixPath

from common import Finding, ScanResult, is_cancelled, safe_name, validate_paths, walk_files, zip_preflight

APP_NAME = "ResoArc Secret Scout"
MAX_TEXT = 16 * 1024 * 1024
MAX_MEMBER = 8 * 1024 * 1024
MAX_ZIP_TOTAL = 64 * 1024 * 1024
MAX_ZIP_ENTRIES = 2000
TEXT_EXTENSIONS = {
    ".txt", ".md", ".json", ".jsonl", ".js", ".jsx", ".ts", ".tsx",
    ".py", ".php", ".rb", ".go", ".java", ".kt", ".swift", ".sh", ".ps1",
    ".bat", ".cmd", ".yaml", ".yml", ".toml", ".ini", ".properties",
    ".xml", ".html", ".htm", ".css", ".sql", ".cfg", ".conf",
    ".config", ".tf", ".env", ".pem", ".key", ".asc", ".csv", ".gradle",
    ".gitignore", ".example", ".sample", ".npmrc",
}
ADVICE = "公開前に秘密情報を除去してください。既に公開した場合は該当資格情報を失効・再発行してください。"
PATTERNS = (
    ("秘密鍵の開始行", "高", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----")),
    ("GitHubトークン形式", "高", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{30,}|github_pat_[A-Za-z0-9_]{30,})\b")),
    ("AWSアクセスキーID形式", "高", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("Slackトークン形式", "高", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{16,}\b")),
    ("Stripe本番秘密キー形式", "高", re.compile(r"\bsk_live_[A-Za-z0-9]{16,}\b")),
    ("Google APIキー形式", "中", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("JWT形式", "中", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{8,}\b")),
    ("認証情報付き接続URI", "高", re.compile(r"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://[^\s:/@]+:[^\s@]+@", re.I)),
)
ASSIGNMENT = re.compile(
    r'''(?i)(?<![\w])(?:api[_-]?key|access[_-]?token|auth[_-]?token|github[_-]?token|gitlab[_-]?token|cloudflare[_-]?token|slack[_-]?token|stripe[_-]?token|bearer[_-]?token|client[_-]?secret|secret[_-]?key|private[_-]?key|password|passwd|db[_-]?password|database[_-]?password|aws[_-]?secret[_-]?access[_-]?key)\s*["']?\s*[:=]\s*["']?([^"'\s;,#]{8,})'''
)
PLACEHOLDER = re.compile(
    r"(?i)^(?:example(?:[_-].*)?|sample(?:[_-].*)?|dummy(?:[_-].*)?|placeholder(?:[_-].*)?|"
    r"changeme(?:[_-].*)?|change_me(?:[_-].*)?|your[_-].*|test[_-]?only(?:[_-].*)?|"
    r"\*+|x+|0+|1+)$"
)


def _placeholder(value: str) -> bool:
    # Do not silently exclude arbitrary secrets merely because they *contain*
    # a substring like 'sample' or 'example' inside a legitimate credential.
    return bool(PLACEHOLDER.fullmatch(value.strip())) or len(set(value)) <= 2


def _inspect_text(blob: bytes, target: str, out: ScanResult, cancel: threading.Event | None):
    if b"\0" in blob[:4096]:
        out.skipped += 1
        return
    try:
        content = blob.decode("utf-8-sig")
    except UnicodeDecodeError:
        content = blob.decode("cp932", errors="replace")
    for n, line in enumerate(content.splitlines(), start=1):
        if is_cancelled(cancel):
            return
        if len(line) > 100_000:
            out.skipped += 1
            continue
        # Never retain the match value, line body, or any snippet in a Finding.
        for rule, severity, pattern in PATTERNS:
            match = pattern.search(line)
            if match:
                # High-confidence known formats are not exempted by placeholder words.
                out.add(Finding(severity, rule, target, "資格情報の形式を検出（秘密の値は非表示）。", ADVICE, n))
        match = ASSIGNMENT.search(line)
        if match and not _placeholder(match.group(1)):
            out.add(Finding("中", "機密値を含む設定", target,
                            "機密情報と思われる代入を検出（秘密の値は非表示）。", ADVICE, n))


def _inspect_zip(path: Path, out: ScanResult, cancel: threading.Event | None):
    preflight = zip_preflight(path, max_entries=MAX_ZIP_ENTRIES)
    if preflight:
        out.skipped += 1
        out.truncated = True
        out.errors.append(f"{safe_name(path.name)}: {preflight}")
        return
    total = 0
    try:
        with zipfile.ZipFile(path, "r") as archive:
            infos = archive.infolist()
            if len(infos) > MAX_ZIP_ENTRIES:
                out.skipped += 1
                out.truncated = True
                out.errors.append(f"{safe_name(path.name)}: ZIP内部の項目数が上限を超えています。")
                return
            for info in infos:
                if is_cancelled(cancel):
                    return
                if info.is_dir():
                    continue
                original = info.filename.replace("\\", "/")
                name = safe_name(original)
                member = PurePosixPath(original)
                if member.is_absolute() or ".." in member.parts or ":" in original:
                    out.skipped += 1
                    out.add(Finding("中", "ZIP内の危険なパス", safe_name(path.name),
                                    "展開時にディレクトリの外へアクセスする恐れがある名前です。",
                                    "信頼できないZIPは展開しないでください。"))
                    continue
                if info.flag_bits & 1:
                    out.skipped += 1
                    out.add(Finding("情報", "暗号化ZIP項目", safe_name(path.name),
                                    "暗号化されているため、この項目は検査できません。"))
                    continue
                if info.file_size > MAX_MEMBER or total + info.file_size > MAX_ZIP_TOTAL:
                    out.skipped += 1
                    continue
                if info.file_size > 1024 * 1024 and info.file_size > max(1, info.compress_size) * 100:
                    out.skipped += 1
                    continue
                inner = Path(original)
                if inner.suffix.lower() not in TEXT_EXTENSIONS and not inner.name.startswith(".env"):
                    out.skipped += 1
                    continue
                try:
                    with archive.open(info, "r") as fp:
                        blob = fp.read(MAX_MEMBER + 1)
                    if len(blob) > MAX_MEMBER:
                        out.skipped += 1
                        continue
                    total += len(blob)
                    out.scanned += 1
                    _inspect_text(blob, f"{safe_name(path.name)} / {name}", out, cancel)
                except (OSError, RuntimeError, ValueError, EOFError, zipfile.BadZipFile):
                    out.skipped += 1
                    out.errors.append(f"{safe_name(path.name)}: ZIP内の項目を読み取れません。")
    except (OSError, RuntimeError, ValueError, EOFError, zipfile.BadZipFile):
        out.errors.append(f"{safe_name(path.name)}: ZIPを解析できません。")


def scan(paths, progress=None, cancel: threading.Event | None = None) -> ScanResult:
    result = ScanResult(APP_NAME)
    found = False
    for index, path in enumerate(walk_files(validate_paths(paths, result), limit=3001, cancel=cancel)):
        if index >= 3000:
            result.truncated = True
            result.errors.append("走査対象の件数が上限(3000)を超えたため途中で停止しました。")
            break
        if is_cancelled(cancel):
            break
        found = True
        if progress:
            progress(safe_name(path.name))
        try:
            size = path.stat().st_size
            ext = path.suffix.lower()
            if ext in (".zip", ".jar"):
                if size > 256 * 1024 * 1024:
                    result.skipped += 1
                    continue
                result.scanned += 1
                _inspect_zip(path, result, cancel)
            elif ext in TEXT_EXTENSIONS or path.name.startswith(".env") or path.name in ("Dockerfile", "Makefile"):
                if size > MAX_TEXT:
                    result.skipped += 1
                    continue
                with path.open("rb") as fp:
                    blob = fp.read(MAX_TEXT + 1)
                if len(blob) > MAX_TEXT:
                    result.skipped += 1
                    continue
                result.scanned += 1
                _inspect_text(blob, safe_name(path.name), result, cancel)
            else:
                result.skipped += 1
        except (OSError, PermissionError, ValueError):
            result.errors.append(f"{safe_name(path.name)}: 読み取りに失敗しました。")
    if not found:
        result.errors.append("対象ファイルがありません。シンボリックリンクは読み取りません。")
    result.metrics = {
        "target_limit": 3000, "text_limit_mib": 16, "zip_member_limit_mib": 8,
        "nested_archives": "非対応", "cancelled": is_cancelled(cancel),
    }
    return result
