"""
learning_skill_loader.py — Carrega playbook para o laboratório de aprendizado.

Separado do processor.py para não criar dependência circular.
"""
from __future__ import annotations
import os

_SKILLS_DIR = os.path.join(os.path.dirname(__file__), "..", "skills")

_PLAYBOOK_MAP = {
    "sentenca":   "sentenca_ordinaria.md",
    "acordao":    "acordao.md",
    "liquidacao": "calculo_liquidacao.md",
    "embargos":   "embargos_declaracao.md",
    "despacho":   "despacho_execucao.md",
    "completo":   "sentenca_ordinaria.md",
}


def carregar_skill_para_lab(doc_type: str) -> str:
    filename = _PLAYBOOK_MAP.get(doc_type, "sentenca_ordinaria.md")
    path = os.path.join(_SKILLS_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""
