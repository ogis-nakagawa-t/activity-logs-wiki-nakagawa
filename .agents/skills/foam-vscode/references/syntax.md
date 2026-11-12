# Foam の記法

出典（2026-10-21 取得）:

- https://docs.foam.md/features/wikilinks/
- https://docs.foam.md/features/embeds/
- https://docs.foam.md/features/tags/
- https://docs.foam.md/features/note-properties/
- https://docs.foam.md/features/link-reference-definitions/

「CLI で確認」と書いた項目は、foam-cli 0.46.4 で実際に解決先を確かめた。

## wikilink

### 識別子リンクとパスリンク

| 書き方 | 解決のしかた |
| --- | --- |
| `[[notes]]`、`[[house/todo]]` | 識別子リンク。ワークスペース全体からファイル名（拡張子なし）の末尾が一致するノートを探す |
| `[[./file]]`、`[[../other/file]]`、`[[/from/root]]` | パスリンク。`/` か `.` で始まるとパスとして解決する |

- 識別子は、ファイル名を一意にできる最短の形になる。`10_Daily/2026/10/20.md` の識別子は `10/20` だった（CLI で確認）。`foam note id --path <パス>` で確かめられる。
- 曖昧な識別子（例: `projects/house/todo.md` と `work/todo.md` があるときの `[[todo]]`）は、アルファベット順で決まった方に解決する。VS Code では警告の診断が出る。CLI では警告が出ず、`foam lint` も報告しない（CLI で確認）。
- `[[10_Daily/2026/10/20]]`（先頭 `/` なし）と `[[/10_Daily/2026/10/20]]` は、どちらも同じノートに解決した（CLI で確認）。このリポジトリでは、先頭 `/` なしのパス付きで書く（AGENTS.md の例に合わせる）。
- 拡張子 `.md` は書かない。

### 見出し・ブロック・別名

| 書き方 | 意味 |
| --- | --- |
| `[[note#見出し]]` | 見出しへのリンク。日本語の見出しも解決した（CLI で確認） |
| `[[note#^blockid]]` | ブロックへのリンク。リンク先の段落・リスト項目・見出し・引用の末尾に `^blockid` を付ける |
| `[[note\|表示名]]` | 別名で表示する。表の中では `\|` とエスケープする。`[[10_Daily/2026/10/20\|昨日]]` が解決した（CLI で確認。docs の wikilink ページには記載なし） |

### ディレクトリリンク

- `[[projects]]` は `projects/index.md` か `projects/README.md` を開く。同じ階層に `projects.md` があればそちらが優先される。
- `foam.links.directory.mode` を `disabled` にすると無効になる。

### プレースホルダー

- 存在しないノートへの wikilink はプレースホルダーになる。VS Code では見た目が変わり、クリックするとノートが作られる。
- `foam list placeholders` で一覧できる。

### Markdown リンク

- `[表示名](path/to/note.md)`、`[表示名](note.md#見出し)` も Foam のリンクとして扱われる。
- Foam が扱わないファイルへのリンクは、存在していてもプレースホルダーとして出る。README の `[now.ps1](scripts/now.ps1)` や `[.vscode/extensions.json](.vscode/extensions.json)` がそうだった（CLI で確認）。Foam が扱うのは、ノート（`.md`）、画像、`foam.files.attachmentExtensions` に挙がった添付ファイル（pdf、docx、xlsx など）だけである。`.vscode/` は `foam.files.exclude` の既定値で除外されている。

## 埋め込み

| 書き方 | 意味 |
| --- | --- |
| `![[note]]` | ノート全体を埋め込む |
| `![[note#見出し]]` | その見出しの節を埋め込む |
| `![[note#^blockid]]` | そのブロックを埋め込む |
| `![[image.png\|300]]`、`![[image.png\|50%]]`、`![[image.png\|300x200]]` | 画像の幅（・高さ）を指定する |
| `![[image.png\|300\|center]]` | 配置（`left` / `center` / `right`） |
| `![[chart.png\|400\|月次売上のグラフ]]` | 代替テキスト |

- 表示形式の既定は設定 `foam.preview.embedNoteType` で変える。値は `full-card`（既定）、`full-inline`、`content-card`、`content-inline`。`full` は見出しを含み、`content` は見出しを除く。
- 埋め込みもリンクとして数えられ、`foam links` の Outgoing に出る（CLI で確認）。

## タグ

- 本文に `#tag` と書くか、frontmatter に `tags: [a, b]` と書く。
- `/` で階層にできる（`#work/projects/website`）。
- 日本語のタグ（`#調査`）も認識された（CLI で確認）。
- 一覧は `foam list tags`、検索は `foam search --tag <tag>`。

## frontmatter

Foam が特別に扱うのは次の 4 つで、ほかは独自プロパティになる。frontmatter はファイルの先頭に置く。

| キー | 意味 |
| --- | --- |
| `title` | グラフなどに出る名前。ファイル名や最初の見出しより優先される |
| `type` | グラフでの表示の種類。既定は `note` |
| `tags` | タグ |
| `alias` | 別名。リンクの補完候補に出る。`foam note show` の `Aliases:` に出た（CLI で確認） |

独自プロパティは `foam search --property key=value` で検索できる。

## リンク参照定義

- 設定 `foam.edit.linkReferenceDefinitions` を有効にすると、Foam がファイル末尾に `[Data Science]: data-science.md 'Data Science'` のような定義を自動で書き足す。値は `off`（既定）、`withoutExtensions`、`withExtensions`。
- 他の Markdown ツールや公開用の変換で wikilink を読めるようにするためのもの。このリポジトリでは設定しておらず（`off`）、有効にすると全ノートが書き換わるため、勝手に有効にしない。
