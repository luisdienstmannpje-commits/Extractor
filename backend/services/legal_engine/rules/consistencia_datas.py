from services.legal_engine.rule_base import LegalRule, ContextoJuridico


class ConsistenciaDatasRule(LegalRule):
    """
    Consistência temporal das datas principais do processo trabalhista.

    Equivalente à checagem `_check_consistencia_datas` do validador legado.
    """

    id = "CONSISTENCIA_DATAS"
    titulo = "Consistência das datas do processo"
    base_legal = (
        "Consistência cronológica — ordem lógica entre admissão, demissão, "
        "saída em CTPS, ajuizamento e sentença."
    )
    prioridade = 50
    descricao = (
        "Verifica incoerências básicas entre datas (ex.: admissão depois da "
        "demissão, sentença antes da demissão, ajuizamento depois da sentença)."
    )

    def _parse_data(self, data_str: str):
        from datetime import datetime

        if not data_str:
            return None
        for fmt in ("%d/%m/%Y", "%d/%m/%y"):
            try:
                return datetime.strptime(data_str.strip(), fmt).date()
            except ValueError:
                continue
        return None

    def aplicar(self, contexto: ContextoJuridico) -> ContextoJuridico:
        try:
            saida = self._parse_data(contexto.data_saida_ctps or "")
            demis = self._parse_data(contexto.data_demissao or "")
            admis = self._parse_data(contexto.data_admissao or "")
            sentenca = self._parse_data(contexto.data_sentenca or "")
            ajuiz = self._parse_data(contexto.data_ajuizamento or "")

            if saida and demis and saida < demis:
                self._alerta(
                    contexto,
                    (
                        f"Data CTPS ({contexto.data_saida_ctps}) anterior à demissão "
                        f"({contexto.data_demissao}). Verificar projeção do aviso prévio."
                    ),
                    nivel="ERRO",
                )

            if admis and demis and admis > demis:
                self._alerta(
                    contexto,
                    (
                        f"Admissão ({contexto.data_admissao}) posterior à demissão "
                        f"({contexto.data_demissao}). Dados incorretos."
                    ),
                    nivel="ERRO",
                )

            if sentenca and demis and sentenca < demis:
                self._alerta(
                    contexto,
                    (
                        f"Sentença ({contexto.data_sentenca}) anterior à demissão "
                        f"({contexto.data_demissao}). Verificar extração das datas."
                    ),
                    nivel="AVISO",
                )

            if ajuiz and sentenca and ajuiz > sentenca:
                self._alerta(
                    contexto,
                    (
                        f"Ajuizamento ({contexto.data_ajuizamento}) posterior à sentença "
                        f"({contexto.data_sentenca}). Ordem cronológica inválida."
                    ),
                    nivel="ERRO",
                )

            if admis and ajuiz and ajuiz < admis:
                self._alerta(
                    contexto,
                    (
                        f"Ajuizamento ({contexto.data_ajuizamento}) anterior à admissão "
                        f"({contexto.data_admissao}). Verificar datas."
                    ),
                    nivel="AVISO",
                )

            self._registrar(contexto)
        except Exception as e:
            self._alerta(
                contexto,
                f"Erro ao aplicar regra de consistência de datas: {e}",
                nivel="ERRO",
            )
        return contexto

