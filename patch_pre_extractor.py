"""
Patch cirúrgico para pre_extractor.py — integra validação CNJ em _extract_numero_processo
Aplica em: services/pre_extractor.py
"""

import os

PATH = "services/pre_extractor.py"

OLD = '''    def _extract_numero_processo(self):
        """Número CNJ — altíssima precisão via regex rígido."""
        # Prioridade: cabeçalho explícito
        m = _RE_PROCESSO_CABECALHO.search(self.texto)
        if m:
            self._set_high("numero_processo", m.group(1))
            return
        # Fallback: primeira ocorrência de padrão CNJ no texto
        m = _RE_CNJ.search(self.texto)
        if m:
            self._set_high("numero_processo", m.group(1))'''

NEW = '''    def _extract_numero_processo(self):
        """Número CNJ — altíssima precisão via regex rígido + validação de dígito."""
        from services.legal_engine.jurisprudencia.numero_cnj_validator import validar_cnj

        candidato = None

        # Prioridade: cabeçalho explícito
        m = _RE_PROCESSO_CABECALHO.search(self.texto)
        if m:
            candidato = m.group(1)

        # Fallback: primeira ocorrência de padrão CNJ no texto
        if not candidato:
            m = _RE_CNJ.search(self.texto)
            if m:
                candidato = m.group(1)

        if not candidato:
            return

        # Valida dígito verificador antes de promover para HIGH
        valido, motivo = validar_cnj(candidato)
        if valido:
            self._set_high("numero_processo", candidato)
        else:
            # Dígito inválido: desce para MEDIUM (IA pode corrigir)
            # e emite aviso no log para rastreabilidade
            print(f"[PRE-EXTRACT] numero_processo MEDIUM (dígito inválido): {motivo}")
            self._set_medium("numero_processo", candidato)'''

content = open(PATH, encoding="utf-8").read()

if OLD not in content:
    print("ERRO: trecho de referência não encontrado — verifique o arquivo")
elif NEW in content:
    print("Patch já aplicado (skipped)")
else:
    open(PATH, "w", encoding="utf-8").write(content.replace(OLD, NEW, 1))
    print("✓ Patch aplicado em", PATH)