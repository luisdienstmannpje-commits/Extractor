"""
VERIFICAR_MOTOR.py -- Verificador de integridade do Motor de Direito Programavel

Uso:
    cd backend
    python services/VERIFICAR_MOTOR.py           # verificacao completa
    python services/VERIFICAR_MOTOR.py --lista    # so lista as regras
    python services/VERIFICAR_MOTOR.py --smoke    # so roda o smoke test

Exit codes:
    0 -- tudo OK
    1 -- uma ou mais falhas de integridade

Integravel em CI:
    python services/VERIFICAR_MOTOR.py || exit 1
"""

from __future__ import annotations

import sys

# Fix encoding para Git Bash / Windows (cp1252 nao suporta caracteres especiais)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import os
import argparse
from datetime import date
from typing import Optional

# Garante que o backend/ esta no path (script rodado de dentro de backend/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Campos de data validos para data_ref_campo ────────────────────────────────
_CAMPOS_DATA_VALIDOS = {
    "data_admissao",
    "data_demissao",
    "data_saida_ctps",
    "data_ajuizamento",
    "data_sentenca",
}

# ── Processo sintetico minimo para smoke test ─────────────────────────────────
_PROCESSO_SMOKE = {
    "numero_processo":             "0099999-99.2025.5.03.0167",
    "reclamante":                  "Reclamante Teste",
    "reclamada":                   "Reclamada Teste LTDA",
    "data_admissao":               "01/01/2022",
    "data_demissao":               "01/06/2025",
    "data_ajuizamento":            "15/07/2025",
    "data_sentenca":               "01/11/2025",
    "motivo_rescisao":             "Sem justa causa",
    "salario_base":                "R$ 3.200,00",
    "jornada_contratual":          "8h diarias / 44h semanais",
    "indice_correcao":             "IPCA-E ate ajuizamento e SELIC apos",
    "juros_mora":                  "1% ao mes ate a sentenca",
    "fgts_sobre_aviso_previo":     "Sim -- incide",
    "fgts_multa_40_aviso_previo":  "Nao incide",
    "fgts_sobre_ferias_indenizadas": "Nao incide",
    "percentual_honorarios":       "10%",
    "aviso_previo_dias":           "60 dias",
    "justica_gratuita":            True,
    "verbas_deferidas": [
        {
            "nome": "Horas Extras",
            "status_final": "deferida",
            "periodo": "01/01/2022 a 01/06/2025",
            "percentual": "50%",
            "integracao_salarial": True,
            "reflexos": ["DSR", "Ferias", "13º Salario", "FGTS"],
        },
        {
            "nome": "Aviso Previo",
            "status_final": "deferida",
            "periodo": "01/06/2025 a 31/07/2025",
            "integracao_salarial": False,
            "reflexos": [],
        },
        {
            "nome": "Ferias + 1/3",
            "status_final": "deferida",
            "periodo": "2024/2025",
            "integracao_salarial": False,
            "reflexos": [],
        },
    ],
}


# ── Helpers de output ─────────────────────────────────────────────────────────

def _ok(msg: str):
    print(f"  [OK]    {msg}")

def _fail(msg: str):
    print(f"  [FALHA] {msg}")

def _warn(msg: str):
    print(f"  [AVISO] {msg}")

def _secao(titulo: str):
    print(f"\n{'='*60}")
    print(f"  {titulo}")
    print(f"{'='*60}")


# ── Verificacoes de integridade ───────────────────────────────────────────────

