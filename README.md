# ResoArc

**Open technology. Inspectable by everyone. Reusable by humans and AI.**

[ResoArc公式サイト](https://resoarc.com) の公開ソースコードです。ResoArcは独立した技術プロジェクトであり、法人・公的機関を名乗るものではありません。

## 公開原則

- **無料で使える:** 公開ツールは登録不要で利用できます。
- **中身を調べられる:** 公開サイトのHTML、CSS、JavaScript、各種静的アセット、検証用スクリプトをリポジトリで公開します。
- **AIによる取り込みを歓迎:** オリジナルコードと文章のAI解析、検索インデックス化、RAG、改変、学習用利用をライセンス範囲で認めます。詳細は [AI_USAGE.md](AI_USAGE.md)。
- **確認できる品質:** 検証方法と実行結果は、誰でも確認できる形で残します。テストが通ったことと安全性が完全保証されることは別です。
- **依存関係と権利を明示:** 第三者素材は固有のライセンスを保持します。詳細は [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## 収録物

- `site/`: 公開Webサイトの静的な実装。HTML/CSS/JavaScriptを含み、このディレクトリ自体が公開用の実装です。
- `site/assets/tools/hash.js`: ブラウザー内で動くSHA-256確認ツール。
- `site/assets/tools/csv.js`: ブラウザー内で動くCSV構造検査ツール。
- `site/llms.txt`: AI向けの公開索引と利用条件。
- `scripts/verify_site.py`: 参照リンク・必須ファイル・公開前の機械的チェック。
- `.github/workflows/verify.yml`: GitHub Actionsでの基本検証。

## ローカルで動かす

Python 3.10以降を推奨します。ビルドやクラウド鍵は不要です。

```bash
python scripts/verify_site.py
python -m http.server 8000 --directory site
```

ブラウザーで http://localhost:8000 を開いて確認できます。サイトは基本的に静的ファイルとして動作し、ビルドツールの実行を前提としません。

## ライセンス

ResoArc独自のソフトウェア・HTML・CSS・文章・SVGは、リポジトリの [MIT License](LICENSE) に従って再利用できます。第三者写真・フォントなどはMITの対象外で、それぞれの条件が適用されます。商標等の権利はライセンスで譲渡されません。

## 公開・変更の記録

公開後の変更はコミットとPull Requestで追跡できる形を目指します。リリース時には変更内容、確認結果、既知の制約を残します。[検証手順](docs/VERIFICATION.md) と [公開チェックリスト](docs/PUBLISHING.md) を参照してください。

公式公開リポジトリ: https://github.com/resoarc/resoarc-site 。`main` のコードはGitHub Actionsで自動検証します。本番配信との一致は別途照合する必要があり、コードの公開だけで全インフラの安全性を保証するものではありません。
