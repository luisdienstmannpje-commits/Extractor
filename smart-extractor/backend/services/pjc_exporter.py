"""
Re-exporta exportar_pjc e gerar_nome_arquivo do exporter em _archive.
Mantém a API esperada por main.py sem duplicar o código do PJeCalc v5.9.
"""
import importlib.util
import os

_ARCHIVE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "_archive", "pjc", "pjc_exporter_v5.9.py"
)
_spec = importlib.util.spec_from_file_location("_pjc_exporter_archive", _ARCHIVE_PATH)
_archive = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_archive)

exportar_pjc = _archive.exportar_pjc
gerar_nome_arquivo = _archive.gerar_nome_arquivo

__all__ = ["exportar_pjc", "gerar_nome_arquivo"]