def verificar_atributos(rule) -> list[str]:
    """Retorna lista de falhas para uma regra. Vazia = ok."""
    falhas = []
    nome_classe = type(rule).__name__

    if not getattr(rule, "id", ""):
        falhas.append(f"{nome_classe}: 'id' vazio ou ausente")

    if not getattr(rule, "titulo", ""):
        falhas.append(f"{nome_classe}: 'titulo' vazio ou ausente")

    if not getattr(rule, "base_legal", ""):
        falhas.append(f"{nome_classe}: 'base_legal' vazio ou ausente")

    prioridade = getattr(rule, "prioridade", None)
    if not isinstance(prioridade, int) or prioridade <= 0:
        falhas.append(f"{nome_classe}: 'prioridade' invalida ({prioridade!r}) -- deve ser int > 0")

    data_ref_campo = getattr(rule, "data_ref_campo", None)
    if data_ref_campo not in _CAMPOS_DATA_VALIDOS:
        falhas.append(
            f"{nome_classe}: 'data_ref_campo' invalido ({data_ref_campo!r}). "
            f"Validos: {sorted(_CAMPOS_DATA_VALIDOS)}"
        )

    vigencia = getattr(rule, "vigencia_inicio", None)
    if not isinstance(vigencia, date):
        falhas.append(f"{nome_classe}: 'vigencia_inicio' nao e um date ({vigencia!r})")

    # Verifica se aplicar() existe e e callable
    if not callable(getattr(rule, "aplicar", None)):
        falhas.append(f"{nome_classe}: metodo 'aplicar()' ausente ou nao callable")

    return falhas


def verificar_duplicatas(rules) -> list[str]:
    """Detecta IDs duplicados entre as regras carregadas."""
    from collections import Counter
    ids = [r.id for r in rules if r.id]
    duplicados = [rid for rid, count in Counter(ids).items() if count > 1]
    if duplicados:
        return [f"IDs duplicados: {duplicados}"]
    return []


def smoke_test(rules) -> tuple[bool, list[str]]:
    """
    Roda o engine completo com um processo sintetico.
    Retorna (sucesso, lista_de_problemas).
    """
    from services.legal_engine.engine import LegalRuleEngine

    problemas = []
    try:
        engine = LegalRuleEngine(rules)
        resultado = engine.executar(_PROCESSO_SMOKE)
    except Exception as e:
        return False, [f"Engine.executar() lancou excecao: {type(e).__name__}: {e}"]

    # Verifica estrutura do resultado
    campos_esperados = {"alertas", "regras_aplicadas", "memorial_juridico"}
    faltando = campos_esperados - set(resultado.keys())
    if faltando:
        problemas.append(f"Resultado do engine sem campos: {faltando}")

    alertas = resultado.get("alertas", [])
    if not isinstance(alertas, list):
        problemas.append(f"'alertas' deveria ser list, e {type(alertas).__name__}")

    regras_aplicadas = resultado.get("regras_aplicadas", [])
    if not isinstance(regras_aplicadas, list):
        problemas.append(f"'regras_aplicadas' deveria ser list, e {type(regras_aplicadas).__name__}")

    # Verifica que nenhum alerta e de erro de execucao (regra que falhou)
    for alerta in alertas:
        if isinstance(alerta, str) and "falhou:" in alerta.lower():
            problemas.append(f"Regra falhou durante smoke test: {alerta}")

    return len(problemas) == 0, problemas


# ── Modos de execucao ─────────────────────────────────────────────────────────

def cmd_lista(rules):
    """Imprime tabela de todas as regras carregadas."""
    _secao("REGRAS CARREGADAS")

    if not rules:
        print("  Nenhuma regra carregada.")
        return

    col_id      = max(len(r.id) for r in rules)
    col_titulo  = min(max(len(r.titulo) for r in rules), 40)

    header = f"  {'Prio':<5}  {'ID':<{col_id}}  {'data_ref_campo':<18}  {'Titulo':<{col_titulo}}  Base Legal"
    print(header)
    print(f"  {'-'*4}  {'-'*col_id}  {'-'*18}  {'-'*col_titulo}  {'-'*30}")

    for rule in sorted(rules, key=lambda r: r.prioridade):
        titulo = rule.titulo[:col_titulo]
        print(
            f"  {rule.prioridade:<5}  "
            f"{rule.id:<{col_id}}  "
            f"{rule.data_ref_campo:<18}  "
            f"{titulo:<{col_titulo}}  "
            f"{rule.base_legal}"
        )

    print(f"\n  Total: {len(rules)} regras")


