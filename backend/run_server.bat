@echo off
REM Inicia o backend com logs em tempo real no terminal (obrigatorio para ver [LAB], [FINDER], [AI], etc.)
REM Uso: run_server.bat
REM Abra no navegador a URL que o Uvicorn mostrar (ex.: http://localhost:8001/)

cd /d "%~dp0"
set PORT=8001
venv\Scripts\python.exe -u -m uvicorn main:app --host 0.0.0.0 --port 8001
