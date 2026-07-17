# Build script to create a standalone executable from MatchResolution.py
# Usage: .\build_exe.ps1

Write-Host "================================================" -ForegroundColor Green
Write-Host "MatchResolution Executable Builder" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""

# Check if PyInstaller is installed
Write-Host "Checking for PyInstaller..." -ForegroundColor Yellow
try {
    python -m pip show pyinstaller | Out-Null
    Write-Host "PyInstaller found" -ForegroundColor Green
}
catch {
    Write-Host "PyInstaller not found. Installing..." -ForegroundColor Red
    python -m pip install pyinstaller
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to install PyInstaller" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "Reading version from VERSION file..." -ForegroundColor Yellow

# Read version from VERSION file
if (Test-Path "VERSION") {
    $version = (Get-Content "VERSION" -Raw).Trim()
    Write-Host "Version: $version" -ForegroundColor Green
}
else {
    Write-Host "VERSION file not found" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Building executable..." -ForegroundColor Yellow

# Build the executable
$exeName = "MatchResolution_V$version"
python -m PyInstaller --onefile --windowed --name $exeName --distpath dist --workpath build --specpath build MatchResolution.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "Build Complete!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""

# Verify output
if (Test-Path "dist\$exeName.exe") {
    $exeSize = (Get-Item "dist\$exeName.exe").Length / 1MB
    Write-Host "Executable created successfully" -ForegroundColor Green
    Write-Host "Location: dist\$exeName.exe" -ForegroundColor Cyan
    Write-Host "Size: $([Math]::Round($exeSize, 2)) MB" -ForegroundColor Cyan
    Write-Host "Version: $version" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Test the executable: .\dist\$exeName.exe" -ForegroundColor Cyan
    Write-Host "2. Verify functionality" -ForegroundColor Cyan
    Write-Host "3. Check RELEASE_CHECKLIST.md" -ForegroundColor Cyan
}
else {
    Write-Host "Executable not found in dist directory" -ForegroundColor Red
    exit 1
}

Write-Host ""
