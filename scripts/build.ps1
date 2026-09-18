param(
  [string]$OutputRoot = ""
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot
if (-not $OutputRoot) {
  $OutputRoot = $projectRoot
}
$distPath = Join-Path $OutputRoot "dist"
$workPath = Join-Path $OutputRoot "build/pyinstaller"
$specPath = Join-Path $OutputRoot "build"
$webPath = Join-Path $projectRoot "src/mouth_monitor/web"
$assetsPath = Join-Path $projectRoot "src/mouth_monitor/assets"
$env:PYINSTALLER_CONFIG_DIR = Join-Path $OutputRoot "pyinstaller-cache"
New-Item -ItemType Directory -Force -Path $distPath, $workPath, $specPath | Out-Null

Write-Host "同步开发与构建依赖……"
uv sync --group dev --group build

Write-Host "运行自动测试……"
uv run pytest -q --basetemp=.pytest-tmp

Write-Host "构建 Windows 目录发布包……"
uv run --group build pyinstaller `
  --name MouthMonitor `
  --onedir `
  --noconfirm `
  --clean `
  --paths src `
  --hidden-import mouth_monitor.app `
  --add-data "$webPath;mouth_monitor/web" `
  --add-data "$assetsPath;mouth_monitor/assets" `
  --distpath $distPath `
  --workpath $workPath `
  --specpath $specPath `
  src/mouth_monitor/__main__.py
if ($LASTEXITCODE -ne 0) {
  throw "PyInstaller 构建失败，退出码：$LASTEXITCODE"
}

$releaseDirectory = Join-Path $distPath "MouthMonitor"
$archive = Join-Path $distPath "MouthMonitor-windows-x64.zip"
if (Test-Path -LiteralPath $archive) {
  Remove-Item -LiteralPath $archive -Force
}
Compress-Archive -Path (Join-Path $releaseDirectory "*") -DestinationPath $archive

Write-Host "构建完成：$(Join-Path $releaseDirectory 'MouthMonitor.exe')"
Write-Host "压缩包：$archive"
