from services.legal_engine.rule_base import LegalRule, ContextoJuridico

class Sumula91SalarioComplessivo(LegalRule):
    id = "SUMULA_91_TST"
    titulo = "Sumula 91 TST"
    base_legal = "Sumula 91 TST"
    prioridade = 20
    _TERMOS = ["salario complessivo","remuneracao global","salario global","tudo incluído","ja incluidas todas","engloba todos"]
    def aplicar(self, contexto):
        texto = ((contexto.salario_base or "") + " " + (contexto.jornada_contratual or "")).lower()
        for termo in self._TERMOS:
            if termo in texto:
                self._alerta(contexto, f"Sumula 91 TST: salario complessivo ('{termo}'). Verbas devem ser separadas.", nivel="AVISO")
                break
        self._registrar(contexto)
        return contexto
