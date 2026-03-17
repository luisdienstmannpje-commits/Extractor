from services.legal_engine.rule_base import LegalRule, ContextoJuridico

_PROIBIDOS = {
    "DSR": ["Férias", "13º Salário", "FGTS"],
    "Multa Art. 467 CLT": ["DSR", "Férias", "13º Salário", "FGTS", "Aviso Prévio"],
    "Multa Art. 477 CLT": ["DSR", "Férias", "13º Salário", "FGTS", "Aviso Prévio"],
    "Dano Moral": ["DSR", "Férias", "13º Salário", "FGTS", "Aviso Prévio"],
    "Dano Material": ["DSR", "Férias", "13º Salário", "FGTS", "Aviso Prévio"],
    "Aviso Prévio": ["Aviso Prévio"],
}


class ReflexosProibidosRule(LegalRule):
    id='OJ_394_SDI1_TST_REFLEXOS_PROIBIDOS'
    titulo='Reflexos Proibidos entre Verbas'
    base_legal='OJ 394 SDI-I TST; vedacao legal'
    prioridade=30
    def aplicar(self, ctx: ContextoJuridico) -> ContextoJuridico:
        try:
            for v in ctx.verbas_deferidas:
                nome_canonico = self._canonizar_verba(v.nome or "")
                for r in (v.reflexos or []):
                    reflexo_canonico = self._canonizar_verba(r)
                    if reflexo_canonico in _PROIBIDOS.get(nome_canonico, []):
                        base = "OJ 394 SDI-I TST" if nome_canonico == "DSR" else "vedacao legal"
                        self._alerta(
                            ctx,
                            f"{base}: '{nome_canonico}' NAO pode refletir em '{reflexo_canonico}'.",
                            nivel="ERRO",
                        )
            self._registrar(ctx)
        except Exception as e:
            self._alerta(ctx, f"Erro {self.id}: {e}", nivel='ERRO')
        return ctx
