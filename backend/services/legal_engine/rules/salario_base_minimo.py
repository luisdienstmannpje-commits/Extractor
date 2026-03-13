from services.legal_engine.rule_base import LegalRule, ContextoJuridico


class SalarioBaseMinimoRule(LegalRule):
    """
    Consistência: salário base deve ser > 0 e não inferior ao mínimo vigente.

    Equivalente à checagem `_check_salario_base` do validador legado.
    """

    id = "CONSISTENCIA_SALARIO_BASE_MINIMO"
    titulo = "Salário base mínimo"
    base_legal = (
        "Consistência de dados — salário base positivo e compatível com o "
        "salário mínimo vigente."
    )
    prioridade = 50
    descricao = (
        "Gera erro se salário base é inválido (<= 0) e aviso se está abaixo "
        "do salário mínimo configurado no sistema."
    )

    # Mantém o mesmo valor do validador legado (atualizar junto ao decreto anual)
    _SALARIO_MINIMO = 1_518.00

    def aplicar(self, contexto: ContextoJuridico) -> ContextoJuridico:
        try:
            salario_str = contexto.salario_base or ""
            if not salario_str:
                self._registrar(contexto)
                return contexto

            import re

            m = re.search(r"-?[\d.]+,\d{2}", salario_str)
            if not m:
                self._registrar(contexto)
                return contexto

            try:
                valor = float(m.group().replace(".", "").replace(",", "."))
            except ValueError:
                self._registrar(contexto)
                return contexto

            if valor <= 0:
                self._alerta(
                    contexto,
                    f"Salário base inválido: '{salario_str}'.",
                    nivel="ERRO",
                )
            elif valor < self._SALARIO_MINIMO:
                self._alerta(
                    contexto,
                    (
                        f"Salário R$ {valor:.2f} abaixo do mínimo vigente "
                        f"(R$ {self._SALARIO_MINIMO:,.2f}). "
                        "Verificar se é categoria especial ou contrato parcial."
                    ),
                    nivel="AVISO",
                )

            self._registrar(contexto)
        except Exception as e:
            self._alerta(
                contexto,
                f"Erro ao aplicar regra de salário base mínimo: {e}",
                nivel="ERRO",
            )
        return contexto

