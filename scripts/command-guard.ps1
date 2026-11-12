# PreToolUse hook for GitHub Copilot and Claude Code.
# Copilot does not read .claude/settings.json, so this hook enforces the same denials there.
# Claude Code also runs it (Bash|PowerShell), because a permission deny rule cannot carry
# the rm exception below.
# Denies: delete commands, git push, git reset --hard, and reading .env / .env.*.
# Exception: "rm -rf <dir>/.ua/intermediate" (or .understand-anything/intermediate, or
# "$UA_DIR/intermediate") as a whole command segment, used by procedures/knowledge-graph.md.
# Reads the hook JSON from stdin. On deny: prints permissionDecision JSON and exits 2.
. "$PSScriptRoot/hook-common.ps1"

$payload = Read-HookPayload
if (-not $payload) { exit 0 }
$toolArgs = Get-HookToolArgs $payload

$reason = $null
$command = Get-HookCommand $toolArgs

if ($command) {
  # Start of a command segment: after ; & | ( { ` a quote or a newline, optionally followed by
  # shell keywords or wrappers (then, do, sudo, xargs, ...).
  $segStart = '(^|[;&|({\n`"'']\s*)((then|do|else|elif|sudo|command|exec|nohup|time|xargs)\s+)*'
  # Delete commands at the start of a segment, also with a path prefix such as /bin/rm.
  $deletePattern = '(?im)' + $segStart + '([\w.~/\\-]*[\\/])?(Remove-Item|rm|del|erase|ri|rd|rmdir)(\s|$|[;)"''`])'
  $envPattern = '(^|[\s''"\\/=])\.env(\.[\w.-]+)?($|[\s''";|)])'
  # The only allowed delete: the understand-anything intermediate directory, with nothing else
  # in the same segment. Strip those segments before checking for delete commands.
  $allowedRmPattern = '(?im)' + $segStart + 'rm\s+-rf\s+(?<q>["'']?)(\$UA_DIR|\$\{UA_DIR\}|([\w./-]*/)?\.(ua|understand-anything))/intermediate/?\k<q>(?=\s*($|[;&|)}\n]))'
  $checked = [regex]::Replace($command, $allowedRmPattern, '$1')
  # Keep this file ASCII-only: Windows PowerShell 5.1 misreads BOM-less UTF-8.
  if ([regex]::IsMatch($checked, $deletePattern)) {
    $reason = 'Denied by AGENTS.md: do not delete files. Move unneeded files to 99_Archive/ with Move-Item. The only exception is "rm -rf 90_Wiki/.ua/intermediate" (procedures/knowledge-graph.md).'
  } elseif ([regex]::IsMatch($command, '(?i)\bgit\s+push\b')) {
    $reason = 'Denied by AGENTS.md: do not run git push. The user pushes.'
  } elseif ([regex]::IsMatch($command, '(?i)\bgit\s+reset\s+(.*\s)?--hard\b')) {
    $reason = 'Denied by AGENTS.md: do not run git reset --hard.'
  } elseif ([regex]::IsMatch($command, $envPattern)) {
    $reason = 'Denied: do not read .env or .env.* (they may contain credentials).'
  }
} else {
  foreach ($path in (Get-HookFilePaths $toolArgs)) {
    if ([regex]::IsMatch($path, '(^|[\\/])\.env(\.[^\\/]*)?$')) {
      $reason = 'Denied: do not read .env or .env.* (they may contain credentials).'
      break
    }
  }
}

if (-not $reason) { exit 0 }

Write-HookJson @{
  permissionDecision       = 'deny'
  permissionDecisionReason = $reason
  hookSpecificOutput       = @{
    hookEventName            = 'PreToolUse'
    permissionDecision       = 'deny'
    permissionDecisionReason = $reason
  }
}
[Console]::Error.WriteLine($reason)
exit 2
