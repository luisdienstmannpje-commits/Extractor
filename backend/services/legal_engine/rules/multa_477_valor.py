"""
Consistência: multa art. 477 CLT = 1 salário base.

Equivalente à checagem _check_multa_477_valor do validador legado.
Usa valor da verba 'Multa art. 477' em verbas_deferidas e salario_base do contexto.
"""

import re
from services.legal_engine.rule_base import LegalRule, ContextoJuridico


def _parse_valor_monetario(valor_str: str | None) -> float | None:
    if not valor_str:
        return None
    m = re.search(r"R\$\s*([\d.]+,\d{2})", valor_str)
    if not m:
        return None
    try:
        return float(m.group(1).replace(".", "").replace(",", "."))
    except ValueError:
        return None


class Multa477ValorRule(LegalRule):
    id = "CONSISTENCIA_MULTA_477_VALOR"
    titulo = "Multa art. 477 — valor equivalente a 1 salário"
    base_legal = "Art. 477 CLT — multa = 1 salário base."
    prioridade = 50
    descricao = (
        "Aviso quando o valor da multa art. 477 difere do salário base em mais de 5%."
    )

    def aplicar(self, contexto: ContextoJuridico) -> ContextoJuridico:
        try:
            salario_str = contexto.salario_base or ""
            val_salario = _parse_valor_monetario(salario_str)
            if not val_salario:
                self._registrar(contexto)
                return contexto

            multa_verba = None
            for v in contexto.verbas_deferidas or []:
                nome = (v.nome or "").lower()
                canon = self._canonizar_verba(v.nome or "")
                if canon == "Multa art. 477" or ("multa" in nome and "477" in nome):
                    multa_verba = v
                    break

            if not multa_verba:
                self._registrar(contexto)
                return contexto

            valor_str = multa_verba.valor_fixado or multa_verba.nome or ""
            if "indeniz" in valor_str.lower():
                self._registrar(contexto)
                return contexto

            val_multa = _parse_valor_monetario(valor_str)
            if not val_multa:
                self._registrar(contexto)
                return contexto

            diff_pct = abs(val_multa - val_salario) / val_salario * 100
            if diff_pct > 5:
                self._alerta(
                    contexto,
                    (
                        f"Multa art. 477 (R$ {val_multa:.2f}) difere do salário base "
                        f"(R$ {val_salario:.2f}) em {diff_pct:.0f}%. "
                        "Art. 477 CLT: multa = 1 salário. Verificar extração."
                    ),
                    nivel="AVISO",
                )
            self._registrar(contexto)
        except Exception as e:
            self._alerta(
                contexto,
                f"Erro ao aplicar regra multa 477 valor: {e}",
                nivel="ERRO",
            )
        return contexto
