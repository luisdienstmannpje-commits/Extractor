from pydantic import BaseModel, Field, field_validator
from typing import List, Optional

# ── Versão do schema — incrementar sempre que campos forem adicionados/removidos ──
# database.py usa esta constante para invalidar entradas de cache com schema antigo.
# Histórico: 2.3 (base), 2.4 (fgts_observacoes no ContextoJuridico + schema_version),
#            2.5 (campos de dedução/autorização financeira)
SCHEMA_VERSION = "2.5"


class VerbaDeferida(BaseModel):
    nome: str = Field(..., description="Nome da verba (ex: Horas Extras, Adicional Noturno)")
    status_final: Optional[str] = Field("não informado", description="Status considerando a reforma (ex: mantida, reformada, excluída, acrescida)")
    periodo: Optional[str] = Field(None, description="Período de apuração (ex: 01/01/2020 a 10/10/2021)")
    percentual: Optional[str] = Field(None, description="Percentual aplicável (ex: 50%, 100%)")
    quantidade_diaria: Optional[str] = Field(None, description="Quantidade diária da verba (ex: '2h extras por dia', '30 min intervalo suprimido')")
    base_calculo: Optional[str] = Field(None, description="Base de cálculo descrita (ex: salário base + adicionais)")
    valor_fixado: Optional[str] = Field(None, description="Valor monetário fixado diretamente pelo juiz (ex: R$ 5.000,00) — usado quando não há percentual")
    integracao_salarial: Optional[bool] = Field(None, description="Se a verba integra o salário para fins de reflexos")
    reflexos: List[str] = Field(default_factory=list, description="Lista de reflexos deferidos (ex: ['13º', 'Férias', 'FGTS', 'DSR'])")
    observacoes: Optional[str] = Field(None, description="Detalhes específicos ou limitações da condenação")


