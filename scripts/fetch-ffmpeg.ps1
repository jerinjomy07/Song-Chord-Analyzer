# PowerShell script to fetch static FFmpeg binary for Windows
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$out = Join-Path $root "resources\ffmpeg"
New-Item -ItemType Directory -Force -Path $out | Out-Null

$existing = Join-Path $out "ffmpeg.exe"
if (Test-Path $existing) {
    Write-Host "FFmpeg binary already present: $existing"
    & $existing -version | Select-Object -First 1
    exit 0
}

$zip = Join-Path $env:TEMP "ffmpeg-build.zip"
$tmpExtract = Join-Path $env:TEMP "ffmpeg-extract"

# Candidate download URLs in priority order
$downloadUrls = [System.Collections.Generic.List[string]]::new()

# 1. Try querying GitHub API for latest BtbN asset
try {
    Write-Host "Querying GitHub API for latest BtbN FFmpeg build..."
    $apiHeaders = @{ "User-Agent" = "SongChordAnalyzer-Build" }
    $release = Invoke-RestMethod -Uri "https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/latest" -Headers $apiHeaders -TimeoutSec 10
    $asset = $release.assets | Where-Object { $_.name -like "*win64-gpl.zip" -and $_.name -notlike "*shared*" } | Select-Object -First 1
    if ($asset -and $asset.browser_download_url) {
        $downloadUrls.Add($asset.browser_download_url)
    }
} catch {
    Write-Host "Could not query GitHub API (likely rate limited or offline): $_"
}

# 2. Known static fallbacks
$downloadUrls.Add("https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip")
$downloadUrls.Add("https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip")

$downloaded = $false
foreach ($url in $downloadUrls) {
    Write-Host "Attempting download from: $url"
    try {
        if (Test-Path $zip) { Remove-Item -Force $zip }
        
        # Use curl.exe if available (fast and reliable with redirects)
        if (Get-Command curl.exe -ErrorAction SilentlyContinue) {
            curl.exe -fSL --retry 3 --retry-delay 2 -o $zip $url
            if ($LASTEXITCODE -eq 0 -and (Test-Path $zip) -and ((Get-Item $zip).Length -gt 1000000)) {
                $downloaded = $true
                break
            }
        }
        
        # Fallback to Invoke-WebRequest
        Invoke-WebRequest -Uri $url -OutFile $zip -UserAgent "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" -TimeoutSec 120
        if ((Test-Path $zip) -and ((Get-Item $zip).Length -gt 1000000)) {
            $downloaded = $true
            break
        }
    } catch {
        Write-Warning "Failed downloading from $url : $_"
    }
}

if (-not $downloaded) {
    throw "Failed to download FFmpeg from all available sources."
}

if (Test-Path $tmpExtract) { Remove-Item -Recurse -Force $tmpExtract }
Write-Host "Extracting FFmpeg archive..."
Expand-Archive -Path $zip -DestinationPath $tmpExtract -Force

$exe = Get-ChildItem $tmpExtract -Recurse -Filter "ffmpeg.exe" | Select-Object -First 1
if (-not $exe) { throw "ffmpeg.exe not found inside downloaded archive" }

Copy-Item $exe.FullName $existing -Force
Remove-Item -Recurse -Force $tmpExtract
Remove-Item -Force $zip

Write-Host "FFmpeg successfully installed to: $existing"
& $existing -version | Select-Object -First 1
