"""
Consistência: em dispensa sem justa causa, aviso prévio deve constar.

Equivalente à checagem _check_aviso_previo_sem_justa_causa do validador legado.
"""

from services.legal_engine.rule_base import LegalRule, ContextoJuridico


class AvisoPrevioSemJustaCausaRule(LegalRule):
    id = "CONSISTENCIA_AVISO_PREVIO_SEM_JUSTA_CAUSA"
    titulo = "Aviso prévio em dispensa sem justa causa"
    base_legal = (
        "Consistência — dispensa sem justa causa exige previsão de aviso prévio "
        "(campo ou verba deferida)."
    )
    prioridade = 50
    descricao = (
        "Gera aviso quando motivo_rescisao indica 'sem justa causa' mas não há "
        "aviso_previo_dias nem verba de aviso nas verbas_deferidas."
    )

    def aplicar(self, contexto: ContextoJuridico) -> ContextoJuridico:
        try:
            rescisao = (contexto.motivo_rescisao or "").lower()
            if "sem justa causa" not in rescisao:
                self._registrar(contexto)
                return contexto

            aviso_campo = contexto.aviso_previo_dias
            verbas_nomes = [
                self._canonizar_verba(v.nome or "").lower()
                for v in (contexto.verbas_deferidas or [])
            ]
            tem_aviso = bool(aviso_campo and str(aviso_campo).strip()) or any(
                "aviso" in n for n in verbas_nomes
            )
            if not tem_aviso:
                self._alerta(
                    contexto,
                    (
                        "Demissão sem justa causa mas aviso prévio não encontrado nas verbas "
                        "nem no campo aviso_previo_dias. Verificar se foi deferido."
                    ),
                    nivel="AVISO",
                )
            self._registrar(contexto)
        except Exception as e:
            self._alerta(
                contexto,
                f"Erro ao aplicar regra aviso prévio sem justa causa: {e}",
                nivel="ERRO",
            )
        return contexto
