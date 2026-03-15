"""
art_477a.py — Art. 477-A CLT — Dispensas Coletivas sem homologação sindical

Fundamento: Lei 13.467/2017 — inseriu o art. 477-A na CLT
Vigência:   A partir de 11/11/2017

Lógica:
  - Regra aplicável a contratos ADMITIDOS a partir de 11/11/2017 (data_admissao)
  - Varre campos textuais em busca de linguagem que trate homologação sindical
    como REQUISITO de validade da rescisão
  - Homologação voluntária (já realizada, sem exigência) NÃO dispara alerta
  - Detecta: "obrigatória", "exigida", "condicionada", "depende de", "falta de"
"""

from __future__ import annotations

import re
from datetime import date
from typing import Optional

from services.legal_engine.rule_base import LegalRule, ContextoJuridico


# Padrões que indicam EXIGÊNCIA de homologação como requisito de validade
_PADROES_EXIGENCIA = re.compile(
    r"homologa[çc][aã]o\s+sindical\s+(é\s+|e\s+)?obrigat[oó]ria"
    r"|homologa[çc][ãa]o\s+sindical\s+exigida"
    r"|rescis[aã]o\s+condicionada\s+a\s+homologa[çc][aã]o"
    r"|validade\s+da\s+rescis[aã]o\s+depende\s+de\s+homologa[çc][aã]o"
    r"|nulidade\s+(da\s+rescis[aã]o\s+)?por\s+falta\s+de\s+homologa[çc][aã]o"
    r"|homologa[çc][aã]o\s+sindical\s+(é\s+|e\s+)?necess[aá]ria",
    re.IGNORECASE,
)

# Campos do contexto a varrer (em ordem de relevância)
_CAMPOS_BUSCA = (
    "motivo_rescisao",
    "anotacao_ctps",
    "fgts_observacoes",
)


class Art477AHomologacao(LegalRule):
    """
    Detecta linguagem que exige homologação sindical como requisito de validade
    da rescisão — prática abolida pelo art. 477-A CLT (Reforma Trabalhista).

    O art. 477-A dispensa expressamente a assistência do sindicato ou homologação
    perante autoridade para qualquer modalidade de dispensa, individual ou coletiva.
    Sentenças que impõem tal requisito contradizem a norma vigente pós-reforma.
    """

    id          = "ART_477A_HOMOLOGACAO"
    titulo      = "Dispensa de Homologação Sindical — Art. 477-A CLT"
    base_legal  = "Art. 477-A CLT, inserido pela Lei 13.467/2017"
    prioridade  = 40   # CLT
    descricao   = (
        "O art. 477-A da CLT, inserido pela Reforma Trabalhista (Lei 13.467/2017), "
        "dispensa expressamente a assistência sindical ou homologação perante autoridade "
        "para rescisões individuais e coletivas de contratos admitidos a partir de "
        "11/11/2017. Qualquer exigência de homologação como condição de validade "
        "contraria a norma vigente."
    )

    data_ref_campo  = "data_admissao"
    vigencia_inicio = date(2017, 11, 11)

    # Campos extras que o contexto pode ter mas não estão no schema Pydantic padrão
    # art_477a precisa também checar anotacao_ctps — tratado via getattr com default None
    _CAMPOS_EXTRAS = ("anotacao_ctps",)

    def is_aplicavel(self, data_referencia: Optional[date] = None) -> bool:
        if data_referencia is None:
            return True
        return data_referencia >= self.vigencia_inicio

    def aplicar(self, contexto: ContextoJuridico) -> ContextoJuridico:
        self._registrar(contexto)

        # Reúne todos os campos textuais relevantes em uma única string de busca
        textos = []
        for campo in _CAMPOS_BUSCA:
            valor = getattr(contexto, campo, None)
            if valor:
                textos.append(str(valor))

        for texto in textos:
            if _PADROES_EXIGENCIA.search(texto):
                self._alerta(
                    contexto,
                    mensagem=(
                        "Sentença contém linguagem que trata homologação sindical como "
                        "requisito de validade da rescisão. O art. 477-A CLT (Reforma "
                        "Trabalhista, Lei 13.467/2017) dispensou expressamente essa "
                        "exigência para contratos pós-reforma. Verificar fundamento legal."
                    ),
                    nivel="AVISO",
                )
                break   # um alerta por contexto é suficiente

        return contexto