@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0deploy\setup.py" %*
) else (
    where python >nul 2>nul
    if errorlevel 1 (
        echo Instale Python 3.11 ou superior e habilite sua inclusao no PATH.
        exit /b 1
    )
    python "%~dp0deploy\setup.py" %*
)
exit /b %errorlevel%
