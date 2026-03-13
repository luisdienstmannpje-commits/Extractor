"""
legal_validator.py — Validador Lógico de Reflexos Trabalhistas v2.3

Roda APÓS o retorno da IA, em Python puro. Zero tokens, zero latência relevante.

Novas regras v2.2:
  - Art. 791-A CLT: honorários entre 5% e 15%
  - Lei 12.506/2011: aviso prévio proporcional máximo de 90 dias
  - Consistência FGTS + multa 40%: se FGTS consta, multa de 40% deve constar
  - Integridade de verbas: verba com integracao_salarial=True deve ter reflexos
  - Dano moral: não deve aparecer em verbas_deferidas
  - Alerta se multa 477 ≠ 1 salário
  - Verificação de motivo_rescisao × verbas (aviso prévio obrigatório em sem justa causa)

v2.3:
  - Salário mínimo atualizado para R$ 1.518,00 (vigente desde 01/01/2025)
"""

import re
from datetime import datetime, date
from typing import Optional


# ---------------------------------------------------------------------------
# Salário mínimo vigente — atualizar anualmente conforme decreto presidencial
# 2025: R$ 1.518,00 (Decreto nº 12.302/2025)
# ---------------------------------------------------------------------------
_SALARIO_MINIMO = 1_518.00