class ProcessoTrabalhista(BaseModel):
    # ── Identificação ──────────────────────────────────────────────────────────
    numero_processo: Optional[str] = Field(None, description="Número do processo no formato CNJ")
    vara_trabalho: Optional[str] = Field(None, description="Vara de origem")
    reclamante: Optional[str] = Field(None, description="Nome do autor da ação")
    reclamada: Optional[str] = Field(None, description="Nome da empresa ré")
    tipo_rito: Optional[str] = Field(None, description="Rito processual (ex: Ordinário, Sumaríssimo)")
    funcao_reclamante: Optional[str] = Field(None, description="Cargo ou função exercida (ex: Auxiliar de Produção, Motorista)")
    advogado_reclamante: Optional[str] = Field(None, description="Nome do advogado do reclamante")
    advogado_reclamada: Optional[str] = Field(None, description="Nome do advogado da reclamada")
    juiz_responsavel: Optional[str] = Field(None, description="Nome do juiz ou desembargador que assinou a sentença/acórdão")
    valor_causa: Optional[str] = Field(None, description="Valor da causa (ex: R$ 10.000,00)")

    # ── Datas Cruciais ─────────────────────────────────────────────────────────
    data_sentenca: Optional[str] = Field(None, description="Data de prolação da sentença ou acórdão — base para juros e prescrição")
    data_ajuizamento: Optional[str] = Field(None, description="Data de ajuizamento da ação")
    data_admissao: Optional[str] = Field(None, description="Data de admissão")
    data_demissao: Optional[str] = Field(None, description="Data de demissão")
    motivo_rescisao: Optional[str] = Field(None, description="Tipo de rescisão (ex: Sem justa causa, Pedido de demissão, Rescisão indireta)")
    tipo_contrato: Optional[str] = Field(None, description="Natureza jurídica reconhecida (ex: CLT, Pejotização reconhecida, Autônomo)")

    # ── Parâmetros Financeiros ─────────────────────────────────────────────────
    salario_base: Optional[str] = Field(None, description="Último salário ou salário base reconhecido pelo juiz")
    jornada_contratual: Optional[str] = Field(None, description="Jornada contratual padrão (ex: 44h semanais, 8h diárias)")
    horario_trabalho: Optional[str] = Field(None, description="Horário de entrada, saída e intervalo reconhecido (ex: 07h às 17h com 1h de intervalo)")
    aviso_previo_dias: Optional[str] = Field(None, description="Duração total do aviso prévio deferido (ex: '33 dias', '42 dias — 30 + 12 pela Lei 12.506/2011')")
    data_saida_ctps: Optional[str] = Field(None, description="Data de saída a anotar na CTPS com projeção do aviso prévio (OJ 82 SDI-I TST)")
    anotacao_ctps: Optional[str] = Field(None, description="Determinação de anotação da CTPS — prazo e penalidade se mencionados")
    seguro_desemprego: Optional[str] = Field(None, description="Resultado do pedido de seguro-desemprego (guias, indenização substitutiva ou indeferido)")

    # ── Parâmetros de Cálculo ──────────────────────────────────────────────────
    indice_correcao: Optional[str] = Field(None, description="Índice de correção monetária (ex: IPCA-E, SELIC, TR)")
    juros_mora: Optional[str] = Field(None, description="Juros de mora aplicáveis (ex: 1% ao mês, juros legais, SELIC)")

    # ── Encargos Fiscais e Previdenciários ─────────────────────────────────────
    contribuicao_previdenciaria: Optional[str] = Field(None, description="Responsável pelo recolhimento do INSS (ex: Reclamada recolhe cota patronal e desconta do reclamante)")
    ir_retido_fonte: Optional[str] = Field(None, description="Responsável pelo desconto e recolhimento do IR na fonte (ex: Reclamada)")

    # ── Honorários e Custas ────────────────────────────────────────────────────
    honorarios_sucumbenciais: Optional[str] = Field(None, description="Quem paga honorários advocatícios sucumbenciais (ex: Reclamada, Recíproca, Reclamante)")
    percentual_honorarios: Optional[str] = Field(None, description="Percentual de honorários fixado (ex: 5%, 10%, entre 5% e 15%)")
    justica_gratuita: bool = Field(False, description="Se foi deferida justiça gratuita ao reclamante")
    custas_processuais: Optional[str] = Field(None, description="Quem paga as custas e valor (ex: Reclamada, sobre R$ 10.000,00 calculados)")

    # ── Verbas de Natureza Indenizatória (valor fixo) ──────────────────────────
    dano_moral: Optional[str] = Field(None, description="Valor fixado a título de dano moral (ex: R$ 5.000,00) — não integra base de reflexos")
    dano_material: Optional[str] = Field(None, description="Valor fixado a título de dano material ou emergente (ex: R$ 2.000,00)")

    # ── Proteção financeira — deduções/compensações autorizadas ────────────────
    autorizada_deducao: bool = Field(
        False,
        description=(
            "True se o juiz autorizou expressamente dedução/abatimento/compensação de "
            "valores já pagos a idêntico título (evitar enriquecimento sem causa)."
        ),
    )
    observacoes_deducao: Optional[str] = Field(
        None,
        description="Transcrição da cláusula de dedução/compensação determinada na sentença.",
    )

    # ── Multas Rescisórias ─────────────────────────────────────────────────────
    multa_art_467: Optional[str] = Field(None, description="Multa do art. 467 CLT — 50% sobre verbas incontroversas não pagas na rescisão")
    multa_art_477: Optional[str] = Field(None, description="Multa do art. 477 CLT — 1 salário por atraso no pagamento das verbas rescisórias")

    # ── Regras Especiais de FGTS ───────────────────────────────────────────────
    fgts_sobre_aviso_previo: Optional[str] = Field(None, description="Se FGTS incide sobre aviso prévio indenizado (Súm. 305 TST)")
    fgts_multa_40_aviso_previo: Optional[str] = Field(None, description="Se multa de 40% incide sobre aviso prévio — regra padrão: NÃO (Súm. 305/OJ 42 TST)")
    fgts_sobre_ferias_indenizadas: Optional[str] = Field(None, description="Se FGTS incide sobre férias indenizadas — regra padrão: NÃO (OJ 195 SDI-1 TST)")
    fgts_periodo_completo: Optional[str] = Field(None, description="Período total coberto pelo FGTS (ex: 'Todo o período contratual — 01/02/2023 a 17/02/2025')")
    fgts_observacoes: Optional[str] = Field(None, description="Observações adicionais sobre o FGTS (depósitos não realizados, guias pendentes etc.)")

    # ── A Lista de Verbas (o coração do cálculo) ───────────────────────────────
    verbas_deferidas: List[VerbaDeferida] = Field(default_factory=list)

    # ── Campos calculados / derivados (preenchidos pelo pós-processamento) ─────
    prescricao_quinquenal: Optional[str] = Field(
        None,
        description="Data-limite da prescrição quinquenal (ajuizamento - 5 anos). "
                    "Ex: '24/06/2020'. Preenchido automaticamente ou extraído do dispositivo."
    )
    divisor_horas: Optional[str] = Field(
        None,
        description="Divisor para cálculo de horas extras fixado pelo juiz. "
                    "Valores comuns: '150', '180', '200', '220'. "
                    "Crítico para parametrização no PJe-Calc."
    )
    evolucao_salarial: Optional[str] = Field(
        None,
        description="Base salarial para cálculo: 'conforme CTPS', 'salário fixo reconhecido', "
                    "ou descrição do critério adotado pelo juiz."
    )

    # ── Alertas do validador de reflexos (preenchidos pela ValidadorReflexos) ──
    alertas_juridicos: List[str] = Field(
        default_factory=list,
        description="Lista de alertas gerados pelo validador automático de regras trabalhistas. "
                    "Ex: ['OJ 394: DSR não reflete em férias', 'Bis in idem: Horas Extras → Horas Extras']"
    )

    # ── Validadores de normalização ────────────────────────────────────────────

    @field_validator("justica_gratuita", mode="before")
    @classmethod
    def normalizar_justica_gratuita(cls, v):
        """Aceita variações semânticas da IA: 'concedida', 'deferida', 'sim' -> True; 'indeferida', 'não' -> False."""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            low = v.strip().lower()
            if low in ("true", "sim", "yes", "1", "concedida", "concedido", "deferida", "deferido"):
                return True
            if low in ("false", "não", "nao", "no", "0", "indeferida", "indeferido", "negada", "negado"):
                return False
        return v

    @field_validator(
        # Identificação
        "numero_processo", "vara_trabalho", "reclamante", "reclamada",
        "tipo_rito", "funcao_reclamante", "advogado_reclamante", "juiz_responsavel",
        # Datas e contrato
        "data_sentenca", "data_ajuizamento", "data_admissao", "data_demissao",
        "motivo_rescisao", "tipo_contrato",
        # Parâmetros financeiros
        "salario_base", "jornada_contratual", "horario_trabalho",
        "aviso_previo_dias", "data_saida_ctps", "anotacao_ctps", "seguro_desemprego",
        # Cálculo
        "indice_correcao", "juros_mora",
        "contribuicao_previdenciaria", "ir_retido_fonte",
        "honorarios_sucumbenciais", "percentual_honorarios", "custas_processuais",
        # Indenizações
        "dano_moral", "dano_material",
        # Multas
        "multa_art_467", "multa_art_477",
        # FGTS
        "fgts_sobre_aviso_previo", "fgts_multa_40_aviso_previo",
        "fgts_sobre_ferias_indenizadas", "fgts_periodo_completo", "fgts_observacoes",
        # Derivados
        "prescricao_quinquenal", "divisor_horas", "evolucao_salarial",
        mode="before"
    )
    @classmethod
    def normalizar_campo_str(cls, v, info):
        """
        Validador genérico para todos os campos Optional[str].
        Converte booleanos e valores semânticos para string útil ou None.
        Evita ValidationError quando a IA retorna true/false em campo de texto.
        """
        if v is None:
            return None

        # Booleano puro da IA
        if isinstance(v, bool):
            # Campos que têm semântica de deferimento
            campo = info.field_name if info else ""
            campos_deferimento = {
                "multa_art_467", "multa_art_477", "dano_moral", "dano_material",
                "anotacao_ctps", "seguro_desemprego",
            }
            campos_fgts = {
                "fgts_sobre_aviso_previo", "fgts_multa_40_aviso_previo",
                "fgts_sobre_ferias_indenizadas",
            }
            if campo in campos_deferimento:
                return "Deferida — valor a calcular" if v else None
            if campo in campos_fgts:
                return "Sim — incide" if v else "Não incide"
            # Qualquer outro campo string com booleano: converte para texto
            return "Sim" if v else None

        # Número inteiro/float acidental
        if isinstance(v, (int, float)):
            return str(v)

        # String — "não informado" em datas → None (evita quebra de validação; Regex no processor preenche depois)
        if isinstance(v, str):
            campo = info.field_name if info else ""
            if campo in ("data_sentenca", "data_ajuizamento", "data_admissao", "data_demissao"):
                if v.strip().lower() in ("não informado", "nao informado", ""):
                    return None
            # normalizar termos semânticos em campos de multa/indenização
            campos_multa = {"multa_art_467", "multa_art_477"}
            campos_indeniz = {"dano_moral", "dano_material"}

            if campo in campos_multa or campo in campos_indeniz:
                texto = v.strip().lower()
                positivos = {"procedente", "deferida", "deferido", "sim", "true",
                             "acolhida", "acolhido", "condenada", "procedentes"}
                negativos = {"improcedente", "indeferida", "indeferido", "não",
                             "false", "improcedentes", "rejeitada", "rejeitado"}
                if texto in positivos:
                    return "Deferida — valor a calcular (1 salário)" \
                           if campo in campos_multa else "Deferida — valor a calcular"
                if texto in negativos:
                    return None

        return v