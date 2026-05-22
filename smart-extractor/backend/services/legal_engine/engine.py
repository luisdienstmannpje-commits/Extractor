from __future__ import annotations

from datetime import datetime, date
from typing import List, Optional

from services.legal_engine.rule_base import LegalRule, ContextoJuridico, VerbaContexto

# ── Campos que NÃO devem ser preenchidos a partir de `dados` em _dict_para_contexto ──
# - verbas_deferidas : tratado à parte (lista de VerbaContexto)
# - alertas, regras_aplicadas : saída do engine, não entrada
# - correcao_pre_judicial, correcao_judicial, juros_judicial : derivados pelas regras (ADC 58)
_CAMPOS_EXCLUIDOS_DO_CONTEXTO: frozenset[str] = frozenset({
    "verbas_deferidas",
    "alertas",
    "regras_aplicadas",
    "shadow_hits",
    "correcao_pre_judicial",
    "correcao_judicial",
    "juros_judicial",
})

# Derivado automaticamente do modelo Pydantic — nunca fica fora de sincronia.
# Qualquer campo novo adicionado a ContextoJuridico (exceto os excluídos acima)
# passa a ser preenchido automaticamente a partir de `dados`.
_CAMPOS_ESCALARES: frozenset[str] = frozenset(
    ContextoJuridico.model_fields.keys()
) - _CAMPOS_EXCLUIDOS_DO_CONTEXTO


class LegalRuleEngine:
    def __init__(self, rules: List[LegalRule]):
        self.rules = sorted(rules, key=lambda r: r.prioridade)
        # Log de inicialização omitido — terminal fica limpo até "Application startup complete"

    def executar(self, dados: dict) -> dict:
        contexto = self._dict_para_contexto(dados)
        data_ref = self._parse_data(dados.get("data_admissao"))
        regras_puladas = []
        for rule in self.rules:
            if not rule.is_aplicavel(data_ref):
                regras_puladas.append(rule.id)
                continue
            try:
                contexto = rule.aplicar(contexto)
            except Exception as e:
                print(f"[ENGINE] Erro em {rule.id}: {e}", flush=True)
                contexto.alertas.append({
                    "nivel": "INFO",
                    "mensagem": f"Regra {rule.id} falhou: {type(e).__name__}",
                    "regra_id": rule.id,
                    "base_legal": rule.base_legal,
                })
        alertas_str = self._alertas_para_strings(contexto.alertas)
        erros  = sum(1 for a in alertas_str if "[ERRO]"  in a)
        avisos = sum(1 for a in alertas_str if "[AVISO]" in a)
        if not alertas_str:
            print("[ENGINE] Nenhum alerta", flush=True)
        else:
            print(f"[ENGINE] {erros} erro(s), {avisos} aviso(s)", flush=True)
        return {
            "alertas":           alertas_str,
            "regras_aplicadas":  contexto.regras_aplicadas,
            "memorial_juridico": self._gerar_memorial(contexto),
            "shadow_hits":       [dict(h) for h in contexto.shadow_hits],
        }

    def _dict_para_contexto(self, dados: dict) -> ContextoJuridico:
        # Verbas: construção manual (lista de VerbaContexto)
        verbas_raw = dados.get("verbas_deferidas") or []
        verbas = []
        for v in verbas_raw:
            if not isinstance(v, dict):
                continue
            try:
                verbas.append(VerbaContexto(
                    nome=v.get("nome") or "Verba nao identificada",
                    status_final=v.get("status_final"),
                    periodo=v.get("periodo"),
                    percentual=v.get("percentual"),
                    quantidade_diaria=v.get("quantidade_diaria"),
                    base_calculo=v.get("base_calculo"),
                    valor_fixado=v.get("valor_fixado"),
                    integracao_salarial=v.get("integracao_salarial"),
                    reflexos=v.get("reflexos") or [],
                    observacoes=v.get("observacoes"),
                ))
            except Exception as e:
                print(f"[ENGINE] Verba ignorada: {e}", flush=True)

        # Campos escalares: derivados automaticamente do modelo Pydantic.
        # Inclui fgts_observacoes (ausente na lista hardcoded anterior — bug corrigido).
        kwargs = {k: dados.get(k) for k in _CAMPOS_ESCALARES if k in dados}
        kwargs["verbas_deferidas"] = verbas
        return ContextoJuridico(**kwargs)

    @staticmethod
    def _alertas_para_strings(alertas: list) -> list:
        resultado = []
        for a in alertas:
            if isinstance(a, dict):
                resultado.append(f"[{a.get('nivel', 'AVISO')}] {a.get('mensagem', '')}")
            elif isinstance(a, str):
                resultado.append(a)
        return resultado

    @staticmethod
    def _parse_data(data_str):
        if not data_str:
            return None
        for fmt in ("%d/%m/%Y", "%d/%m/%y"):
            try:
                return datetime.strptime(data_str.strip(), fmt).date()
            except ValueError:
                continue
        return None

    def _gerar_memorial(self, contexto):
        regras_por_id = {r.id: r for r in self.rules}
        memorial = []
        for rid in contexto.regras_aplicadas:
            rule = regras_por_id.get(rid)
            if rule:
                memorial.append({
                    "id":        rule.id,
                    "titulo":    rule.titulo,
                    "base_legal": rule.base_legal,
                    "descricao": rule.descricao,
                    "prioridade": rule.prioridade,
                })
        return memorial
