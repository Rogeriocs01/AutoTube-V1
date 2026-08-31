$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================"
Write-Host "   AUTOTUBE - BUILD DO EXECUTAVEL"
Write-Host "========================================"
Write-Host ""

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "ERRO: ambiente virtual .venv nao encontrado."
    exit 1
}

Write-Host "Ativando ambiente virtual..."
& ".\.venv\Scripts\Activate.ps1"

Write-Host ""
Write-Host "Verificando PyInstaller..."

python -m PyInstaller --version

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "PyInstaller nao encontrado."
    Write-Host "Instalando..."
    python -m pip install pyinstaller
}

Write-Host ""
Write-Host "Limpando builds anteriores..."

if (Test-Path ".\build") {
    Remove-Item ".\build" -Recurse -Force
}

if (Test-Path ".\dist") {
    Remove-Item ".\dist" -Recurse -Force
}

if (Test-Path ".\AutoTube.spec") {
    Remove-Item ".\AutoTube.spec" -Force
}

Write-Host ""
Write-Host "Gerando AutoTube.exe..."

python -m PyInstaller `
    --onefile `
    --console `
    --name AutoTube `
    app.py

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERRO: falha durante o build."
    exit 1
}

Write-Host ""
Write-Host "Copiando executavel para a raiz..."

Copy-Item ".\dist\AutoTube.exe" ".\AutoTube.exe" -Force

Write-Host ""
Write-Host "========================================"
Write-Host "BUILD CONCLUIDO COM SUCESSO"
Write-Host "========================================"
Write-Host ""
Write-Host "Executavel:"
Write-Host "$(Resolve-Path '.\AutoTube.exe')"
Write-Host ""