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

$zip = Join-Path $env:TEMP "ffmpeg-btbn.zip"
$tmpExtract = Join-Path $env:TEMP "ffmpeg-extract"

Write-Host "Downloading static FFmpeg build for Windows x64..."
Invoke-WebRequest -Uri "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-n7.1-latest-win64-gpl-7.1.zip" -OutFile $zip

if (Test-Path $tmpExtract) { Remove-Item -Recurse -Force $tmpExtract }
Expand-Archive -Path $zip -DestinationPath $tmpExtract -Force

$exe = Get-ChildItem $tmpExtract -Recurse -Filter "ffmpeg.exe" | Select-Object -First 1
if (-not $exe) { throw "ffmpeg.exe not found inside downloaded archive" }

Copy-Item $exe.FullName $existing -Force
Remove-Item -Recurse -Force $tmpExtract
Remove-Item -Force $zip

Write-Host "FFmpeg successfully installed to: $existing"
& $existing -version | Select-Object -First 1
