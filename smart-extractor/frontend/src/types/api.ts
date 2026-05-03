export interface ItemComparativo {
  verba_alvo: string;
  resumo_pedido: string;
  resumo_defesa: string;
  resumo_decisao: string;
  status_final: string;
}

export interface TeseDefesa {
  verba_alvo: string;
  tese_principal: string;
  trecho_fundamentacao?: string | null;
  pagina_origem?: number | null;
  incontroversa: boolean;
}

export interface Verba {
  nome: string;
  status_final: string;
  periodo?: string | null;
  percentual?: string | null;
  quantidade_diaria?: string | null;
  base_calculo?: string | null;
  valor_fixado?: string | null;
  integracao_salarial?: boolean | null;
  reflexos: string[];
  observacoes?: string | null;
  /** Trecho literal do dispositivo/fundamento (rastreabilidade). */
  trecho_fundamentacao?: string | null;
  /** Página 1-based no PDF de origem (quando disponível). */
  pagina_origem?: number | null;
}

export interface FonteExtracao {
  campo: string;
  valor_resumo: string;
  pagina_origem?: number | null;
  trecho?: string | null;
  origem: "ia" | "regex" | "regra" | "derivado" | string;
  confianca?: number | null;
}

export interface ProcessoTrabalhista {
  // Identificação
  numero_processo?: string | null;
  vara_trabalho?: string | null;
  reclamante?: string | null;
  reclamada?: string | null;
  tipo_rito?: string | null;
  funcao_reclamante?: string | null;
  advogado_reclamante?: string | null;
  advogado_reclamada?: string | null;
  juiz_responsavel?: string | null;
  valor_causa?: string | null;

  // Datas
  data_sentenca?: string | null;
  data_ajuizamento?: string | null;
  data_admissao?: string | null;
  data_demissao?: string | null;
  motivo_rescisao?: string | null;
  tipo_contrato?: string | null;

  // Parâmetros financeiros
  salario_base?: string | null;
  jornada_contratual?: string | null;
  horario_trabalho?: string | null;
  aviso_previo_dias?: string | null;
  data_saida_ctps?: string | null;
  anotacao_ctps?: string | null;
  seguro_desemprego?: string | null;

  // Cálculo
  indice_correcao?: string | null;
  juros_mora?: string | null;

  // Encargos
  contribuicao_previdenciaria?: string | null;
  ir_retido_fonte?: string | null;

  // Honorários e custas
  honorarios_sucumbenciais?: string | null;
  percentual_honorarios?: string | null;
  justica_gratuita: boolean;
  custas_processuais?: string | null;

  // Indenizações
  dano_moral?: string | null;
  dano_material?: string | null;

  // Multas
  multa_art_467?: string | null;
  multa_art_477?: string | null;

  // FGTS
  fgts_sobre_aviso_previo?: string | null;
  fgts_multa_40_aviso_previo?: string | null;
  fgts_sobre_ferias_indenizadas?: string | null;
  fgts_periodo_completo?: string | null;
  fgts_observacoes?: string | null;

  // Verbas deferidas
  verbas_deferidas: Verba[];

  /** Fluxo contestação (cache_context=contestacao). */
  teses_defesa?: TeseDefesa[] | null;

  /** Dossiê multi-peça: cruzamento pedido × defesa × decisão. */
  quadro_comparativo?: ItemComparativo[] | null;

  /** Definido pelo backend no fluxo de petição inicial (export Excel / UI). */
  _meta_doc_type?: string | null;

  // Derivados
  prescricao_quinquenal?: string | null;
  divisor_horas?: string | null;
  evolucao_salarial?: string | null;

  // Alertas
  alertas_juridicos: string[];

  /** Regras dinâmicas KB em modo shadow (observação; não são alertas de UI). */
  shadow_logs?: Record<string, unknown>[] | null;
  fontes_extracao?: FonteExtracao[] | null;
}

export type AlertaJuridico = string;

