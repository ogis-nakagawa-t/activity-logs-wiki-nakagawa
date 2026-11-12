# foam-cli

出典（2026-10-21 取得）:

- https://docs.foam.md/tools/cli/ と、その下の各コマンドのページ
- https://docs.foam.md/tools/cli/mcp/
- https://docs.foam.md/tools/telemetry/
- `npx --yes foam-cli --help` の出力（0.46.4）

foam-cli は、Foam の VS Code 拡張と同じ仕組みでワークスペースを読み、リンク・タグ・テンプレートを扱うコマンドである。
エージェントは VS Code の画面を見られないので、リンクの解決先やプレースホルダーはこの CLI で確かめる。
このページのコマンドと出力は、すべてこのリポジトリか scratchpad の検証用ワークスペースで実行したものである。
検証用ワークスペースはリポジトリに含まれていない。`10_Daily/2026/10/20.md` や `40_Notes/2026-10-20_foam-wikilink.md` を指すコマンドは、パスを実在するノートに置き換えて使う。

## 準備

インストールはせず、`npx` で実行する（Node.js v25.9.0 / npm 11.14.1 で動作を確認した）。
初回はパッケージのダウンロードに時間がかかる。

PowerShell で、セッションごとに次を設定する。

```powershell
$env:FOAM_TELEMETRY = '0'
$env:FOAM_WORKSPACE = (Get-Location).Path
```

- `FOAM_TELEMETRY` を設定しないと、各コマンドの先頭に `Foam telemetry is on.` と出て、利用状況が送信される。ユーザー設定（`foam config set telemetry.enabled false`。`~/.config/foam/config.json` に書かれる）はユーザーの判断なので、エージェントは変えない。
- `FOAM_WORKSPACE` の代わりに、各コマンドに `--workspace .` を付けてもよい。どちらも無ければカレントディレクトリが使われる。
- すべてのコマンドが `--format json` を受け付ける。

## 読み取り系コマンド（使ってよい）

### 一覧

```powershell
npx --yes foam-cli list templates
npx --yes foam-cli list placeholders
npx --yes foam-cli list orphans
npx --yes foam-cli list deadends
npx --yes foam-cli list tags --sort count
npx --yes foam-cli list notes --tag 調査
```

このリポジトリでの `list templates` の出力:

```text
daily-note  Daily note template for IT technical work
```

`list placeholders` の出力（抜粋）。テンプレートの中の変数入りリンクもプレースホルダーとして出る。

```text
${FOAM_PREVIOUS_DAILY_NOTE}
  referenced by: .foam/templates/daily-note.md
```

これはテンプレートの「前:」リンクで、リンク切れではない。`.agents/skills/` のテンプレート内の `{article}` なども出るので、記録のディレクトリ（`10_Daily/`・`40_Notes/`・`90_Wiki/` など）に絞って読む。

- `orphans`: リンクの出入りが無いノート
- `deadends`: 外向きのリンクが無いノート

### リンク

```powershell
npx --yes foam-cli links --path 90_Wiki/index.md
npx --yes foam-cli links --path 10_Daily/2026/10/20.md --incoming
```

`--path` はファイルのパスで指定する。識別子で指定する（`foam links my-note`）と、曖昧なときに別のノートを指すことがある。
このリポジトリでの出力:

```text
Outgoing (0):
  (none)

Incoming (1):
  ← README  README.md
```

検証用ワークスペースで、`[[20]]` を含むノートを調べた。`10_Daily/2026/09/20.md` と `10_Daily/2026/10/20.md` がある状態での出力（抜粋）:

```text
Outgoing (9):
  → 09/20                               10_Daily/2026/09/20.md
  → 10/20                               10_Daily/2026/10/20.md
  ...
  → 2026-10-22_not-yet                  ../../../../../../../../../../../40_Notes/2026-10-22_not-yet
```

- 1 行目は `[[20]]` の解決先で、`09/20` になっている。意図と違う先に解決していないかは、この出力で確かめる。
- 存在しないノートへのリンクは、パスが `../../..` のように崩れて出る。

