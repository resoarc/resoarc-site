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
assert.equal(response.status, 502);

const code = await fs.readFile(new URL("assets/scorecard-live-20261017.js", root), "utf8");
const elements = {
  "[data-scorecard-value]": [{textContent:"5.8"}, {textContent:"5.8"}],
  "[data-scorecard-date]": [{tagName:"TIME",textContent:"",dateTime:""}],
  "[data-scorecard-state]": [{textContent:"確認中"}],
};
let waiting = Promise.resolve();
const context = {
  document: {querySelectorAll: key => elements[key] ?? []},
  fetch: () => Promise.resolve({ok:true,json:async()=>({
    score:7.1,date:"2026-10-16T18:54:23Z",repository:"github.com/resoarc/resoarc-site"
  })}),
  Date,Number,Intl,Error,
};
vm.runInNewContext(code,context);
await new Promise(r => setTimeout(r,0));
assert(elements["[data-scorecard-value]"].every(x=>x.textContent==="7.1"));
assert(elements["[data-scorecard-date]"][0].textContent.includes("JST"));
assert.equal(elements["[data-scorecard-state]"][0].textContent,"公式APIから自動取得");
context.fetch = async ()=>({ok:false});
vm.runInNewContext(code,context);
await new Promise(r => setTimeout(r,0));
assert(elements["[data-scorecard-state]"][0].textContent.includes("直近確認値"));
console.log("SCORECARD_AUTO_PASS server proxy status, static assets, error handling, client success/fallback");
