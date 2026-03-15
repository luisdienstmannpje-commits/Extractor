"""
Launcher: ao rodar uvicorn a partir da raiz do projeto, carrega o app do backend.

Uso (na raiz smart-extractor):
  venv/Scripts/python.exe -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""
import sys
import importlib.util
from pathlib import Path

_backend_dir = Path(__file__).resolve().parent / "backend"

# Garante que os imports internos do backend (services, workers, etc.) funcionem
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

# Carrega backend/main.py com nome diferente para evitar import circular
_spec = importlib.util.spec_from_file_location("backend_main", _backend_dir / "main.py")
_backend_main = importlib.util.module_from_spec(_spec)
sys.modules["backend_main"] = _backend_main
_spec.loader.exec_module(_backend_main)

app = _backend_main.app