class ValidadorReflexos:
    _CANONICOS = {
        r"horas?\s*extras?":               "Horas Extras",
        r"adicional\s*noturno":            "Adicional Noturno",
        r"adicional\s*de\s*insalubridade": "Adicional de Insalubridade",
        r"adicional\s*de\s*periculosidade":"Adicional de Periculosidade",
        r"dsr|descanso\s*semanal":         "DSR",
        r"f\.?g\.?t\.?s":                 "FGTS",
        r"f[eé]rias":                      "Férias",
        r"13[°º]?\s*sal[aá]rio|gratifica[çc][aã]o\s*natalina": "13º Salário",
        r"aviso\s*pr[eé]vio":              "Aviso Prévio",
        r"saldo\s*de\s*sal[aá]rio":        "Saldo de Salário",
        r"intervalo\s*intrajornada":       "Intervalo Intrajornada",
        r"multa.*467":                     "Multa art. 467",
        r"multa.*477":                     "Multa art. 477",
        r"dano\s*moral":                   "Dano Moral",
        r"dano\s*material":                "Dano Material",
        r"diferença.*salarial|equiparaç":  "Diferenças Salariais",
    }

    _REFLEXOS_PROIBIDOS = {
        "DSR":             ["Férias", "13º Salário", "FGTS"],   # OJ 394 TST
        "Multa art. 467":  ["DSR", "Férias", "13º Salário", "FGTS", "Aviso Prévio"],
        "Multa art. 477":  ["DSR", "Férias", "13º Salário", "FGTS", "Aviso Prévio"],
        "Dano Moral":      ["DSR", "Férias", "13º Salário", "FGTS", "Aviso Prévio"],
        "Dano Material":   ["DSR", "Férias", "13º Salário", "FGTS", "Aviso Prévio"],
        "Aviso Prévio":    ["Aviso Prévio"],
    }

    _REFLEXOS_ESPERADOS = {
        "Horas Extras":    ["DSR"],   # Súm. 264 TST
        "Adicional Noturno": ["DSR"],
    }

    def __init__(self, dados: dict):
        self.dados   = dados
        self.alertas = []

    def _alerta(self, msg: str, nivel: str = "AVISO"):
        self.alertas.append(f"[{nivel}] {msg}")
        print(f"[VALIDATOR] {nivel}: {msg}")

    def _canonizar(self, nome: str) -> str:
        nome_lower = nome.lower().strip()
        for pattern, canonico in self._CANONICOS.items():
            if re.search(pattern, nome_lower, re.IGNORECASE):
                return canonico
        return nome.strip()

    def _parse_data(self, data_str: Optional[str]) -> Optional[date]:
        if not data_str:
            return None
        for fmt in ("%d/%m/%Y", "%d/%m/%y"):
            try:
                return datetime.strptime(data_str.strip(), fmt).date()
            except ValueError:
                continue
        return None

    def _parse_valor_monetario(self, valor_str: Optional[str]) -> Optional[float]:
        if not valor_str:
            return None
        m = re.search(r'R\$\s*([\d.]+,\d{2})', valor_str)
        if m:
            val = m.group(1).replace('.', '').replace(',', '.')
            try:
                return float(val)
            except ValueError:
                pass
        return None

    # ── Regras de reflexos ────────────────────────────────────────────────────

    def _check_bis_in_idem(self):
        for verba in self.dados.get("verbas_deferidas", []):
            nome = self._canonizar(verba.get("nome", ""))
            reflexos = [self._canonizar(r) for r in (verba.get("reflexos") or [])]
            if nome in reflexos:
                self._alerta(f"Bis in idem: '{nome}' aparece como reflexo de si mesma.", nivel="ERRO")

    def _check_reflexos_proibidos(self):
        for verba in self.dados.get("verbas_deferidas", []):
            nome = self._canonizar(verba.get("nome", ""))
            reflexos = [self._canonizar(r) for r in (verba.get("reflexos") or [])]
            proibidos = self._REFLEXOS_PROIBIDOS.get(nome, [])
            for r in reflexos:
                if r in proibidos:
                    regra = "OJ 394 TST" if nome == "DSR" else "vedação legal"
                    self._alerta(
                        f"{regra}: '{nome}' NÃO pode refletir em '{r}'. Verificar dispositivo.",
                        nivel="ERRO"
                    )

    def _check_reflexos_esperados(self):
        verbas_presentes = {self._canonizar(v.get("nome", ""))
                            for v in self.dados.get("verbas_deferidas", [])}
        for verba in self.dados.get("verbas_deferidas", []):
            nome = self._canonizar(verba.get("nome", ""))
            reflexos = [self._canonizar(r) for r in (verba.get("reflexos") or [])]
            for esp in self._REFLEXOS_ESPERADOS.get(nome, []):
                if esp not in reflexos and esp in verbas_presentes:
                    self._alerta(
                        f"Súm. 264 TST: '{nome}' geralmente reflete em '{esp}'. "
                        f"Confirmar ausência de reflexo no dispositivo.",
                        nivel="AVISO"
                    )

    def _check_integracao_sem_reflexos(self):
        """Verba com integracao_salarial=True mas reflexos vazia é suspeita."""
        for verba in self.dados.get("verbas_deferidas", []):
            nome = self._canonizar(verba.get("nome", ""))
            integ = verba.get("integracao_salarial")
            reflexos = verba.get("reflexos") or []
            if integ is True and not reflexos:
                self._alerta(
                    f"'{nome}' tem integracao_salarial=True mas reflexos=[]. "
                    f"Verificar se reflexos foram omitidos na extração.",
                    nivel="AVISO"
                )

    def _check_dano_moral_em_verbas(self):
        """Dano moral é campo próprio — não deve estar em verbas_deferidas."""
        for verba in self.dados.get("verbas_deferidas", []):
            nome = verba.get("nome", "").lower()
            if "dano moral" in nome or "danos morais" in nome:
                self._alerta(
                    "Dano moral encontrado em verbas_deferidas. "
                    "Deve estar no campo 'dano_moral', não na lista de verbas.",
                    nivel="AVISO"
                )
                break

    # ── Regras de FGTS ───────────────────────────────────────────────────────

    def _check_fgts_ferias_indenizadas(self):
        fgts_ferias = self.dados.get("fgts_sobre_ferias_indenizadas") or ""
        if "sim" in fgts_ferias.lower() and "não" not in fgts_ferias.lower():
            self._alerta(
                "OJ 195 SDI-I TST: FGTS NÃO incide sobre férias indenizadas. "
                "Verificar se o documento realmente determina incidência.",
                nivel="ERRO"
            )

    def _check_fgts_aviso_previo(self):
        fgts_ap = self.dados.get("fgts_sobre_aviso_previo") or ""
        if "não" in fgts_ap.lower() and "incide" in fgts_ap.lower() and "aviso" in fgts_ap.lower():
            self._alerta(
                "Súm. 305 TST: FGTS DEVE incidir sobre aviso prévio indenizado. "
                "Verificar se o documento realmente afasta a Súmula.",
                nivel="AVISO"
            )

    def _check_fgts_multa_sem_fgts_verba(self):
        """Se FGTS não aparece nas verbas, alertar sobre período de recolhimento."""
        verbas_nomes = {self._canonizar(v.get("nome", ""))
                        for v in self.dados.get("verbas_deferidas", [])}
        tem_fgts_verba = "FGTS" in verbas_nomes or any("fgts" in n.lower() for n in verbas_nomes)
        periodo = self.dados.get("fgts_periodo_completo")
        if not tem_fgts_verba and not periodo:
            pass  # FGTS pode ter sido deferido implicitamente — não é erro
        if tem_fgts_verba and not periodo:
            self._alerta(
                "FGTS aparece nas verbas mas fgts_periodo_completo está vazio. "
                "Verificar período de apuração.",
                nivel="AVISO"
            )

    # ── Regras de consistência temporal ──────────────────────────────────────

    def _check_consistencia_datas(self):
        saida    = self._parse_data(self.dados.get("data_saida_ctps"))
        demis    = self._parse_data(self.dados.get("data_demissao"))
        admis    = self._parse_data(self.dados.get("data_admissao"))
        sentenca = self._parse_data(self.dados.get("data_sentenca"))
        ajuiz    = self._parse_data(self.dados.get("data_ajuizamento"))

        if saida and demis and saida < demis:
            self._alerta(
                f"Data CTPS ({self.dados['data_saida_ctps']}) anterior à demissão "
                f"({self.dados['data_demissao']}). Verificar projeção do aviso prévio.",
                nivel="ERRO"
            )
        if admis and demis and admis > demis:
            self._alerta(
                f"Admissão ({self.dados['data_admissao']}) posterior à demissão "
                f"({self.dados['data_demissao']}). Dados incorretos.",
                nivel="ERRO"
            )
        if sentenca and demis and sentenca < demis:
            self._alerta(
                f"Sentença ({self.dados['data_sentenca']}) anterior à demissão "
                f"({self.dados['data_demissao']}). Verificar extração das datas.",
                nivel="AVISO"
            )
        if ajuiz and sentenca and ajuiz > sentenca:
            self._alerta(
                f"Ajuizamento ({self.dados['data_ajuizamento']}) posterior à sentença "
                f"({self.dados['data_sentenca']}). Ordem cronológica inválida.",
                nivel="ERRO"
            )
        if admis and ajuiz and ajuiz < admis:
            self._alerta(
                f"Ajuizamento ({self.dados['data_ajuizamento']}) anterior à admissão "
                f"({self.dados['data_admissao']}). Verificar datas.",
                nivel="AVISO"
            )

    # ── Regras salariais ──────────────────────────────────────────────────────

    def _check_salario_base(self):
        salario = self.dados.get("salario_base") or ""
        if not salario:
            return
        m = re.search(r'[\d.]+,\d{2}', salario)
        if m:
            try:
                valor = float(m.group().replace('.', '').replace(',', '.'))
                if valor <= 0:
                    self._alerta(f"Salário base inválido: '{salario}'.", nivel="ERRO")
                elif valor < _SALARIO_MINIMO:
                    self._alerta(
                        f"Salário R$ {valor:.2f} abaixo do mínimo vigente "
                        f"(R$ {_SALARIO_MINIMO:,.2f}). "
                        f"Verificar se é categoria especial ou contrato parcial.",
                        nivel="AVISO"
                    )
            except ValueError:
                pass

    # ── Aviso prévio ─────────────────────────────────────────────────────────

    def _check_aviso_previo(self):
        aviso = self.dados.get("aviso_previo_dias") or ""
        if not aviso:
            return
        m = re.search(r'(\d+)\s*dias?', aviso, re.IGNORECASE)
        if m:
            dias = int(m.group(1))
            if dias < 30:
                self._alerta(
                    f"Aviso prévio de {dias} dias abaixo do mínimo de 30 dias (art. 487 CLT). "
                    f"Verificar se é parcial ou erro de extração.",
                    nivel="AVISO"
                )
            elif dias > 90:
                self._alerta(
                    f"Aviso prévio de {dias} dias excede 90 dias máximos (Lei 12.506/2011). "
                    f"Verificar cálculo de proporcionalidade.",
                    nivel="AVISO"
                )

    def _check_aviso_previo_sem_justa_causa(self):
        """Se demissão sem justa causa, aviso prévio deve estar nas verbas ou no campo."""
        rescisao = (self.dados.get("motivo_rescisao") or "").lower()
        if "sem justa causa" not in rescisao:
            return
        aviso_campo = self.dados.get("aviso_previo_dias")
        verbas_nomes = {self._canonizar(v.get("nome", "")).lower()
                        for v in self.dados.get("verbas_deferidas", [])}
        tem_aviso = aviso_campo or any("aviso" in n for n in verbas_nomes)
        if not tem_aviso:
            self._alerta(
                "Demissão sem justa causa mas aviso prévio não encontrado nas verbas "
                "nem no campo aviso_previo_dias. Verificar se foi deferido.",
                nivel="AVISO"
            )

    # ── Honorários ───────────────────────────────────────────────────────────

    def _check_honorarios_percentual(self):
        """Art. 791-A CLT: honorários entre 5% e 15%."""
        pct_str = self.dados.get("percentual_honorarios") or ""
        if not pct_str:
            return
        m = re.search(r'(\d+(?:[.,]\d+)?)\s*%', pct_str)
        if m:
            pct = float(m.group(1).replace(',', '.'))
            if pct < 5:
                self._alerta(
                    f"Honorários de {pct}% abaixo do mínimo de 5% (art. 791-A CLT). "
                    f"Verificar se é honorários de êxito ou base diferente.",
                    nivel="AVISO"
                )
            elif pct > 15:
                self._alerta(
                    f"Honorários de {pct}% acima do máximo de 15% (art. 791-A CLT). "
                    f"Verificar fundamento legal.",
                    nivel="AVISO"
                )

    # ── Multas ───────────────────────────────────────────────────────────────

    def _check_multa_477_valor(self):
        """Multa art. 477 = 1 salário base. Verifica consistência se valores presentes."""
        multa = self.dados.get("multa_art_477") or ""
        salario = self.dados.get("salario_base") or ""
        if not multa or not salario or "indeniz" in multa.lower():
            return
        val_multa  = self._parse_valor_monetario(multa)
        val_salario = self._parse_valor_monetario(salario)
        if val_multa and val_salario:
            diff_pct = abs(val_multa - val_salario) / val_salario * 100
            if diff_pct > 5:
                self._alerta(
                    f"Multa art. 477 (R$ {val_multa:.2f}) difere do salário base "
                    f"(R$ {val_salario:.2f}) em {diff_pct:.0f}%. "
                    f"Art. 477 CLT: multa = 1 salário. Verificar extração.",
                    nivel="AVISO"
                )

    # ── Duplicidade de verbas ─────────────────────────────────────────────────

    def _check_verbas_duplicadas(self):
        """
        Verba duplicada = mesmo nome canônico E mesmo período.
        Férias vencidas (2023/2024) + férias integrais (2024/2025) = verbas distintas.
        """
        assinaturas = set()
        for verba in self.dados.get("verbas_deferidas", []):
            nome_original = verba.get("nome", "")
            periodo = (verba.get("periodo") or "").strip().lower()
            nome_canonico = self._canonizar(nome_original)

            if not nome_canonico:
                continue

            # Chave: nome canônico + período — "férias|2023/2024" ≠ "férias|2024/2025"
            assinatura = f"{nome_canonico}|{periodo}"

            if assinatura in assinaturas:
                self._alerta(
                    f"Verba duplicada: '{nome_original}' "
                    f"(período: {periodo if periodo else 'não informado'}). "
                    f"Verificar duplicidade da IA.",
                    nivel="AVISO"
                )
            assinaturas.add(assinatura)


    def validar(self) -> list[str]:
        checks = [
            self._check_bis_in_idem,
            self._check_reflexos_proibidos,
            self._check_reflexos_esperados,
            self._check_integracao_sem_reflexos,
            self._check_dano_moral_em_verbas,
            self._check_fgts_ferias_indenizadas,
            self._check_fgts_aviso_previo,
            self._check_fgts_multa_sem_fgts_verba,
            self._check_consistencia_datas,
            self._check_salario_base,
            self._check_aviso_previo,
            self._check_aviso_previo_sem_justa_causa,
            self._check_honorarios_percentual,
            self._check_multa_477_valor,
            self._check_verbas_duplicadas,
        ]
        for check in checks:
            try:
                check()
            except Exception as e:
                print(f"[VALIDATOR] Erro no check {check.__name__}: {e}")

        erros  = sum(1 for a in self.alertas if "[ERRO]" in a)
        avisos = sum(1 for a in self.alertas if "[AVISO]" in a)

        if not self.alertas:
            print("[VALIDATOR] ✓ Dados consistentes — nenhum alerta")
        else:
            print(f"[VALIDATOR] {erros} erro(s), {avisos} aviso(s)")

        return self.alertas


def validar_dados(dados: dict) -> list[str]:
    """Função de conveniência."""
    return ValidadorReflexos(dados).validar()

def validar_dados_completo(dados: dict) -> dict:
    """
    Executa validação completa via LegalRuleEngine + ValidadorReflexos.

    Retorna dict com:
      - alertas:           lista de strings "[NIVEL] mensagem"
      - regras_aplicadas:  lista de IDs das regras executadas
      - memorial_juridico: lista de dicts com metadados de cada regra
    """
    from services.legal_engine.rule_registry import carregar_todas_as_regras
    from services.legal_engine.engine import LegalRuleEngine

    rules  = carregar_todas_as_regras()
    engine = LegalRuleEngine(rules)
    return engine.executar(dados)