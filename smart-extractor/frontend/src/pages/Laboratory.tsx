import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  BrainCircuit,
  FileText,
  FileSpreadsheet,
  FileCode,
  CheckCircle,
  AlertCircle,
  Play,
  Trash2,
  Pencil,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { useAnalyze } from "../hooks/useAnalyze";
import { AnalysisReport } from "../components/features/AnalysisReport";
import type { ProcessoTrabalhista } from "../types/api";
import { api } from "../services/api";
import type { AnalyzePayload } from "../hooks/useAnalyze";

// Pesos e regras do motor IA — Termômetro de Eficiência
const FILE_TYPES = [
  {
    id: "sentenca" as const,
    name: "Sentença / Acórdão",
    weight: 35,
    icon: FileText,
    desc: "Base da Coisa Julgada (O que foi deferido)",
    color: "text-blue-400",
    accept: ".pdf,.doc,.docx",
    multiple: true,
  },
  {
    id: "liquidacao" as const,
    name: "Liquidação (PDF)",
    weight: 25,
    icon: FileSpreadsheet,
    desc: "Cálculo a ser auditado",
    color: "text-red-400",
    accept: ".pdf,.doc,.docx",
    multiple: false,
  },
  {
    id: "pjc" as const,
    name: "Arquivo .PJC",
    weight: 20,
    icon: FileCode,
    desc: "Dados matemáticos precisos do PJe-Calc",
    color: "text-green-400",
    accept: ".pdf,.doc,.docx,.pjc,.xml",
    multiple: false,
  },
  {
    id: "manifestacao" as const,
    name: "Manifestação/Impugnação",
    weight: 10,
    icon: FileText,
    desc: "Foco nos pontos de controvérsia",
    color: "text-yellow-400",
    accept: ".pdf,.doc,.docx",
    multiple: false,
  },
  {
    id: "parecer" as const,
    name: "Parecer/Amostragem",
    weight: 10,
    icon: BrainCircuit,
    desc: "Clonagem do seu estilo de redação",
    color: "text-purple-400",
    accept: ".pdf,.doc,.docx",
    multiple: false,
  },
];

type FileTypeId = (typeof FILE_TYPES)[number]["id"];

interface CerebroFiles {
  sentenca: File[];
  liquidacao: File | null;
  pjc: File | null;
  manifestacao: File | null;
  parecer: File | null;
}

function hasFile(files: CerebroFiles, id: FileTypeId): boolean {
  if (id === "sentenca") return files.sentenca.length > 0;
  return !!files[id];
}

// Som de notificação (estilo WhatsApp Web) — Web Audio API, sem arquivos externos
function playNotificationSound(): void {
  try {
    const AudioContextClass =
      typeof window !== "undefined"
        ? (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)
        : null;
    if (!AudioContextClass) return;
    const ctx = new AudioContextClass();
    const osc = ctx.createOscillator();
    const gainNode = ctx.createGain();
    osc.connect(gainNode);
    gainNode.connect(ctx.destination);
    osc.type = "sine";
    osc.frequency.setValueAtTime(880, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(1760, ctx.currentTime + 0.1);
    gainNode.gain.setValueAtTime(0, ctx.currentTime);
    gainNode.gain.linearRampToValueAtTime(0.3, ctx.currentTime + 0.05);
    gainNode.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.3);
  } catch {
    // ignorar em ambientes sem AudioContext ou bloqueio de áudio
  }
}

// Frases do "terminal" embutido no botão (atualizadas a cada ~600ms)
const LOG_PHRASES = [
  "Iniciando motor analítico...",
  "Lendo estrutura do documento...",
  "Buscando Coisa Julgada...",
  "Auditando cálculos...",
  "Extraindo estilo jurídico...",
  "Consolidando aprendizado...",
];

// Painel HITL: itens aprendidos (regras / linguagem) para auditoria humana
export interface LearnedItem {
  id: string;
  tipo: "Regra de Cálculo" | "Linguagem";
  descricao: string;
  _raw?: Record<string, unknown>;
}

