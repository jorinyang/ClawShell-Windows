# ClawShell 2.0 — Windows Installer
# Run: powershell -ExecutionPolicy Bypass -File install.ps1

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  ClawShell 2.0 — Windows Installer" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ── Python Check ──────────────────────────────────────
Write-Host "[INFO] Checking Python..." -ForegroundColor Blue
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command python3 -ErrorAction SilentlyContinue }
if (-not $python) {
    Write-Host "[ERR] Python 3 not found. Please install Python 3.10+ from https://python.org" -ForegroundColor Red
    exit 1
}
Write-Host "[OK]   Python $($python.Version)" -ForegroundColor Green

# ── Detect ClawShell Source ────────────────────────────
$clawshellSrc = $null
$candidates = @(
    "$env:USERPROFILE\.ClawShell",
    "$PSScriptRoot\.."
)
foreach ($d in $candidates) {
    if (Test-Path "$d\scripts\env_detector.py") {
        $clawshellSrc = $d
        break
    }
}
if ($clawshellSrc) {
    Write-Host "[OK]   ClawShell source: $clawshellSrc" -ForegroundColor Green
} else {
    Write-Host "[WARN] ClawShell source not found" -ForegroundColor Yellow
}

# ── Install Core Packages ──────────────────────────────
Write-Host "[INFO] Installing core dependencies..." -ForegroundColor Blue
& $python.Source -m pip install --quiet websockets psutil
Write-Host "[OK]   Core packages installed" -ForegroundColor Green

# ── Ecosystem Installer ────────────────────────────────
if ($clawshellSrc) {
    Write-Host "[INFO] Launching ecosystem selector..." -ForegroundColor Blue
    & $python.Source "$clawshellSrc\scripts\ecosystem_installer.py"
}

# ── Configuration Wizard ───────────────────────────────
if ($clawshellSrc) {
    Write-Host "[INFO] Running configuration wizard..." -ForegroundColor Blue
    & $python.Source "$clawshellSrc\scripts\config_wizard.py"
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Installation Complete!" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
