[CmdletBinding()]
param(
    [switch]$ForceInstall,
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $PSCommandPath
$bootstrapScript = Join-Path $repoRoot "start-kipilot-mcp.ps1"
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
$buildRoot = Join-Path $repoRoot "build"
$distRoot = Join-Path $repoRoot "dist"
$artifactsRoot = Join-Path $repoRoot "artifacts"
$pyInstallerSpecRoot = Join-Path $buildRoot "pyinstaller"

function Write-KiPilotBuildStatus {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    [Console]::Error.WriteLine($Message)
}

function Test-ZipContainsRequiredFiles {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ZipPath,

        [Parameter(Mandatory = $true)]
        [string[]]$RequiredFileNames
    )

    Add-Type -AssemblyName System.IO.Compression.FileSystem

    $archive = [System.IO.Compression.ZipFile]::OpenRead($ZipPath)
    try {
        $leafNames = @(
            $archive.Entries |
                ForEach-Object { [System.IO.Path]::GetFileName($_.FullName) } |
                Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
        )

        foreach ($requiredFileName in $RequiredFileNames) {
            if ($requiredFileName -notin $leafNames) {
                throw "Required file '$requiredFileName' is missing from ZIP artifact $ZipPath."
            }
        }
    }
    finally {
        $archive.Dispose()
    }
}

if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
    throw "This build helper only supports Windows."
}

if (-not (Test-Path $bootstrapScript)) {
    throw "The bootstrap script start-kipilot-mcp.ps1 was not found."
}

Push-Location $repoRoot
try {
    $bootstrapParameters = @{
        SkipRun = $true
    }
    if ($ForceInstall) {
        $bootstrapParameters["ForceInstall"] = $true
    }

    & $bootstrapScript @bootstrapParameters
    if ($LASTEXITCODE -ne 0) {
        throw "KiPilot runtime bootstrap failed with exit code $LASTEXITCODE."
    }

    if (-not (Test-Path $venvPython)) {
        throw "Expected Python executable was not found at $venvPython."
    }

    Write-KiPilotBuildStatus "Installing Windows packaging dependencies into .venv..."
    & $venvPython -m pip install -e ".[build]"
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install KiPilot build dependencies into .venv."
    }

    if ($Clean) {
        Remove-Item $buildRoot -Recurse -Force -ErrorAction SilentlyContinue
        Remove-Item $distRoot -Recurse -Force -ErrorAction SilentlyContinue
        Remove-Item $artifactsRoot -Recurse -Force -ErrorAction SilentlyContinue
    }

    $packageVersion = (& $venvPython -c "from kipilot_mcp import __version__; print(__version__)").Trim()
    if ([string]::IsNullOrWhiteSpace($packageVersion)) {
        throw "Unable to resolve the KiPilot package version."
    }

    $releaseName = "kipilot-mcp-$packageVersion-windows-x64"
    $distPackageRoot = Join-Path $distRoot "kipilot-mcp"
    $stagingRoot = Join-Path $artifactsRoot $releaseName
    $zipPath = Join-Path $artifactsRoot "$releaseName.zip"

    New-Item -ItemType Directory -Force -Path $artifactsRoot | Out-Null
    New-Item -ItemType Directory -Force -Path $pyInstallerSpecRoot | Out-Null
    Remove-Item $stagingRoot -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item $zipPath -Force -ErrorAction SilentlyContinue

    Write-KiPilotBuildStatus "Building KiPilot MCP Windows executable with PyInstaller..."
    $pyInstallerArgs = @(
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--console",
        "--name",
        "kipilot-mcp",
        "--specpath",
        $pyInstallerSpecRoot,
        "--paths",
        "src",
        "--collect-all",
        "kipy",
        "--copy-metadata",
        "kipilot-mcp",
        "--copy-metadata",
        "kicad-python",
        "--copy-metadata",
        "mcp",
        "pyinstaller_entry.py"
    )
    & $venvPython @pyInstallerArgs
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE."
    }

    $exePath = Join-Path $distPackageRoot "kipilot-mcp.exe"
    if (-not (Test-Path $exePath)) {
        throw "Expected executable was not created at $exePath."
    }

    New-Item -ItemType Directory -Force -Path $stagingRoot | Out-Null
    Copy-Item -Path (Join-Path $distPackageRoot "*") -Destination $stagingRoot -Recurse -Force
    Copy-Item -Path (Join-Path $repoRoot "README.md") -Destination $stagingRoot -Force
    Copy-Item -Path (Join-Path $repoRoot "LICENSE") -Destination $stagingRoot -Force

    Compress-Archive -Path $stagingRoot -DestinationPath $zipPath -Force
    Test-ZipContainsRequiredFiles -ZipPath $zipPath -RequiredFileNames @("kipilot-mcp.exe", "README.md", "LICENSE")
    Write-KiPilotBuildStatus "Windows ZIP artifact ready: $zipPath"
}
finally {
    Pop-Location
}