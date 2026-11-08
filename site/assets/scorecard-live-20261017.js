// Historical OpenSSF Scorecard display. Values are from a retired source-hosting origin.
// Not a current score for the official Codeberg repository. No GitHub dependency.
(() => {
  "use strict";
  const label = "過去の外部評価（2026年10月）。現行Codebergソースの評価ではありません";
  for (const el of document.querySelectorAll("[data-scorecard-state]")) {
    el.textContent = label;
  }
})();
