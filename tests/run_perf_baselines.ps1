# Run all endpoint baselines in sequence (no /api/v1/auth routes).
$ErrorActionPreference = "Continue"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Locust = Join-Path $RepoRoot "backend\.venv\Scripts\locust.exe"
$Host_ = "http://localhost:8000"
$Results = @()

$Targets = @(
    "auth-me",
    "auth-register",
    "auth-login",
    "products-list",
    "products-get",
    "products-create",
    "products-update",
    "products-delete",
    "orders-create",
    "orders-me",
    "orders-get",
    "orders-list",
    "orders-status"
)

Write-Host "Running $($Targets.Count) endpoint baselines sequentially..."
Write-Host ""

foreach ($Target in $Targets) {
    Write-Host ">>> LOCUST_TARGET=$Target"
    $env:LOCUST_TARGET = $Target
    $output = & $Locust -f (Join-Path $RepoRoot "tests\locustfile.py") `
        --headless -u 10 -r 2 --run-time 30s --host $Host_ 2>&1
    $output | ForEach-Object { Write-Host $_ }
    $line = $output | Where-Object { $_ -match "^LOCUST_PERF_RESULT\|" } | Select-Object -Last 1
    if ($line) {
        $Results += $line
    } else {
        $Results += "LOCUST_PERF_RESULT|UNKNOWN|0|0|0|0.00|0|0|$Target"
    }
    Write-Host ""
    if ($Target -eq "auth-login") {
        Write-Host ">>> Cooling down 65s for login rate-limit window..."
        Start-Sleep -Seconds 65
    } else {
        Start-Sleep -Seconds 2
    }
}

Write-Host "========== ALL RESULTS =========="
$Results | ForEach-Object { Write-Host $_ }
