import React, { useRef, useState } from "react";
import { Loader2 } from "lucide-react";
import {
  api,
  DEFAULT_USER_ID,
  type ExtractionResponseEnvelope,
  type UploadJobResponse,
} from "../services/api";
import { AnalysisReport } from "../components/features/AnalysisReport";
import { PdfViewer, isPdfFile } from "../components/features/PdfViewer";
import type { ProcessoTrabalhista } from "../types/api";

type BaseFile = File;

type ExtractorResult = {
  bruto: ExtractionResponseEnvelope | Record<string, unknown>;
  processo: ProcessoTrabalhista | null;
};

function buildWsUrl(jobId: string, wsPathFromApi: string | undefined): string {
  const path = wsPathFromApi && wsPathFromApi.startsWith("/") ? wsPathFromApi : `/ws/${jobId}`;
  if (typeof window === "undefined") {
    return `ws://localhost:8000${path}`;
  }
  const wsOrigin = window.location.origin.replace(/^http/, "ws");
  return `${wsOrigin}${path}`;
}

export const Extractor: React.FC = () => {
  const [file, setFile] = useState<BaseFile | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ExtractorResult | null>(null);
  const [partialData, setPartialData] = useState<Partial<ProcessoTrabalhista> | null>(null);
  const [progressMessages, setProgressMessages] = useState<string[]>([]);
  const [pdfNav, setPdfNav] = useState<{ page: number; seq: number }>({
    page: 1,
    seq: 0,
  });
  const wsRef = useRef<WebSocket | null>(null);

  const appendProgress = (msg: string) => {
    setProgressMessages((prev) => [...prev, msg]);
  };

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selected = event.target.files?.[0] ?? null;
    wsRef.current?.close();
    wsRef.current = null;
    setFile(selected);
    setError(null);
    setResult(null);
    setPartialData(null);
    setProgressMessages([]);
    setPdfNav({ page: 1, seq: 0 });
  };

  const handleAnalyze = async () => {
    if (!file) return;
    wsRef.current?.close();
    wsRef.current = null;
    setIsLoading(true);
    setError(null);
    setResult(null);
    setPartialData({});
    setProgressMessages(["Preparando envio…"]);

    try {
      const form = new FormData();
      form.append("user_id", DEFAULT_USER_ID);
      form.append("files", file);
      form.append("cache_context", "auto");

      appendProgress("Enviando documento (job assíncrono)…");
      const { data: uploadInfo } = await api.post<UploadJobResponse>("/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      const jobId = uploadInfo.job_id;
      appendProgress(
        `Job ${jobId.slice(0, 8)}… aceito. Conectando ao canal em tempo real…`,
      );

      await new Promise<void>((resolve) => {
        let settled = false;
        const markDone = () => {
          if (!settled) {
            settled = true;
            resolve();
          }
        };

        const applyFinalPayload = (raw: Record<string, unknown>) => {
          const st = raw.status;
          if (st === "done") {
            const processoValido =
              (raw.data as ProcessoTrabalhista | undefined) ?? null;
            setResult({
              bruto: raw as unknown as ExtractionResponseEnvelope,
              processo: processoValido,
            });
            appendProgress("Análise concluída com sucesso.");
            // eslint-disable-next-line no-console
            console.log("ESTRUTURA BRUTA DO BACKEND (job final):", raw);
          } else if (st === "error" || st === "timeout") {
            setError(String(raw.msg ?? "Erro no processamento."));
            appendProgress(`Erro: ${String(raw.msg ?? "desconhecido")}`);
          } else {
            setError("Resposta inesperada do servidor.");
          }
          setIsLoading(false);
          markDone();
        };

        const tryRecoverFromHttp = () => {
          void api
            .get<Record<string, unknown>>(`/status/${jobId}`)
            .then((stRes) => {
              const j = stRes.data;
              if (j && (j.status === "done" || j.status === "error")) {
                applyFinalPayload(j);
                return;
              }
              if (!settled) {
                setIsLoading(false);
                setError(
                  "Canal em tempo real encerrado antes do resultado. Tente novamente ou verifique o backend.",
                );
                markDone();
              }
            })
            .catch(() => {
              if (!settled) {
                setIsLoading(false);
                markDone();
              }
            });
        };

        const wsUrl = buildWsUrl(jobId, uploadInfo.ws_url);
        const socket = new WebSocket(wsUrl);
        wsRef.current = socket;

        socket.onopen = () => {
          appendProgress("Canal em tempo real ativo. Aguardando etapas da extração…");
        };

        socket.onmessage = (event: MessageEvent<string>) => {
          try {
            const msg = JSON.parse(event.data) as Record<string, unknown>;
            if (
              msg.type === "partial_update" &&
              msg.payload &&
              typeof msg.payload === "object" &&
              !Array.isArray(msg.payload)
            ) {
              setPartialData((prev) => ({
                ...(prev || {}),
                ...(msg.payload as Partial<ProcessoTrabalhista>),
              }));
              if (msg.message) {
                appendProgress(String(msg.message));
              }
              return;
            }
            if (msg.status === "processing" && msg.type === undefined) {
              return;
            }
            if (msg.status === "done" || msg.status === "error") {
              applyFinalPayload(msg);
              socket.close();
              return;
            }
          } catch {
            appendProgress(String(event.data));
          }
        };

        socket.onerror = () => {
          appendProgress("Falha no WebSocket. Tentando recuperar o resultado via HTTP…");
        };

        socket.onclose = () => {
          wsRef.current = null;
          if (!settled) {
            tryRecoverFromHttp();
          } else {
            markDone();
          }
        };
      });
    } catch (e: unknown) {
      const msg =
        e && typeof e === "object" && "message" in e
          ? String((e as { message: string }).message)
          : "Erro ao processar o documento.";
      setError(msg);
      setIsLoading(false);
      setPartialData(null);
    }
  };

  const processo = result?.processo ?? null;
  const processoEmRender = (processo ?? partialData) as ProcessoTrabalhista | null;
  const terminalMsgs = progressMessages.slice(-3);

  return (
    <div className="flex flex-col gap-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold text-slate-50">Extrator Rápido</h1>
        <p className="text-xs text-slate-400">
          Envie a Sentença ou Título Executivo em um único arquivo para obter o
          relatório pericial resumido. O processamento usa o mesmo motor que o
          upload assíncrono, com atualização progressiva quando possível.
        </p>
      </header>

      <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 shadow-sm">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm font-medium text-slate-50">
              Processo / Sentença (arquivo único)
            </p>
            <p className="text-xs text-slate-400">
              PDF ou DOCX contendo o título executivo (sentença/acórdão). O
              sistema tentará identificar automaticamente o número do processo.
            </p>
          </div>
          <div className="flex flex-col items-start gap-2 md:items-end">
            <label className="inline-flex cursor-pointer items-center gap-2 rounded-md border border-dashed border-slate-700 bg-slate-900/80 px-3 py-2 text-xs text-slate-300 hover:border-slate-500 hover:bg-slate-900">
              <span className="rounded bg-slate-800 px-2 py-1 text-[10px] font-medium uppercase tracking-wide text-slate-200">
                selecionar arquivo
              </span>
              <span className="max-w-[220px] truncate text-slate-400">
                {file ? file.name : "Nenhum arquivo selecionado"}
              </span>
              <input type="file" className="hidden" onChange={handleChange} />
            </label>
            <button
              type="button"
              disabled={!file || isLoading}
              onClick={handleAnalyze}
              className="inline-flex items-center justify-center rounded-md bg-blue-600 px-4 py-1.5 text-[11px] font-medium text-white shadow-sm hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-700"
            >
              {isLoading ? "Analisando..." : "🔎 Analisar Documento"}
            </button>
          </div>
        </div>
        {error && (
          <p className="mt-3 text-xs text-rose-400">
            Erro ao executar o extrator: {error}
          </p>
        )}
      </section>

      <section className="mt-2 min-h-[120px]">
        {isLoading && (
          <div className="mb-3 rounded-lg border border-slate-800 bg-black/50 p-3 font-mono text-xs text-slate-300">
            {terminalMsgs.map((msg, idx) => {
              const isLast = idx === terminalMsgs.length - 1;
              return (
                <div key={`${msg}-${idx}`} className="mb-1 flex items-center gap-2 last:mb-0">
                  {isLast ? <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-400" /> : null}
                  <span>{msg}</span>
                </div>
              );
            })}
          </div>
        )}

        {!isLoading && !processo && result && (
          <div className="space-y-2 text-xs text-amber-200">
            <p>
              A análise foi concluída, mas não foi possível montar um relatório
              estruturado para este documento. Verifique o log do backend para
              detalhes técnicos.
            </p>
            <button
              type="button"
              onClick={() => {
                setResult(null);
                setError(null);
              }}
              className="inline-flex items-center justify-center rounded-md bg-slate-800 px-3 py-1.5 text-[11px] font-medium text-slate-100 shadow-sm hover:bg-slate-700"
            >
              Tentar novamente
            </button>
          </div>
        )}

        {(processoEmRender || isLoading) && (
          <div
            className={
              file && isPdfFile(file)
                ? "grid gap-4 lg:grid-cols-2 lg:items-start"
                : "space-y-4"
            }
          >
            {file && isPdfFile(file) ? (
              <PdfViewer
                file={file}
                jumpToPage={pdfNav.page}
                jumpSeq={pdfNav.seq}
                className="rounded-xl border border-slate-800 bg-slate-900/50 p-3"
              />
            ) : null}
            <AnalysisReport
              processo={processoEmRender}
              raw={
                (result?.bruto ?? undefined) as ExtractionResponseEnvelope | undefined
              }
              onNavegar={(p) =>
                setPdfNav({ page: p, seq: Date.now() })
              }
              isLoading={isLoading}
            />
          </div>
        )}
      </section>
    </div>
  );
};
