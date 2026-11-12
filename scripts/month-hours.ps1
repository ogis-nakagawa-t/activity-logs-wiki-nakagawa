# Aggregate a month of hours from the daily notes (10_Daily/YYYY/MM/DD.md, the hours section)
# by project ID, for pasting into the Excel time-entry workbook (procedures/monthly-hours.md).
#   -Format tsv    : one line per ID in the profile.md order; fields are day 1..last day (blank = no hours).
#   -Format md     : the full table with the Excel header columns, a total row and notes.
#   -Format report : monthly totals, IDs not in the order list, unregistered @[...], invalid hours.
#   -Write         : write the tsv and md to 70_<hours-entry>/YYYY/MM.{tsv,md} (UTF-8 without BOM, LF),
#                    then print the written paths and the report.
# Keep this file ASCII-only: Windows PowerShell 5.1 misreads BOM-less UTF-8.
param(
  [Parameter(Mandatory = $true)][int]$Year,
  [Parameter(Mandatory = $true)][ValidateRange(1, 12)][int]$Month,
  [string]$Root = (Split-Path -Parent $PSScriptRoot),
  [ValidateSet('tsv', 'md', 'report')][string]$Format = 'tsv',
  [switch]$Write
)

$ci = [System.Globalization.CultureInfo]::InvariantCulture
$ja = [System.Globalization.CultureInfo]::GetCultureInfo('ja-JP')
$utf8 = New-Object System.Text.UTF8Encoding($false)
# Build a string from code points (the Japanese labels), keeping this file ASCII-only.
function J { -join ($args | ForEach-Object { [char][int]$_ }) }

# Purpose code: only the holiday project gets one.
$holidayId = 'A295482100'
$holidayPurpose = 'HLD'

$hoursWord = J 0x5de5 0x6570
$projectId = (J 0x30d7 0x30ed 0x30b8 0x30a7 0x30af 0x30c8) + 'ID'
$orderHeading = (J 0x6708 0x672b 0x51e6 0x7406 0x306e) + $hoursWord + (J 0x5165 0x529b 0x3067 0x5165 0x529b 0x3059 0x308b) + $projectId + (J 0x306e 0x9806 0x756a)
$hoursHeadingPattern = '^##\s.*' + $hoursWord + '\s*$'
$uncategorized = J 0x672a 0x5206 0x985e
$dayLabel = J 0x65e5
$totalLabel = J 0x5408 0x8a08
$monthTotalLabel = J 0x6708 0x9593 0x8a08
$none = J 0x306a 0x3057
$outDirName = '70_' + $hoursWord + (J 0x5165 0x529b)

function Fail([string]$message) {
  [Console]::Error.WriteLine($message)
  exit 1
}

function Read-Lines([string]$path) {
  [System.IO.File]::ReadAllLines($path, $utf8)
}

# Split a Markdown table row into trimmed cells. Returns $null for non-table lines.
function Split-Row([string]$line) {
  $t = $line.Trim()
  if (-not $t.StartsWith('|')) { return $null }
  $t = $t.Substring(1)
  if ($t.EndsWith('|')) { $t = $t.Substring(0, $t.Length - 1) }
  , @($t.Split('|') | ForEach-Object { $_.Trim() })
}

function Format-Hours([decimal]$v) {
  if ($v -eq 0) { return '' }
  $v.ToString('0.####', $ci)
}

$days = [DateTime]::DaysInMonth($Year, $Month)
$monthLabel = '{0:D4}-{1:D2}' -f $Year, $Month

# --- project-codes.md: key -> code, code -> first project name ---
$codeByKey = @{}
$nameByCode = @{}
$codesPath = Join-Path $Root 'project-codes.md'
if (Test-Path -LiteralPath $codesPath) {
  foreach ($line in (Read-Lines $codesPath)) {
    $cells = Split-Row $line
    if ($null -eq $cells -or $cells.Count -lt 3) { continue }
    $code = $cells[2].ToUpperInvariant()
    if ($code -notmatch '^[A-Z0-9]+$') { continue }
    if (-not $codeByKey.ContainsKey($cells[0])) { $codeByKey[$cells[0]] = $code }
    if (-not $nameByCode.ContainsKey($code) -and $cells.Count -ge 7) { $nameByCode[$code] = $cells[6] }
  }
}

