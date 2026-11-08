"""Shared primitives for ResoArc's three read-only, offline security tools."""
from __future__ import annotations

import csv
import hashlib
import ipaddress
import json
import os
import re
import tempfile
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

VERSION = "0.3.0-rc4"
MAX_FINDINGS = 3000
SKIP_DIRS = {".git", ".svn", ".hg", "node_modules", ".venv", "venv", "__pycache__", ".next", "dist", "build"}
SEVERITY_ORDER = {"高": 0, "中": 1, "低": 2, "情報": 3}
Progress = Callable[[str], None]


@dataclass(frozen=True)
class Finding:
    severity: str
    rule: str
    target: str
    detail: str
    advice: str = ""
    line: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ScanResult:
    app: str
    scanned: int = 0
    skipped: int = 0
    findings: list[Finding] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    truncated: bool = False

    def add(self, finding: Finding):
        if len(self.findings) < MAX_FINDINGS:
            self.findings.append(finding)
        else:
            self.truncated = True

    def export_data(self) -> dict:
        return {
            "tool": self.app,
            "version": VERSION,
            "exported_at_utc": datetime.now(timezone.utc).isoformat(),
            "privacy": "インターネット送信なし。秘密の値・IPアドレス原文・URLのクエリ文字列は出力しません。",
            "scanned": self.scanned,
            "skipped": self.skipped,
            "metrics": self.metrics,
            "findings": [f.to_dict() for f in self.findings],
            "errors": self.errors,
            "truncated": self.truncated,
            "note": "ヒューリスティックな静的点検です。検出なしは安全を保証しません。",
        }


def is_cancelled(cancel: threading.Event | None) -> bool:
    return cancel is not None and cancel.is_set()


def safe_name(name: str) -> str:
    name = str(name)
    name = re.sub(r"(?i)(?:gh[pousr]_[A-Za-z0-9_]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk_live_[A-Za-z0-9]{16,})", "[TOKEN]", name)
    # Filenames may contain short key-value tokens (for example backup_token=xxxxx.json).
    name = re.sub(r"(?i)(?<![a-z0-9])(?:token|password|passwd|apikey|api_key|secret|auth)\s*[:=]\s*[^/\\\s&;]+", "[CREDENTIAL]", name)
    for codepoint in ("\u202a", "\u202b", "\u202c", "\u202d", "\u202e", "\u2066", "\u2067", "\u2068", "\u2069"):
        name = name.replace(codepoint, "[BIDI]")
    # Filenames are untrusted and may themselves include credentials or e-mail addresses.
    name = re.sub(r"(?i)([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})", "[EMAIL]", name)
    name = re.sub(r"(?i)(?:AKIA|ASIA)[A-Z0-9]{16}|AIza[0-9a-z_-]{35}", "[TOKEN]", name)
    name = re.sub(r"(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{32,}(?![A-Za-z0-9_-])", "[LONG_ID]", name)
    return re.sub(r"[\x00-\x1f\x7f]", "", name)[:200]


def walk_files(paths: Iterable[str | Path], *, limit: int, cancel: threading.Event | None = None):
    """No symlink traversal, hidden build trees or duplicate hard links."""
    seen: set[object] = set()
    emitted = 0
    for raw in paths:
        if is_cancelled(cancel):
            return
        p = Path(raw)
        if p.is_symlink():
            continue
        if p.is_file():
            candidates = iter((p,))
        elif p.is_dir():
            def _inside():
                for dirname, dirs, filenames in os.walk(p, topdown=True, followlinks=False):
                    dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not (Path(dirname) / d).is_symlink()]
                    for filename in filenames:
                        yield Path(dirname) / filename
            candidates = _inside()
        else:
            continue
        for candidate in candidates:
            if is_cancelled(cancel):
                return
            try:
                if candidate.is_symlink() or not candidate.is_file():
                    continue
                st = candidate.stat()
                identity = (st.st_dev, st.st_ino) if st.st_ino else str(candidate.resolve())
                if identity in seen:
                    continue
                seen.add(identity)
            except (OSError, PermissionError):
                continue
            yield candidate
            emitted += 1
            if emitted >= limit:
                return



def validate_paths(paths: Iterable[str | Path], result: ScanResult) -> list[Path]:
    """Make explicitly requested missing/symlink targets visible as incomplete."""
    valid: list[Path] = []
    for raw in paths:
        try:
            path = Path(raw)
            if path.is_symlink():
                result.skipped += 1
                result.errors.append(f"{safe_name(path.name)}: リンク先の走査は行いません。")
            elif not path.exists():
                result.skipped += 1
                result.errors.append(f"{safe_name(path.name)}: 指定した対象が見つかりません。")
            elif not (path.is_file() or path.is_dir()):
                result.skipped += 1
                result.errors.append(f"{safe_name(path.name)}: 通常のファイル・フォルダではありません。")
            else:
                valid.append(path)
        except (OSError, ValueError, TypeError):
            result.skipped += 1
            result.errors.append("指定されたパスを確認できません。")
    return valid

