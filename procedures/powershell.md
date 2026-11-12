# PowerShell コマンド対応表

ファイルの読み書きは Read/Write/Edit/Glob/Grep ツールを優先し、シェルは下表の用途だけに使う。

| 用途 | PowerShell |
|---|---|
| 現在の日付・時刻・曜日 | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/now.ps1` |
| 週番号と月〜金の日付 | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/get-week.ps1 [-Date 2026-04-16]` |
| ディレクトリ作成 | `New-Item -ItemType Directory -Force -Path '10_Daily/2026/04' \| Out-Null` |
| 存在確認 | `Test-Path '10_Daily/2026/04/16.md'` |
| 一覧 | `Get-ChildItem -Path '10_Daily/2026/04' -File` |
| 直近のdailyを探す | `Get-ChildItem -Path 10_Daily -Recurse -File -Filter '*.md' \| Sort-Object FullName -Descending \| Select-Object -First 5 -ExpandProperty FullName` |
| 移動（アーカイブ等） | `Move-Item -LiteralPath '<元>' -Destination '99_Archive/<先>'` |
| Git | `git status` / `git diff` / `git log` / `git add -A` / `git commit -m "docs(daily): 2026-04-16 の作業ログを記録した"` |

## 注意
- コマンドの連結は `;` を使う。`&&` と `||` は Windows PowerShell 5.1 では使えない。
- 削除系コマンドは使わない（Move-Item で 99_Archive/ へ移動する）。
- パスは `/` 区切りで書く。空白や日本語を含むパスは引用符で囲む。
- bash が必要なときは Git 同梱の bash を使う（AGENTS.md の「実行環境」）。PATH 上の `bash` は WSL を指すことがあるので、`bash` だけで呼ばない。パスは `git.exe` の場所（`<Git>\cmd\git.exe`）から求め、フルパスで呼ぶ: `$gitBash = Join-Path (Split-Path (Split-Path (Get-Command git).Source)) 'bin/bash.exe'; & $gitBash -lc '<コマンド>'`