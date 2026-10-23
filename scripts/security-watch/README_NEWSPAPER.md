<!--
SPDX-FileCopyrightText: 2026 ResoArc contributors
SPDX-License-Identifier: MIT
-->

# SWWW 脆弱性朝刊（2026-10-23 パイロット）

## 目的
脆弱性の網羅的な検索画面とは別に、忙しいユーザーが約5分でその日の重要な論点を知り、関係する技術を確認できる日本語新聞型の閲覧ページを提供する。

## 2026-10-23版の構成
1面: 今日の大見出し + 3本ピックアップ
2面: 編集判断に基づく「読む順番」8件
3面: 技術別の話題とPostgreSQLタグ集計（本日件数とは別）
4面: 行動チェックリスト・言葉の説明・一次出典
追加: 4面まとめ読みと印刷用CSS

## URI
- `/security/weather/newspaper/`
- `/security/weather/newspaper/ranking/`
- `/security/weather/newspaper/technologies/`
- `/security/weather/newspaper/action/`
- `/security/weather/newspaper/all/`

## 自動収集データと編集内容を混ぜない
- データ元: SWWW public-only PostgreSQL API (127.0.0.1:18763) の品質OK日報
- 元データは `swww_newspaper_export.py` のみでホワイトリスト項目を抽出。ResoArc内部台帳・担当者・機器情報は使わない。
- `generate_newspaper.py --input <approved-public-snapshot.json> --site <site-root>` で生成する。生成ファイルは通常の検証・REUSE・公開ガードを通す。
- 記事タイトル、日本語解説、更新バージョン、ランキングは編集確認済みのテンプレート `EDITORIAL` / `PRIORITY_IDS` による。
- 2026-10-23版は対象アドバイザリーが揃わなければ失敗する **fail-closed方式**。新しい日付の紙面を自動生成・公開する仕組みは現時点でない。次号の自動化では新規記事の一次情報検証・日付表示・重複排除・誤った重大度の照合が必要。
- 2026-10-23の収集 18:12 JST はPARTIALなので、09:11 JSTのOKデータを使った。31件はその日のDB収録日を持つ記事数で、今日発見された欠陥の数ではない。
- 原文の著作権はそれぞれの発行元に帰属。公開新聞は独自日本語要約と短い抜粋・リンクのみを使う。
- ランキングは編集部が選ぶ「読む優先順位」。CVSS/EPSSがそのまま順位であるかのように説明しない。
- ResoArcの個別影響・対応未審査を被害なしと表現しない。

## 初版QA
- 2026-10-23、公表可能な31件/CRITICAL 5件/情報源13件を確認
- Windows Chrome Playwright、390/768/1440幅 x 5ページ: 15/15 PASS
- Javascript未使用の紙面、ナビゲーション用公式スクリプトのみ
- サイト品質検証 280ファイル / 67HTML / REUSE / ナビ・署名済み製品不変 PASS
- Cloudflare Preview `https://swww-newspaper-preview.resoarc.pages.dev/` にのみ配信
- PROD `resoarc.com` 本番公開は中央GO後
- 中央公開停止ガードは維持
