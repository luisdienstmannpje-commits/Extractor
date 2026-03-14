#!/usr/bin/env bash
# Roda a API a partir da pasta backend (obrigatório).
# Evita carregar o main.py da raiz e evita que o --reload vigie a pasta venv/.
# Carrega .env para PYTHONUNBUFFERED=1 (logs em tempo real no terminal).
cd "$(dirname "$0")/backend" || exit 1
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -x "venv/Scripts/python.exe" ]; then
  exec venv/Scripts/python.exe -u -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
elif [ -x "../venv/Scripts/python.exe" ]; then
  exec ../venv/Scripts/python.exe -u -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
else
  exec python -u -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
fi
