import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
const source = await readFile(new URL("../site/_worker.js", import.meta.url), "utf8");
const worker = (await import("data:text/javascript;charset=utf-8," + encodeURIComponent(source))).default;
const rows = [];
const tasks = [];
const ctx = {waitUntil(promise) {tasks.push(promise);}};
const env = {
  ASSETS: {
    async fetch(request) {
      const path = new URL(request.url).pathname;
      if (path === "/not-found/") return new Response("missing", {status: 404, headers: {"Content-Type": "text/html"}});
      if (path.endsWith(".zip")) return new Response("zip", {status: 200, headers: {"Content-Type": "application/zip"}});
      return new Response("<html></html>", {status: 200, headers: {"Content-Type": "text/html; charset=utf-8"}});
    },
  },
  RESOARC_ACTIVITY: {writeDataPoint(row) {rows.push(row);}},
};
const fetchSite = (path, options={}) => worker.fetch(new Request("https://resoarc.com" + path, options), env, ctx);
await fetchSite("/products/kintone/?secret=never-save", {headers: {Referer: "https://note.com/any/private/path?token=secret"}});
await fetchSite("/downloads/plugin-v1.zip?tracking=x", {headers: {Referer: "https://github.com/resoarc/resoarc-site"}});
await fetchSite("/not-found/");
await fetchSite("/downloads/plugin-v1.zip", {method: "HEAD"});
await fetchSite("/assets/not-image.js");
await Promise.all(tasks);
assert.equal(rows.length, 2, "page and ZIP events only");
assert.deepEqual(rows.map(row=>row.blobs.slice(1)), [
  ["page_request", "/products/kintone/", "note.com"],
  ["download_request", "/downloads/plugin-v1.zip", "github.com"],
]);
assert.ok(rows.every(row=>row.blobs[0].match(/^\d{4}-\d{2}-\d{2}$/)));
assert.ok(!JSON.stringify(rows).includes("secret"), "query and referrer paths must not be recorded");
assert.ok(!JSON.stringify(rows).includes("tracking"));
assert.ok(rows.every(row => row.doubles[0] === 1));
await worker.fetch(new Request("https://resoarc.com/"), {ASSETS: env.ASSETS}, ctx);
console.log("PASS: privacy-safe activity collection, fail-open and route filters");