# --- profile.md: the project ID order (and an optional memo used as the project name) ---
$profilePath = Join-Path $Root 'profile.md'
if (-not (Test-Path -LiteralPath $profilePath)) { Fail 'profile.md not found.' }
$order = New-Object System.Collections.Generic.List[string]
$memo = @{}
$inSection = $false
$found = $false
foreach ($line in (Read-Lines $profilePath)) {
  if ($line -match '^#{1,2}\s') {
    $inSection = ($line -match ('^##\s+' + [regex]::Escape($orderHeading) + '\s*$'))
    if ($inSection) { $found = $true }
    continue
  }
  if (-not $inSection) { continue }
  # "- <ID> <memo>" or "1. <ID> <memo>"; the memo is used as the project name in the md table.
  if ($line -match '^\s*(?:[-*]|\d+[.)])\s+`?([A-Za-z0-9]+)`?\s*(.*)$') {
    $id = $Matches[1].ToUpperInvariant()
    if ($order.Contains($id)) { Fail ("Duplicate project ID in profile.md order list: {0}" -f $id) }
    $order.Add($id)
    $memo[$id] = $Matches[2].Trim()
  }
}
if (-not $found) { Fail ("Section '## {0}' not found in profile.md." -f $orderHeading) }
if ($order.Count -eq 0) { Fail ("Section '## {0}' in profile.md has no '- <project ID>' or '1. <project ID>' lines." -f $orderHeading) }

# --- daily notes ---
$byId = @{}
$unregistered = New-Object System.Collections.Generic.List[object]
$invalid = New-Object System.Collections.Generic.List[object]
$noteCount = 0
$dailyDir = Join-Path $Root ('10_Daily/{0:D4}/{1:D2}' -f $Year, $Month)
if (Test-Path -LiteralPath $dailyDir) {
  $files = Get-ChildItem -LiteralPath $dailyDir -File | Where-Object { $_.Name -match '^\d{2}\.md$' } | Sort-Object Name
  foreach ($file in $files) {
    $day = [int]$file.Name.Substring(0, 2)
    if ($day -lt 1 -or $day -gt $days) { continue }
    $noteCount++
    $inHours = $false
    $tableRow = 0
    foreach ($line in (Read-Lines $file.FullName)) {
      if ($line -match $hoursHeadingPattern) { $inHours = $true; continue }
      if (-not $inHours) { continue }
      if ($line -match '^##\s' -or $line -match '^---\s*$') { break }
      $cells = Split-Row $line
      if ($null -eq $cells) { continue }
      # The first row is the table header (its first cell is @[category/project]).
      $tableRow++
      if ($tableRow -eq 1 -or $cells.Count -lt 4) { continue }
      if ($cells[0] -notmatch '^@\[(.+)\]$') { continue }
      $label = $cells[0]
      $key = $Matches[1]
      $slash = $key.LastIndexOf('/')
      if ($slash -ge 0) { $key = $key.Substring($slash + 1) }
      $task = $cells[2]
      $raw = $cells[3]
      $hours = [decimal]0
      if (-not [decimal]::TryParse($raw, [System.Globalization.NumberStyles]::Number, $ci, [ref]$hours)) {
        $invalid.Add([pscustomobject]@{ Day = $day; Label = $label; Task = $task; Raw = $raw })
        continue
      }
      if ($hours -eq 0) { continue }
      $code = $cells[1].ToUpperInvariant()
      if ($code -eq '' -and $key -ne $uncategorized -and $codeByKey.ContainsKey($key)) { $code = $codeByKey[$key] }
      if ($code -eq '') {
        $unregistered.Add([pscustomobject]@{ Day = $day; Label = $label; Task = $task; Hours = $hours })
        continue
      }
      if (-not $byId.ContainsKey($code)) { $byId[$code] = New-Object 'decimal[]' ($days + 1) }
      $byId[$code][$day] += $hours
    }
  }
}

function Get-Days([string]$id) {
  if ($byId.ContainsKey($id)) { return , $byId[$id] }
  , (New-Object 'decimal[]' ($days + 1))
}

function Get-Total([decimal[]]$arr) {
  $sum = [decimal]0
  for ($d = 1; $d -le $days; $d++) { $sum += $arr[$d] }
  $sum
}

function Get-DayList([decimal[]]$arr) {
  $parts = for ($d = 1; $d -le $days; $d++) {
    if ($arr[$d] -ne 0) { '{0}{1} {2}' -f $d, $dayLabel, (Format-Hours $arr[$d]) }
  }
  (@($parts) -join ', ')
}

$outside = @($byId.Keys | Where-Object { -not $order.Contains($_) } | Sort-Object)

function Get-TsvLines {
  foreach ($id in $order) {
    $arr = Get-Days $id
    (@(for ($d = 1; $d -le $days; $d++) { Format-Hours $arr[$d] }) -join "`t")
  }
}

