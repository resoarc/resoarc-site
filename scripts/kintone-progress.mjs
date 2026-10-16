#!/usr/bin/env node
// ResoArc kintone release portfolio: canonical JSON, deterministic Markdown, release checks.
// Run: node scripts/kintone-progress.mjs --check / --write / --summary
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { resolve, dirname } from 'node:path';
const repoRoot=resolve(dirname(fileURLToPath(import.meta.url)), '..');
const jsonFile=resolve(repoRoot,'docs/kintone-progress/tracker.json');
const mdFile=resolve(repoRoot,'docs/kintone-progress/README.md');
const validateTracker=function validateTracker(d) {
 const stages = ["source","unit","manifest","signature","tenant","desktop","mobile","negative","coexistence","publish"];
 const allowed = ["passed","failed","unverified","not_applicable"];
 if (d.schema_version!==1 || !Array.isArray(d.items)) throw Error("unknown inventory");
 if (d.items.length!==29 || d.items.filter(x=>x.group==="mini").length!==18 || d.items.filter(x=>x.group==="package").length!==11)throw Error("expected exactly 18 mini + 11 packages");
 if (new Set(d.items.map(x=>x.id)).size!==29)throw Error("duplicate ids");
 for(const x of d.items){
   for(const stage of stages) if(!allowed.includes(x.gates?.[stage])) throw Error(`unknown gate status ${x.id}:${stage}`);
   if(x.gates.unit==="passed" && !(Number.isInteger(x.unit_tests?.pass) && x.unit_tests?.fail===0 && x.unit_tests?.evidence))throw Error("unit pass without evidence: "+x.id);
   if(x.gates.manifest==="not_applicable" && !x.focus)throw Error("manifest N/A without rationale: "+x.id);
   const allReady=stages.every(g=>x.gates[g]==="passed" || (g==="manifest"&&x.gates[g]==="not_applicable"));
   if(x.release_decision==="approved"&&!allReady)throw Error("release approved with unverified gates: "+x.id);
   if(!["approved","hold"].includes(x.release_decision))throw Error("bad release decision: "+x.id);
 }
};
const renderTracker=function renderTracker(d){
 const fmt = s=>({passed:"合格",failed:"失敗",unverified:"未確認",not_applicable:"対象外"}[s]??"不明");
 const count=(g,s)=>d.items.filter(x=>x.gates[g]===s).length;
 const tests=d.items.reduce((n,x)=>n+(x.unit_tests?.pass||0),0);
 const released=d.items.filter(x=>x.release_decision==="approved").length;
 const ln=[
 "# ResoArc kintone 統合進捗管理",
 "",
 `更新基準日: ${d.as_of}　｜　原本: [tracker.json](./tracker.json)`,
 "",
 "> このファイルは tracker.json から生成したスナップショットです。編集はJSONに行い、`node scripts/kintone-progress.mjs --write` で再生成します。",
 "",
 "## 全体サマリー",
 "",
 "| 管理項目 | 結果 |",
 "|---|---:|",
 `| 管理対象 | **${d.items.length}件（追加18機能 + 既存11パッケージ）** |`,
 `| 製品別単体テスト合格 | **${count("unit","passed")}/29件、計${tests}テスト成功・0失敗** |`,
 `| manifest 静的検査合格 | **${count("manifest","passed")}/29件**（対象外${count("manifest","not_applicable")}件、他は未確認） |`,
 `| 独立したZIP署名検証 | ${count("signature","passed")}/29件 |`,
 `| kintoneテスト環境E2E | ${count("tenant","passed")}/29件 |`,
 `| 今回の統合基準で正式リリース承認 | **${released}/29件** |`,
 "",
 "**注記:** 11パッケージは11種類の独立機能とは限りません。自動採番の安定版と次期β版は個別の配布・品質対象として2件計上。18件は別系列のミニプラグイン機能です。",
 "",
 "## 追加18機能",
 "",
 "| 優先 | ID | 機能 | 現行記録 | ソース | 単体 | 署名 | テナント | 承認 |",
 "|---:|---|---|---|---|---|---|---|---|"
 ];
 for(const x of d.items.filter(x=>x.group==="mini"))ln.push(`| ${x.priority} | \`${x.id}\` | ${x.name} | ${x.version} | ${fmt(x.gates.source)} | ${fmt(x.gates.unit)} | ${fmt(x.gates.signature)} | ${fmt(x.gates.tenant)} | ${x.release_decision==="approved"?"可":"保留"} |`);
 ln.push("","## 既存11パッケージ","","| ID | パッケージ | バージョン | 単体合格数 | 静的 | 署名 | テナント | 承認 |","|---|---|---|---:|---|---|---|---|");
 for(const x of d.items.filter(x=>x.group==="package"))ln.push(`| \`${x.id}\` | ${x.name} | ${x.version} | ${x.unit_tests?.pass??0} | ${fmt(x.gates.manifest)} | ${fmt(x.gates.signature)} | ${fmt(x.gates.tenant)} | ${x.release_decision==="approved"?"可":"保留"} |`);
 ln.push("","## 進め方と優先順位","",
 "1. **成果物照合**: 追加18機能の既存ソースとβ ZIPの所在、ハッシュ、署名を確認。発見できないものは未確認のまま扱い、重複開発を避ける。",
 "2. **既存11パッケージ**: 単体合格済みの成果物について再現ビルド、署名、隔離kintoneアプリで実機試験を実施。",
 "3. **ミニプラグイン**: 表の優先順をベースに、低難度から不足機能を拡充。16〜18はAPI/権限/ブラウザ依存を重点検証。",
 "4. **正式判定**: PC・モバイル・異常系・共存確認まで合格した成果物のみ昇格し、GitHubソース/配布物とサイトURLを検証。",
 "",
 "## 証拠の区分","",
 "- **実行済み**: 2026-10-17、Windowsローカルで11パッケージの単体テスト計187件合格（`Documents/AI-Work/MR-kintone-tests/reports/plugin-unit-tests-20261017.json`）。",
 "- **実行済み**: 9個のmanifestディレクトリで静的preflight合格。これはZIPの暗号学的署名検証を意味しません。",
 "- **過去のβ版リリースノートの記録**: 18機能の実装・署名済ZIP作成、モック31件＋ブラウザモック10件。ただし実物未照合かつ各機能別のテスト内訳がないため、個別合格に転記しません。",
 "- **未確認**: 実テナント導入、PC/モバイルE2E、独立署名検証、今回の統合判定での公式公開。",
 "",
 "## 完了条件","",
 "すべての製品で `source` → `unit` → `manifest`（理由付き対象外可）→ `signature` → `tenant` → `desktop` → `mobile` → `negative` → `coexistence` → `publish` が合格した場合だけ `release_decision` を `approved` に更新可能。プログラム検査が条件違反を拒否します。",
 "",
 "### 追跡元","",
 "- [18機能のβ版リリースノート](https://github.com/resoarc/resoarc-site/blob/feature/mini-plugins-beta-20261016/docs/mini-plugins/RELEASE-NOTES-v0.1.1-beta.md)",
 "- [追加18機能の重点項目](https://github.com/resoarc/resoarc-site/blob/feature/mini-plugins-beta-20261016/docs/mini-plugins/RELEASE-TRACKER-20261017.md)",
 "- [各機能の証拠・次アクション（機械可読の原本）](./tracker.json)",
 ""
 );
 return ln.join("\n");
};
const inventory=JSON.parse(readFileSync(jsonFile,'utf8'));
validateTracker(inventory);
const expected=renderTracker(inventory);
const arg=process.argv[2]||'--check';
if(arg==='--write'){
  writeFileSync(mdFile,expected,'utf8');
  console.log('Progress dashboard generated:', mdFile);
}else if(arg==='--check'){
  if(readFileSync(mdFile,'utf8').replace(/\r\n/g,'\n')!==expected)throw Error('Tracker Markdown is stale; run --write');
  console.log('Progress schema and dashboard verified; 29 tracked items');
}else if(arg==='--summary'){
  console.log(JSON.stringify({
    total:inventory.items.length,
    mini:inventory.items.filter(x=>x.group==='mini').length,
    packages:inventory.items.filter(x=>x.group==='package').length,
    unitPassedItems:inventory.items.filter(x=>x.gates.unit==='passed').length,
    passedUnitTests:inventory.items.reduce((v,x)=>v+(x.unit_tests?.pass||0),0),
    manifestPassedItems:inventory.items.filter(x=>x.gates.manifest==='passed').length,
    tenantPassedItems:inventory.items.filter(x=>x.gates.tenant==='passed').length,
    releaseApproved:inventory.items.filter(x=>x.release_decision==='approved').length
  },null,2));
}else{console.error('Usage: --check, --write, --summary');process.exitCode=2}
