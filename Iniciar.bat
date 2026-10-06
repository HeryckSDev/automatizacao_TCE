@echo off
setlocal
cd /d "%~dp0"
title Analise Municipal
echo Abrindo a Analise Municipal...
if exist ".venv\Scripts\python.exe" goto ambiente_pronto
py -3 -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>&1
if errorlevel 1 goto tentar_python
py -3 -m venv .venv
if errorlevel 1 goto falha
goto ambiente_pronto
:tentar_python
python -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>&1
if errorlevel 1 goto sem_python
python -m venv .venv
if errorlevel 1 goto falha
:ambiente_pronto
if not exist ".venv\requisitos_instalados.txt" goto instalar
fc /b requirements.txt ".venv\requisitos_instalados.txt" >nul 2>&1
if errorlevel 1 goto instalar
goto abrir
:instalar
echo Na primeira abertura, vamos preparar o sistema. Aguarde com a internet conectada.
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto falha
copy /y requirements.txt ".venv\requisitos_instalados.txt" >nul
if errorlevel 1 goto falha
:abrir
".venv\Scripts\python.exe" iniciar.py
if errorlevel 1 goto falha
exit /b 0
:sem_python
echo Este computador precisa do Python 3.11 ou mais recente.
echo Instale em https://www.python.org/downloads/ marcando Add Python to PATH.
echo Depois, abra este arquivo novamente.
pause
exit /b 1
:falha
echo Nao foi possivel abrir agora. Confira a mensagem acima e tente novamente.
pause
exit /b 1
