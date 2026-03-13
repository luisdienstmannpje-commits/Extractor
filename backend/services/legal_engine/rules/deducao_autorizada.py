"""
deducao_autorizada.py — Proteção financeira: alerta quando há dedução/compensação autorizada

Quando a sentença autoriza a dedução/compensação de valores já pagos a idêntico título,
o modelo marca `autorizada_deducao = True` e preenche `observacoes_deducao`. Esta regra
gera um INFO no motor de regras lembrando o perito a importar recibos e ativar a dedução
nas verbas correspondentes no PJe-Calc.
"""
from __future__ import annotations

from services.legal_engine.rule_base import ContextoJuridico, LegalRule


class DeducaoAutorizadaRule(LegalRule):
    """
    Consistência/Proteção financeira: alerta sobre dedução/compensação autorizada.
    """

    id = "CONSISTENCIA_DEDUCAO_AUTORIZADA"
    titulo = "Dedução/compensação autorizada pelo juiz"
    base_legal = (
        "Princípio do não enriquecimento sem causa — dedução/compensação de valores já pagos "
        "quando expressamente autorizada na sentença."
    )
    prioridade = 50
    descricao = (
        "Gera alerta informativo quando o campo autorizada_deducao estiver verdadeiro, "
        "lembrando o perito a importar os recibos salariais no PJe-Calc e ativar a dedução "
        "nas verbas correspondentes."
    )

    def aplicar(self, contexto: ContextoJuridico) -> ContextoJuridico:
        try:
            if getattr(contexto, "autorizada_deducao", False):
                obs = (contexto.observacoes_deducao or "").strip()
                mensagem = (
                    "O juiz autorizou a dedução/compensação de valores já pagos a idêntico título. "
                    "Lembre-se de importar os recibos salariais no PJe-Calc e ativar a dedução nas "
                    "verbas correspondentes."
                )
                if obs:
                    mensagem += f" Trecho da sentença: {obs}"
                self._alerta(
                    contexto,
                    mensagem,
                    nivel="INFO",
                )
            self._registrar(contexto)
        except Exception as e:
            self._alerta(
                contexto,
                f"Erro ao aplicar regra de dedução autorizada: {e}",
                nivel="AVISO",
            )
        return contexto

