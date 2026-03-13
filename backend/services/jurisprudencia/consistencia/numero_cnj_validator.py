from __future__ import annotations
import re
from typing import Optional, Tuple
from services.legal_engine.rule_base import ContextoJuridico, LegalRule

_REGEX_CNJ = re.compile(r"^(\d{7})-(\d{2})\.(\d{4})\.(\d)\.(\d{2})\.(\d{4})$")

def extrair_partes_cnj(numero):
    if not numero:
        return None
    m = _REGEX_CNJ.match(numero.strip())
    if not m:
        return None
    return {"nnnnnnn":m.group(1),"dd":m.group(2),"aaaa":m.group(3),"j":m.group(4),"tt":m.group(5),"oooo":m.group(6)}

def _calcular_dd(nnnnnnn, aaaa, j, tt, oooo):
    seq = nnnnnnn+aaaa+j+tt+oooo
    return f"{98 - int(seq) % 97:02d}"

def calcular_numero_cnj(nnnnnnn, aaaa, j, tt, oooo):
    return f"{nnnnnnn}-{_calcular_dd(nnnnnnn,aaaa,j,tt,oooo)}.{aaaa}.{j}.{tt}.{oooo}"

def validar_cnj(numero):
    if not numero: return False, "Numero nao informado."
    partes = extrair_partes_cnj(numero)
    if partes is None: return False, f"Formato inválido: {numero}"
    dd_esp = _calcular_dd(partes["nnnnnnn"],partes["aaaa"],partes["j"],partes["tt"],partes["oooo"])
    if partes["dd"] != dd_esp:
        return False, f"Dígito verificador inválido: informado={partes[chr(100)+chr(100)]}, esperado={dd_esp}."
    return True, ""

class NumeroCNJValidator(LegalRule):
    id="CNJ_DIGITO_VERIFICADOR"; titulo="Validacao CNJ"; base_legal="Resolucao CNJ n 65/2008"; prioridade=50
    def aplicar(self, contexto):
        try:
            numero = contexto.numero_processo
            if not numero:
                self._alerta(contexto,"[INFO] Numero do processo nao encontrado na extracao.",nivel="INFO")
                self._registrar(contexto); return contexto
            ok, motivo = validar_cnj(numero)
            if not ok:
                msg = (
                    f"[AVISO] Dígito verificador CNJ parece atípico: {numero}. "
                    f"{motivo} Apenas confira se o número do processo foi extraído corretamente."
                )
                self._alerta(contexto, msg, nivel="AVISO")
            self._registrar(contexto)
        except Exception as exc:
            self._alerta(contexto,f"[AVISO] Falha interna: {exc}",nivel="AVISO"); self._registrar(contexto)
        return contexto
