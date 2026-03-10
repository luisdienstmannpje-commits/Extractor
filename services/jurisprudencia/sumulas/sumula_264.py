import re
from services.legal_engine.rule_base import LegalRule, ContextoJuridico

class Sumula264DSRReflexoHE(LegalRule):
    id = "SUMULA_264_TST"
    titulo = "Sumula 264 TST"
    base_legal = "Sumula 264 TST"
    prioridade = 20
    _RE_HE = re.compile(r"horas?\s*extras?", re.IGNORECASE)
    _RE_DSR = re.compile(r"dsr|descanso\s*semanal", re.IGNORECASE)
    def aplicar(self, contexto):
        for verba in contexto.verbas_deferidas:
            nome = verba.nome or ""
            if not self._RE_HE.search(nome): continue
            if verba.integracao_salarial is False: continue
            reflexos = verba.reflexos or []
            if not any(self._RE_DSR.search(r) for r in reflexos):
                self._alerta(contexto, f"Sumula 264 TST: '{nome}' sem DSR nos reflexos.", nivel="AVISO")
        self._registrar(contexto)
        return contexto
