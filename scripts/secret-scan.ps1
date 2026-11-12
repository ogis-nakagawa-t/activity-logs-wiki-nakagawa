# PostToolUse hook: scan the file just written for secret-like strings.
# Reads the hook JSON from stdin.
#   Claude Code (default): exit code 2 sends stderr back to Claude.
#   -Copilot: GitHub Copilot ignores stderr on exit 2 for postToolUse, so print
#             additionalContext as JSON on stdout and exit 0.
param([switch]$Copilot)

$pattern = '(AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|ghp_[A-Za-z0-9]{36}|xox[baprs]-[A-Za-z0-9-]+|(password|passwd|secret|token|api[_-]?key)\s*[:=]\s*\S{8,})'

function Test-Secret([string]$file) {
  if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { return $false }
  $text = Get-Content -LiteralPath $file -Raw -Encoding UTF8
  return [bool]($text -and [regex]::IsMatch($text, $pattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase))
}

if ($Copilot) {
  . "$PSScriptRoot/hook-common.ps1"
  $payload = Read-HookPayload
  if (-not $payload) { exit 0 }
  $hits = @(Get-HookFilePaths (Get-HookToolArgs $payload) |
    ForEach-Object { Resolve-HookPath $_ $payload } |
    Where-Object { Test-Secret $_ })
  if ($hits.Count -eq 0) { exit 0 }
  $message = "Possible secret detected in: $($hits -join ', '). Mask the matching part with *** and tell the user."
  Write-HookJson @{
    additionalContext  = $message
    hookSpecificOutput = @{ hookEventName = 'PostToolUse'; additionalContext = $message }
  }
  exit 0
}

try { [Console]::InputEncoding = [System.Text.Encoding]::UTF8 } catch {}
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

$raw = [Console]::In.ReadToEnd()
if ([string]::IsNullOrWhiteSpace($raw)) { exit 0 }

try { $payload = $raw | ConvertFrom-Json } catch { exit 0 }
$file = $payload.tool_input.file_path
if (-not $file) { exit 0 }

if (Test-Secret $file) {
  [Console]::Error.WriteLine("Possible secret detected in: $file. Mask the matching part with *** and tell the user.")
  exit 2
}
exit 0
