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

  // Derivados
  prescricao_quinquenal?: string | null;
  divisor_horas?: string | null;
  evolucao_salarial?: string | null;

  // Alertas
  alertas_juridicos: string[];
}

export type AlertaJuridico = string;

