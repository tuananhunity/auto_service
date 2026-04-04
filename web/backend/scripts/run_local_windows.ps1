$ErrorActionPreference = "Stop"

$repoRoot = "c:\Users\ADMIN\Documents\auto_service\auto_service_clean"
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
$storageDir = Join-Path $repoRoot "web\backend\storage"
$windowsProfiles = Join-Path $storageDir "windows_profiles"
$chromeDriverPath = "C:\Users\ADMIN\.wdm\drivers\chromedriver\win64\146.0.7680.165\chromedriver-win32\chromedriver.exe"
New-Item -ItemType Directory -Force (Join-Path $storageDir "runtime") | Out-Null
New-Item -ItemType Directory -Force $windowsProfiles | Out-Null

$env:DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/remote_browser_dev"
$env:SECRET_KEY = "dev-secret"
$env:BASE_STORAGE_DIR = $storageDir
$env:BROWSER_RUNTIME_MODE = "windows_local"
$env:WINDOWS_CHROME_BINARY_PATH = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$env:WINDOWS_USER_DATA_ROOT = $windowsProfiles
$env:CHROMEDRIVER_BINARY_PATH = $chromeDriverPath
$env:ADMIN_SEED_USERNAME = "admin"
$env:ADMIN_SEED_PASSWORD = "admin123"

Set-Location $repoRoot
$existing = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq "python.exe" -and $_.CommandLine -match "web\\backend\\app.py"
}
foreach ($process in $existing) {
    Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
}
& $pythonExe "web\backend\app.py"
