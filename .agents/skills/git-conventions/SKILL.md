---
name: git-conventions
description: ブランチを作る、コミットする、プルリクエストを作る、Git 履歴を見直すときに使う。ブランチ名の形式、Conventional Commits の書式と日本語の説明文の書き方、コミットタイプの選び方、コミットの粒度、プルリクエストのタイトルと説明、リベースとマージの使い分けを提供する。
license: MIT
compatibility: GitHub Copilot、Copilot Coding Agent、Copilot CLI、VS Code Agent Mode、Claude Code、および Agent Skills をサポートするその他のエージェントと互換性がある。
metadata:
  category: git
  maturity: stable
  audience:
    - professional-teams
    - open-source
    - enterprise
  philosophy:
    - git-history-as-documentation
    - correctness-over-convenience
  enforced-standards:
    - conventional-commits
    - semantic-branch-naming
---

# Git 規約

このスキルは、このリポジトリのブランチ名、コミットメッセージ、プルリクエスト、履歴の整え方を定める。
判断が割れたら、規約に合い変更内容を正確に表すこと（正確性）、他の開発者が読んで分かること（可読性）、履歴が追跡しやすいこと（履歴の品質）の順で優先する。
可読性と履歴の品質のために正確性を削らない。
正確性は 2 つを指す。メッセージ、type、scope が実際の変更と一致していること、そして Conventional Commits、ブランチ名、1 コミット 1 論点の規約に従っていること。

## 使う場面

- ブランチを作る、またはブランチ名を提案するとき
- コミットメッセージを書く、または直すとき
- コミットを分ける、またはまとめるとき
- プルリクエストのタイトルと説明を書くとき
- Git 履歴や差分を見直すとき

## ブランチ名

形式は `<type>/<short-description>` で、type は feature、fix、hotfix、refactor、chore、docs、test のいずれかである。
小文字、数字、ハイフンだけを使い、単語の区切りにハイフンを使う。説明は簡潔にし、最大 5〜7 語にする。
バックログの ID は `feature/b-390-stage1-overlay-shell` のように含めてよい。Issue 番号は明示的に求められたときだけ含める。
ブランチ名を提案するときは、常に準拠する名前を提案する。利用者が非準拠の名前を出したら、準拠する名前に修正して提示する。

例：`feature/add-user-auth`、`fix/handle-null-response`、`docs/update-readme`

| 誤り | 理由 |
| --- | --- |
| `Feature/AddUserAuth` | 大文字を使い、単語がハイフンで区切られていない |
| `bugfix_login_issue` | `<type>/<short-description>` 形式でなく、type が許可されていない |
| `feature/1234-add-auth` | 求められていない Issue 番号を含んでいる |

## コミットメッセージ

形式は `<type>(<scope>): <description>` で、type は次の 8 つのいずれかである。

| type | 対象 |
| --- | --- |
| feat | 新しい外部動作または API |
| fix | 機能追加を伴わないバグ修正 |
| refactor | 動作を保つ内部の改善 |
| perf | パフォーマンスだけの改善 |
| docs | ドキュメントだけの変更 |
| style | 整形とリント（ロジック変更なし） |
| test | テストの追加または修正 |
| chore | ビルド、CI、ツール、依存関係の更新、内部の保守と整理 |

- scope は任意で、論理的なモジュールかドメインを書く。ファイル名を scope にしない
- 変更が複数のモジュールに跨るときは scope を省略せず、`feat(auth,logging): ...` のようにカンマで並べるか、コミットを分ける
- description は日本語で簡潔に書き、動詞の終止形か過去形で終える（「追加する」「追加した」）。体言止めにしない。句点や読点で終えない
- 簡潔さのために正確性を削らない。変更の場所と内容が分かるように書く（例：`fix(api): ユーザー取得時の null チェックを追加して NullPointerException を修正した`）
- feat か fix か迷ったら fix にする。利用者向けの新しい機能か外部 API が増えるときだけ feat にし、feat を多用しない
- コミットを提案するときは、type を選んだ理由を 1 行添える
- 非準拠のメッセージは、準拠する形へ書き直して提示する

例：`feat(auth): トークンリフレッシュロジックを追加した`、`fix(api): null エラー応答を処理した`、`chore(ci): ワークフローのタイムアウトを更新した`

| 誤り | 理由 |
| --- | --- |
| `ログインのバグを修正した` | type が無い |
| `feat: Added new feature` | 説明が英語である |
| `feat: 新しい機能を追加した。` | 句点で終わっている |
| `feat: 新機能の追加` | 体言止めである |
| `fix(login_bug)` | description が無い |

## コミットの粒度

- 1 つのコミットに 1 つの論理的な変更を入れる。焦点が複数あるなら分け、小さく焦点を絞ったコミットを複数に分けることを優先する
- リファクタリングと機能変更を同じコミットに混ぜない
- 無関係な変更が混ざっていたら、分割を提案する
- 共有ブランチと保護されたブランチに WIP コミットを置かない

## プルリクエスト

- タイトルは Conventional Commits 形式で、主要なコミットの type と一致させる
- 説明は `.github/pull_request_template.md` の節に沿って書く。無ければ以下の内容で書く
  - 変更概要
  - 変更理由
  - 変更詳細
  - 影響範囲
    - 影響範囲の有無や影響の大きさを明示する
  - テストの有無や影響を明示する
  - 関連するチケットや課題があれば明示する
  - その他、レビュアーに伝えるべき情報があれば明示する
    - レビューの観点を明示する
    - レビューのポイントや注意点を明示する
- タイトルとコミット履歴が食い違っていたら指摘する

## 履歴

- ブランチは短命にする
- 明示的に指示されない限り、マージよりリベースを優先し、可能な限りクリーンで直線的な履歴を保つ
- マージコミットが価値を追加しないときは、リベースを提案する
- 履歴がノイズだらけか不明瞭になったら、警告する

## 守ること

- 非準拠の提案や入力を見つけたら、必ず準拠する案を提示する
- 求められない限り、別の Git ワークフローを持ち込まない
- 一般的なベストプラクティスより、このリポジトリの規則を優先する
- 便宜のために規則を緩めない
