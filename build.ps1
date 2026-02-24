<#
.SYNOPSIS
    Build Nova Voice Assistant into a distributable package.
.DESCRIPTION
    Runs PyInstaller with nova.spec, then generates a ready-to-distribute
    folder at dist\Nova\ containing Nova.exe + all dependencies.
.NOTES
    Run from the assistant\ directory with the venv activated.
    Usage:  .\build.ps1
#>

$ErrorActionPreference = "Stop"

$ProjectDir = $PSScriptRoot
if (-not $ProjectDir) { $ProjectDir = Get-Location }

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Nova Voice Assistant — Build Script" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# ── Step 1: Check PyInstaller ───────────────────────────────────────────────
Write-Host "[1/5] Checking PyInstaller..." -ForegroundColor Yellow
$pi = Get-Command pyinstaller -ErrorAction SilentlyContinue
if (-not $pi) {
    Write-Host "  PyInstaller not found. Installing..." -ForegroundColor DarkYellow
    pip install pyinstaller
}
Write-Host "  OK — $(pyinstaller --version)" -ForegroundColor Green

# ── Step 2: Clean previous build ────────────────────────────────────────────
Write-Host "[2/5] Cleaning previous build..." -ForegroundColor Yellow
$buildDir = Join-Path $ProjectDir "build"
$distDir  = Join-Path $ProjectDir "dist"
if (Test-Path $buildDir) { Remove-Item $buildDir -Recurse -Force }
if (Test-Path $distDir)  { Remove-Item $distDir -Recurse -Force }
Write-Host "  Cleaned." -ForegroundColor Green

# ── Step 3: Run PyInstaller ─────────────────────────────────────────────────
Write-Host "[3/5] Running PyInstaller (this may take a few minutes)..." -ForegroundColor Yellow
Push-Location $ProjectDir
pyinstaller nova.spec --noconfirm 2>&1 | ForEach-Object {
    if ($_ -match "ERROR|WARN") {
        Write-Host "  $_" -ForegroundColor Red
    }
}
Pop-Location

$exePath = Join-Path $distDir "Nova" "Nova.exe"
if (-not (Test-Path $exePath)) {
    Write-Host "  BUILD FAILED — Nova.exe not found!" -ForegroundColor Red
    exit 1
}
Write-Host "  Build successful!" -ForegroundColor Green

# ── Step 4: Copy extra runtime files ────────────────────────────────────────
Write-Host "[4/5] Copying runtime data files..." -ForegroundColor Yellow
$novaDir = Join-Path $distDir "Nova"

# Ensure data dir exists and copy contacts if not already bundled
$dataDir = Join-Path $novaDir "data"
if (-not (Test-Path $dataDir)) { New-Item -ItemType Directory -Path $dataDir -Force | Out-Null }

# Copy README and command reference for users
Copy-Item (Join-Path $ProjectDir "COMMAND_REFERENCE.md") $novaDir -Force -ErrorAction SilentlyContinue
Copy-Item (Join-Path $ProjectDir "README.md") $novaDir -Force -ErrorAction SilentlyContinue

Write-Host "  Done." -ForegroundColor Green

# ── Step 5: Report ──────────────────────────────────────────────────────────
Write-Host "[5/5] Build summary:" -ForegroundColor Yellow
$size = (Get-ChildItem $novaDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
Write-Host "  Output:     $novaDir" -ForegroundColor White
Write-Host "  Executable: $exePath" -ForegroundColor White
Write-Host "  Total size: $([math]::Round($size, 1)) MB" -ForegroundColor White

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  BUILD COMPLETE" -ForegroundColor Green
Write-Host "  Run:  dist\Nova\Nova.exe" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
