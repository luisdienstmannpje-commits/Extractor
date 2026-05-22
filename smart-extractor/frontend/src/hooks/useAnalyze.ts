import { useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "../services/api";
import type { ProcessoTrabalhista } from "../types/api";

export interface AnalyzePayload {
  userId?: string;
  processo: File[];
  liquidacao?: File | null;
  parecer?: File | null;
  impugnacao?: File | null;
  calculoPjc?: File | null;
  amostragemPdf?: File | null;
  amostragemWord?: File | null;
  amostragens?: File[];
  manifestacao?: File | null;
  peticao?: File | null;
  contestacao?: File | null;
}

export interface LabReport {
  numero_processo?: string;
  discrepancias?: unknown[];
  aprendizados?: unknown[];
  [key: string]: unknown;
}

interface UseAnalyzeResult {
  mutate: (payload: AnalyzePayload) => void;
  isLoading: boolean;
  isSuccess: boolean;
  isError: boolean;
  data: LabReport | undefined;
  error: unknown;
  progressMessages: string[];
  partialData: Partial<ProcessoTrabalhista> | null;
}

export function useAnalyze(): UseAnalyzeResult {
  const [progressMessages, setProgressMessages] = useState<string[]>([]);
  const [partialData, setPartialData] = useState<Partial<ProcessoTrabalhista> | null>(
    null,
  );
  const wsRef = useRef<WebSocket | null>(null);

  const appendProgress = (msg: string) => {
    setProgressMessages((prev) => [...prev, msg]);
  };

  const mutation = useMutation({
    mutationFn: async (payload: AnalyzePayload): Promise<LabReport> => {
      const form = new FormData();

      const userId = payload.userId?.trim() || "anonimo";
      form.append("user_id", userId);

      (payload.processo || []).forEach((file) => {
        form.append("processo", file);
      });

      if (payload.liquidacao) form.append("liquidacao", payload.liquidacao);
      if (payload.parecer) form.append("parecer", payload.parecer);
      if (payload.impugnacao) form.append("impugnacao", payload.impugnacao);
      if (payload.calculoPjc) form.append("calculo_pjc", payload.calculoPjc);
      if (payload.amostragemPdf) form.append("amostragem_pdf", payload.amostragemPdf);
      if (payload.amostragemWord) form.append("amostragem_word", payload.amostragemWord);
      if (payload.manifestacao) form.append("manifestacao", payload.manifestacao);
      if (payload.peticao) form.append("peticao", payload.peticao);
      if (payload.contestacao) form.append("contestacao", payload.contestacao);

      (payload.amostragens || []).forEach((file) => {
        form.append("amostragens", file);
      });

      appendProgress("Enviando arquivos para o Laboratório...");

      const response = await api.post<LabReport>("/lab/analisar", form, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      appendProgress("Análise recebida. Iniciando monitorização do pipeline...");

      return response.data;
    },
    onError: (err) => {
      appendProgress(
        err instanceof Error ? `Erro na análise: ${err.message}` : "Erro desconhecido na análise.",
      );
    },
    onMutate: () => {
      setPartialData(null);
      setProgressMessages([]);
    },
  });

  useEffect(() => {
    if (!mutation.isSuccess || wsRef.current) return;

    try {
      const base =
        typeof window !== "undefined" ? window.location.origin : "http://localhost:8000";
      const wsUrl = base.replace(/^http/, "ws") + "/ws/lab-pipeline";
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      appendProgress("Conectando ao canal em tempo real do pipeline...");

      ws.onopen = () => {
        appendProgress("Canal WebSocket conectado.");
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data?.type === "partial_update" && data?.payload && typeof data.payload === "object") {
            setPartialData((prev) => ({
              ...(prev || {}),
              ...(data.payload as Partial<ProcessoTrabalhista>),
            }));
            if (data?.message) {
              appendProgress(String(data.message));
            }
            return;
          }
          if (Array.isArray(data?.steps)) {
            data.steps.forEach((step: string) => appendProgress(step));
          } else if (data?.message) {
            appendProgress(String(data.message));
          } else {
            appendProgress(String(event.data));
          }
        } catch {
          appendProgress(String(event.data));
        }
      };

      ws.onerror = () => {
        appendProgress("Falha ao conectar ao WebSocket do pipeline. Continuando com o resultado final.");
      };

      ws.onclose = () => {
        appendProgress("Canal do pipeline encerrado.");
        wsRef.current = null;
      };
    } catch {
      appendProgress(
        "Erro ao iniciar listener de WebSocket. Monitorização em tempo real indisponível neste ambiente.",
      );
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [mutation.isSuccess]);

  return {
    mutate: mutation.mutate,
    isLoading: mutation.isPending,
    isSuccess: mutation.isSuccess,
    isError: mutation.isError,
    data: mutation.data,
    error: mutation.error,
    progressMessages,
    partialData,
  };
}

