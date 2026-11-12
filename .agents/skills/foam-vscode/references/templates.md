# テンプレートと日次ノート

出典（2026-10-21 取得）:

- https://docs.foam.md/features/templates/
- https://docs.foam.md/features/daily-notes/
- https://docs.foam.md/tools/cli/daily/

「CLI で確認」と書いた項目は、scratchpad の検証用ワークスペースで foam-cli 0.46.4 を実行して確かめた。

## 置き場所と特別な名前

- テンプレートは `.foam/templates/` に置く。Markdown（`.md`）と JavaScript（`.js`）がある。
- 次の名前は特別扱いされる（`.js` が先に探される）。

  | ファイル | 使われる場面 |
  | --- | --- |
  | `.foam/templates/new-note.js` / `new-note.md` | `Foam: Create New Note`、`foam note create` |
  | `.foam/templates/daily-note.js` / `daily-note.md` | `Foam: Open Today's Note`（Alt+D）、`Foam: Open Daily Note`（Alt+H）、`foam daily` |

- それ以外の名前は、`Foam: Create New Note From Template` で選んだときだけ使われる。`foam list templates` で一覧できる。
- このリポジトリの日次ノートのテンプレートは `.foam/templates/daily-note.md` である（以前は `10_Daily.md` という名前で、Alt+D に使われていなかった）。

## `foam_template` メタデータ

テンプレートの frontmatter に書く。ノートを作るときには取り除かれる（CLI で確認）。

```yaml
foam_template:
    filepath: "/10_Daily/${FOAM_DATE_YEAR}/${FOAM_DATE_MONTH}/${FOAM_DATE_DATE}.md"
    name: "日次ノート"
    description: "Daily note template for IT technical work"
```

| キー | 意味 |
| --- | --- |
| `filepath` | 作るノートのパス。ワークスペースの外は指定できない |
| `name` | テンプレート選択画面に出る名前 |
| `description` | テンプレート選択画面に出る説明 |

- `foam_template` の直後の行に、ブロック形式の YAML で書く。
- メタデータの中では Foam の変数は使えるが、VS Code のスニペット変数は使えない。

## 変数

Markdown テンプレートでは、VS Code のスニペット変数に加えて次の Foam 変数が使える。書き方は `${FOAM_TITLE}` か `$FOAM_TITLE`。

| 変数 | 内容 |
| --- | --- |
| `FOAM_TITLE` | ノートのタイトル |
| `FOAM_TITLE_SAFE` | ファイル名に使える形にしたタイトル |
| `FOAM_SLUG` | タイトルのスラッグ |
| `FOAM_SELECTED_TEXT` | エディタで選択していたテキスト |
| `FOAM_CURRENT_DIR` | 現在のディレクトリ |
| `FOAM_PREVIOUS_DAILY_NOTE` | 直近の既存の日次ノート。daily-note テンプレートでのみ使える。`${FOAM_PREVIOUS_DAILY_NOTE:なし}` で既定値を指定できる |
| `FOAM_DATE_FORMAT` | dayjs の書式で日付を出す。例: `${FOAM_DATE_FORMAT:YYYY-MM-DD}`。`${FOAM_DATE_FORMAT:ddd}` は OS のロケールにかかわらず `Fri` の形になった（CLI で確認） |
| `FOAM_DATE_YEAR`、`FOAM_DATE_MONTH`、`FOAM_DATE_DATE` | 年、月（2 桁）、日（2 桁） |
| `FOAM_DATE_DAY_NAME`、`FOAM_DATE_DAY_NAME_SHORT` | 曜日。OS のロケールに従う（この環境では `金`。`.vscode/settings.json` の `foam.dateLocale` は foam-cli には効かなかった。CLI で確認） |
| `FOAM_DATE_WEEK`、`FOAM_DATE_WEEK_YEAR`、`FOAM_DATE_DAY_ISO` | 週番号、週の年、ISO の曜日番号 |
| `FOAM_DATE_HOUR`、`FOAM_DATE_MINUTE`、`FOAM_DATE_SECOND`、`FOAM_DATE_SECONDS_UNIX` | 時刻 |

