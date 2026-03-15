import re
from services.legal_engine.rule_base import LegalRule, ContextoJuridico
_MIN = 1518.00
_MAX = 100000.00
def _parse(t):
    if not t: return None
    try: return float(re.sub(r"[R$\s]","",t).replace(".","").replace(",","."))
    except: return None
class ConsistenciaSalario(LegalRule):
    id = "CONSISTENCIA_SALARIO"
    titulo = "Consistencia salario base"
    base_legal = "Art. 7 IV CF/88 - Decreto 12.302/2025"
    prioridade = 50
    def aplicar(self, contexto):
        s = contexto.salario_base
        if not s: self._registrar(contexto); return contexto
        v = _parse(s)
        if v is None:
            self._alerta(contexto, f"Salario '{s}' nao interpretavel.", nivel="AVISO")
        elif v <= 0:
            # Mantém consistência básica de salário positivo; regra de mínimo oficial
            # é tratada em CONSISTENCIA_SALARIO_BASE_MINIMO (LegalRuleEngine).
            self._alerta(contexto, f"Salario invalido: R$ {v:.2f}.", nivel="ERRO")
        elif v > _MAX:
            # Apenas alerta para valores muito altos (possível erro de extração)
            self._alerta(
                contexto,
                f"Salario R$ {v:,.2f} acima de R$ {_MAX:,.0f}. Verificar extracao.",
                nivel="AVISO",
            )
        self._registrar(contexto)
        return contexto
