# SWWW ResoArc 限定サイト公開記録

2026-10-22 ユーザーからSWWWをResoArcへデプロイする明示的な依頼あり。
対象は site/security/weather/、site/security/index.html 内の案内リンク、
scripts/security-watch/weather_* の公開ソースのみ。
既存プラグインZIP、ResoArcOS、DNS、メール、RSS、その他公開物は変更禁止。
PRODUCTION_FREEZE.flag はほかの公開物に対して引き続き有効。
一般向けの脆弱性観測でありResoArc製品の影響や被害確定ではない。
日次収集は内部自動化済み。日々のCloudflare再デプロイは今回のGOに含まれず、
別途安全な更新ゲートを要する。

ホームフッターからの導線、sitemap、ナビゲーションマップ更新も本SWWW公開の限定変更に含む。

QA: python3.11 scripts/verify_site.py PASS; 241 files, 57 HTML, NAV 56 pages (46 public), plugin transparency 12/12.
Old OS source ZIP SHA256 remains 72b427a8ef08ab388dc70ad2f1b14bcb2a7517b8f5edd0ebe67c8d934a93bb20.
Baseline redirects manifest entry corrected to Git LF blob digest.
