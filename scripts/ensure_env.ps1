[CmdletBinding()]
param(
    [switch]$Force,
    [switch]$Frontend
)

$ErrorActionPreference = 'Stop'

function Ensure-VirtualEnvironment {
    param(
        [string]$ProjectRoot,
        [switch]$Force
    )

    $venvPath = Join-Path $ProjectRoot '.venv'
    $venvPython = Join-Path $venvPath 'Scripts/python.exe'

    if ($Force -and (Test-Path $venvPath)) {
        Write-Host "Removing existing virtual environment..." -ForegroundColor Yellow
        Remove-Item $venvPath -Recurse -Force
    }

    if (-not (Test-Path $venvPython)) {
        Write-Host "Creating virtual environment with Python 3.13..." -ForegroundColor Cyan
        & py -3.13 -m venv $venvPath
    }

    Write-Host "Upgrading pip..." -ForegroundColor Cyan
    & $venvPython -m pip install --upgrade pip | Out-Host

    Write-Host "Installing backend requirements..." -ForegroundColor Cyan
    & $venvPython -m pip install -r (Join-Path $ProjectRoot 'requirements.txt') | Out-Host

    Write-Host "Backend environment ready." -ForegroundColor Green
}

function Ensure-FrontendDependencies {
    param(
        [string]$ProjectRoot,
        [switch]$Force
    )

    $webPath = Join-Path $ProjectRoot 'web'
    $nodeModules = Join-Path $webPath 'node_modules'

    Push-Location $webPath
    try {
        if ($Force -and (Test-Path $nodeModules)) {
            Write-Host "Removing existing node_modules..." -ForegroundColor Yellow
            Remove-Item $nodeModules -Recurse -Force
        }

        if (-not (Test-Path $nodeModules)) {
            Write-Host "Installing frontend dependencies..." -ForegroundColor Cyan
            npm install | Out-Host
        }
        else {
            Write-Host "Running incremental npm install to sync dependencies..." -ForegroundColor Cyan
            npm install | Out-Host
        }

        Write-Host "Frontend dependencies ready." -ForegroundColor Green
    }
    finally {
        Pop-Location
    }
}

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

Ensure-VirtualEnvironment -ProjectRoot $projectRoot -Force:$Force

if ($Frontend) {
    Ensure-FrontendDependencies -ProjectRoot $projectRoot -Force:$Force
}

Write-Host "All requested setup steps completed." -ForegroundColor Green
