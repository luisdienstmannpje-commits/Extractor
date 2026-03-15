"""
Consistência: verbas duplicadas (mesmo nome canônico + mesmo período).

Equivalente à checagem _check_verbas_duplicadas do validador legado.
"""

from services.legal_engine.rule_base import LegalRule, ContextoJuridico


class VerbasDuplicadasRule(LegalRule):
    """
    Verba duplicada = mesmo nome canônico E mesmo período.
    Férias vencidas (2023/2024) + férias integrais (2024/2025) = verbas distintas.
    """

    id = "CONSISTENCIA_VERBAS_DUPLICADAS"
    titulo = "Verbas duplicadas"
    base_legal = (
        "Consistência de dados — mesma verba e mesmo período não deve aparecer duas vezes."
    )
    prioridade = 50
    descricao = (
        "Aviso quando existe mais de uma verba com o mesmo nome canônico e período."
    )

    def aplicar(self, contexto: ContextoJuridico) -> ContextoJuridico:
        try:
            assinaturas = set()
            for verba in contexto.verbas_deferidas or []:
                nome_original = verba.nome or ""
                periodo = (verba.periodo or "").strip().lower()
                nome_canonico = self._canonizar_verba(nome_original)

                if not nome_canonico:
                    continue

                assinatura = f"{nome_canonico}|{periodo}"
                if assinatura in assinaturas:
                    self._alerta(
                        contexto,
                        (
                            f"Verba duplicada: '{nome_original}' "
                            f"(período: {periodo if periodo else 'não informado'}). "
                            "Verificar duplicidade da IA."
                        ),
                        nivel="AVISO",
                    )
                assinaturas.add(assinatura)

            self._registrar(contexto)
        except Exception as e:
            self._alerta(
                contexto,
                f"Erro ao aplicar regra de verbas duplicadas: {e}",
                nivel="ERRO",
            )
        return contexto
