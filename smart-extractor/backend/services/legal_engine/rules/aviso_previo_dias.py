from services.legal_engine.rule_base import LegalRule, ContextoJuridico


class AvisoPrevioDiasRule(LegalRule):
    """
    Consistência: dias de aviso prévio dentro dos limites legais.

    Equivalente à checagem `_check_aviso_previo` do validador legado.
    """

    id = "CONSISTENCIA_AVISO_PREVIO_DIAS"
    titulo = "Dias de aviso prévio"
    base_legal = (
        "Art. 487 CLT (mínimo 30 dias) e Lei 12.506/2011 (máximo 90 dias)."
    )
    prioridade = 50
    descricao = (
        "Gera avisos quando o número de dias de aviso prévio está abaixo de 30 "
        "ou acima de 90, sugerindo revisão do cálculo ou da extração."
    )

    def aplicar(self, contexto: ContextoJuridico) -> ContextoJuridico:
        try:
            aviso_str = contexto.aviso_previo_dias or ""
            if not aviso_str:
                self._registrar(contexto)
                return contexto

            import re

            m = re.search(r"(\d+)\s*dias?", aviso_str, re.IGNORECASE)
            if not m:
                self._registrar(contexto)
                return contexto

            dias = int(m.group(1))

            if dias < 30:
                self._alerta(
                    contexto,
                    (
                        f"Aviso prévio de {dias} dias abaixo do mínimo de 30 dias "
                        "(art. 487 CLT). Verificar se é parcial ou erro de extração."
                    ),
                    nivel="AVISO",
                )
            elif dias > 90:
                self._alerta(
                    contexto,
                    (
                        f"Aviso prévio de {dias} dias excede 90 dias máximos "
                        "(Lei 12.506/2011). Verificar cálculo de proporcionalidade."
                    ),
                    nivel="AVISO",
                )

            self._registrar(contexto)
        except Exception as e:
            self._alerta(
                contexto,
                f"Erro ao aplicar regra de aviso prévio (dias): {e}",
                nivel="ERRO",
            )
        return contexto

