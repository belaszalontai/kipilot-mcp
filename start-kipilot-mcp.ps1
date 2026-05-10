[CmdletBinding()]
param(
    [switch]$ForceInstall,
    [switch]$SkipRun
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $PSCommandPath
$venvPath = Join-Path $repoRoot ".venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"

function Write-KiPilotStatus {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    [Console]::Error.WriteLine($Message)
}

function New-KiPilotVirtualEnvironment {
    $pyCommand = Get-Command py -ErrorAction SilentlyContinue
    if ($null -ne $pyCommand) {
        foreach ($version in @("3.13", "3.12", "3.11")) {
            & $pyCommand.Source "-$version" -c "import sys" 1>$null 2>$null
            if ($LASTEXITCODE -ne 0) {
                continue
            }

            Write-KiPilotStatus "Creating .venv with Python $version..."
            & $pyCommand.Source "-$version" -m venv $venvPath
            if ($LASTEXITCODE -eq 0 -and (Test-Path $venvPython)) {
                return
            }
        }
    }

    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($null -eq $pythonCommand) {
        throw (
            "Python was not found. Install Python 3.13.x (recommended) or another Python 3.11+ release, then rerun this script."
        )
    }

    Write-KiPilotStatus "Creating .venv with the default python command..."
    & $pythonCommand.Source -m venv $venvPath
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $venvPython)) {
        throw "Virtual environment creation failed."
    }
}

function Test-KiPilotRuntimeInstalled {
    if (-not (Test-Path $venvPython)) {
        return $false
    }

    & $venvPython -c "import kipy, mcp, kipilot_mcp" 1>$null 2>$null
    return $LASTEXITCODE -eq 0
}

function Install-KiPilotRuntime {
    Write-KiPilotStatus "Installing KiPilot MCP runtime dependencies into .venv..."
    & $venvPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to upgrade pip inside .venv."
    }

    & $venvPython -m pip install -e .
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install the KiPilot MCP package into .venv."
    }
}

function Set-DefaultEnvironmentValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,

        [Parameter(Mandatory = $true)]
        [string]$Value
    )

    $currentValue = [Environment]::GetEnvironmentVariable($Name, "Process")
    if ([string]::IsNullOrWhiteSpace($currentValue)) {
        Set-Item -Path "Env:$Name" -Value $Value
    }
}

Push-Location $repoRoot
try {
    if (-not (Test-Path $venvPython)) {
        New-KiPilotVirtualEnvironment
    }

    if ($ForceInstall -or -not (Test-KiPilotRuntimeInstalled)) {
        Install-KiPilotRuntime
    }

    Set-DefaultEnvironmentValue -Name "KIPILOT_KICAD_CLIENT_NAME" -Value "kipilot-mcp"
    Set-DefaultEnvironmentValue -Name "KIPILOT_KICAD_TIMEOUT_MS" -Value "60000"
    Set-DefaultEnvironmentValue -Name "KIPILOT_ENABLE_MUTATIONS" -Value "0"
    Set-DefaultEnvironmentValue -Name "KIPILOT_COMMIT_MESSAGE_PREFIX" -Value "KiPilot MCP"
    Set-DefaultEnvironmentValue -Name "KIPILOT_LOG_LEVEL" -Value "INFO"
    Set-DefaultEnvironmentValue -Name "KIPILOT_LOG_FILE" -Value (Join-Path $repoRoot ".logs\kipilot-mcp.log")

    $logFile = [Environment]::GetEnvironmentVariable("KIPILOT_LOG_FILE", "Process")
    $logDirectory = Split-Path -Parent $logFile
    if (-not [string]::IsNullOrWhiteSpace($logDirectory)) {
        New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
    }

    if ($SkipRun) {
        Write-KiPilotStatus "KiPilot MCP environment is ready. Launch skipped because -SkipRun was specified."
        return
    }

    Write-KiPilotStatus "Starting KiPilot MCP server..."
    & $venvPython -m kipilot_mcp.server
    if ($LASTEXITCODE -ne 0) {
        throw "The KiPilot MCP server exited with code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}