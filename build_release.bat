@echo off
setlocal
cd /d "%~dp0"

set "PYTHON=%~dp0venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"

"%PYTHON%" -m PyInstaller --version >nul 2>nul
if errorlevel 1 (
    echo PyInstaller is not installed. Run: "%PYTHON%" -m pip install -r requirements.txt
    exit /b 1
)

"%PYTHON%" -m PyInstaller --clean --noconfirm neuralcontrol.spec
if errorlevel 1 exit /b 1

"%PYTHON%" scripts\stage_release.py
if errorlevel 1 exit /b 1

"%PYTHON%" scripts\package_release.py
if errorlevel 1 exit /b 1

echo Release package created: NeuralControl_Release.zip
exit /b 0
