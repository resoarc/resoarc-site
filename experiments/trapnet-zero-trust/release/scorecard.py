#!/usr/bin/env python3
"""TrapNet release gate accounting with immutable meaning for formal PASS.

Standalone Python stdlib. No network, GitHub credentials, production writes,
status auto-promotion or fabricated independent human approvals.
"""
import argparse
import hashlib
import re
import json
from pathlib import Path

ALL_IDS = {f"{group}{i}" for group in "ABCDE" for i in range(1, 5)}
STATES = {"PASS", "PARTIAL", "TODO"}
ROUTES = {"none", "internal", "mixed", "hardware", "external"}
MANIFEST = Path(__file__).with_name("gate_register_v058.json")

def validate(document):
    if document.get("schema") != "trapnet.release-gates.v058":
        raise ValueError("unknown gate register schema")
    entries = document.get("gates")
    if not isinstance(entries, list) or len(entries) != 20:
        raise ValueError("exactly 20 gate records required")
    ids = [entry["id"] for entry in entries]
    if len(ids) != len(set(ids)) or set(ids) != ALL_IDS:
        raise ValueError("gate ID duplication, omission or unexpected addition")
    by_id = {entry["id"]: entry for entry in entries}
    for gate in entries:
        identifier = gate["id"]
        functional = gate.get("technical_status")
        formal = gate.get("release_status")
        if functional not in STATES or formal not in STATES:
            raise ValueError(f"{identifier}: illegal status")
        if gate.get("route") not in ROUTES:
            raise ValueError(f"{identifier}: invalid owner route")
        if not isinstance(gate.get("own_open"), list):
            raise ValueError(f"{identifier}: missing acceptance checklist")
        if "release_open" in gate and (
            not isinstance(gate["release_open"], list)
            or any(not isinstance(v,str) or not v for v in gate["release_open"])
        ):
            raise ValueError(f"{identifier}: invalid release acceptance checklist")
        if not isinstance(gate.get("dependencies"), list):
            raise ValueError(f"{identifier}: missing dependencies")
        if any(dep not in ALL_IDS or dep == identifier for dep in gate["dependencies"]):
            raise ValueError(f"{identifier}: invalid dependency")
        if functional == "PASS" and gate["own_open"]:
            raise ValueError(f"{identifier}: claimed technical PASS with own work incomplete")
        if functional == "PASS":
            if not gate.get("evidence_summary"):
                raise ValueError(f"{identifier}: missing technical evidence")
            proofs = gate.get("technical_evidence")
            if not isinstance(proofs, list) or not proofs:
                raise ValueError(f"{identifier}: technical PASS lacks pinned evidence")
            for proof in proofs:
                kind = proof.get("kind")
                uri = proof.get("uri", "")
                if kind not in {"local_json", "ci_artifact", "ci_regression"} or not uri:
                    raise ValueError(f"{identifier}: invalid technical proof reference")
                sha = proof.get("sha256")
                if kind in {"local_json", "ci_artifact"} and not (
                    isinstance(sha, str) and re.fullmatch(r"[0-9a-f]{64}", sha)
                ):
                    raise ValueError(f"{identifier}: unpinned technical proof")
                if kind in {"ci_artifact", "ci_regression"} and not (
                    uri.startswith("https://github.com/resoarc/resoarc-site/actions/runs/")
                    and re.fullmatch(r"[0-9a-f]{40}", proof.get("commit", ""))
                ):
                    raise ValueError(f"{identifier}: wrong CI origin or missing commit SHA")
        if formal == "PASS" and functional != "PASS":
            raise ValueError(f"{identifier}: formal PASS without technical PASS")
        if formal == "PASS" and gate.get("release_open"):
            raise ValueError(f"{identifier}: release-specific acceptance outstanding")
        if formal == "PASS":
            # Legacy A1 status was already accepted as a limited lab
            # component. All *new* formal approvals require a separate
            # human review record. This is a structural gate only and does
            # not authenticate the human or the signature.
            if identifier != "A1":
                review = gate.get("review_approval")
                if not isinstance(review, dict):
                    raise ValueError(f"{identifier}: independent review record missing")
                for field in ("reviewer", "verified_commit", "evidence_uri", "signed_decision_uri"):
                    if not review.get(field):
                        raise ValueError(f"{identifier}: incomplete independent review record")
                # The cross-gate dependencies are GLOBAL public-release
                # blockers, not cyclic prerequisites for each individual
                # gate's review. An independently accepted A2 can close
                # before D3/E3, but publication still remains HOLD until ALL
                # formal gates have been separately completed.
                if gate["own_open"]:
                    raise ValueError(f"{identifier}: formal PASS with own acceptance outstanding")
    if document.get("release_authorization") == "READY":
        if any(entry["release_status"] != "PASS" for entry in entries):
            raise ValueError("release READY cannot bypass any incomplete gate")
        if any(by_id[id]["release_status"] != "PASS" for id in ("D4", "E3")):
            raise ValueError("release READY without independent operators and audit")
    elif document.get("release_authorization") != "HOLD":
        raise ValueError("invalid release authorization")
    return True