docs の一覧は「など」で終わっており、全変数ではない。ここに無い変数を使う前に docs で確かめる。

### 存在しない変数

`FOAM_DATE_YESTERDAY` と `FOAM_DATE_TOMORROW` は無い。使うと展開されずに文字のまま残る（CLI で確認）。以前のこのリポジトリのテンプレートは、これを前日・翌日のリンクに使っていた。

```markdown
前: [[10_Daily/2026/10/${FOAM_DATE_YESTERDAY}|昨日]] | 次: [[10_Daily/2026/10/${FOAM_DATE_TOMORROW}|明日]]
```

### `FOAM_PREVIOUS_DAILY_NOTE` の値

値は角かっこなしの識別子で、作成時点で一意になる最短の形になる。検証用ワークスペースでの結果:

| 状況 | 値 |
| --- | --- |
| 直近の日次ノートが `10_Daily/2026/10/26.md` で、ほかに `26.md` が無い | `26` |
| 直近が `10_Daily/2026/10/21.md` で、`10_Daily/2026/09/21.md` もある | `10/21` |
| 前の日次ノートが無い（`${FOAM_PREVIOUS_DAILY_NOTE:なし}` と書いた場合） | `なし` |

リンクにするには `[[${FOAM_PREVIOUS_DAILY_NOTE}]]` と書く。後で同じ日の別の月のノートができると、このリンクは曖昧になる（[syntax.md](syntax.md) の曖昧な識別子を参照）。このリポジトリのテンプレートは `前: [[${FOAM_PREVIOUS_DAILY_NOTE}|前回]]` としており、エージェントが業務開始時にパス付きリンクに直す。テンプレートファイル自体のこのリンクは、`foam list placeholders` に `${FOAM_PREVIOUS_DAILY_NOTE}` として出る。VS Code の `foam.placeholders.exclude` 設定は foam-cli の出力には効かなかった（CLI で確認）。

## 日次ノート

- 開き方: 今日の分は `Foam: Open Today's Note`（Alt+D）、日付を選ぶなら `Foam: Open Daily Note`（Alt+H）。docs は前者も「Open Daily Note」と呼んでいるが、拡張 0.46.0 のコマンド名はこのとおり。設定 `foam.openDailyNote.onStartup` を `true` にすると、起動時に開く。
- 保存先は次の順で決まる（`foam daily` も同じ）。
  1. `.foam/templates/daily-note.md`（または `.js`）の `filepath`
  2. 非推奨の `foam.openDailyNote.*` 設定
  3. どちらも無ければ `journals/YYYY-MM-DD.md`（docs には `journal/` とあるが、0.46.4 では `journals/` だった。CLI で確認）
- このリポジトリでは `daily-note.md` の `filepath` により、`foam daily --path-only` が `10_Daily\2026\10\21.md` を返す（CLI で確認）。検証用ワークスペースでテンプレートを展開すると、`weekday: Fri`、`前: [[20|前回]] | 次: （次回の業務開始時に記入）` となり、`foam_template` は取り除かれた。
- 本文中で使えるスニペット: `/today`、`/tomorrow`、`/yesterday`、`/monday`、`/+1d`、`/-3d`、`/+1w`、`/-1m`、`/+1y`。その日付の日次ノートへのリンクを入れる。

## JavaScript テンプレート

- `async function createNote({ trigger, foam, resolver, foamDate })` を export し、`{ content, filepath }` を返す。
- 変数は `resolver.resolveFromName('FOAM_TITLE')` で読む。`FOAM_PREVIOUS_DAILY_NOTE` は使えない。
- 信頼済みのワークスペースでしか動かず、CLI では `--trust` が要る。`foam mcp` では使えない。docs は、サンドボックスがセキュリティ境界ではないと明記している。このリポジトリでは Markdown テンプレートだけを使う。
