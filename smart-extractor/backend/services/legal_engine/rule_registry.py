"""
rule_registry.py — Registro automático de regras jurídicas

Varre recursivamente:
  - services/legal_engine/rules/   (regras v5.0 — novas)
  - services/jurisprudencia/        (regras legadas — mantidas)

Permite adicionar uma nova regra apenas criando um novo arquivo .py
na pasta correta — sem alterar o motor ou o registry.

Uso:
    from services.legal_engine.rule_registry import carregar_todas_as_regras
    rules = carregar_todas_as_regras()
    engine = LegalRuleEngine(rules)
"""

from __future__ import annotations

import importlib
import inspect
import os
from typing import List

from services.legal_engine.rule_base import LegalRule

# Pastas varridas pelo registry
_PASTAS = [
    (
        os.path.join(os.path.dirname(__file__), "rules"),
        "services.legal_engine.rules",
    ),
    (
        os.path.join(os.path.dirname(__file__), "..", "jurisprudencia"),
        "services.jurisprudencia",
    ),
]


def _discover_modules(base_dir: str, base_package: str) -> list[str]:
    """
    Varre base_dir recursivamente e retorna lista de nomes de módulos Python.
    Ignora __init__.py e arquivos que começam com underscore.
    """
    modules = []
    base_dir = os.path.abspath(base_dir)

    if not os.path.exists(base_dir):
        print(f"[REGISTRY] Pasta não encontrada (ignorada): {base_dir}")
        return []

    for dirpath, _, filenames in os.walk(base_dir):
        for fname in sorted(filenames):
            if not fname.endswith(".py"):
                continue
            if fname.startswith("_"):
                continue

            full_path  = os.path.join(dirpath, fname)
            rel_path   = os.path.relpath(full_path, base_dir)
            module_rel = rel_path.replace(os.sep, ".").replace("/", ".")[:-3]
            full_module = f"{base_package}.{module_rel}"
            modules.append(full_module)

    return modules


def _load_rules_from_module(module_name: str) -> list[LegalRule]:
    """
    Importa o módulo e retorna instâncias de todas as subclasses de LegalRule.
    Ignora a própria LegalRule e classes abstratas.
    """
    rules = []
    try:
        mod = importlib.import_module(module_name)
    except ImportError as e:
        print(f"[REGISTRY] Aviso: não foi possível importar {module_name}: {e}")
        return rules

    for name, obj in inspect.getmembers(mod, inspect.isclass):
        if obj is LegalRule:
            continue
        if not issubclass(obj, LegalRule):
            continue
        if inspect.isabstract(obj):
            continue
        if not getattr(obj, "id", ""):
            print(f"[REGISTRY] Aviso: {name} em {module_name} sem 'id' — ignorada")
            continue
        try:
            instance = obj()
            rules.append(instance)
            # Log por regra omitido na inicialização — terminal fica limpo até "Application startup complete"
        except Exception as e:
            print(f"[REGISTRY] Erro ao instanciar {name}: {e}")

    return rules


def carregar_todas_as_regras() -> List[LegalRule]:
    """
    Carrega automaticamente todas as regras jurídicas das pastas registradas.
    A ordenação por prioridade é responsabilidade do LegalRuleEngine.
    """
    all_rules = []
    ids_vistos: set[str] = set()

    for base_dir, base_package in _PASTAS:
        module_names = _discover_modules(base_dir, base_package)
        for module_name in module_names:
            for rule in _load_rules_from_module(module_name):
                if rule.id in ids_vistos:
                    # Duplicados são esperados (regras em rules/ e jurisprudencia/) — não logar na inicialização
                    continue
                ids_vistos.add(rule.id)
                all_rules.append(rule)

    # Total omitido na inicialização — terminal fica limpo até "Application startup complete"
    return all_rules


def carregar_regras_por_prioridade(prioridade_max: int = 50) -> List[LegalRule]:
    """
    Carrega apenas regras até uma prioridade máxima.
    Útil para testes ou execução parcial (ex: apenas STF + TST).
    """
    todas = carregar_todas_as_regras()
    return [r for r in todas if r.prioridade <= prioridade_max]