function Get-MdLines {
  $head = @(((J 0x4ee3 0x8868) + '<br/>PJ'), ((J 0x5272 0x5408) + '<br/>(%)'), $projectId, '',
    ((J 0x30d7 0x30ed 0x30b8 0x30a7 0x30af 0x30c8 0x540d 0x79f0)), (J 0x76ee 0x7684 0x30b3 0x30fc 0x30c9), '', $monthTotalLabel)
  $head += @(for ($d = 1; $d -le $days; $d++) { '{0}{1}' -f $d, $dayLabel })
  $weekdays = @('', '', '', '', '', '', '', '')
  $weekdays += @(for ($d = 1; $d -le $days; $d++) { '({0})' -f (Get-Date -Year $Year -Month $Month -Day $d).ToString('ddd', $ja) })
  $row = { param($cells) '| ' + (($cells | ForEach-Object { $_ -replace '\|', '\|' }) -join ' | ') + ' |' }

  '# {0} {1}' -f $monthLabel, ($hoursWord + (J 0x5165 0x529b 0x30c7 0x30fc 0x30bf))
  ''
  & $row $head
  '|' + ((@($head | ForEach-Object { ' --- ' })) -join '|') + '|'
  & $row $weekdays
  $dayTotals = New-Object 'decimal[]' ($days + 1)
  foreach ($id in $order) {
    $arr = Get-Days $id
    $name = $memo[$id]
    if (-not $name -and $nameByCode.ContainsKey($id)) { $name = $nameByCode[$id] }
    $purpose = ''
    if ($id -eq $holidayId) { $purpose = $holidayPurpose }
    $cells = @('', '', $id, '', $name, $purpose, '', (Format-Hours (Get-Total $arr)))
    $cells += @(for ($d = 1; $d -le $days; $d++) { $dayTotals[$d] += $arr[$d]; Format-Hours $arr[$d] })
    & $row $cells
  }
  $cells = @(('**{0}**' -f $totalLabel), '', '', '', '', '', '', (Format-Hours (Get-Total $dayTotals)))
  $cells += @(for ($d = 1; $d -le $days; $d++) { Format-Hours $dayTotals[$d] })
  & $row $cells
  ''
  '## ' + (J 0x30ea 0x30b9 0x30c8 0x5916 0x306e) + $projectId
  ''
  if ($outside.Count -eq 0) { $none }
  foreach ($id in $outside) {
    $arr = $byId[$id]
    $name = ''
    if ($nameByCode.ContainsKey($id)) { $name = ' ' + $nameByCode[$id] }
    '- {0}{1} ({2} {3}): {4}' -f $id, $name, $monthTotalLabel, (Format-Hours (Get-Total $arr)), (Get-DayList $arr)
  }
  ''
  '## ' + (J 0x672a 0x767b 0x9332 0x306e) + ' @[' + (J 0x2026) + ']'
  ''
  if ($unregistered.Count -eq 0) { $none }
  foreach ($u in $unregistered) {
    '- {0}{1}: {2} {3} {4}' -f $u.Day, $dayLabel, $u.Label, $u.Task, (Format-Hours $u.Hours)
  }
}

function Get-ReportLines {
  'month={0} days={1} daily_notes={2}' -f $monthLabel, $days, $noteCount
  '[totals]'
  foreach ($id in $order) { "{0}`t{1}" -f $id, (Format-Hours (Get-Total (Get-Days $id))) }
  '[not_in_order_list]'
  foreach ($id in $outside) { "{0}`t{1}`t{2}" -f $id, (Format-Hours (Get-Total $byId[$id])), (Get-DayList $byId[$id]) }
  '[unregistered]'
  foreach ($u in $unregistered) { "{0}-{1:D2}`t{2}`t{3}`t{4}" -f $monthLabel, $u.Day, $u.Label, $u.Task, (Format-Hours $u.Hours) }
  '[invalid_hours]'
  foreach ($u in $invalid) { "{0}-{1:D2}`t{2}`t{3}`t{4}" -f $monthLabel, $u.Day, $u.Label, $u.Task, $u.Raw }
}

if ($Write) {
  # Write the files here, not through the agent's file tool: tool output drops trailing tabs,
  # so the TSV cannot be copied back reliably. Encoding is fixed to UTF-8 without BOM and LF.
  $outRel = '{0}/{1:D4}' -f $outDirName, $Year
  $outDir = Join-Path $Root $outRel
  New-Item -ItemType Directory -Force -Path $outDir | Out-Null
  foreach ($ext in 'tsv', 'md') {
    if ($ext -eq 'tsv') { $lines = @(Get-TsvLines) } else { $lines = @(Get-MdLines) }
    $path = Join-Path $outDir ('{0:D2}.{1}' -f $Month, $ext)
    [System.IO.File]::WriteAllText($path, (($lines -join "`n") + "`n"), $utf8)
    'wrote {0}/{1:D2}.{2}' -f $outRel, $Month, $ext
  }
  Get-ReportLines
} else {
  switch ($Format) {
    'tsv' { Get-TsvLines }
    'md' { Get-MdLines }
    'report' { Get-ReportLines }
  }
}