function normalizeAprendizados(aprendizados: unknown[]): LearnedItem[] {
  return aprendizados
    .filter((ap): ap is Record<string, unknown> => ap != null && typeof ap === "object")
    .map((ap, idx) => {
      const tipoBack = String(ap.tipo || "").toLowerCase();
      const tipo: LearnedItem["tipo"] =
        tipoBack === "playbook" ? "Linguagem" : "Regra de Cálculo";
      const id =
        (ap.id as string) ||
        (tipoBack === "playbook" ? `STY_${idx + 1}` : `DYN_${idx + 1}`);
      const descricao =
        (ap.descricao as string) ||
        (ap.titulo as string) ||
        "Aprendizado extraído";
      return { id, tipo, descricao, _raw: ap };
    });
}

// ----- Main Laboratory: Cérebro Analítico -----
export const Laboratory: React.FC = () => {
  const [files, setFiles] = useState<CerebroFiles>({
    sentenca: [],
    liquidacao: null,
    pjc: null,
    manifestacao: null,
    parecer: null,
  });

  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [learnedItems, setLearnedItems] = useState<LearnedItem[]>([]);
  const [isLearningsExpanded, setIsLearningsExpanded] = useState(false);
  const [currentLog, setCurrentLog] = useState("");
  const logIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const { mutate, isLoading, isSuccess, data } = useAnalyze();

  const efficiency = useMemo(() => {
    return FILE_TYPES.reduce((total, ft) => {
      return total + (hasFile(files, ft.id) ? ft.weight : 0);
    }, 0);
  }, [files]);

  const getEfficiencyStatus = useCallback(() => {
    const hasSentenca = files.sentenca.length > 0;
    const hasLiquidacaoOrPjc = !!files.liquidacao || !!files.pjc;
    const hasManifestacaoOrParecer = !!files.manifestacao || !!files.parecer;
    const onlyStyleDocs =
      !hasSentenca && !hasLiquidacaoOrPjc && hasManifestacaoOrParecer;

    if (efficiency === 0)
      return {
        color: "bg-slate-500",
        text: "Nenhum documento anexado",
        icon: AlertCircle,
      };
    if (onlyStyleDocs)
      return {
        color: "bg-purple-500",
        text: "Treinamento de Estilo (Sem base de cálculo)",
        icon: BrainCircuit,
      };
    if (efficiency < 35)
      return {
        color: "bg-yellow-500",
        text: "Extração parcial (adicione Sentença para análise completa)",
        icon: AlertCircle,
      };
    if (efficiency < 60)
      return {
        color: "bg-yellow-500",
        text: "Análise Básica (Apenas Extração)",
        icon: AlertCircle,
      };
    if (efficiency < 80)
      return {
        color: "bg-blue-500",
        text: "Auditoria Sólida (Sentença + Cálculo)",
        icon: CheckCircle,
      };
    return {
      color: "bg-green-500",
      text: "Análise Pericial Profunda (Máxima Precisão)",
      icon: BrainCircuit,
    };
  }, [efficiency, files]);

  const status = getEfficiencyStatus();

  useEffect(() => {
    if (data) setIsReportModalOpen(true);
  }, [data]);

  // Popula painel de aprendizados a partir do relatório (ou mocks) e expande o painel ao concluir
  useEffect(() => {
    if (!data) return;
    const raw = (data.aprendizados as unknown[] | undefined) || [];
    const normalized = normalizeAprendizados(raw);
    if (normalized.length > 0) {
      setLearnedItems(normalized);
    } else {
      // Simulação: 2–3 exemplos fictícios para visualizar a UI
      setLearnedItems([
        {
          id: "DYN_123",
          tipo: "Regra de Cálculo",
          descricao:
            "Se houver horas extras, incluir reflexos em FGTS e DSR conforme comandos sentenciais.",
        },
        {
          id: "STY_456",
          tipo: "Linguagem",
          descricao: 'Uso da expressão "Ex positis" na conclusão de pareceres.',
        },
        {
          id: "DYN_789",
          tipo: "Regra de Cálculo",
          descricao:
            "Aplicar IPCA-E na fase pré-judicial e SELIC a partir do ajuizamento (ADC 58).",
        },
      ]);
    }
    setIsLearningsExpanded(true);
  }, [data]);

  // Ao terminar a análise: limpar interval, tocar som e zerar currentLog
  const prevLoadingRef = useRef(false);
  useEffect(() => {
    if (prevLoadingRef.current && !isLoading) {
      if (logIntervalRef.current) {
        clearInterval(logIntervalRef.current);
        logIntervalRef.current = null;
      }
      playNotificationSound();
      setCurrentLog("");
    }
    prevLoadingRef.current = isLoading;
  }, [isLoading]);

  const setFile = useCallback((id: FileTypeId, value: File | File[] | null) => {
    setFiles((prev) => {
      const next = { ...prev };
      if (id === "sentenca") {
        next.sentenca = Array.isArray(value) ? value : value ? [value] : [];
      } else {
        next[id] = value && !Array.isArray(value) ? value : null;
      }
      return next;
    });
  }, []);

  const hasAnyFile =
    files.sentenca.length > 0 ||
    !!files.liquidacao ||
    !!files.pjc ||
    !!files.manifestacao ||
    !!files.parecer;

  const handleGlobalAnalysis = useCallback(() => {
    if (!hasAnyFile) {
      alert("Anexe pelo menos um documento para análise.");
      return;
    }
    setCurrentLog(LOG_PHRASES[0] ?? "Processando...");
    let idx = 0;
    logIntervalRef.current = setInterval(() => {
      idx = (idx + 1) % LOG_PHRASES.length;
      setCurrentLog(LOG_PHRASES[idx] ?? "Processando...");
    }, 600);
    const payload: AnalyzePayload = {
      processo: files.sentenca,
      liquidacao: files.liquidacao ?? undefined,
      calculoPjc: files.pjc ?? undefined,
      manifestacao: files.manifestacao ?? undefined,
      parecer: files.parecer ?? undefined,
    };
    mutate(payload);
  }, [hasAnyFile, files, mutate]);

  const processoTrabalhista = (data || null) as unknown as
    | ProcessoTrabalhista
    | null;

  const handleDownload = async (url: string, fallbackFilename: string) => {
    try {
      const response = await api.get<Blob>(url, { responseType: "blob" });
      const disposition = response.headers["content-disposition"] as
        | string
        | undefined;
      const match = disposition?.match(/filename="?([^";]+)"?/i);
      const filename = match?.[1] ?? fallbackFilename;
      const blob = new Blob([response.data]);
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch {
      // silent
    }
  };

  const handleGenerateDocx = async () => {
    if (!data) return;
    try {
      const response = await api.post("/lab/gerar-docx", data, {
        responseType: "blob",
      });
      const disposition = response.headers["content-disposition"] as
        | string
        | undefined;
      const match = disposition?.match(/filename="?([^";]+)"?/i);
      const fallback =
        "Manifestacao_" +
        (processoTrabalhista?.numero_processo || "minuta") +
        ".docx";
      const filename = match?.[1] ?? fallback;
      const blob = new Blob([response.data]);
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch {
      // silent
    }
  };

  const handleGenerateExcel = async () => {
    const jobId = processoTrabalhista?.numero_processo || "lab";
    await handleDownload(
      `/export-excel/${encodeURIComponent(jobId)}`,
      "Relatorio_Lab.xlsx",
    );
  };

  const handleGeneratePjc = async () => {
    const jobId = processoTrabalhista?.numero_processo || "lab";
    await handleDownload(
      `/download-pjc/${encodeURIComponent(jobId)}`,
      "Parametros_PJeCalc_Lab.pjc",
    );
  };

  const handleRemoveLearned = useCallback((item: LearnedItem) => {
    const ok = window.confirm(
      `Deseja remover o aprendizado ID ${item.id} da base de conhecimento?`,
    );
    if (ok) {
      setLearnedItems((prev) => prev.filter((x) => x.id !== item.id));
    }
  }, []);

  const StatusIcon = status.icon;

  return (
    <div className="flex flex-col gap-6 max-w-5xl mx-auto min-h-screen">
      {/* Header e barra de eficiência — Termômetro */}
      <div className="rounded-xl border border-slate-700 bg-slate-800/80 p-6 shadow-sm">
        <div className="flex justify-between items-end mb-4">
          <div>
            <h2 className="text-2xl font-bold text-slate-50 flex items-center gap-2">
              <BrainCircuit className="w-7 h-7 text-indigo-400" />
              Cérebro Analítico
            </h2>
            <p className="text-slate-400 text-sm mt-1">
              Nível de profundidade da Inteligência Artificial
            </p>
          </div>
          <div className="text-right">
            <span className="text-3xl font-black text-slate-50">
              {efficiency}%
            </span>
          </div>
        </div>

        <div className="w-full bg-slate-700 rounded-full h-4 mb-2 overflow-hidden">
          <div
            className={`h-4 rounded-full transition-all duration-700 ease-out ${status.color}`}
            style={{ width: `${efficiency}%` }}
          />
        </div>

        <div
          className={`flex items-center gap-2 text-sm font-medium ${
            status.color === "bg-slate-500"
              ? "text-slate-400"
              : status.color === "bg-purple-500"
                ? "text-purple-400"
                : status.color === "bg-red-500"
                  ? "text-red-400"
                  : status.color === "bg-yellow-500"
                    ? "text-yellow-400"
                    : status.color === "bg-blue-500"
                      ? "text-blue-400"
                      : "text-green-400"
          }`}
        >
          <StatusIcon className="w-4 h-4" />
          <span>{status.text}</span>
        </div>
      </div>

      {/* Cards de upload (sem botão analisar individual) */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {FILE_TYPES.map((ft) => {
          const isUploaded = hasFile(files, ft.id);
          const Icon = ft.icon;
          const current =
            ft.id === "sentenca"
              ? files.sentenca
              : files[ft.id as keyof CerebroFiles];

          return (
            <div
              key={ft.id}
              className={`relative rounded-xl border-2 p-5 transition-all duration-200 ${
                isUploaded
                  ? "border-indigo-500 bg-indigo-500/10"
                  : "border-slate-700 bg-slate-800/60 hover:border-slate-600"
              }`}
            >
              <div className="flex justify-between items-start mb-3">
                <div
                  className={`p-3 rounded-lg ${
                    isUploaded ? "bg-indigo-500/20" : "bg-slate-700/80"
                  }`}
                >
                  <Icon
                    className={`w-6 h-6 ${
                      isUploaded ? "text-indigo-400" : "text-slate-500"
                    } ${ft.color}`}
                  />
                </div>
                {isUploaded && (
                  <CheckCircle className="w-6 h-6 text-indigo-400 shrink-0" />
                )}
              </div>

              <h3 className="font-bold text-slate-50">{ft.name}</h3>
              <p className="text-xs text-slate-400 mt-1 line-clamp-2">
                {ft.desc}
              </p>

              {ft.multiple ? (
                <div className="mt-4 space-y-2" onClick={(e) => e.stopPropagation()}>
                  <label className="flex items-center gap-2 rounded-lg border border-slate-600 bg-slate-900/80 px-3 py-2 cursor-pointer hover:bg-slate-800">
                    <span className="text-xs text-slate-300 truncate flex-1">
                      {files.sentenca.length > 0
                        ? `${files.sentenca.length} arquivo(s)`
                        : "Escolher arquivo(s)"}
                    </span>
                    <input
                      type="file"
                      className="hidden"
                      accept={ft.accept}
                      multiple
                      onChange={(e) => {
                        const list = Array.from(e.target.files ?? []);
                        setFile("sentenca", list);
                      }}
                    />
                    <span className="text-[10px] text-indigo-400">Escolher</span>
                  </label>
                  {files.sentenca.length > 0 && (
                    <button
                      type="button"
                      className="text-[10px] text-rose-400 hover:text-rose-300"
                      onClick={() => setFile("sentenca", [])}
                    >
                      Remover todos
                    </button>
                  )}
                </div>
              ) : (
                <div className="mt-4 space-y-2" onClick={(e) => e.stopPropagation()}>
                  <label className="flex items-center gap-2 rounded-lg border border-slate-600 bg-slate-900/80 px-3 py-2 cursor-pointer hover:bg-slate-800">
                    <span className="text-xs text-slate-300 truncate flex-1">
                      {(current as File | null)?.name ?? "Nenhum arquivo"}
                    </span>
                    <input
                      type="file"
                      className="hidden"
                      accept={ft.accept}
                      onChange={(e) => {
                        const f = e.target.files?.[0];
                        setFile(ft.id, f ?? null);
                      }}
                    />
                    <span className="text-[10px] text-indigo-400">Escolher</span>
                  </label>
                  {(current as File | null) && (
                    <button
                      type="button"
                      className="text-[10px] text-rose-400 hover:text-rose-300"
                      onClick={() => setFile(ft.id, null)}
                    >
                      Remover
                    </button>
                  )}
                </div>
              )}

              <div className="mt-4 inline-block px-2 py-1 bg-slate-700/80 text-xs font-semibold text-slate-300 rounded">
                Peso: +{ft.weight}%
              </div>
            </div>
          );
        })}
      </div>

      {/* Botão global de análise — integração real POST /lab/analisar */}
      <div className="sticky bottom-6 z-10">
        <button
          type="button"
          onClick={handleGlobalAnalysis}
          disabled={isLoading || !hasAnyFile}
          className={`w-full flex items-center justify-center gap-3 py-4 px-8 rounded-xl text-lg font-bold text-white shadow-lg transition-all duration-300 ${
            !hasAnyFile
              ? "bg-slate-600 cursor-not-allowed"
              : isLoading
                ? "bg-indigo-500 animate-pulse"
                : "bg-indigo-600 hover:bg-indigo-700 hover:shadow-indigo-500/30 hover:-translate-y-0.5"
          }`}
        >
          {isLoading ? (
            <>
              <BrainCircuit className="w-6 h-6 shrink-0 animate-spin" />
              <div className="flex min-w-0 flex-1 flex-col items-start overflow-hidden">
                <span className="text-[10px] uppercase tracking-wider text-indigo-200 opacity-80 leading-none">
                  Analisando
                </span>
                <span className="mt-0.5 w-full max-w-[200px] truncate text-left font-mono text-sm animate-pulse sm:max-w-xs">
                  &gt; {currentLog || "..."}
                </span>
              </div>
            </>
          ) : (
            <>
              <Play className="w-6 h-6 shrink-0" />
              Analisar Processo Completo
            </>
          )}
        </button>
      </div>

      {/* Painel de transparência: Regras e Linguagem Aprendidas (HITL) */}
      {learnedItems.length > 0 && (
        <section className="rounded-xl border border-slate-700 bg-slate-800 text-slate-300 overflow-hidden shadow-sm">
          <button
            type="button"
            className="w-full flex items-center justify-between gap-2 px-4 py-3 text-left hover:bg-slate-700/50 transition-colors"
            onClick={() => setIsLearningsExpanded((e) => !e)}
          >
            <span className="font-medium text-slate-200">
              🧠 [{learnedItems.length}] Novos Aprendizados Extraídos (Clique
              para expandir)
            </span>
            {isLearningsExpanded ? (
              <ChevronUp className="w-5 h-5 text-slate-400 shrink-0" />
            ) : (
              <ChevronDown className="w-5 h-5 text-slate-400 shrink-0" />
            )}
          </button>
          {isLearningsExpanded && (
            <div className="border-t border-slate-700 bg-slate-900/60 max-h-80 overflow-y-auto">
              <ul className="divide-y divide-slate-700/80 p-2">
                {learnedItems.map((item) => (
                  <li
                    key={item.id}
                    className="flex items-start gap-3 px-3 py-2.5 text-sm font-mono rounded hover:bg-slate-800/60"
                  >
                    <span
                      className={`shrink-0 rounded px-2 py-0.5 text-[10px] font-semibold uppercase ${
                        item.tipo === "Regra de Cálculo"
                          ? "bg-blue-500/20 text-blue-300"
                          : "bg-purple-500/20 text-purple-300"
                      }`}
                    >
                      {item.tipo}
                    </span>
                    <span className="flex-1 min-w-0 text-slate-300">
                      {item.descricao}
                    </span>
                    <span className="text-[10px] text-slate-500 shrink-0">
                      {item.id}
                    </span>
                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        type="button"
                        className="p-1.5 rounded text-slate-400 hover:text-amber-400 hover:bg-slate-700"
                        title="Editar"
                        aria-label="Editar"
                      >
                        <Pencil className="w-4 h-4" />
                      </button>
                      <button
                        type="button"
                        className="p-1.5 rounded text-slate-400 hover:text-red-400 hover:bg-slate-700"
                        title="Excluir"
                        aria-label="Excluir"
                        onClick={() => handleRemoveLearned(item)}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}

      {/* Relatório de Discrepância */}
      {processoTrabalhista && (
        <section className="rounded-xl border border-slate-700 bg-slate-800/50 p-4">
          <div className="flex items-center justify-between gap-2 mb-3">
            <h2 className="text-sm font-semibold text-slate-50">
              Relatório de Discrepância
            </h2>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="rounded-md bg-slate-700 px-2 py-1 text-[11px] text-slate-200 hover:bg-slate-600"
                onClick={() => setIsReportModalOpen(true)}
              >
                Abrir em modal
              </button>
              <button
                type="button"
                className="rounded-md bg-slate-700 px-2 py-1 text-[11px] text-slate-200 hover:bg-slate-600 disabled:opacity-50"
                disabled={!processoTrabalhista}
                onClick={handleGeneratePjc}
              >
                Gerar PJC
              </button>
              <button
                type="button"
                className="rounded-md bg-slate-700 px-2 py-1 text-[11px] text-slate-200 hover:bg-slate-600 disabled:opacity-50"
                disabled={!processoTrabalhista}
                onClick={handleGenerateExcel}
              >
                Gerar Excel
              </button>
              <button
                type="button"
                className="rounded-md bg-emerald-600 px-2 py-1 text-[11px] text-white hover:bg-emerald-500 disabled:opacity-50"
                disabled={!processoTrabalhista}
                onClick={handleGenerateDocx}
              >
                Gerar Minuta Word
              </button>
            </div>
          </div>
          <div className="max-h-[480px] overflow-y-auto rounded-lg bg-slate-950/60 p-3">
            <AnalysisReport processo={processoTrabalhista} raw={data} />
          </div>
        </section>
      )}

      {/* Modal: Relatório (tela cheia) */}
      {isReportModalOpen && processoTrabalhista && (
        <div className="fixed inset-0 z-50 flex flex-col bg-slate-950">
          <div className="flex shrink-0 items-center justify-between border-b border-slate-800 bg-slate-900/90 px-4 py-3">
            <h2 className="text-sm font-semibold text-slate-50">
              Relatório de Discrepância
            </h2>
            <button
              type="button"
              className="rounded-md px-3 py-1.5 text-[11px] text-slate-300 hover:bg-slate-800"
              onClick={() => setIsReportModalOpen(false)}
            >
              Fechar
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            <AnalysisReport processo={processoTrabalhista} raw={data} />
          </div>
        </div>
      )}
    </div>
  );
};
