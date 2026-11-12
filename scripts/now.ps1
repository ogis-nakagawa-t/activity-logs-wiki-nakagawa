# Print current date/time in a fixed, culture-independent format.
$now = Get-Date
$ci = [System.Globalization.CultureInfo]::InvariantCulture
'date={0} time={1} weekday={2}' -f $now.ToString('yyyy-MM-dd', $ci), $now.ToString('HH:mm', $ci), $now.ToString('ddd', $ci)