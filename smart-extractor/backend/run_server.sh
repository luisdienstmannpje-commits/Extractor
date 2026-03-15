#!/usr/bin/env bash
# Inicia o backend com logs em tempo real no terminal (obrigatorio para ver [LAB], [FINDER], [AI], etc.)
# Uso: ./run_server.sh   ou   bash run_server.sh
# Abra no navegador a URL que o Uvicorn mostrar (ex.: http://localhost:8001/)

set -e
cd "$(dirname "$0")"

export PORT=8001
exec venv/Scripts/python.exe -u -m uvicorn main:app --host 0.0.0.0 --port 8001