def sha256(path: Path, cancel: threading.Event | None = None) -> str | None:
    digest = hashlib.sha256()
    with path.open("rb") as fp:
        while block := fp.read(1024 * 1024):
            if is_cancelled(cancel):
                return None
            digest.update(block)
    return digest.hexdigest()


def mask_ip(address: str) -> str:
    """Mask valid IPs and hash unparseable host strings."""
    try:
        obj = ipaddress.ip_address(address)
        if obj.version == 4:
            parts = str(obj).split(".")
            return ".".join(parts[:2]) + ".x.x"
        return ":".join(obj.exploded.split(":")[:2]) + ":****"
    except ValueError:
        return "host-" + hashlib.sha256(address.encode("utf-8", "replace")).hexdigest()[:10]


def redact_url(value: str) -> str:
    """Return a useful path shape, never raw query, userinfo, or opaque path identifiers.

    Logs can contain password reset tokens *in the URL path*, not just the query.
    Normalize percent encodings for redaction and replace likely identifiers while
    preserving static route segments for useful frequency analysis.
    """
    from urllib.parse import unquote, urlsplit
    value = str(value)[:4096]
    try:
        parsed = urlsplit(value)
        path = parsed.path or "/"
    except ValueError:
        path = "/"
    # Two decoding rounds cover common percent-encoded and double-encoded identifiers.
    for _ in range(2):
        decoded = unquote(path, errors="replace")
        if decoded == path:
            break
        path = decoded
    path = path.split("?", 1)[0].split("#", 1)[0]
    # Known password-reset, invitation, token, and verification routes may put
    # *short* opaque secrets into the next path segment. A length-only heuristic
    # misses these and can leak usable one-time tokens into exported reports.
    route_secret = re.compile(
        r"(?i)^(?:reset|password[-_]?reset|reset[-_]?password|set[-_]?password|register|registration|"
        r"verify|verification|invite|invitation|activate|activation|confirm|"
        r"magic[-_]?link|magic|unsubscribe|token|otp|one[-_]?time[-_]?code)$"
    )
    inline_secret = re.compile(
        r"(?i)(?:^|[;,&])(?:[\w-]*?(?:token|secret|password|passwd|api[_-]?key|"
        r"access[_-]?key|session(?:id)?|auth|signature|jwt|otp|code))\s*[:=]"
    )
    # Profile and customer routes frequently contain personal identifiers in
    # otherwise innocent-looking short path segments (e.g. /users/alice).
    # Favor privacy over keeping every path label in exported statistics.
    personal_route = re.compile(r"(?i)^(?:users|profiles|members|customers|people)$")
    parts = []
    redact_next = False
    for segment in path.split("/"):
        if (not segment or segment in (".", "..")):
            parts.append(segment)
            # The empty segment preceding a value must not clear the guard.
            continue
        if redact_next:
            parts.append("[REDACTED]")
            redact_next = False
            continue
        if inline_secret.search(segment):
            parts.append("[REDACTED]")
            continue
        if route_secret.fullmatch(segment) or personal_route.fullmatch(segment):
            parts.append(segment)
            redact_next = True
            continue
        if ("@" in segment or len(segment) > 80 or
            re.fullmatch(r"(?i)[a-f0-9]{24,}", segment) or
            re.fullmatch(r"[0-9]{7,}", segment) or
            (len(segment) >= 20 and re.fullmatch(r"[A-Za-z0-9_-]+", segment) and
             any(ch.isdigit() for ch in segment) and any(ch.isalpha() for ch in segment)) or
            re.fullmatch(r"(?i)[a-f0-9]{8}-[a-f0-9-]{27,}", segment) or
            re.search(r"(?i)(?:gh[pousr]_|github_pat_|sk_live_|AKIA|ASIA|AIza|eyJ[A-Za-z0-9_-]{10,}\.)", segment)):
            parts.append("[REDACTED]")
            continue
        segment = re.sub(r"[\x00-\x1f\x7f]", "", segment)
        parts.append(segment)
    return "/".join(parts)[:180] or "/"



