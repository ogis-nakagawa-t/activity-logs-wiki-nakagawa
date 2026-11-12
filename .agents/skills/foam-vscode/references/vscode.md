# VS Code での Foam

出典（2026-10-21 取得）:

- インストール済みの拡張 `foam.foam-vscode` 0.46.0 の `package.json`（コマンド名・キー割り当て・ビュー・設定キーと既定値）
- https://docs.foam.md/features/commands/
- https://docs.foam.md/features/daily-notes/
- https://docs.foam.md/features/wikilinks/

エージェントは VS Code の画面を操作できない。このページは、ユーザーに操作方法を説明するときと、設定の意味を調べるときに使う。
リンクの状態を自分で確かめるときは [cli.md](cli.md) を使う。

## 主なコマンド

コマンドパレット（Ctrl+Shift+P）で名前を入力して実行する。

| コマンド | ID | 内容 |
| --- | --- | --- |
| Foam: Open Today's Note（Alt+D） | `foam-vscode.open-daily-note` | 今日の日次ノートを開く。無ければ `.foam/templates/daily-note.md` から `10_Daily/YYYY/MM/DD.md` に作る（SKILL.md の注意点 2・3） |
| Foam: Open Daily Note（Alt+H） | `foam-vscode.open-daily-note-for-date` | 日付を選んで日次ノートを開く |
| Foam: Create New Note | `foam-vscode.create-note` | 新しいノートを作る（`new-note` テンプレートがあれば使う） |
| Foam: Create New Note From Template | `foam-vscode.create-note-from-template` | テンプレートを選んでノートを作る |
| Foam: Create New Template | `foam-vscode.create-new-template` | `.foam/templates/` にテンプレートを作る |
| Foam: Show Graph | `foam-vscode.show-graph` | リンクのグラフを表示する |
| Foam: Search Tag | `foam-vscode.search-tag` | タグで検索する |
| Foam: Rename Tag | `foam-vscode.rename-tag` | タグを全ノートで書き換える |
| Foam: Convert Wikilink to Markdown Link | `foam-vscode.convert-wikilink-to-mdlink` | カーソル位置の `[[my-note]]` を `[My Note](../path/to/my-note.md)` に変える |
| Foam: Convert Markdown Link to Wikilink | `foam-vscode.convert-mdlink-to-wikilink` | 上の逆 |
| Foam: Update Wikilink Definitions | `foam-vscode.update-wikilink-definitions` | リンク参照定義を更新する |
| Foam: Lint Workspace (Experimental) | `foam-vscode.lint` | ワークスペースを点検する |
| Foam: Clear Cache | `foam-vscode.clear-cache` | Foam のキャッシュを消す |

### `foam-vscode.create-note` の引数

キー割り当て（keybindings.json）から引数付きで呼べる。

| 引数 | 内容 |
| --- | --- |
| `notePath` | 作るノートのパス（ワークスペースからの相対パス） |
| `templatePath` | 使うテンプレートのパス |
| `title` | タイトル（`FOAM_TITLE`） |
| `text` | 本文。テンプレートがあればテンプレートが優先される |
| `variables` | テンプレートで使う変数 |
| `date` | `FOAM_DATE_*` に使う日付（`YYYY-MM-DD`） |
| `onFileExists` | `overwrite` / `open` / `ask` / `cancel` |

## サイドバーのビュー

| ビュー | 内容 |
| --- | --- |
| Connections | 開いているノートのバックリンクと外向きリンク |
| Tag Explorer | タグの階層と件数 |
| Notes | ノートの一覧 |
| Orphans | リンクの出入りが無いノート |
| Placeholders | 存在しないノートへのリンク |
| Smart Folders | 保存したクエリ |

リンク先へは Ctrl+クリックか F12 で移動する。`[[` と入力すると補完候補が出る。

## 主な設定キー

`.vscode/settings.json` に書く。このリポジトリには現在 `.vscode/settings.json` が無く、すべて既定値で動いている。設定を加えるときはユーザーに確認する。

| キー | 既定値 | 内容 |
| --- | --- | --- |
| `foam.files.exclude` | `**/.vscode/**/*`、`**/node_modules/**/*` など | Foam が読まないファイルの glob。foam-cli もこの設定に従う |
| `foam.files.attachmentExtensions` | `pdf mp3 ... docx xls xlsx ... pptx` | 添付ファイルとして扱う拡張子 |
| `foam.templates.folder` | `.foam/templates` | テンプレートのフォルダー |
| `foam.files.newNotePath` | `root` | 新しいノートを作る場所（`root` / `currentDir`）。テンプレートやコマンドの引数が優先される |
| `foam.completion.label` | `path` | リンク補完の表示（`path` / `title` / `identifier`） |
| `foam.completion.useAlias` | `never` | 補完で別名付きリンクを作るか（`never` / `whenPathDiffersFromTitle`） |
| `foam.completion.linkFormat` | `wikilink` | 補完で作るリンクの形式 |
| `foam.links.sync.enable` | `true` | VS Code 上でノートを名前変更・移動したときに wikilink を書き換える |
| `foam.links.directory.mode` | `resolve` | ディレクトリへのリンクを `index.md` / `README.md` に解決する |
| `foam.edit.linkReferenceDefinitions` | `off` | リンク参照定義を書き足すか（[syntax.md](syntax.md)） |
| `foam.preview.embedNoteType` | `full-card` | 埋め込みの表示形式 |
| `foam.dateLocale` | `default` | 日付変数の曜日・月名のロケール（`ja-JP` など） |
| `foam.dateSnippets.afterCompletion` | `createNote` | `/today` などを確定したときに日次ノートを作るか（`noop` / `createNote` / `navigateToNote`） |
| `foam.openDailyNote.onStartup` | `false` | 起動時に日次ノートを開く |
| `foam.orphans.exclude`、`foam.placeholders.exclude` | なし | Orphans・Placeholders ビューから除く glob |

`foam.openDailyNote.directory` などのほかの `foam.openDailyNote.*` は非推奨である。日次ノートの場所は `daily-note.md` テンプレートの `filepath` で決める。
