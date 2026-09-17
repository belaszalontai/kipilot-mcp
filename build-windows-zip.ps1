[CmdletBinding()]
param(
    [switch]$ForceInstall,
    [switch]$Clean,
    [string]$KiCadPythonSource = "",
    [string]$ProtobufVersion = "6.33.5",
    [switch]$ForceBindingInstall
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

function Get-KiCadPythonSource {
    <#
    .SYNOPSIS
    Resolve the kicad-python source used for packaging.

    .DESCRIPTION
    PyPI releases of kicad-python can lag behind the IPC API surface KiPilot
    needs (0.8.0 ships inconsistent generated protos: kipy.board_jobs,
    kipy.schematic_types, kipy.schematic and kipy.board_rules cannot be
    imported).  Packaging therefore installs an explicit binding: the vendored
    wheel in vendor\ by default, or the path/URL passed through
    -KiCadPythonSource or KIPILOT_KICAD_PYTHON_SOURCE.
    #>

    $source = $KiCadPythonSource
    if ([string]::IsNullOrWhiteSpace($source)) {
        $source = [Environment]::GetEnvironmentVariable("KIPILOT_KICAD_PYTHON_SOURCE", "Process")
    }

    if (-not [string]::IsNullOrWhiteSpace($source)) {
        if (Test-Path $source) {
            return (Resolve-Path $source).Path
        }

        return $source
    }

    $vendorWheel = Get-ChildItem -Path (Join-Path $repoRoot "vendor\kicad_python-*.whl") `
    -ErrorAction SilentlyContinue | Sort-Object Name -Descending | Select-Object -First 1
    if ($null -ne $vendorWheel) {
        return $vendorWheel.FullName
    }

    throw (
        "No kicad-python binding is available for packaging. Add the vendored binding wheel to " +
        "vendor\ (see scripts\install_dev_kipy.py --wheel) or pass -KiCadPythonSource with a " +
        "prepared kicad-python checkout or wheel."
    )
}

function Invoke-VenvPythonSnippet {
    <#
    .SYNOPSIS
    Run an inline Python snippet inside the packaging venv and return its output.

    .DESCRIPTION
    Native stderr output must not abort the build (Windows PowerShell turns it into
    a terminating error while $ErrorActionPreference is Stop), so the snippet is run
    from a temporary file and both streams are captured for the caller.
    #>
    param(
        [Parameter(Mandatory = $true)]
        [string]$Snippet
    )

    $probePath = Join-Path ([IO.Path]::GetTempPath()) ("kipilot-probe-" + [Guid]::NewGuid().ToString("N") + ".py")
    Set-Content -Path $probePath -Value $Snippet -Encoding UTF8

    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = (& $venvPython $probePath 2>&1 | Out-String)
        return [pscustomobject]@{
            ExitCode = $LASTEXITCODE
            Output   = $output
        }
    }
    finally {
        $ErrorActionPreference = $previousPreference
        Remove-Item -Path $probePath -Force -ErrorAction SilentlyContinue
    }
}

function Test-KiPyBindingCapability {
    if (-not (Test-Path $venvPython)) {
        return $false
    }

    $probe = @"
import kipy.board_jobs
import kipy.board_rules
import kipy.common_types as common_types
import kipy.proto.board.board_rules_pb2
import kipy.proto.schematic.schematic_types_pb2
import kipy.schematic_types

assert common_types.PathType is not None
print("kipy-capable")
"@

    $result = Invoke-VenvPythonSnippet -Snippet $probe
    $capable = ($result.ExitCode -eq 0 -and $result.Output -match "kipy-capable")
    if (-not $capable) {
        Write-KiPilotBuildStatus "Binding capability probe failed (exit code $($result.ExitCode)):"
        Write-KiPilotBuildStatus $result.Output.Trim()
    }

    return $capable
}

function Install-KiCadPythonBinding {
    $source = Get-KiCadPythonSource
    Write-KiPilotBuildStatus "Installing a schematic-capable kicad-python binding from $source..."

    # The binding ships protobuf 6.x generated code, so the matching runtime is
    # installed explicitly (its own metadata still declares the older 5.x range).
    # The remaining entries are the libraries kipy imports for the IPC transport
    # and for the payload validation helpers.
    $requirements = @(
        "protobuf==$ProtobufVersion",
        "pynng>=0.9.0,<0.10.0",
        "jsonschema>=4.23.0,<5",
        "typing_extensions>=4.13.2",
        "zstandard>=0.25.0,<0.26.0"
    )

    & $venvPython -m pip install --no-input --upgrade @requirements
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install the runtime dependencies of kicad-python."
    }

    $stagingRoot = Join-Path ([IO.Path]::GetTempPath()) ("kipilot-binding-" + [Guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $stagingRoot -Force | Out-Null

    try {
        if ($source -match "\.whl$" -and (Test-Path $source)) {
            Write-KiPilotBuildStatus "Installing the prebuilt binding wheel $source ..."
            & $venvPython -m pip install --no-input --no-deps --upgrade --force-reinstall $source
            if ($LASTEXITCODE -ne 0) {
                throw "Failed to install the kicad-python wheel $source."
            }
        }
        else {
            $checkout = $source
            if ($source -match "^https?://") {
                $archivePath = Join-Path $stagingRoot "kicad-python.tar.gz"
                Write-KiPilotBuildStatus "Downloading $source ..."
                Invoke-WebRequest -Uri $source -OutFile $archivePath -UseBasicParsing
                & tar -xzf $archivePath -C $stagingRoot
                if ($LASTEXITCODE -ne 0) {
                    throw "Failed to extract the kicad-python archive downloaded from $source."
                }

                $extracted = Get-ChildItem -Path $stagingRoot -Directory | Select-Object -First 1
                if ($null -eq $extracted) {
                    throw "The kicad-python archive from $source did not contain a source directory."
                }

                $checkout = $extracted.FullName
            }

            # pip cannot install the upstream repository without its Poetry build backend and
            # proto tooling, so the pure-Python package is staged directly into the venv.
            $installer = Join-Path $repoRoot "scripts\install_dev_kipy.py"
            & $venvPython $installer $checkout
            if ($LASTEXITCODE -ne 0) {
                throw "Failed to stage the kicad-python package from $checkout."
            }
        }
    }
    finally {
        Remove-Item -Path $stagingRoot -Recurse -Force -ErrorAction SilentlyContinue
    }

    if (-not (Test-KiPyBindingCapability)) {
        throw (
            "The installed kicad-python binding from $source does not provide the IPC surface " +
            "KiPilot needs (protobuf $ProtobufVersion was installed for it). Pass -KiCadPythonSource " +
            "with a known-good checkout or branch, and -ProtobufVersion if the binding expects a " +
            "different protobuf runtime."
        )
    }

    $versionProbe = @"
import importlib.metadata as metadata

try:
    print(metadata.version('kicad-python'))
except Exception:
    try:
        import kipy

        print(getattr(kipy, '__version__', 'unknown'))
    except Exception:
        print('unknown')
"@
    $versionResult = Invoke-VenvPythonSnippet -Snippet $versionProbe
    $bindingVersion = ($versionResult.Output -split "`n" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Last 1)
    if (-not [string]::IsNullOrWhiteSpace($bindingVersion)) {
        Write-KiPilotBuildStatus "Packaged kicad-python binding: $($bindingVersion.Trim())"
    }
}

function New-ReleaseZipArchive {
    <#
    .SYNOPSIS
    Create the release ZIP from a staged folder.

    .DESCRIPTION
    Compress-Archive fails when a freshly written file is still held by another
    process (a Windows Defender scan of the copied runtime is the usual cause) and
    it has no retry logic.  The archive is therefore written by
    scripts/create_release_zip.py, which retries on sharing violations and works the
    same way on every machine; Compress-Archive remains as a last-resort fallback.
    #>
    param(
        [Parameter(Mandatory = $true)]
        [string]$StagingRoot,

        [Parameter(Mandatory = $true)]
        [string]$ZipPath,

        [Parameter(Mandatory = $true)]
        [string]$ArchiveEntryName
    )

    Remove-Item $ZipPath -Force -ErrorAction SilentlyContinue

    $zipScript = Join-Path $repoRoot "scripts\create_release_zip.py"
    if (Test-Path $zipScript) {
        & $venvPython $zipScript --source $StagingRoot --output $ZipPath --entry-root $ArchiveEntryName
        if ($LASTEXITCODE -eq 0 -and (Test-Path $ZipPath)) {
            return
        }
    }

    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        Compress-Archive -Path $StagingRoot -DestinationPath $ZipPath -Force -ErrorAction Stop
        if (Test-Path $ZipPath) {
            return
        }
    }
    catch {
        throw "Failed to create the release ZIP at $ZipPath. $($_.Exception.Message)"
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }
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
    & $venvPython -m pip install --no-deps -e .
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install the KiPilot package into .venv for packaging."
    }

    & $venvPython -m pip install "pyinstaller>=6.14.0"
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install PyInstaller into .venv."
    }

    # Applied last so that the packaged runtime is not rewritten by earlier steps.
    if ($ForceBindingInstall -or -not (Test-KiPyBindingCapability)) {
        Install-KiCadPythonBinding
    }
    else {
        Write-KiPilotBuildStatus "The installed kicad-python binding already exposes the required IPC surface."
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

    New-ReleaseZipArchive -StagingRoot $stagingRoot -ZipPath $zipPath -ArchiveEntryName $releaseName
    Test-ZipContainsRequiredFiles -ZipPath $zipPath -RequiredFileNames @("kipilot-mcp.exe", "README.md", "LICENSE")

    $smokeTestScript = Join-Path $repoRoot "scripts\smoke_test_binary.py"
    if (Test-Path $smokeTestScript) {
        Write-KiPilotBuildStatus "Verifying that the packaged executable completes the MCP handshake..."
        & $venvPython $smokeTestScript $exePath
        if ($LASTEXITCODE -ne 0) {
            throw "The packaged executable failed the MCP handshake smoke test."
        }
    }

    Write-KiPilotBuildStatus "Windows ZIP artifact ready: $zipPath"
}
finally {
    Pop-Location
}