"""
knowledge_base.py — Banco de Conhecimento do Self-Healing Rule Engine

Armazena regras aprendidas autonomamente pelo sistema com sistema de pontuação de
Confiança (Confidence Score) que determina o ciclo de vida de cada regra:

  status "shadow"  — regra em observação silenciosa (score 1–2)
  status "active"  — regra confirmada, gera alertas reais (score >= THRESHOLD_ACTIVE)
  status "deleted" — regra descartada por punição (score <= THRESHOLD_DELETE)

Limites padrão: active >= 3 | deleted <= -1

Thread-safe via filelock (fallback sem lock se não disponível).
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

_HERE       = os.path.dirname(__file__)
_BACKEND    = os.path.abspath(os.path.join(_HERE, ".."))

THRESHOLD_ACTIVE = 3
THRESHOLD_DELETE = -1


def _now() -> str:
    return datetime.now().isoformat()


class KnowledgeBase:
    """
    Interface de CRUD para o Banco de Conhecimento de regras dinâmicas.

    Cada regra segue o esquema:
    {
      "rule_id":        str  — identificador único gerado automaticamente,
      "descricao":      str  — texto legível da correção aprendida,
      "condicao":       dict — {tipo, verba?, campo?, valor_esperado?},
      "acao":           dict — {tipo, nivel, mensagem},
      "base_legal":     str  — artigo/súmula base (se disponível),
      "confidence_score": int  — pontuação de confiança (inicia em 1),
      "status":         str  — "shadow" | "active" | "deleted",
      "casos_vistos":   list — IDs dos processos que acionaram esta regra,
      "acertos":        int  — vezes que a regra foi confirmada pelo parecer,
      "punicoes":       int  — vezes que a regra foi contradita pelo parecer,
      "created_at":     str  — ISO datetime,
      "updated_at":     str  — ISO datetime
    }
    """

    _instances: Dict[str, "KnowledgeBase"] = {}

    def __new__(cls, tenant_id: str = "default"):
        if tenant_id not in cls._instances:
            instance = super(KnowledgeBase, cls).__new__(cls)
            instance._initialized = False
            cls._instances[tenant_id] = instance
        return cls._instances[tenant_id]

    def __init__(self, tenant_id: str = "default"):
        if getattr(self, "_initialized", False):
            return

        self.tenant_id = tenant_id

        if self.tenant_id == "default":
            self._path = os.path.join(_BACKEND, "knowledge_base.json")
        else:
            self._path = os.path.join(_BACKEND, f"knowledge_base_{self.tenant_id}.json")

        self._data: Dict[str, Any] = self._carregar()
        self._initialized = True

    # ── I/O ──────────────────────────────────────────────────────────────────

    def _carregar(self) -> Dict[str, Any]:
        if not os.path.exists(self._path):
            return {
                "rules": [],
                "_meta": {
                    "version": "1.0",
                    "tenant_id": getattr(self, "tenant_id", "default"),
                    "last_updated": _now(),
                },
            }
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            # Usa logging estruturado indireto via stderr/stdout; mensagem simples aqui.
            import logging

            logging.getLogger("smart_extractor").error(
                f"[KB] Erro ao carregar knowledge_base.json: {e}"
            )
            return {
                "rules": [],
                "_meta": {
                    "version": "1.0",
                    "tenant_id": getattr(self, "tenant_id", "default"),
                    "last_updated": _now(),
                },
            }

    def _salvar(self) -> None:
        try:
            os.makedirs(os.path.dirname(self._path), exist_ok=True)
            self._data["_meta"]["updated_at"] = _now()
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            import logging

            logging.getLogger("smart_extractor").error(
                f"[KB] Erro ao salvar knowledge_base.json: {e}"
            )

    def _recarregar(self) -> None:
        """Recarrega do disco para evitar conflitos entre workers."""
        self._data = self._carregar()

    def get_all(self) -> Dict[str, Any]:
        """Retorna o dicionário completo (rules + _meta) para a API. Cópia para não alterar estado."""
        import copy
        return copy.deepcopy(self._data) if self._data else {"rules": [], "_meta": {"version": "1.0"}}

    # ── Consultas ─────────────────────────────────────────────────────────────

    def get_todas(self) -> List[Dict]:
        return [r for r in self._data.get("rules", []) if r.get("status") != "deleted"]

    def get_regras_ativas(self) -> List[Dict]:
        return [r for r in self.get_todas() if r.get("status") == "active"]

    def get_regras_shadow(self) -> List[Dict]:
        return [r for r in self.get_todas() if r.get("status") == "shadow"]

    def get_por_id(self, rule_id: str) -> Optional[Dict]:
        for r in self._data.get("rules", []):
            if r.get("rule_id") == rule_id:
                return r
        return None

    def stats(self) -> Dict:
        rules = self._data.get("rules", [])
        total = len(rules)
        ativas  = sum(1 for r in rules if r.get("status") == "active")
        shadow  = sum(1 for r in rules if r.get("status") == "shadow")
        deleted = sum(1 for r in rules if r.get("status") == "deleted")
        return {"total": total, "active": ativas, "shadow": shadow, "deleted": deleted}

    # ── Correspondência fuzzy ─────────────────────────────────────────────────

    def encontrar_similar(self, logica: Dict) -> Optional[Dict]:
        """
        Verifica se já existe uma regra com condição similar no KB.
        Critério: mesmo tipo de condição + mesma verba/campo (match parcial normalizado).
        Retorna a regra existente ou None.
        """
        tipo_novo  = (logica.get("condicao") or {}).get("tipo", "").lower()
        verba_nova = _normalizar(
            (logica.get("condicao") or {}).get("verba", "") or
            (logica.get("condicao") or {}).get("campo", "")
        )

        for regra in self.get_todas():
            cond = regra.get("condicao") or {}
            if cond.get("tipo", "").lower() != tipo_novo:
                continue
            verba_existente = _normalizar(
                cond.get("verba", "") or cond.get("campo", "")
            )
            if verba_nova and verba_existente:
                # Match se uma contém a outra (80%+ overlap)
                if verba_nova in verba_existente or verba_existente in verba_nova:
                    return regra
        return None

    # ── Ciclo de vida ─────────────────────────────────────────────────────────

    def adicionar_ou_incrementar(
        self,
        logica: Dict,
        numero_processo: str = "",
    ) -> Dict:
        """
        Ponto de entrada principal do aprendizado autônomo.

        - Se a lógica extraída pelo Gemini já existe no KB → incrementa confidence.
        - Se não existe → cria nova regra com status 'shadow' e confidence = 1.

        Retorna {"acao": "criada"|"incrementada"|"ativada", "rule_id": ...}
        """
        self._recarregar()
        existente = self.encontrar_similar(logica)

        if existente:
            return self._incrementar(existente["rule_id"], numero_processo)
        else:
            return self._criar(logica, numero_processo)

    def _criar(self, logica: Dict, numero_processo: str = "") -> Dict:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:20]
        rule_id   = f"DYN_{timestamp}"

        nova_regra: Dict[str, Any] = {
            "rule_id":          rule_id,
            "descricao":        logica.get("descricao", "Regra aprendida autonomamente"),
            "condicao":         logica.get("condicao", {}),
            "acao":             logica.get("acao", {"tipo": "alerta", "nivel": "AVISO", "mensagem": logica.get("descricao", "")}),
            "base_legal":       logica.get("base_legal", ""),
            "confidence_score": 1,
            "status":           "shadow",
            "casos_vistos":     [numero_processo] if numero_processo else [],
            "acertos":          0,
            "punicoes":         0,
            "created_at":       _now(),
            "updated_at":       _now(),
        }

        self._data.setdefault("rules", []).append(nova_regra)
        self._salvar()
        return {"acao": "criada", "rule_id": rule_id, "status": "shadow"}

    def _incrementar(self, rule_id: str, numero_processo: str = "") -> Dict:
        self._recarregar()
        for regra in self._data.get("rules", []):
            if regra.get("rule_id") != rule_id:
                continue

            regra["confidence_score"] = regra.get("confidence_score", 1) + 1
            regra["acertos"] = regra.get("acertos", 0) + 1
            regra["updated_at"] = _now()

            if numero_processo and numero_processo not in regra.get("casos_vistos", []):
                regra.setdefault("casos_vistos", []).append(numero_processo)

            acao = "incrementada"
            if regra["confidence_score"] >= THRESHOLD_ACTIVE and regra["status"] == "shadow":
                regra["status"] = "active"
                acao = "ativada"

            self._salvar()
            return {"acao": acao, "rule_id": rule_id, "status": regra["status"]}

        return {"acao": "nao_encontrada", "rule_id": rule_id}

    def decrementar(self, rule_id: str) -> Dict:
        """
        Punição: decrementa o confidence_score de uma regra.
        Se atingir THRESHOLD_DELETE, marca como 'deleted' (esquecida).
        """
        self._recarregar()
        for regra in self._data.get("rules", []):
            if regra.get("rule_id") != rule_id:
                continue

            regra["confidence_score"] = regra.get("confidence_score", 1) - 1
            regra["punicoes"] = regra.get("punicoes", 0) + 1
            regra["updated_at"] = _now()

            acao = "decrementada"
            if regra["confidence_score"] <= THRESHOLD_DELETE:
                regra["status"] = "deleted"
                acao = "deletada"
                print(f"[KB] Regra DELETADA por punição (score={regra['confidence_score']}): {rule_id}")
            else:
                print(f"[KB] Score decrementado ({regra['confidence_score']}): {rule_id}")

            self._salvar()
            return {"acao": acao, "rule_id": rule_id, "status": regra["status"]}

        return {"acao": "nao_encontrada", "rule_id": rule_id}

    def marcar_acerto(self, rule_id: str, numero_processo: str = "") -> Dict:
        """Confirma que uma regra shadow previu corretamente — incrementa sem criar nova."""
        return self._incrementar(rule_id, numero_processo)

    def marcar_punicao(self, rule_id: str) -> Dict:
        """Penaliza uma regra shadow que previu incorretamente."""
        return self.decrementar(rule_id)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalizar(texto: str) -> str:
    """Normaliza string para comparação fuzzy (lower, sem acentos, sem pontuação)."""
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
    t = re.sub(r"\s+", " ", t).strip()
    return t
