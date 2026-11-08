"""Log Lantern: privacy-preserving offline access-log analysis."""
from __future__ import annotations

import re
import threading
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

from common import Finding, ScanResult, is_cancelled, mask_ip, redact_url, safe_name, validate_paths, walk_files

APP_NAME = "ResoArc Log Lantern"
MAX_FILE_SIZE = 128 * 1024 * 1024
MAX_LINES = 1_000_000
# Bounded cardinalities prevent a crafted log with unique hosts, timestamps,
# or URLs from consuming unbounded memory. Limit-triggered scans are incomplete.
MAX_UNIQUE_ENDPOINTS = 20_000
MAX_UNIQUE_TIME_BUCKETS = 50_000
MAX_UNIQUE_SOURCES_PER_MINUTE = 50_000
MAX_UNIQUE_SUSPICIOUS_SOURCES = 20_000
ACCESS = re.compile(
    r'^(?P<ip>\S+)\s+\S+\s+\S+\s+\[(?P<when>[^\]]+)\]\s+"(?P<method>[A-Z]+)\s+(?P<path>\S+)(?:\s+HTTP/[\d.]+)?"\s+(?P<status>\d{3})\s+(?P<bytes>\S+)'
)
SUSPICIOUS = (
    ("設定・秘密ファイルへの探索", re.compile(r"(?i)(?:^|/)\.(?:env(?:[./-]|$)|git(?:/|$)|aws(?:/|$)|ssh(?:/|$))|(?:^|/)(?:config\.php|phpinfo\.php|id_rsa)(?:$|/)")),
    ("ディレクトリ移動の試行", re.compile(r"(?i)(?:\.\./|\.\.\\|%2e%2e|%252e%252e)")),
    ("SQL注入を示唆する入力", re.compile(r"(?i)(?:union\s+(?:all\s+)?select|or\s+1\s*=\s*1|information_schema|sleep\s*\(|benchmark\s*\()")),
    ("既知管理画面への探索", re.compile(r"(?i)(?:/wp-admin|/wp-login\.php|/xmlrpc\.php|/actuator/(?:env|health)|/server-status)")),
)
ACCEPT_EXTENSIONS = {".log", ".txt", ""}


def _parse_apache(line: str):
    m = ACCESS.match(line)
    if not m:
        return None
    d = m.groupdict()
    try:
        when = datetime.strptime(d["when"], "%d/%b/%Y:%H:%M:%S %z")
    except ValueError:
        when = None
    return d["ip"], d["method"], d["path"], int(d["status"]), when


def _parse_iis(line: str, fields: list[str]):
    cols = line.split()
    if len(cols) != len(fields):
        return None
    d = dict(zip(fields, cols))
    ip = d.get("c-ip") or d.get("s-ip")
    if not ip:
        return None
    try:
        status = int(d.get("sc-status", "0"))
    except ValueError:
        return None
    when = None
    if d.get("date") and d.get("time"):
        try:
            when = datetime.fromisoformat(d["date"] + "T" + d["time"]).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    # IIS W3C stores URL queries in a separate column; include that only for
    # in-memory classification. redact_url() drops the query before reporting.
    resource = d.get("cs-uri-stem", "/")
    query = d.get("cs-uri-query", "-")
    if query not in ("", "-"):
        resource += "?" + query
    return ip, d.get("cs-method", "GET"), resource, status, when


