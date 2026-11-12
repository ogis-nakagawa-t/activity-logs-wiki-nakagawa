# Print ISO week label, Monday, Friday, and daily-file status (Mon-Fri) for the week of -Date.
param([datetime]$Date = (Get-Date))

$ci = [System.Globalization.CultureInfo]::InvariantCulture
$root = Split-Path -Parent $PSScriptRoot

$d = $Date.Date
$dow = [int]$d.DayOfWeek
if ($dow -eq 0) { $dow = 7 }
$monday = $d.AddDays(1 - $dow)
$friday = $monday.AddDays(4)
$thursday = $monday.AddDays(3)
$week = [int][math]::Ceiling($thursday.DayOfYear / 7)

'{0}-W{1:D2}' -f $thursday.Year, $week
$monday.ToString('yyyy-MM-dd', $ci)
$friday.ToString('yyyy-MM-dd', $ci)

0..4 | ForEach-Object {
  $day = $monday.AddDays($_)
  $rel = '10_Daily/{0}/{1}/{2}.md' -f $day.ToString('yyyy', $ci), $day.ToString('MM', $ci), $day.ToString('dd', $ci)
  '{0} {1} {2}' -f $day.ToString('yyyy-MM-dd', $ci), $rel, (Test-Path -LiteralPath (Join-Path $root $rel))
}
