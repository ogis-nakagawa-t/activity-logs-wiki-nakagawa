---
name: foam-vscode
description: "Foam for VS Code のノートを書く・つなぐ・調べるときに使う。wikilink（パス付きリンク・見出し・ブロック・別名）、埋め込み、タグ、frontmatter、.foam/templates のテンプレートと変数、日次ノート（Foam: Open Today's Note / Foam: Open Daily Note / Alt+D）、バックリンク・プレースホルダー・孤立ノートの確認、foam-cli（list / links / lint / search / daily）と foam mcp を扱う。トリガー例: 'Foam', 'wikilink', 'リンク切れを調べて', 'バックリンク', 'プレースホルダー', '孤立ノート', 'Foam テンプレート', 'foam-cli'。"
---

# Foam for VS Code

Foam は VS Code 上の Markdown ノートを wikilink でつなぐ拡張機能である（このリポジトリでは `foam.foam-vscode` を推奨拡張にしている）。
このスキルは、Foam の記法と、エージェントがリンクの状態を確かめる手段（foam-cli）を定める。
内容は docs.foam.md（2026-10-21 取得）と、foam-cli 0.46.4 をこのリポジトリで実行した結果に基づく。

## 使う場面

- ノートに wikilink・埋め込み・タグ・frontmatter を書くとき
- `.foam/templates/` のテンプレートを作る・直すとき
- リンク切れ（プレースホルダー）、バックリンク、孤立ノートを調べるとき
- Foam の VS Code コマンドや設定についてユーザーに説明するとき

## 判断ルール

1. 記法は記憶で書かず、[references/syntax.md](references/syntax.md) と [references/templates.md](references/templates.md) で確かめる。
2. パス付きでないリンクを書いたときや、ユーザーにリンクの確認を頼まれたときは、意図した先に解決するかを foam-cli で確かめる（[references/cli.md](references/cli.md)）。VS Code の画面は見られないので、CLI の出力を根拠にする。日々の記録でパス付きリンクを書くだけなら、CLI は実行しない。
3. foam-cli は読み取り系だけを使う。書き込み系は下の「本リポジトリでの注意点」4 を守る。
4. リンクやファイルの作成・編集は Write/Edit ツールで行い、AGENTS.md の規則（削除禁止、80_Raw/ 編集禁止など）を優先する。

## 本リポジトリでの注意点

1. **日次ノートへのリンクは必ずパス付きで書く。** 日次ノートは `10_Daily/YYYY/MM/DD.md` なので、`[[20]]` のような識別子だけのリンクは月をまたいで衝突する。Foam は曖昧なリンクをアルファベット順で解決する。このため `10_Daily/2026/09/20.md` と `10_Daily/2026/10/20.md` があると、`[[20]]` は `09/20` を指す（foam-cli で確認済み）。VS Code では警告の診断が出るが、foam-cli の出力と `foam lint` には警告が出ない。`[[10_Daily/2026/10/20]]` と書く。
2. **日次ノートのテンプレートは `.foam/templates/daily-note.md` である。** この名前なので、`Foam: Open Today's Note`（Alt+D）・`Foam: Open Daily Note`（Alt+H）・`/today` などの日付スニペット・`foam daily` は、すべて `10_Daily/YYYY/MM/DD.md` を指す（`foam daily --path-only` で確認済み）。テンプレートが無い場合の既定はルートの `journals/YYYY-MM-DD.md` である（docs には `journal/` とあるが、0.46.4 の実際の値は `journals/`）。テンプレートを改名・削除すると、Alt+D のノートが `journals/` に作られるようになる。
3. **「前:」「次:」のリンクは day-start の手順で埋める。** Foam には前日・翌日を表す変数が無い（`FOAM_DATE_YESTERDAY` などは存在しない）。テンプレートの「前:」は `[[${FOAM_PREVIOUS_DAILY_NOTE}|前回]]` で、Alt+D で作ると `[[20|前回]]` のような識別子だけのリンクになる。注意点 1 のとおり識別子だけのリンクは曖昧になりうるので、エージェントは procedures/day-start.md に従ってパス付きに直す。前回のdailyの「次:」は、次の業務開始時に、その日のノートへのパス付きリンクに書き換える。テンプレート自身の `${FOAM_PREVIOUS_DAILY_NOTE}` は `foam list placeholders` に出るが、これはリンク切れではない。
4. **foam-cli の書き込み系操作は使わない。使うならユーザーに確認する。**

   | 操作 | AGENTS.md との衝突 |
   | --- | --- |
   | `foam note delete` | ファイルを `.foam/trash/` へ移すか、`--permanent` で消す。削除禁止に反する |
   | `foam note move` / `foam rename` | ワークスペース全体のリンクを書き換える。編集禁止の `80_Raw/` も書き換わりうる |
   | `foam lint --fix` | 見出しの無いノートに見出しを足す。`80_Raw/` や `.agents/` の中も対象になる |
   | `foam daily --create` | テンプレートの変数だけを埋めて作り、パス付きの前回リンクや持ち越しは入らない。日次ノートは day-start の手順で作る |
   | `foam tag rename` | 全ノートのタグを書き換える |
   | `foam mcp --allow-writes` | 上記の書き込みをエージェントに開放する |

   使ってよいもの: `list` / `links` / `note show` / `note id` / `outline` / `search` / `grep` / `tag list` / `tag search` / `lint`（`--fix` なし）/ `daily --path-only`。
5. **PowerShell で実行する。** 環境変数は `export` ではなく `$env:FOAM_WORKSPACE` で設定する。テレメトリーは既定で有効になっている。実行前に `$env:FOAM_TELEMETRY = '0'` を設定して止める（ユーザー設定ファイルは変えない）。
6. **ワークスペースには `.agents/` も含まれる。** スキルのテンプレート内の `[[{article}]]` などもプレースホルダーとして出る。リンク切れを調べるときは、`10_Daily/`・`40_Notes/`・`90_Wiki/` などの記録の部分に絞って読む。`.vscode/settings.json` の `foam.files.exclude` で除外でき、foam-cli もこの設定に従う（検証用ワークスペースで確認済み）。ただし設定ファイルの追加はユーザーに確認してから行う。
7. **ファイルの移動でリンクが切れる。** VS Code 上での名前変更・移動では、Foam がリンクを書き換える（`foam.links.sync.enable` が既定で有効）。`Move-Item` で `99_Archive/` へ移したときは書き換わらない。移動の後は `foam list placeholders` でリンク切れを確かめ、ユーザーに報告する。
8. **曜日の変数はロケールに注意する。** `FOAM_DATE_DAY_NAME_SHORT` は OS のロケールに従い、この環境では `金` になる。設定 `foam.dateLocale` は foam-cli には効かなかった（検証用ワークスペースで確認済み）。テンプレートの `weekday` は `${FOAM_DATE_FORMAT:ddd}` にしてあり、`scripts/now.ps1` と同じ `Fri` 形式になる。エージェントが書くときは now.ps1 の値を使う。

## リファレンス

| ファイル | 内容 |
| --- | --- |
| [references/syntax.md](references/syntax.md) | wikilink、埋め込み、タグ、frontmatter、リンク参照定義 |
| [references/templates.md](references/templates.md) | テンプレートの置き場所、`foam_template`、変数、日次ノート |
| [references/cli.md](references/cli.md) | foam-cli の実行方法と読み取り系コマンドの出力例、foam mcp |
| [references/vscode.md](references/vscode.md) | VS Code のコマンド、パネル、設定キー |
