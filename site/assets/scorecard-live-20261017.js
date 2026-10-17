// ResoArc live Scorecard display. Only trusted same-origin JSON; textContent prevents HTML injection.
(() => {
  "use strict";
  const values = document.querySelectorAll("[data-scorecard-value]");
  if (!values.length) return;
  const dates = document.querySelectorAll("[data-scorecard-date]");
  const states = document.querySelectorAll("[data-scorecard-state]");
  const markFallback = () => {
    for (const el of states) el.textContent = "公式APIへの接続が一時的に利用できないため、直近確認値を表示中";
  };
  fetch("/api/scorecard", {credentials: "omit"})
    .then(response => {
      if (!response.ok) throw new Error("scorecard unavailable");
      return response.json();
    })
    .then(data => {
      const score = Number(data.score);
      if (!Number.isFinite(score) || score < 0 || score > 10) throw new Error("invalid score");
      const d = new Date(data.date);
      if (!Number.isFinite(d.getTime()) || data.repository !== "github.com/resoarc/resoarc-site") {
        throw new Error("invalid source");
      }
      const numeric = score.toFixed(1);
      const formatted = new Intl.DateTimeFormat("ja-JP", {
        year: "numeric", month: "numeric", day: "numeric",
        hour: "2-digit", minute: "2-digit", hour12: false,
        timeZone: "Asia/Tokyo"
      }).format(d) + " JST";
      for (const el of values) el.textContent = numeric;
      for (const el of dates) {
        el.textContent = formatted;
        if (el.tagName === "TIME") el.dateTime = d.toISOString();
      }
      for (const el of states) el.textContent = "公式APIから自動取得";
    })
    .catch(markFallback);
})();
