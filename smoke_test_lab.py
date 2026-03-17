"""
Smoke test do Laboratorio: executa a partir da raiz do projeto.
Comando: python smoke_test_lab.py
"""
import sys
from pathlib import Path

# Inclui backend no path (orquestrador na raiz)
_root = Path(__file__).resolve().parent
_backend = _root / "backend"
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

# Executa o teste que esta em backend/smoke_test_lab.py
import runpy
runpy.run_path(str(_backend / "smoke_test_lab.py"), run_name="__main__")
