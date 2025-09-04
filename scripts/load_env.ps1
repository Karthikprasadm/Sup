param([string]$Path = ".env")
if (-not (Test-Path $Path)) { Write-Error "Missing $Path"; exit 1 }
Get-Content $Path | ForEach-Object {
  if ($_ -match '^\s*$' -or $_ -match '^\s*#') { return }
  if ($_ -match '^\s*([^=]+)\s*=\s*(.*)\s*$') {
    $k=$matches[1].Trim(); $v=$matches[2]
    # strip surrounding quotes if present
    if ($v -match '^\s*"(.*)"\s*$') { $v=$matches[1] }
    [Environment]::SetEnvironmentVariable($k,$v,'Process')
  }
}