def scan(paths, progress=None, cancel: threading.Event | None = None) -> ScanResult:
    out = ScanResult(APP_NAME)
    statuses, endpoints, suspicious, minutes, failed_auth, time_chart = (
        Counter(), Counter(), Counter(), Counter(), Counter(), Counter()
    )
    not_found: dict[tuple, set] = defaultdict(set)
    # Never group sources by anonymized IP prefix: different IPs can share one /16.
    # Keep raw addresses only in transient memory; expose an anonymous scan-local label.
    source_labels: dict[str, str] = {}
    def label_source(address: str) -> str:
        if address not in source_labels:
            source_labels[address] = mask_ip(address) + f" (接続元{len(source_labels) + 1})"
        return source_labels[address]
    malformed = valid = 0
    limited: set[str] = set()
    def cap_add(counter: Counter, key, limit: int, description: str):
        if key in counter:
            counter[key] += 1
        elif len(counter) < limit:
            counter[key] = 1
        else:
            limited.add(description)
    for index, path in enumerate(walk_files(validate_paths(paths, out), limit=51, cancel=cancel)):
        if index >= 50:
            out.truncated = True
            out.errors.append("走査対象の件数が上限(50)を超えたため途中で停止しました。")
            break
        if is_cancelled(cancel):
            break
        if path.suffix.lower() not in ACCEPT_EXTENSIONS:
            out.skipped += 1
            continue
        if progress:
            progress(safe_name(path.name))
        try:
            if path.stat().st_size > MAX_FILE_SIZE:
                out.skipped += 1
                out.errors.append(f"{safe_name(path.name)}: 128 MiBを超えるため除外しました。")
                continue
            iis_fields: list[str] = []
            with path.open("r", encoding="utf-8-sig", errors="replace") as fp:
                for index, raw in enumerate(fp):
                    if is_cancelled(cancel):
                        break
                    if index >= MAX_LINES:
                        out.errors.append(f"{safe_name(path.name)}: 100万行に達したため途中で終了しました。")
                        out.truncated = True
                        break
                    if len(raw) > 32768:
                        malformed += 1
                        continue
                    line = raw.strip()
                    if not line:
                        continue
                    if line.startswith("#Fields:"):
                        iis_fields = line.split()[1:]
                        continue
                    if line.startswith("#"):
                        continue
                    record = _parse_iis(line, iis_fields) if iis_fields else _parse_apache(line)
                    if record is None:
                        malformed += 1
                        continue
                    address, method, raw_path, status, when = record
                    valid += 1
                    statuses[str(status)] += 1
                    safe_path = redact_url(raw_path)
                    cap_add(endpoints, safe_path, MAX_UNIQUE_ENDPOINTS, "URL種類")
                    if when is not None:
                        minute = when.strftime("%Y-%m-%d %H:%M")
                        key = (address, minute)
                        cap_add(minutes, key, MAX_UNIQUE_SOURCES_PER_MINUTE, "接続元・分単位")
                        if key in minutes:
                            if status in (401, 403):
                                failed_auth[key] += 1
                            # Only 12 distinct paths are necessary to trigger
                            # the alert. Stop retaining new paths after that.
                            if status == 404 and len(not_found[key]) < 12:
                                not_found[key].add(safe_path)
                        cap_add(time_chart, when.strftime("%Y-%m-%d %H:00"),
                                MAX_UNIQUE_TIME_BUCKETS, "時間単位")
                    # Raw query is kept in memory only for classification, not output.
                    test_text = raw_path[:512]
                    # Inspect two decoding layers for common double-encoded probes.
                    for _ in range(2):
                        decoded = unquote(test_text, errors="replace")
                        if decoded == test_text:
                            break
                        test_text = decoded
                    for label, expression in SUSPICIOUS:
                        if expression.search(test_text):
                            cap_add(suspicious, (label, address),
                                    MAX_UNIQUE_SUSPICIOUS_SOURCES, "攻撃兆候・接続元")
            out.scanned += 1
        except (OSError, ValueError, UnicodeError):
            out.errors.append(f"{safe_name(path.name)}: ログを読み取れませんでした。")
    for (label, address), count in suspicious.most_common(100):
        out.add(Finding("中", label, label_source(address),
                        f"該当 {count} 件。攻撃成功や不正アクセスの断定はできません。",
                        "HTTP応答コードや同時刻のサーバーイベントを照合してください。"))
    for (address, minute), count in minutes.items():
        masked = label_source(address)
        if count >= 80:
            out.add(Finding("中", "短時間のアクセス集中", masked,
                            f"{minute} に {count}件/分（基準80件）。",
                            "正規クローラー・監視サービス・負荷試験も確認してください。"))
        if failed_auth[(address, minute)] >= 12:
            out.add(Finding("中", "認証エラーの集中", masked,
                            f"{minute} に401/403が {failed_auth[(address, minute)]} 件（基準12件）。",
                            "ログイン失敗やアクセス制御の設定と照合してください。"))
        if len(not_found[(address, minute)]) >= 12:
            out.add(Finding("低", "404の多種類アクセス", masked,
                            f"{minute} に異なる404 URLが {len(not_found[(address, minute)])} 種類（基準12種類）。",
                            "リンク切れ・クローラーなどの正常な原因も確認してください。"))
    if limited:
        out.truncated = True
        out.errors.append("大量の異なる値により集計上限に達しました（" + "・".join(sorted(limited)) +
                          "）。一部の集計と検出結果が省略されています。入力を分割してください。")
    if valid == 0:
        out.errors.append("対応するログがありません。Apache/Nginx combined、IIS W3C形式を指定してください。")
    if malformed:
        out.add(Finding("情報", "解析できなかった行", "入力ログ",
                        f"{malformed} 行は非対応形式または長すぎるため除外しました。",
                        "ログ形式と入力文字コードを確認してください。"))
    out.metrics = {
        "requests": valid, "unparsed_lines": malformed,
        "status_codes": dict(statuses.most_common(20)),
        "popular_paths": [{"path": name, "requests": n} for name, n in endpoints.most_common(15)],
        "hourly": [{"hour": hour, "requests": n} for hour, n in sorted(time_chart.items())[:500]],
        "thresholds": {"requests_per_min": 80, "auth_errors_per_min": 12, "unique_404_per_min": 12},
        "privacy": "IP匿名化、クエリ文字列と秘密を含むURLパスの匿名化", "cancelled": is_cancelled(cancel),
        "cardinality_limit_hit": bool(limited),
    }
    return out
