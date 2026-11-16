$ErrorActionPreference = 'Stop'

# --- Paths -------------------------------------------------------------
$cfgDir  = Join-Path $env:APPDATA 'Claude'
$cfgPath = Join-Path $cfgDir 'claude_desktop_config.json'
$extDir  = Join-Path $env:APPDATA 'pyRevit\Extensions\mcp-server-for-revit-python.extension'
$mainPy  = Join-Path $extDir 'main.py'
$uvExe   = Join-Path $env:USERPROFILE '.local\bin\uv.exe'

Write-Host "=== Preflight ==="
Write-Host "config  : $cfgPath"
Write-Host "main.py : $mainPy"
Write-Host "uv.exe  : $uvExe"

if (-not (Test-Path $mainPy)) { throw "main.py not found at $mainPy" }
if (-not (Test-Path $uvExe))  { throw "uv.exe not found at $uvExe" }

$uvOnPath = (Get-Command uv -ErrorAction SilentlyContinue)
if ($uvOnPath) { Write-Host "uv on PATH: $($uvOnPath.Source)" } else { Write-Host "uv on PATH: NO (using absolute path)" }
Write-Host ("uv version: " + (& $uvExe --version))

# --- Load existing config (PS 5.1 compatible) --------------------------
function ConvertTo-Hash($o) {
  if ($null -eq $o) { return $null }
  if ($o -is [System.Management.Automation.PSCustomObject]) {
    $h = @{}
    foreach ($p in $o.PSObject.Properties) { $h[$p.Name] = ConvertTo-Hash $p.Value }
    return $h
  }
  if (($o -is [System.Collections.IEnumerable]) -and ($o -isnot [string])) {
    return @(foreach ($i in $o) { ConvertTo-Hash $i })
  }
  return $o
}

if (-not (Test-Path $cfgDir)) { New-Item -ItemType Directory -Path $cfgDir -Force | Out-Null }

$cfg = @{}
if (Test-Path $cfgPath) {
  $stamp  = Get-Date -Format 'yyyyMMdd-HHmmss'
  $backup = "$cfgPath.bak-$stamp"
  Copy-Item $cfgPath $backup -Force
  Write-Host "backup  : $backup"

  $raw = Get-Content $cfgPath -Raw
  if (-not [string]::IsNullOrWhiteSpace($raw)) {
    $cfg = ConvertTo-Hash ($raw | ConvertFrom-Json)
  }
} else {
  Write-Host "backup  : (no existing config; creating a new one)"
}

if ($cfg -isnot [hashtable]) { $cfg = @{} }
if (-not $cfg.ContainsKey('mcpServers') -or $cfg['mcpServers'] -isnot [hashtable]) {
  $cfg['mcpServers'] = @{}
}

$existing = @($cfg['mcpServers'].Keys)
Write-Host ("existing mcpServers: " + ($(if ($existing.Count) { $existing -join ', ' } else { '(none)' })))

# --- Add / replace the Revit Connector entry ---------------------------
$cfg['mcpServers']['Revit Connector'] = @{
  command = $uvExe
  args    = @('run', '--frozen', '--directory', $extDir, 'mcp', 'run', $mainPy)
}

$json = $cfg | ConvertTo-Json -Depth 20
[System.IO.File]::WriteAllText($cfgPath, $json, (New-Object System.Text.UTF8Encoding($false)))

Write-Host ""
Write-Host "=== Wrote $cfgPath ==="
Get-Content $cfgPath -Raw

# --- Verify it parses and the entry is present -------------------------
$check = Get-Content $cfgPath -Raw | ConvertFrom-Json
if ($check.mcpServers.'Revit Connector'.command) {
  Write-Host ""
  Write-Host "RESULT: OK - 'Revit Connector' present, JSON parses."
} else {
  throw "RESULT: FAILED - entry missing after write."
}