### ノートの情報

```powershell
npx --yes foam-cli note id --path 10_Daily/2026/10/20.md
npx --yes foam-cli note show --path 40_Notes/2026-10-20_foam-wikilink.md
npx --yes foam-cli outline --path 40_Notes/2026-10-20_foam-wikilink.md
```

検証用ワークスペースでの出力:

```text
10/20
```

```text
ID:       2026-10-20_foam-wikilink
Title:    Foam の wikilink の仕様
Path:     40_Notes/2026-10-20_foam-wikilink.md
Type:     note
Tags:     #foam #調査
Aliases:  wikilink仕様
```

```text
# Foam の wikilink の仕様
  ## 背景
  ## 結論
```

### 検索

```powershell
npx --yes foam-cli search --tag 調査
npx --yes foam-cli search --property weekday=Wed
npx --yes foam-cli grep "パス付き"
```

- `search`: タイトル・別名・タグ・frontmatter で探す。`<query>` はタイトルと別名の部分一致（大文字小文字を区別しない）。
- `grep`: 本文を探す。出力は `ファイル:行番号: 行` の形。

### 点検

```powershell
npx --yes foam-cli lint
```

このリポジトリでの出力:

```text
CLAUDE.md
  1:1  warning  Note is missing an h1 heading (fixable)  missing-heading
templates/20_Weekly.md
  1:1  warning  Note is missing an h1 heading (fixable)  missing-heading

2 problems (0 errors, 2 warnings , 2 fixable with --fix)
```

- 終了コードは、問題なしが `0`、コマンドのエラーが `1`、問題ありが `2`。
- ルールは `missing-heading` と `stale-definitions`（リンク参照定義が有効なときだけ）の 2 つで、リンク切れや曖昧なリンクは調べない。リンク切れは `list placeholders` で調べる。
- `--fix` は付けない（SKILL.md の注意点 4）。

### 日次ノートの保存先

```powershell
npx --yes foam-cli daily --path-only
```

このリポジトリでの出力（SKILL.md の注意点 2）:

```text
[info] Processing markdown template
[info] Note creation triggered by command: foam.open-daily-note
[info] Generic command: foam.open-daily-note
<ワークスペース>\10_Daily\2026\10\21.md
```

`<ワークスペース>` の部分には、実際にはワークスペースの絶対パスが出る。
daily-note テンプレートがあるので、パスの前に `[info]` のログが標準出力に出る。スクリプトでパスを使うときは最後の行を取る。

## 書き込み系コマンド（使わない）

`note create` / `note move` / `note delete` / `rename` / `tag rename` / `lint --fix` / `daily --create` はファイルを書き換える。
AGENTS.md の規則と衝突するので、使わない（SKILL.md の注意点 4）。ノートの作成・編集は Write/Edit ツールで行う。

## foam mcp

Foam のワークスペースを MCP サーバーとして公開する。既定は読み取り専用で、`--allow-writes` を付けたときだけ書き込み用のツールが出る。

- 読み取り用のツール: `list_resources`、`get_resource`、`read_resource`、`get_workspace_info`、`get_connections`、`traverse_graph`、`get_orphans`、`get_deadends`、`get_placeholders`、`get_graph_summary`、`list_tags`、`search_by_tag`、`search_by_property`、`search_resources`、`get_outline`
- 書き込み用のツール（`--allow-writes`）: `create_resource`、`update_resource`、`delete_resource`、`move_resource`、`add_tags`、`remove_tags`、`rename_tag`

`foam mcp --help` に載っている設定例:

```json
{
  "mcpServers": {
    "foam": {
      "command": "npx",
      "args": ["foam-cli", "mcp", "--workspace", "/path/to/workspace"]
    }
  }
}
```

- このリポジトリには MCP の設定を入れていない。入れるかはユーザーが決める。入れる場合も `--allow-writes` は付けず、`env` に `"FOAM_TELEMETRY": "0"` を足す。
- ログは標準エラーに出る。詳しく見るには `FOAM_LOG_LEVEL=debug` を設定する。
