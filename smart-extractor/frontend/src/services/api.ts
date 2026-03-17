import axios, { type AxiosInstance } from "axios";
import type { ProcessoTrabalhista } from "../types/api";

// Backend FastAPI roda na porta 8001 (ver run_server.sh)
const API_BASE_URL = "http://localhost:8001";
const DEFAULT_USER_ID = "usuario_teste";

export const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json"
  }
});

api.interceptors.request.use((config) => {
  const userId = DEFAULT_USER_ID;
  config.headers = config.headers ?? {};
  // Header multi-tenant para o backend
  config.headers["x-user-id"] = userId;
  return config;
});

// Tipagens auxiliares para respostas principais do backend

export interface ExtractionResponseEnvelope {
  status: "sucesso" | "erro";
  source?: "ai" | "cache";
  doc_type?: string;
  model_used?: string | null;
  doc_id?: string | number;
  data?: ProcessoTrabalhista;
  raiox?: unknown;
  alertas_juridicos?: string[];
  regras_aplicadas?: string[];
  memorial_juridico?: unknown;
  explicacoes?: unknown;
  qualidade_ok?: boolean;
  qualidade_motivo?: string | null;
}

export type StatsResponse = {
  processos_analisados: number;
  regras_oficiais_ativas: number;
  regras_em_teste_shadow: number;
  omissoes_detectadas: number;
  eficiencia_motor: number | null;
  ultimas_regras: Array<{
    rule_id: string;
    descricao: string;
    status: string;
    confidence_score: number;
    created_at: string | null;
    updated_at: string | null;
  }>;
  top_verbas_divergencias: Array<{
    verba: string;
    contagem: number;
    percentual: number;
  }>;
};

