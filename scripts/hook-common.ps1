# Shared helpers for the GitHub Copilot hooks (.github/hooks/agent-hooks.json).
# Dot-source this file: . "$PSScriptRoot/hook-common.ps1"
# Accepts both payload shapes:
#   Copilot CLI (camelCase): toolName, toolArgs (object or JSON string), cwd
#   VS Code / Claude-compatible (snake_case): tool_name, tool_input, cwd
try { [Console]::InputEncoding = [System.Text.Encoding]::UTF8 } catch {}
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

$script:RepoRoot = Split-Path -Parent $PSScriptRoot

function Read-HookPayload {
  $raw = [Console]::In.ReadToEnd()
  if ([string]::IsNullOrWhiteSpace($raw)) { return $null }
  # Set AGENT_HOOK_DEBUG to a directory to save every payload for inspection.
  if ($env:AGENT_HOOK_DEBUG) {
    try {
      $name = 'payload-{0}-{1}.json' -f (Get-Date -Format 'yyyyMMdd-HHmmss-fff'), $PID
      [System.IO.File]::WriteAllText((Join-Path $env:AGENT_HOOK_DEBUG $name), $raw, (New-Object System.Text.UTF8Encoding $false))
    } catch {}
  }
  try { return $raw | ConvertFrom-Json } catch { return $null }
}

function Get-HookToolName($payload) {
  if ($payload.toolName) { return [string]$payload.toolName }
  if ($payload.tool_name) { return [string]$payload.tool_name }
  return ''
}

function Get-HookToolArgs($payload) {
  $toolArgs = $payload.toolArgs
  if ($null -eq $toolArgs) { $toolArgs = $payload.tool_input }
  if ($toolArgs -is [string]) {
    try { $toolArgs = $toolArgs | ConvertFrom-Json } catch { return $null }
  }
  return $toolArgs
}

# Collect file paths from the tool arguments (path / filePath / file_path at any depth,
# and "*** Add File:" / "*** Update File:" lines of an apply_patch input).
function Get-HookFilePaths($toolArgs) {
  $found = New-Object System.Collections.Generic.List[string]
  $walk = {
    param($node, $depth)
    if ($null -eq $node -or $depth -gt 5) { return }
    if ($node -is [System.Array]) {
      foreach ($item in $node) { & $walk $item ($depth + 1) }
      return
    }
    if ($node -isnot [System.Management.Automation.PSCustomObject]) { return }
    foreach ($prop in $node.PSObject.Properties) {
      if ($prop.Value -is [string]) {
        if ($prop.Name -in @('path', 'filePath', 'file_path')) { $found.Add($prop.Value) }
        foreach ($m in [regex]::Matches($prop.Value, '(?m)^\*\*\* (?:Add|Update) File: (.+?)\s*$')) {
          $found.Add($m.Groups[1].Value)
        }
      } else {
        & $walk $prop.Value ($depth + 1)
      }
    }
  }
  & $walk $toolArgs 0
  return $found | Select-Object -Unique
}

function Resolve-HookPath([string]$path, $payload) {
  if ([System.IO.Path]::IsPathRooted($path)) { return $path }
  $base = $payload.cwd
  if (-not $base) { $base = $script:RepoRoot }
  return Join-Path $base $path
}

function Get-HookCommand($toolArgs) {
  if ($null -eq $toolArgs) { return '' }
  if ($toolArgs.command) { return [string]$toolArgs.command }
  return ''
}

# Emit exactly one JSON object on stdout (several objects are ignored as invalid JSON).
function Write-HookJson($object) {
  [Console]::Out.Write(($object | ConvertTo-Json -Compress -Depth 5))
}
