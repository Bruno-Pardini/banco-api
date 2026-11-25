# Instala las dependencias de banco-api en un entorno virtual (.venv) en Windows.
# Uso: doble clic en instalar.bat (o en PowerShell: .\instalar.ps1)
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
Write-Host "== Banco E6 · instalación de dependencias ==" -ForegroundColor Cyan

function Buscar-Python {
    foreach ($v in @("3.13", "3.12")) {
        try { & py "-$v" -c "import sys" 2>$null; if ($LASTEXITCODE -eq 0) { return ,@("py", "-$v") } } catch {}
    }
    try {
        $ok = & python -c "import sys; print(int(sys.version_info >= (3,12)))" 2>$null
        if ($ok -eq "1") { return ,@("python") }
    } catch {}
    return $null
}

$py = Buscar-Python
if (-not $py) {
    Write-Host "No encontré Python 3.12 o superior." -ForegroundColor Yellow
    $r = Read-Host "¿Instalo Python 3.12 con winget? (s/n)"
    if ($r -ne "s") { throw "Instala Python 3.12+ desde https://www.python.org/downloads/ y vuelve a ejecutar este script." }
    winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
    $py = Buscar-Python
    if (-not $py) { throw "Python se instaló pero no aparece en esta ventana. Cierra y vuelve a ejecutar instalar.bat." }
}
$pyExe = $py[0]; $pyArgs = @(); if ($py.Count -gt 1) { $pyArgs = $py[1..($py.Count - 1)] }
Write-Host ("Python: " + (& $pyExe @pyArgs --version))

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creando entorno virtual .venv ..."
    & $pyExe @pyArgs -m venv .venv
}
$venv = ".\.venv\Scripts\python.exe"

Write-Host "Instalando FastAPI, SQLAlchemy, Alembic, asyncpg y el resto ..."
& $venv -m pip install --upgrade pip
& $venv -m pip install -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw "pip no pudo instalar las dependencias (revisa el mensaje de arriba)." }

if (-not (Test-Path ".env") -and (Test-Path ".env.example")) { Copy-Item ".env.example" ".env"; Write-Host "Creado .env (cambia la contraseña)" }
if (-not (Test-Path ".env.local") -and (Test-Path ".env.local.example")) { Copy-Item ".env.local.example" ".env.local"; Write-Host "Creado .env.local" }

Write-Host "`nVersiones instaladas:" -ForegroundColor Cyan
& $venv -c "import fastapi, sqlalchemy, alembic, asyncpg, pydantic, pydantic_settings, uvicorn; print('fastapi', fastapi.__version__); print('sqlalchemy', sqlalchemy.__version__); print('alembic', alembic.__version__); print('asyncpg', asyncpg.__version__); print('pydantic', pydantic.__version__); print('uvicorn', uvicorn.__version__)"

Write-Host "`nComprobando que la app carga y corriendo pruebas ..." -ForegroundColor Cyan
$env:DATABASE_URL = "postgresql+asyncpg://u:p@localhost:5432/x"
& $venv -c "from app.main import app; print('App OK:', len(app.routes), 'rutas')"
& $venv -m pytest -q
Write-Host "`nListo. En VS Code elige el intérprete .venv\Scripts\python.exe" -ForegroundColor Green