def zip_preflight(path: str | Path, *, max_entries: int, max_directory_bytes: int = 16 * 1024 * 1024) -> str | None:
    """Conservatively reject oversized ZIP central directories *before* ZipFile.

    Python zipfile eagerly parses the central directory. A crafted archive with
    huge numbers of entries can exhaust memory before our later entry limit is
    checked. Standard ZIP EOCD has a small bounded tail, so inspect it first.
    This is not a complete ZIP validator; normal ZipFile parsing still follows.
    """
    import struct
    path = Path(path)
    try:
        with path.open("rb") as stream:
            size = stream.seek(0, os.SEEK_END)
            stream.seek(max(0, size - 65_557))
            tail = stream.read(65_557)
        # ZIP comments can themselves contain EOCD-looking bytes. Only accept
        # the terminal record whose declared comment actually reaches the end.
        index = tail.rfind(b"PK\x05\x06")
        record = None
        while index >= 0:
            if len(tail) - index >= 22:
                candidate = struct.unpack_from("<IHHHHIIH", tail, index)
                if index + 22 + candidate[-1] == len(tail):
                    record = candidate
                    break
            index = tail.rfind(b"PK\x05\x06", 0, index)
        if record is None:
            return None  # Existing ZIP parser will report corruption.
        _, disk, start_disk, disk_count, total, central_size, offset, comment_len = record
        if (disk != 0 or start_disk != 0 or total == 65535 or
            central_size == 0xFFFFFFFF or offset == 0xFFFFFFFF):
            return "複数ディスク・ZIP64形式のディレクトリは安全な事前検査の対象外です。"
        if total > max_entries or disk_count > max_entries:
            return f"ZIPの項目数が上限({max_entries})を超えています。"
        if central_size > max_directory_bytes:
            return f"ZIPの中央ディレクトリが上限({max_directory_bytes // (1024*1024)} MiB)を超えています。"
        return None
    except (OSError, ValueError, OverflowError):
        return "ZIPの中央ディレクトリを事前検査できませんでした。"


def output_overwrites_input(output: str | Path, paths: Iterable[str | Path]) -> bool:
    """Reject direct file overwrite even when called from the scan CLI or GUI."""
    try:
        dest = Path(output).resolve(strict=False)
        for raw in paths:
            p = Path(raw)
            if p.is_file():
                if p.resolve(strict=False) == dest:
                    return True
                # Hard links are different paths for the same underlying file.
                if dest.exists() and os.path.samefile(dest, p):
                    return True
            if p.is_dir() and dest.exists():
                # A report must not replace an existing file within an input tree.
                # New reports in selected directories are allowed.
                try:
                    dest.relative_to(p.resolve(strict=False))
                    return True
                except ValueError:
                    pass
    except (OSError, ValueError, TypeError):
        # Let regular export error handling report invalid output paths.
        return False
    return False

def atomic_write(path: str | Path, content: str, *, encoding="utf-8"):
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".resoarc-", suffix=".tmp", dir=destination.parent)
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="") as out:
            out.write(content)
        os.replace(temp, destination)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def export_json(path: str | Path, result: ScanResult):
    atomic_write(path, json.dumps(result.export_data(), ensure_ascii=False, indent=2))


def export_csv(path: str | Path, result: ScanResult):
    """RFC4180-ish CSV plus spreadsheet formula injection hardening."""
    import io
    def safe(value):
        v = str(value if value is not None else "")
        return "'" + v if v.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else v
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(["重要度", "検出種別", "対象", "内容", "対策", "行番号"])
    for f in result.findings:
        writer.writerow([safe(v) for v in (f.severity, f.rule, f.target, f.detail, f.advice, f.line)])
    # A 'clean' finding table must not hide incomplete or failed examinations.
    if result.truncated or result.metrics.get("cancelled"):
        writer.writerow(["情報", "検査は未完了", "全体", "検査が中断または上限で途中終了しました。", "再検査してください。", ""])
    if result.skipped:
        writer.writerow(["情報", "未検査の項目あり", "全体", safe(f"{result.skipped} 件は未検査です。"), "対象形式・サイズ制限を確認してください。", ""])
    if result.metrics.get("unparsed_lines", 0):
        writer.writerow(["情報", "解析不能なログ行", "入力ログ",
                         safe(f"{result.metrics['unparsed_lines']} 行を解析できませんでした。"),
                         "ログ形式を確認してください。", ""])
    for error in result.errors[:100]:
        writer.writerow(["情報", "解析上の制限・エラー", "全体", safe(error), "解析できなかった項目を確認してください。", ""])
    if len(result.errors) > 100:
        writer.writerow(["情報", "エラー一覧の省略", "全体", f"追加 {len(result.errors)-100} 件のエラーはCSV内で省略。", "JSON出力を参照してください。", ""])
    atomic_write(path, buffer.getvalue(), encoding="utf-8-sig")
