<#
.SYNOPSIS
    Build QuickSnake.exe - a single-file, windowed (no console) executable
    of the Quick Snake pygame game.

.REBUILD (the ONE command, run from the project root):
        .\build.ps1

    Equivalent direct PyInstaller call:
        .\.venv\Scripts\python.exe -m PyInstaller --noconfirm QuickSnake.spec

.REQUIREMENTS
    .venv with the runtime deps (requirements.txt: pygame==2.6.1).
    PyInstaller is installed automatically from requirements-build.txt
    if it is missing from the .venv.

.OUTPUT
    dist\QuickSnake.exe   (single file - ready to drop into a GitHub release)

.NOTES
    Bundle rules: settings.json, stats.dat, settings.json.bak, music/ and
    tests/ are NEVER bundled (PyInstaller `datas` stays empty; only code +
    pygame runtime binaries are packed). sfx/ is not bundled either - the
    WAVs are auto-generated at startup by game/audio.py (guarded).
#>
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$Py   = Join-Path $Root '.venv\Scripts\python.exe'
$Spec = Join-Path $Root 'QuickSnake.spec'
$Icon = Join-Path $Root 'assets\icon.ico'

if (-not (Test-Path $Py)) {
    throw "Missing venv Python at $Py. Create it first: py -3.12 -m venv .venv && .\.venv\Scripts\pip.exe install -r requirements.txt"
}

# 1) Ensure PyInstaller is available inside the .venv.
$ErrorActionPreference = 'Continue'   # native stderr must not throw
& $Py -m PyInstaller --version *> $null
$HasPyInstaller = $LASTEXITCODE -eq 0
$ErrorActionPreference = 'Stop'
if (-not $HasPyInstaller) {
    Write-Host 'PyInstaller not found in .venv - installing from requirements-build.txt ...'
    & (Join-Path $Root '.venv\Scripts\pip.exe') install -r (Join-Path $Root 'requirements-build.txt')
    if ($LASTEXITCODE -ne 0) { throw 'pip install of build requirements failed' }
}

# 2) Generate the icon if it is missing (stdlib-only procedural generator).
if (-not (Test-Path $Icon)) {
    Write-Host 'assets\icon.ico missing - generating it ...'
    & $Py (Join-Path $Root 'tools\make_icon.py')
    if ($LASTEXITCODE -ne 0) { throw 'icon generation failed' }
}

# 3) Clean previous outputs, then build.
foreach ($dir in 'build', 'dist') {
    $path = Join-Path $Root $dir
    if (Test-Path $path) {
        Write-Host "Cleaning $dir\ ..."
        Remove-Item $path -Recurse -Force
    }
}

Write-Host 'Building dist\QuickSnake.exe (onefile, windowed) ...'
& $Py -m PyInstaller --noconfirm --clean $Spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }

$Exe = Join-Path $Root 'dist\QuickSnake.exe'
if (-not (Test-Path $Exe)) {
    throw "Build reported success but $Exe was not produced."
}

$Size = (Get-Item $Exe).Length
Write-Host ''
Write-Host ('=' * 64)
Write-Host "BUILD OK : $Exe"
Write-Host ('SIZE     : {0:N1} MB ({1:N0} bytes)' -f ($Size / 1MB), $Size)
Write-Host ('=' * 64)
