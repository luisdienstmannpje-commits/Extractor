"""
dynamic_rule_loader.py — Carregador de Regras Dinâmicas (Self-Healing Rule Engine)

Lê o knowledge_base.json e instancia DynamicLegalRule para cada entrada:

  status "active"  → regra injetada no LegalRuleEngine real (gera alertas para o usuário)
  status "shadow"  → regra executada em modo fantasma (silêncio total; apenas métricas internas)

As DynamicLegalRule suportam os seguintes tipos de condição:
  verba_ausente    — verba deferida na sentença mas não calculada (nome parcial)
  verba_presente   — verba presente nas verbas deferidas (detecção de inclusão)
  indice_ausente   — contexto.indice_correcao é None/vazio
  campo_ausente    — campo específico do ContextoJuridico é None/vazio
  campo_diferente  — campo não contém o valor esperado

Prioridade padrão das regras dinâmicas: 45 (entre CLT=40 e Consistência=50).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from services.legal_engine.rule_base import ContextoJuridico, LegalRule


# ── Regra Dinâmica ────────────────────────────────────────────────────────────

class DynamicLegalRule(LegalRule):
    """
    Regra jurídica gerada dinamicamente a partir de uma entrada do Knowledge Base.

    Cada instância encapsula a lógica de condição/ação extraída pelo Gemini e
    avaliada autonomamente contra o ContextoJuridico no pipeline.
    """

    id        = "DYN_PLACEHOLDER"
    titulo    = "Regra dinâmica"
    base_legal = ""
    prioridade = 45
    descricao  = ""

    def __init__(self, kb_entry: Dict[str, Any]):
        super().__init__()
        self.id         = kb_entry.get("rule_id", "DYN_UNKNOWN")
        self.titulo     = kb_entry.get("descricao", "Regra aprendida")[:80]
        self.base_legal = kb_entry.get("base_legal", "")
        self.descricao  = kb_entry.get("descricao", "")
        self._condicao  = kb_entry.get("condicao") or {}
        self._acao      = kb_entry.get("acao") or {}
        self._shadow    = kb_entry.get("status") == "shadow"
        self._confidence = kb_entry.get("confidence_score", 1)

    # ── Avaliação da condição ─────────────────────────────────────────────────

    def _avaliar_condicao(self, contexto: ContextoJuridico) -> bool:
        """
        Avalia se a condição da regra se aplica ao contexto atual.
        Retorna True se a regra deve disparar.
        """
        tipo = self._condicao.get("tipo", "").lower()

        if tipo == "verba_ausente":
            # Verba deveria estar nas verbas_deferidas mas não está
            verba = _norm(self._condicao.get("verba") or "")
            if not verba:
                return False
            verbas_ctx = [_norm(v.nome) for v in (contexto.verbas_deferidas or [])]
            return not any(verba in v or v in verba for v in verbas_ctx)

        if tipo == "verba_presente":
            # Verba está presente (detecta inclusão — pode ser usada para verificações)
            verba = _norm(self._condicao.get("verba") or "")
            if not verba:
                return False
            verbas_ctx = [_norm(v.nome) for v in (contexto.verbas_deferidas or [])]
            return any(verba in v or v in verba for v in verbas_ctx)

        if tipo == "indice_ausente":
            return not bool(contexto.indice_correcao)

        if tipo == "campo_ausente":
            campo = self._condicao.get("campo", "")
            return campo and not bool(getattr(contexto, campo, None))

        if tipo == "campo_diferente":
            campo    = self._condicao.get("campo", "")
            esperado = _norm(str(self._condicao.get("valor_esperado") or ""))
            atual    = _norm(str(getattr(contexto, campo, "") or ""))
            return bool(esperado) and bool(atual) and esperado not in atual

        # Tipo desconhecido — não dispara
        return False

    # ── Aplicação ─────────────────────────────────────────────────────────────

    def aplicar(self, contexto: ContextoJuridico) -> ContextoJuridico:
        try:
            if not self._avaliar_condicao(contexto):
                return contexto

            nivel    = self._acao.get("nivel", "AVISO")
            mensagem = self._acao.get("mensagem") or self.descricao

            if self._shadow:
                # Shadow mode: registra internamente mas NÃO adiciona ao contexto de alertas
                _shadow_log(self.id, contexto.numero_processo or "?", mensagem)
                contexto.shadow_hits.append(
                    {
                        "rule_id": self.id,
                        "mensagem": mensagem,
                        "nivel": str(self._acao.get("nivel", "SHADOW")),
                        "numero_processo": contexto.numero_processo,
                    }
                )
                self._registrar(contexto)
            else:
                # Modo ativo: alerta real para o usuário
                sufixo = f" [DYN score={self._confidence}]"
                self._alerta(contexto, mensagem + sufixo, nivel=nivel)
                self._registrar(contexto)

        except Exception as e:
            print(f"[DYNAMIC_RULE] Erro em {self.id}: {e}")

        return contexto


# ── Shadow Log ────────────────────────────────────────────────────────────────

_shadow_hits: List[Dict] = []   # buffer em memória; não persiste entre restarts


def _shadow_log(rule_id: str, processo: str, mensagem: str) -> None:
    from datetime import datetime
    _shadow_hits.append({
        "rule_id":    rule_id,
        "processo":   processo,
        "mensagem":   mensagem,
        "ts":         datetime.now().isoformat(),
    })


def get_shadow_hits() -> List[Dict]:
    """Retorna os hits de shadow mode desde o último restart (debug/métricas)."""
    return list(_shadow_hits)


def clear_shadow_hits() -> None:
    _shadow_hits.clear()


# ── Carregador Principal ──────────────────────────────────────────────────────

def carregar_regras_ativas() -> List[DynamicLegalRule]:
    """
    Carrega e instancia apenas as regras com status 'active' do Knowledge Base.
    Usadas no pipeline principal (passo 8) — geram alertas reais para o usuário.
    """
    try:
        from services.knowledge_base import KnowledgeBase
        from services.request_context import current_tenant_id

        kb = KnowledgeBase(tenant_id=current_tenant_id())
        ativas = kb.get_regras_ativas()
        regras = [DynamicLegalRule(e) for e in ativas]
        if regras:
            print(f"[DYN] {len(regras)} regra(s) dinâmica(s) ativa(s) carregada(s)")
        return regras
    except Exception as e:
        print(f"[DYN] Erro ao carregar regras ativas: {e}")
        return []


def carregar_regras_shadow() -> List[DynamicLegalRule]:
    """
    Carrega e instancia apenas as regras com status 'shadow' do Knowledge Base.
    Executadas silenciosamente no pipeline para coleta de métricas.
    """
    try:
        from services.knowledge_base import KnowledgeBase
        from services.request_context import current_tenant_id

        kb = KnowledgeBase(tenant_id=current_tenant_id())
        shadow = kb.get_regras_shadow()
        regras = [DynamicLegalRule(e) for e in shadow]
        if regras:
            print(f"[DYN] {len(regras)} regra(s) shadow carregada(s)")
        return regras
    except Exception as e:
        print(f"[DYN] Erro ao carregar regras shadow: {e}")
        return []


def executar_shadow_pipeline(dados: dict) -> List[Dict]:
    """
    Executa todas as regras shadow (KB) silenciosamente sobre os dados do processo.

    Retorna lista de dicts (rule_id, mensagem, nivel, numero_processo) por **esta**
    execução — seguro em paralelo (acumula em ContextoJuridico, não em buffer global).
    """
    from services.legal_engine.engine import LegalRuleEngine
    shadow_rules = carregar_regras_shadow()
    if not shadow_rules:
        return []

    try:
        engine_shadow = LegalRuleEngine(shadow_rules)
        resultado = engine_shadow.executar(dados)
        hits = resultado.get("shadow_hits") or []
        if hits:
            ids = [h.get("rule_id") for h in hits if isinstance(h, dict)]
            print(f"[SHADOW] {len(hits)} hit(s) shadow: {ids}", flush=True)
        return hits
    except Exception as e:
        print(f"[SHADOW] Erro ao executar shadow pipeline: {e}", flush=True)
        return []


# ── Helper ────────────────────────────────────────────────────────────────────

def _norm(texto: str) -> str:
    if not texto:
        return ""
    t = texto.lower().strip()
    t = re.sub(r"[áàãâä]", "a", t)
    t = re.sub(r"[éèêë]", "e", t)
    t = re.sub(r"[íìîï]", "i", t)
    t = re.sub(r"[óòõôö]", "o", t)
    t = re.sub(r"[úùûü]", "u", t)
    t = re.sub(r"ç", "c", t)
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    return re.sub(r"\s+", " ", t).strip()
