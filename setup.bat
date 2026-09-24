@echo off
echo =========================================
echo   Instalando Dependencias do App 
echo =========================================
echo.

echo 1. Configurando o Ambiente Python (Backend)...
python -m venv venv
call venv\Scripts\activate
pip install -r requirements.txt
echo Backend configurado com sucesso!
echo.

echo 2. Configurando o React (Frontend)...
:: Se o frontend estiver dentro de uma pasta (ex: /frontend), descomente a linha abaixo e mude o nome
:: cd frontend
call npm install
echo Frontend configurado com sucesso!
echo.

echo =========================================
echo   Tudo pronto! 
echo   Para rodar, inicie o backend e o frontend.
echo =========================================
pause