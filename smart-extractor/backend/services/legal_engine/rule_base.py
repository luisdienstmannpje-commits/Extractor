"""
rule_base.py — Classe base do Motor de Direito Programável

Contém:
  - ContextoJuridico: modelo Pydantic tipado (sugestão A do Tech Lead)
  - LegalRule: classe abstrata que toda regra jurídica deve herdar
  - Suporte a vigência temporal (sugestão B — Reforma Trabalhista)
  - Atributo de prioridade para hierarquia normativa (sugestão C — pirâmide de Kelsen)

Hierarquia de prioridade (menor número = executa primeiro):
  10  — STF (decisões vinculantes, ADCs, ADIs)
  20  — TST Súmulas
  30  — TST Orientações Jurisprudenciais (OJs)
  40  — CLT e legislação federal
  50  — Consistência e matemática (validações sem base normativa específica)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Any, List, Optional
from pydantic import BaseModel, Field


# ── Contexto Jurídico (Pydantic — tipagem forte) ──────────────────────────────

class VerbaContexto(BaseModel):
    """Representa uma verba deferida no contexto de execução das regras."""
    nome:               str
    status_final:       Optional[str]  = None
    periodo:            Optional[str]  = None
    percentual:         Optional[str]  = None
    quantidade_diaria:  Optional[str]  = None
    base_calculo:       Optional[str]  = None
    valor_fixado:       Optional[str]  = None
    integracao_salarial: Optional[bool] = None
    reflexos:           Optional[List[str]] = Field(default_factory=list)
    observacoes:        Optional[str]  = None


class ContextoJuridico(BaseModel):
    """
    Objeto tipado que trafega pelo pipeline de regras.

    Cada regra recebe este contexto, pode modificá-lo e deve devolvê-lo.
    Pydantic garante que nenhuma regra escreva uma chave inválida.
    """
    # ── Dados do processo ─────────────────────────────────────────────────────
    numero_processo:    Optional[str]  = None
    reclamante:         Optional[str]  = None
    reclamada:          Optional[str]  = None
    motivo_rescisao:    Optional[str]  = None
    tipo_contrato:      Optional[str]  = None

    # ── Datas ─────────────────────────────────────────────────────────────────
    data_admissao:      Optional[str]  = None
    data_demissao:      Optional[str]  = None
    data_saida_ctps:    Optional[str]  = None
    data_ajuizamento:   Optional[str]  = None
    data_sentenca:      Optional[str]  = None

    # ── Parâmetros financeiros ────────────────────────────────────────────────
    salario_base:       Optional[str]  = None
    jornada_contratual: Optional[str]  = None
    aviso_previo_dias:  Optional[str]  = None

    # ── Parâmetros de cálculo ─────────────────────────────────────────────────
    indice_correcao:    Optional[str]  = None
    juros_mora:         Optional[str]  = None

    # ── FGTS ─────────────────────────────────────────────────────────────────
    fgts_sobre_aviso_previo:       Optional[str] = None
    fgts_multa_40_aviso_previo:    Optional[str] = None
    fgts_sobre_ferias_indenizadas: Optional[str] = None
    fgts_periodo_completo:         Optional[str] = None
    fgts_observacoes:              Optional[str] = None

    # ── Encargos, honorários e proteção financeira ────────────────────────────
    percentual_honorarios:  Optional[str]  = None
    honorarios_sucumbenciais: Optional[str] = None
    justica_gratuita:       bool           = False

    # Dedução/compensação de valores já pagos (autorização expressa do juiz)
    autorizada_deducao:     bool           = False
    observacoes_deducao:    Optional[str]  = None

    # ── Verbas deferidas ──────────────────────────────────────────────────────
    verbas_deferidas:   List[VerbaContexto] = Field(default_factory=list)

    # ── Campos de saída (preenchidos pelas regras) ────────────────────────────
    alertas:            List[dict]     = Field(default_factory=list)
    regras_aplicadas:   List[str]      = Field(default_factory=list)

    # ── Campos derivados pela ADC 58 ──────────────────────────────────────────
    correcao_pre_judicial:  Optional[str] = None
    correcao_judicial:      Optional[str] = None
    juros_judicial:         Optional[str] = None

    
        # Impede criação de campos fora do schema — protege contra typos nas regras
       
    model_config = {"extra": "forbid"}


# ── Classe base de regra jurídica ─────────────────────────────────────────────

class LegalRule(ABC):
    """
    Classe abstrata que toda regra jurídica deve herdar.

    Atributos obrigatórios de classe:
      id          — identificador único (ex: "OJ_42_SDI1_TST")
      titulo      — nome curto da regra
      base_legal  — fundamento normativo completo
      prioridade  — ordem de execução (10=STF, 20=TST Súmulas, 30=OJs, 40=CLT, 50=consistência)

    Atributos opcionais:
      vigencia_inicio — data de início da vigência da norma
      vigencia_fim    — data de fim (None = ainda vigente)
      descricao       — texto longo explicativo
    """

    # ── Metadados da regra — obrigatórios em cada subclasse ──────────────────
    id:         str = ""
    titulo:     str = ""
    base_legal: str = ""
    prioridade: int = 50          # default: consistência (mais baixa)
    descricao:  str = ""

    # ── Controle de vigência temporal (Reforma Trabalhista etc.) ─────────────
    vigencia_inicio: date = date(1943, 5, 1)  # CLT original
    vigencia_fim:    Optional[date] = None    # None = ainda vigente

    def is_aplicavel(self, data_referencia: Optional[date] = None) -> bool:
        """
        Retorna True se a regra está vigente na data de referência.
        Usado pelo engine para filtrar regras por data de admissão ou contrato.

        Args:
            data_referencia: normalmente data_admissao ou data_demissao do processo.
                             Se None, verifica apenas se a regra ainda está vigente hoje.
        """
        ref = data_referencia or date.today()
        if ref < self.vigencia_inicio:
            return False
        if self.vigencia_fim and ref > self.vigencia_fim:
            return False
        return True

    @abstractmethod
    def aplicar(self, contexto: ContextoJuridico) -> ContextoJuridico:
        """
        Aplica a regra jurídica ao contexto.

        Deve:
          - Modificar contexto.alertas se encontrar problemas
          - Registrar contexto.regras_aplicadas.append(self.id) quando executar
          - Retornar o contexto sempre (mesmo sem alterações)
          - Nunca lançar exceções — capturar internamente e logar

        Args:
            contexto: ContextoJuridico tipado (Pydantic)

        Returns:
            ContextoJuridico modificado
        """
        raise NotImplementedError

    # ── Helpers disponíveis para todas as subclasses ──────────────────────────

    def _alerta(
        self,
        contexto: ContextoJuridico,
        mensagem: str,
        nivel: str = "AVISO",
    ) -> None:
        """Adiciona alerta ao contexto e registra no log."""
        contexto.alertas.append({
            "nivel":      nivel,
            "mensagem":   mensagem,
            "regra_id":   self.id,
            "base_legal": self.base_legal,
        })
        print(f"[{nivel}] [{self.id}] {mensagem}")

    def _registrar(self, contexto: ContextoJuridico) -> None:
        """Registra esta regra como aplicada (audit trail)."""
        if self.id not in contexto.regras_aplicadas:
            contexto.regras_aplicadas.append(self.id)

    @staticmethod
    def _canonizar_verba(nome: str) -> str:
        """
        Normaliza o nome de uma verba para comparação.
        Centralizado aqui para evitar duplicação entre regras.
        """
        import re
        mapa = {
            r"horas?\s*extras?":                "Horas Extras",
            r"adicional\s*noturno":             "Adicional Noturno",
            r"adicional\s*de\s*insalubridade":  "Adicional de Insalubridade",
            r"adicional\s*de\s*periculosidade": "Adicional de Periculosidade",
            r"dsr|descanso\s*semanal":          "DSR",
            r"f\.?g\.?t\.?s":                  "FGTS",
            r"f[eé]rias":                       "Férias",
            r"13[°º]?\s*sal[aá]rio|gratifica":  "13º Salário",
            r"aviso\s*pr[eé]vio":               "Aviso Prévio",
            r"saldo\s*de\s*sal[aá]rio":         "Saldo de Salário",
            r"intervalo\s*intrajornada":        "Intervalo Intrajornada",
            r"dano\s*moral":                    "Dano Moral",
            r"dano\s*material":                 "Dano Material",
            r"multa\s*(?:do\s*)?art\.?\s*477":  "Multa Art. 477 CLT",
            r"multa\s*(?:do\s*)?art\.?\s*467":  "Multa Art. 467 CLT",
        }
        n = nome.lower().strip()
        for pattern, canonico in mapa.items():
            if re.search(pattern, n, re.IGNORECASE):
                return canonico
        return nome.strip()