def verify_local_files(document, evidence_dir):
    """Rehash local evidence without publishing local absolute paths."""
    if evidence_dir is None:
        return ["local evidence directory required"]
    evidence_dir = Path(evidence_dir)
    failures = []
    for gate in document["gates"]:
        for proof in gate.get("technical_evidence", []):
            if proof.get("kind") != "local_json":
                continue
            name = proof["uri"]
            if Path(name).name != name or name in {".", ".."}:
                failures.append(f"{gate['id']}: unsafe local evidence name")
                continue
            path = evidence_dir / name
            if not path.is_file():
                failures.append(f"{gate['id']}: local artifact missing")
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != proof["sha256"]:
                failures.append(f"{gate['id']}: local artifact digest mismatch")
    return failures

def counts(gates, column):
    return {key: sum(row[column] == key for row in gates) for key in ("PASS", "PARTIAL", "TODO")}

def report(document):
    validate(document)
    gates = document["gates"]
    tech = counts(gates, "technical_status")
    formal = counts(gates, "release_status")
    lines = [
        "# TrapNet 二段階リリースゲート（自動検証）",
        "",
        f"基準日：{document['as_of']}。判定：**{document['release_authorization']}**。",
        "",
        "## 実測された進捗",
        "",
        "| 判定軸 | PASS | PARTIAL | TODO |",
        "|---|---:|---:|---:|",
        f"| ゲート固有の技術受入 | {tech['PASS']} | {tech['PARTIAL']} | {tech['TODO']} |",
        f"| 従来の正式リリースゲート | {formal['PASS']} | {formal['PARTIAL']} | {formal['TODO']} |",
        "",
        "**重要：技術PASSは正式リリース承認ではありません。** 自動化は第三者の実在や署名の真偽まで認証しません。",
        "",
        "## 技術受入PASSの範囲",
    ]
    for gate in gates:
        if gate["technical_status"] == "PASS":
            lines.append(f"- **{gate['id']} {gate['title']}**：{gate['evidence_summary']}。技術範囲：{gate['scope']}。正式：{gate['release_status']}。")
    lines += ["", "## 当面の優先3件"]
    for gate in sorted([g for g in gates if "priority" in g], key=lambda item: item["priority"])[:3]:
        blocker = "、".join(gate["own_open"]) if gate["own_open"] else "技術的な未実施なし。独立確認待ち"
        lines.append(f"- **{gate['priority']}. {gate['id']} {gate['title']}**：{blocker}。実施経路：{gate['route']}。関連ゲート：{', '.join(gate['dependencies']) or 'なし'}。")
    lines += [
        "",
        "## 判定の責任境界",
        "- **A2**：現存する実Cowrieログの欠落・途中破損・完全重複・意味的重複と、署名付き欠測通知のHUB記録までは技術的に完了。過去の観測行が自然に削除された場合の検知は含めない。",
        "- **D3**：独立保管された履歴の完全性、別管理主体のWitness鍵、実停電・断線からの復旧は未達。",
        "- **E3**：実在する第三者の監査と重大指摘の解消は未達。自動CI成功で代用しない。",
        "- **D4**：複数独立運用者の参加・撤退・失効訓練は未達。",
        "- **公開判定**：D3・D4・E3を含むすべての個別正式受入が揃うまでHOLD。",
        "",
        "## 全ゲートの進捗",
        "",
        "| ID | ゲート | 技術 | 正式 | 次の決定を妨げる項目 |",
        "|---|---|---|---|---|",
    ]
    for g in gates:
        pending = g.get("release_open", []) if g["technical_status"] == "PASS" else g["own_open"]
        own = "、".join(pending) if pending else ("依存：" + "、".join(g["dependencies"]) if g["dependencies"] else "なし")
        lines.append(f"| {g['id']} | {g['title']} | {g['technical_status']} | {g['release_status']} | {own} |")
    return "\n".join(lines) + "\n"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--register",type=Path,default=MANIFEST)
    parser.add_argument("--output",type=Path)
    parser.add_argument("--verify-local",action="store_true",
                        help="rehash local evidence; does not contact CI or sign off")
    parser.add_argument("--evidence-dir",type=Path,
                        help="private directory for local evidence, never persisted in public register")
    args = parser.parse_args()
    data = json.loads(args.register.read_text(encoding="utf-8"))
    result = report(data)
    if args.verify_local:
        failures=verify_local_files(data,args.evidence_dir)
        if failures:
            raise SystemExit("; ".join(failures))
    if args.output:
        args.output.write_text(result,encoding="utf-8")
    else:
        print(result,end="")
if __name__ == "__main__":
    main()
