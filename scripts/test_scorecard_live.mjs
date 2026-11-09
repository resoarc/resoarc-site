import assert from "node:assert/strict";
import fs from "node:fs/promises";
import vm from "node:vm";

const root = new URL("../site/", import.meta.url);
const source = await fs.readFile(new URL("_worker.js", root), "utf8");
const moduleData = "data:text/javascript;base64," + Buffer.from(source).toString("base64");
const handler = (await import(moduleData)).default;
const resource = new Request("https://resoarc.com/api/scorecard");
let called = 0;
globalThis.fetch = async (url) => {
  assert.equal(url, "https://api.securityscorecards.dev/projects/github.com/resoarc/resoarc-site");
  called++;
  return new Response(JSON.stringify({
    score: 5.8, date: "2026-10-16T17:54:23Z",
    repo: {name: "github.com/resoarc/resoarc-site"}
  }), {status: 200});
};
let response = await handler.fetch(resource, {
  ASSETS: {fetch: () => { throw Error("static ASSETS must not be called"); }}
});
assert.equal(response.status, 200);
const value = await response.json();
assert.equal(value.score, 5.8);
assert.equal(value.repository, "github.com/resoarc/resoarc-site");
assert.equal(called, 1);
assert.equal(response.headers.get("content-type"), "application/json; charset=utf-8");
response = await handler.fetch(new Request("https://resoarc.com/api/scorecard", {method: "POST"}), {});
assert.equal(response.status, 405);
response = await handler.fetch(new Request("https://resoarc.com/products/"), {ASSETS: {fetch: () => new Response("STATIC_OK")}});
assert.equal(await response.text(), "STATIC_OK");
globalThis.fetch = async () => new Response("temporary error", {status: 500});
response = await handler.fetch(resource, {});
assert.equal(response.status, 200);
assert.equal(response.headers.get("cache-control"), "no-store");
const historical = await response.json();
assert.equal(historical.live_status, "temporarily_unavailable");
assert.equal(historical.historical, true);
assert.equal(historical.repository, "historical-source");
assert.match(historical.source, /not current Codeberg/);

const code = await fs.readFile(new URL("assets/scorecard-live-20261017.js", root), "utf8");
const states = [{textContent:"確認中"}, {textContent:"確認中"}];
vm.runInNewContext(code, {
  document: {querySelectorAll: key => key === "[data-scorecard-state]" ? states : []},
  fetch: () => { throw Error("historical UI must not claim a fresh API lookup"); }
});
assert(states.every(x => x.textContent.includes("過去の外部評価")));
assert(states.every(x => x.textContent.includes("現行Codebergソースの評価ではありません")));
console.log("SCORECARD_AUTO_PASS official upstream, historical fallback, static UI without false current claims");