def cmd_integridade(rules) -> int:
    """Verifica integridade de todas as regras. Retorna numero de falhas."""
    _secao("VERIFICACAO DE INTEGRIDADE")

    total_falhas = 0

    # 1. Atributos por regra
    for rule in rules:
        falhas = verificar_atributos(rule)
        if falhas:
            for f in falhas:
                _fail(f)
            total_falhas += len(falhas)
        else:
            _ok(f"{rule.id} -- atributos OK")

    # 2. Duplicatas globais
    duplicatas = verificar_duplicatas(rules)
    if duplicatas:
        for d in duplicatas:
            _fail(d)
        total_falhas += len(duplicatas)
    else:
        _ok("Sem IDs duplicados")

    # 3. Cobertura minima esperada
    _secao("COBERTURA DE NORMAS")
    normas_esperadas = {
        "ADC_58_STF":       "ADC 58 STF",
        "SUMULA_305_TST":   "Sumula 305 TST",
        "OJ_42_SDI1_TST":   "OJ 42 SDI-I TST",
        "OJ_195_SDI1_TST":  "OJ 195 SDI-I TST",
        "ART_791A_CLT":     "Art. 791-A CLT",
    }
    ids_carregados = {r.id for r in rules}
    for rid, nome in normas_esperadas.items():
        if rid in ids_carregados:
            _ok(f"{nome} ({rid})")
        else:
            _warn(f"{nome} ({rid}) -- nao carregada (arquivo ausente?)")
            # Aviso, nao falha -- pode ser intencional

    return total_falhas


def cmd_smoke(rules) -> int:
    """Executa smoke test. Retorna numero de falhas."""
    _secao("SMOKE TEST -- Processo Sintetico")
    print(f"  Processo: {_PROCESSO_SMOKE['numero_processo']}")
    print(f"  Admissao: {_PROCESSO_SMOKE['data_admissao']} | Sentenca: {_PROCESSO_SMOKE['data_sentenca']}")
    print(f"  Verbas:   {len(_PROCESSO_SMOKE['verbas_deferidas'])} itens\n")

    ok, problemas = smoke_test(rules)
    if ok:
        _ok("Engine.executar() completou sem excecoes")
        _ok("Estrutura do resultado validada")
        _ok("Nenhuma regra falhou durante execucao")
        return 0
    else:
        for p in problemas:
            _fail(p)
        return len(problemas)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Verifica integridade do Motor de Direito Programavel"
    )
    parser.add_argument("--lista",  action="store_true", help="Apenas lista as regras")
    parser.add_argument("--smoke",  action="store_true", help="Apenas roda o smoke test")
    args = parser.parse_args()

    print("\nPJeCalc Smart Extractor -- Verificador do Motor Juridico")
    print(f"Data: {date.today().strftime('%d/%m/%Y')}")

    # Carrega regras
    _secao("CARREGAMENTO DE REGRAS")
    try:
        from services.legal_engine.rule_registry import carregar_todas_as_regras
        rules = carregar_todas_as_regras()
    except Exception as e:
        print(f"\n  [FALHA CRITICA] Nao foi possivel carregar as regras: {e}")
        sys.exit(1)

    if not rules:
        print("  [AVISO] Nenhuma regra carregada -- pasta jurisprudencia/ pode estar vazia.")

    total_falhas = 0

    if args.lista:
        cmd_lista(rules)

    elif args.smoke:
        total_falhas += cmd_smoke(rules)

    else:
        # Modo completo: lista + integridade + smoke
        cmd_lista(rules)
        total_falhas += cmd_integridade(rules)
        total_falhas += cmd_smoke(rules)

    # ── Resumo final ──────────────────────────────────────────────────────────
    _secao("RESUMO")
    if total_falhas == 0:
        print(f"  RESULTADO: OK -- {len(rules)} regras, 0 falhas")
        print(f"  Motor pronto para producao.\n")
        sys.exit(0)
    else:
        print(f"  RESULTADO: FALHA -- {total_falhas} problema(s) encontrado(s)")
        print(f"  Corrija os itens marcados com [FALHA] antes de subir.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()