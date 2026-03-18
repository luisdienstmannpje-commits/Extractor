import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  BrainCircuit,
  FileText,
  FileSpreadsheet,
  FileCode,
  CheckCircle,
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

// ─── Cards do Laboratório ─────────────────────────────────────────────────────
const FILE_TYPES = [
  {
    id: "sentenca" as const,
    card: "3",
    phase: "TÍTULO EXECUTIVO COMPLEXO",
    name: "Sentença / Acórdão",
    weight: 30,
    icon: FileText,
    hint: "Qualquer formato · múltiplos",
    badge: "OBRIGATÓRIO" as const,
    multiple: true,
    dropZone: true,
  },
  {
    id: "liquidacao" as const,
    card: "4",
    phase: "CÁLCULO DA EMPRESA",
    name: "Liquidação",
    weight: 15,
    icon: FileSpreadsheet,
    hint: "Qualquer formato",
    badge: "RECOMENDADO" as const,
    multiple: false,
    dropZone: false,
  },
  {
    id: "pjc" as const,
    card: "5",
    phase: "PLANILHA PJE-CALC",
    name: "Cálculo .PJC",
    weight: 10,
    icon: FileCode,
    hint: "Qualquer formato",
    badge: "OPCIONAL" as const,
    multiple: false,
    dropZone: false,
  },
  {
    id: "parecer" as const,
    card: "7",
    phase: "SEU PARECER TÉCNICO",
    name: "Parecer",
    weight: 20,
    icon: BrainCircuit,
    hint: "Qualquer formato",
    badge: "OBRIGATÓRIO" as const,
    multiple: false,
    dropZone: false,
  },
  {
    id: "manifestacao" as const,
    card: "8",
    phase: "PETIÇÃO DE RESPOSTA",
    name: "Manifestação",
    weight: 10,
    icon: FileText,
    hint: "Qualquer formato",
    badge: "OPCIONAL" as const,
    multiple: false,
    dropZone: false,
  },
] as const;

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

// ─── Som de notificação ───────────────────────────────────────────────────────
function playNotificationSound(): void {
  try {
    const AudioContextClass =
      typeof window !== "undefined"
        ? (window.AudioContext ||
            (
              window as unknown as { webkitAudioContext: typeof AudioContext }
            ).webkitAudioContext)
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
    // ignorar
  }
}

const LOG_PHRASES = [
  "Iniciando motor analítico...",
  "Lendo estrutura do documento...",
  "Buscando Coisa Julgada...",
  "Auditando cálculos...",
  "Extraindo estilo jurídico...",
  "Consolidando aprendizado...",
];

// ─── Tipos do painel de conhecimento ─────────────────────────────────────────
export interface LearnedItem {
  id: string;
  tipo: "Regra de Cálculo" | "Linguagem" | "Lógica Jurídica" | "Fundamento";
  descricao: string;
  base_legal?: string;
  nivel_sugerido?: string;
  correcao?: string;
  _raw?: Record<string, unknown>;
}

function mapTipoBadge(tipoBackend: unknown): LearnedItem["tipo"] {
  const t = String(tipoBackend || "").toLowerCase().trim();
  if (t === "regra") return "Regra de Cálculo";
  if (t === "playbook") return "Linguagem";
  if (t === "fundamento") return "Fundamento";
  return "Lógica Jurídica";
}

function normalizeAprendizados(aprendizados: unknown[]): LearnedItem[] {
  return aprendizados
    .filter(
      (ap): ap is Record<string, unknown> => ap != null && typeof ap === "object",
    )
    .map((ap, idx) => {
      const tipo = mapTipoBadge(ap.tipo);
      const id =
        (typeof ap.id === "string" && ap.id) ||
        (typeof ap.rule_id === "string" && ap.rule_id) ||
        `AP_${idx + 1}`;
      const descricao =
        (typeof ap.descricao === "string" && ap.descricao) ||
        (typeof ap.titulo === "string" && ap.titulo) ||
        "Aprendizado extraído";
      return {
        id,
        tipo,
        descricao,
        base_legal: typeof ap.base_legal === "string" ? ap.base_legal : undefined,
        nivel_sugerido:
          typeof ap.nivel_sugerido === "string" ? ap.nivel_sugerido : undefined,
        correcao: typeof ap.correcao === "string" ? ap.correcao : undefined,
        _raw: ap,
      };
    });
}

function badgeClass(tipo: LearnedItem["tipo"]): string {
  if (tipo === "Regra de Cálculo") return "bg-blue-500/20 text-blue-300";
  if (tipo === "Linguagem") return "bg-purple-500/20 text-purple-300";
  if (tipo === "Fundamento") return "bg-yellow-500/20 text-yellow-300";
  return "bg-emerald-500/20 text-emerald-300";
}

function nivelClass(nivel?: string): string | null {
  const n = String(nivel || "").toUpperCase();
  if (!n) return null;
  if (n.includes("ERRO"))
    return "bg-rose-500/20 text-rose-300 border border-rose-500/30";
  if (n.includes("AVISO"))
    return "bg-yellow-500/20 text-yellow-300 border border-yellow-500/30";
  return "bg-slate-500/20 text-slate-300 border border-slate-500/30";
}

// ════════════════════════════════════════════════════════════════════════════
// COMPONENTE PRINCIPAL
// ════════════════════════════════════════════════════════════════════════════
export const Laboratory: React.FC = () => {
  const [files, setFiles] = useState<CerebroFiles>({
    sentenca: [],
    liquidacao: null,
    pjc: null,
    manifestacao: null,
    parecer: null,
  });
  const [amostragens, setAmostragens] = useState<File[]>([]);
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [learnedItems, setLearnedItems] = useState<LearnedItem[]>([]);
  const [isLearningsExpanded, setIsLearningsExpanded] = useState(true);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingText, setEditingText] = useState<string>("");
  const [currentLog, setCurrentLog] = useState("");
  const logIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const { mutate, isLoading, data } = useAnalyze();

  const hasAmostragens = amostragens.length > 0;

  const totalFilesSelected = useMemo(() => {
    return (
      files.sentenca.length +
      (files.liquidacao ? 1 : 0) +
      (files.pjc ? 1 : 0) +
      (files.parecer ? 1 : 0) +
      (files.manifestacao ? 1 : 0) +
      amostragens.length
    );
  }, [files, amostragens]);

  // ── Eficiência ──────────────────────────────────────────────────────────
  const efficiency = useMemo(() => {
    const base = FILE_TYPES.reduce(
      (total, ft) => total + (hasFile(files, ft.id) ? ft.weight : 0),
      0,
    );
    return Math.min(100, base + (hasAmostragens ? 15 : 0));
  }, [files, hasAmostragens]);

  const efficiencyStatus = useMemo(() => {
    if (efficiency === 0)
      return {
        bar: "bg-gray-600",
        nivel: "Aguardando arquivos...",
        detalhe: "Adicione arquivos para ver a previsão atualizar em tempo real.",
      };
    if (efficiency < 25)
      return {
        bar: "bg-gray-500",
        nivel: "Contexto inicial — aprendizado limitado",
        detalhe: "Adicione Sentença/Acórdão e Parecer para subir para Nível 1.",
      };
    if (efficiency < 45)
      return {
        bar: "bg-blue-500",
        nivel: "⚡ Nível 1 — Rápido: fundamentos jurídicos e estilo da perita",
        detalhe: "Adicione Liquidação para subir para Nível 2.",
      };
    if (efficiency < 65)
      return {
        bar: "bg-yellow-500",
        nivel:
          "🔍 Nível 2 — Auditoria: discrepâncias entre sentença e cálculo da empresa",
        detalhe:
          "Adicione o Cálculo PJC para ativar detecção de omissões de parâmetros.",
      };
    if (efficiency < 85)
      return {
        bar: "bg-orange-500",
        nivel: "📊 Nível 3 — Tríade: detecção automática de omissões de parâmetros",
        detalhe:
          "Adicione Manifestação para atingir o máximo aprendizado preditivo.",
      };
    return {
      bar: "bg-green-500",
      nivel: "🏆 Nível 4 — Tríade de Ouro: máximo aprendizado preditivo ativo",
      detalhe: "Todos os insumos essenciais presentes. Aprendizado completo.",
    };
  }, [efficiency]);

  // ── Efeitos ─────────────────────────────────────────────────────────────
  useEffect(() => {
    if (data) setIsReportModalOpen(true);
  }, [data]);

  useEffect(() => {
    if (!data) return;
    const raw =
      ((data as Record<string, unknown>).aprendizados as unknown[] | undefined) ||
      [];
    setLearnedItems(normalizeAprendizados(raw));
    setIsLearningsExpanded(true);
  }, [data]);

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

  // ── Arquivo ──────────────────────────────────────────────────────────────
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

  // ── Análise ──────────────────────────────────────────────────────────────
  const handleGlobalAnalysis = useCallback(() => {
    const hasAnyFile =
      files.sentenca.length > 0 ||
      !!files.liquidacao ||
      !!files.pjc ||
      !!files.manifestacao ||
      !!files.parecer ||
      amostragens.length > 0;
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
    mutate({
      processo: files.sentenca,
      liquidacao: files.liquidacao ?? undefined,
      calculoPjc: files.pjc ?? undefined,
      manifestacao: files.manifestacao ?? undefined,
      parecer: files.parecer ?? undefined,
      amostragens,
    } as AnalyzePayload);
  }, [files, mutate, amostragens]);

  // ── Downloads ────────────────────────────────────────────────────────────
  const processoTrabalhista = (data || null) as unknown as
    | ProcessoTrabalhista
    | null;

  const handleDownload = async (url: string, fallback: string) => {
    try {
      const r = await api.get<Blob>(url, { responseType: "blob" });
      const m = (r.headers["content-disposition"] as string | undefined)?.match(
        /filename="?([^";]+)"?/i,
      );
      const blob = new Blob([r.data]);
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = m?.[1] ?? fallback;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch {
      /* silent */
    }
  };

  const handleGenerateDocx = async () => {
    if (!data) return;
    try {
      const r = await api.post("/lab/gerar-docx", data, { responseType: "blob" });
      const m = (r.headers["content-disposition"] as string | undefined)?.match(
        /filename="?([^";]+)"?/i,
      );
      const blob = new Blob([r.data]);
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download =
        m?.[1] ??
        `Manifestacao_${processoTrabalhista?.numero_processo || "minuta"}.docx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch {
      /* silent */
    }
  };

  const handleGenerateExcel = () =>
    handleDownload(
      `/export-excel/${encodeURIComponent(
        processoTrabalhista?.numero_processo || "lab",
      )}`,
      "Relatorio_Lab.xlsx",
    );
  const handleGeneratePjc = () =>
    handleDownload(
      `/download-pjc/${encodeURIComponent(
        processoTrabalhista?.numero_processo || "lab",
      )}`,
      "Parametros_PJeCalc_Lab.pjc",
    );

  // ── Conhecimento: editar / excluir ────────────────────────────────────────
  const handleRemoveLearned = useCallback(
    (item: LearnedItem) => {
      if (window.confirm(`Remover aprendizado ID ${item.id} da lista local?`)) {
        setLearnedItems((prev) => prev.filter((x) => x.id !== item.id));
        if (editingId === item.id) {
          setEditingId(null);
          setEditingText("");
        }
      }
    },
    [editingId],
  );

  const startEditLearned = useCallback((item: LearnedItem) => {
    setEditingId(item.id);
    setEditingText(item.descricao || "");
  }, []);

  const saveEditedLearned = useCallback(
    async (item: LearnedItem) => {
      try {
        await api.post("/lab/salvar", {
          aprendizado:
            item._raw || {
              id: item.id,
              tipo: item.tipo,
              descricao: item.descricao,
              base_legal: item.base_legal,
            },
          numero_processo: processoTrabalhista?.numero_processo || "lab",
          conteudo_editado: editingText,
        });
        setLearnedItems((prev) =>
          prev.map((x) =>
            x.id === item.id ? { ...x, descricao: editingText } : x,
          ),
        );
        setEditingId(null);
        setEditingText("");
      } catch {
        alert("Falha ao salvar aprendizado. Verifique o backend.");
      }
    },
    [editingText, processoTrabalhista],
  );

  // ── Drag & drop ──────────────────────────────────────────────────────────
  const allowDrop = useCallback((ev: React.DragEvent) => ev.preventDefault(), []);
  const onDropSentenca = useCallback(
    (ev: React.DragEvent) => {
      ev.preventDefault();
      const f = Array.from(ev.dataTransfer.files || []);
      if (f.length) setFile("sentenca", [...files.sentenca, ...f]);
    },
    [files.sentenca, setFile],
  );
  const onDropAmostragens = useCallback((ev: React.DragEvent) => {
    ev.preventDefault();
    const f = Array.from(ev.dataTransfer.files || []);
    if (f.length) setAmostragens((prev) => [...prev, ...f]);
  }, []);

  // ════════════════════════════════════════════════════════════════════════
  // RENDER
  // ════════════════════════════════════════════════════════════════════════
  return (
    <div className="relative w-full max-w-7xl mx-auto p-6 pb-40">
      {/* Cabeçalho */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-50">
          🧪 Laboratório de Aprendizado da Perita
        </h1>
        <p className="text-slate-400 text-sm mt-1">
          Monte o cérebro do caso anexando as peças principais. Nenhum arquivo é
          enviado automaticamente — você controla o momento da análise.
        </p>
      </div>

      {/* Guia de eficiência */}
      <div className="mb-5 rounded-xl border border-indigo-500/20 bg-slate-900/30 px-4 py-3 flex items-start gap-3">
        <div className="text-lg leading-none mt-0.5">💡</div>
        <div>
          <p className="text-sm font-semibold text-slate-100 mb-1">
            Guia de Eficiência do Aprendizado
          </p>
          <p className="text-xs text-slate-400 leading-relaxed">
            ⚡{" "}
            <span className="font-semibold text-slate-100">
              Nível 1 — Rápido (25%+)
            </span>
            : Processo + Parecer → fundamentos jurídicos e estilo da perita.
            <br />
            🔍{" "}
            <span className="font-semibold text-slate-100">
              Nível 2 — Auditoria (45%+)
            </span>
            : Processo + Parecer + Liquidação → discrepâncias entre sentença e
            cálculo da empresa.
            <br />
            📊{" "}
            <span className="font-semibold text-slate-100">
              Nível 3 — Tríade (65%+)
            </span>
            : Processo + Liquidação + Cálculo PJC → detecção automática de
            omissões de parâmetros.
            <br />
            🏆{" "}
            <span className="font-semibold text-slate-100">
              Nível 4 — Tríade de Ouro (85%+)
            </span>
            : Todos os anteriores + Manifestação → máximo aprendizado de retórica
            de combate e regras preditivas.
          </p>
        </div>
      </div>

      {/* Grid de cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {FILE_TYPES.map((ft) => {
          const Icon = ft.icon;
          const isUploaded = hasFile(files, ft.id);
          const currentSingle =
            ft.id !== "sentenca"
              ? (files[ft.id as keyof CerebroFiles] as File | null)
              : null;
          const badgeColor =
            ft.badge === "OBRIGATÓRIO"
              ? "text-blue-400 border-blue-500/30"
              : ft.badge === "RECOMENDADO"
                ? "text-amber-400 border-amber-500/30"
                : "text-slate-500 border-slate-600/30";

          return (
            <div
              key={ft.id}
              className={`relative flex flex-col rounded-xl border-2 overflow-hidden transition-all duration-200 ${
                isUploaded
                  ? "border-blue-500/60 bg-slate-800/90 shadow-lg shadow-blue-500/10"
                  : "border-slate-700 bg-slate-800/60 hover:border-slate-600"
              }`}
              onDragOver={ft.dropZone ? allowDrop : undefined}
              onDrop={ft.id === "sentenca" ? onDropSentenca : undefined}
            >
              {/* Número */}
              <div className="absolute top-2 left-3">
                <span
                  className={`text-xs font-extrabold font-mono ${
                    isUploaded ? "text-blue-400" : "text-slate-600"
                  }`}
                >
                  {ft.card}
                </span>
              </div>

              <div className="pt-7 px-4 pb-4 flex flex-col flex-1">
                <p className="text-[9px] font-bold tracking-widest uppercase text-slate-500 mb-1">
                  {ft.phase}
                </p>
                <h3
                  className={`font-bold text-sm mb-1 ${
                    isUploaded ? "text-slate-50" : "text-slate-200"
                  }`}
                >
                  {ft.name}
                </h3>
                <p className="text-[11px] text-slate-500 mb-3">{ft.hint}</p>

                {/* Sentença — múltiplos + drop zone */}
                {ft.id === "sentenca" && (
                  <div className="flex-1 space-y-2">
                    {files.sentenca.length === 0 ? (
                      <label className="flex flex-col items-center gap-1 rounded-lg border-2 border-dashed border-slate-600 bg-slate-900/40 px-3 py-4 cursor-pointer hover:border-blue-500/50 hover:bg-slate-900/60 transition-colors text-center">
                        <Icon className="w-5 h-5 text-slate-500 mb-1" />
                        <span className="text-xs text-slate-400">
                          Arraste e solte arquivos do processo
                        </span>
                        <span className="text-[10px] text-slate-500">
                          Aceita vários arquivos. Duplicados são ignorados.
                        </span>
                        <span className="mt-2 rounded-md bg-slate-700 px-3 py-1 text-xs font-medium text-slate-200">
                          Escolher arquivos
                        </span>
                        <input
                          type="file"
                          className="hidden"
                          accept="*"
                          multiple
                          onChange={(e) =>
                            setFile(
                              "sentenca",
                              Array.from(e.target.files ?? []),
                            )
                          }
                        />
                      </label>
                    ) : (
                      <div className="space-y-1">
                        {files.sentenca.slice(0, 6).map((f, i) => (
                          <div
                            key={`${f.name}-${i}`}
                            className="flex items-center gap-2 rounded-md bg-slate-900/60 px-2 py-1.5"
                          >
                            <FileText className="w-3 h-3 text-blue-400 shrink-0" />
                            <span className="text-xs text-slate-300 truncate flex-1">
                              {f.name}
                            </span>
                            <button
                              type="button"
                              className="text-slate-500 hover:text-rose-400"
                              onClick={() =>
                                setFile(
                                  "sentenca",
                                  files.sentenca.filter((_, j) => j !== i),
                                )
                              }
                            >
                              ×
                            </button>
                          </div>
                        ))}
                        {files.sentenca.length > 6 && (
                          <p className="text-[11px] text-slate-400">
                            +{files.sentenca.length - 6} arquivo(s)…
                          </p>
                        )}
                        <div className="flex gap-3 mt-1">
                          <label className="cursor-pointer text-[10px] text-blue-400 hover:text-blue-300">
                            + Adicionar mais
                            <input
                              type="file"
                              className="hidden"
                              accept="*"
                              multiple
                              onChange={(e) => {
                                const novos = Array.from(e.target.files ?? []);
                                const ex = files.sentenca.map((f) => f.name);
                                setFile("sentenca", [
                                  ...files.sentenca,
                                  ...novos.filter((f) => !ex.includes(f.name)),
                                ]);
                              }}
                            />
                          </label>
                          <button
                            type="button"
                            className="text-[10px] text-rose-400/70 hover:text-rose-400"
                            onClick={() => setFile("sentenca", [])}
                          >
                            Remover todos
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Arquivo único */}
                {ft.id !== "sentenca" && (
                  <div className="flex-1 space-y-1.5">
                    <label
                      className={`flex items-center gap-2 rounded-lg border px-3 py-2.5 cursor-pointer transition-colors ${
                        currentSingle
                          ? "border-blue-500/50 bg-blue-500/5 hover:bg-blue-500/10"
                          : "border-slate-600 bg-slate-900/40 hover:bg-slate-900/60 hover:border-slate-500"
                      }`}
                    >
                      <Icon
                        className={`w-4 h-4 shrink-0 ${
                          currentSingle ? "text-blue-400" : "text-slate-500"
                        }`}
                      />
                      <span className="text-xs text-slate-300 truncate flex-1">
                        {currentSingle?.name ?? "ESCOLHER ARQUIVO"}
                      </span>
                      {currentSingle ? (
                        <CheckCircle className="w-4 h-4 text-blue-400 shrink-0" />
                      ) : (
                        <span className="text-[10px] text-slate-500 shrink-0">
                          Selecionar
                        </span>
                      )}
                      <input
                        type="file"
                        className="hidden"
                        accept="*"
                        onChange={(e) =>
                          setFile(ft.id, e.target.files?.[0] ?? null)
                        }
                      />
                    </label>
                    {currentSingle && (
                      <button
                        type="button"
                        className="text-[10px] text-rose-400/70 hover:text-rose-400 flex items-center gap-1"
                        onClick={() => setFile(ft.id, null)}
                      >
                        <Trash2 className="w-3 h-3" /> Remover
                      </button>
                    )}
                  </div>
                )}

                {/* Badge */}
                <div className="mt-4 pt-3 border-t border-slate-700/50">
                  <span
                    className={`text-[9px] font-bold uppercase tracking-widest border rounded px-2 py-0.5 ${badgeColor}`}
                  >
                    {ft.badge}
                  </span>
                </div>
              </div>
            </div>
          );
        })}

        {/* Card + Amostragens */}
        <div
          className={`relative flex flex-col rounded-xl border-2 overflow-hidden transition-all duration-200 ${
            hasAmostragens
              ? "border-purple-500/60 bg-slate-800/90 shadow-lg shadow-purple-500/10"
              : "border-dashed border-slate-700 bg-slate-800/40 hover:border-slate-600"
          }`}
          onDragOver={allowDrop}
          onDrop={onDropAmostragens}
        >
          <div className="absolute top-2 left-3">
            <span
              className={`text-xs font-extrabold font-mono ${
                hasAmostragens ? "text-purple-400" : "text-slate-600"
              }`}
            >
              +
            </span>
          </div>
          <div className="pt-7 px-4 pb-4 flex flex-col flex-1">
            <p className="text-[9px] font-bold tracking-widest uppercase text-slate-500 mb-1">
              OPCIONAL
            </p>
            <h3
              className={`font-bold text-sm mb-1 ${
                hasAmostragens ? "text-slate-50" : "text-slate-400"
              }`}
            >
              Amostragens e Provas Adicionais
            </h3>
            <p className="text-[11px] text-slate-500 mb-1">
              Arraste aqui seu Parecer, Amostragens e Manifestações
            </p>
            <p className="text-[10px] text-slate-600 mb-3">
              Qualquer formato · múltiplos
            </p>
            <div className="flex-1 space-y-2">
              {amostragens.length === 0 ? (
                <label className="flex flex-col items-center gap-1 rounded-lg border-2 border-dashed border-slate-600 bg-slate-900/40 px-3 py-4 cursor-pointer hover:border-purple-500/50 hover:bg-slate-900/60 transition-colors text-center">
                  <span className="text-xl mb-1">📎</span>
                  <span className="text-xs text-slate-400">
                    Arraste arquivos ou clique para selecionar
                  </span>
                  <span className="mt-2 rounded-md bg-slate-700 px-3 py-1 text-xs font-medium text-slate-200">
                    Escolher arquivo(s)
                  </span>
                  <input
                    type="file"
                    className="hidden"
                    accept="*"
                    multiple
                    onChange={(e) =>
                      setAmostragens(Array.from(e.target.files ?? []))
                    }
                  />
                </label>
              ) : (
                <div className="space-y-1">
                  {amostragens.slice(0, 6).map((f, i) => (
                    <div
                      key={`${f.name}-${i}`}
                      className="flex items-center gap-2 rounded-md bg-slate-900/60 px-2 py-1.5"
                    >
                      <span className="text-xs shrink-0">📄</span>
                      <span className="text-xs text-slate-300 truncate flex-1">
                        {f.name}
                      </span>
                      <button
                        type="button"
                        className="text-slate-500 hover:text-rose-400"
                        onClick={() =>
                          setAmostragens((prev) => prev.filter((_, j) => j !== i))
                        }
                      >
                        ×
                      </button>
                    </div>
                  ))}
                  {amostragens.length > 6 && (
                    <p className="text-[11px] text-slate-400">
                      +{amostragens.length - 6} arquivo(s)…
                    </p>
                  )}
                  <div className="flex gap-3 mt-1">
                    <label className="cursor-pointer text-[10px] text-purple-400 hover:text-purple-300">
                      + Adicionar mais
                      <input
                        type="file"
                        className="hidden"
                        accept="*"
                        multiple
                        onChange={(e) => {
                          const novos = Array.from(e.target.files ?? []);
                          const ex = amostragens.map((f) => f.name);
                          setAmostragens((prev) => [
                            ...prev,
                            ...novos.filter((f) => !ex.includes(f.name)),
                          ]);
                        }}
                      />
                    </label>
                    <button
                      type="button"
                      className="text-[10px] text-rose-400/70 hover:text-rose-400"
                      onClick={() => setAmostragens([])}
                    >
                      Remover todos
                    </button>
                  </div>
                </div>
              )}
            </div>
            <div className="mt-4 pt-3 border-t border-slate-700/50">
              <span className="text-[9px] font-bold uppercase tracking-widest border rounded px-2 py-0.5 text-slate-500 border-slate-600/30">
                OPCIONAL
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Barra de eficiência */}
      <div className="mt-4 p-4 rounded-xl bg-slate-900/60 border border-slate-700">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-semibold text-slate-300">
            Previsão de Eficiência de Aprendizado
          </span>
          <span className="text-lg font-bold text-slate-200">{efficiency}%</span>
        </div>
        <div className="w-full bg-slate-800 rounded-full h-3 mb-2 overflow-hidden">
          <div
            className={`h-3 rounded-full transition-all duration-500 ease-out ${efficiencyStatus.bar}`}
            style={{ width: `${Math.max(efficiency, 1)}%` }}
          />
        </div>
        <p className="text-xs text-slate-300">{efficiencyStatus.nivel}</p>
        <p className="text-xs text-slate-400 mt-1">{efficiencyStatus.detalhe}</p>
      </div>

      {/* Painel: Conhecimento Adquirido */}
      {learnedItems.length > 0 && (
        <section className="mt-6 rounded-xl border border-slate-700 bg-slate-900/50 overflow-hidden">
          <button
            type="button"
            className="w-full flex items-center justify-between gap-2 px-4 py-3 text-left hover:bg-slate-800/50 transition-colors"
            onClick={() => setIsLearningsExpanded((v) => !v)}
          >
            <span className="font-semibold text-sm text-slate-100">
              🧠 Conhecimento Adquirido nesta Análise ({learnedItems.length})
            </span>
            {isLearningsExpanded ? (
              <ChevronUp className="w-5 h-5 text-slate-400 shrink-0" />
            ) : (
              <ChevronDown className="w-5 h-5 text-slate-400 shrink-0" />
            )}
          </button>
          {isLearningsExpanded && (
            <div className="border-t border-slate-700 p-3 space-y-2">
              {learnedItems.map((item) => {
                const nivelCls = nivelClass(item.nivel_sugerido);
                const isEditing = editingId === item.id;
                return (
                  <div
                    key={item.id}
                    className="rounded-lg border border-slate-700 bg-slate-950/40 p-3"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2 mb-2">
                          <span
                            className={`rounded px-2 py-0.5 text-[10px] font-semibold uppercase ${badgeClass(item.tipo)}`}
                          >
                            {item.tipo}
                          </span>
                          {nivelCls && (
                            <span
                              className={`rounded px-2 py-0.5 text-[10px] font-semibold uppercase ${nivelCls}`}
                            >
                              {String(item.nivel_sugerido || "").toUpperCase()}
                            </span>
                          )}
                          <span className="text-[10px] text-slate-500 font-mono">
                            {item.id}
                          </span>
                        </div>
                        {!isEditing ? (
                          <p className="text-sm text-slate-200 whitespace-pre-wrap">
                            {item.descricao}
                          </p>
                        ) : (
                          <div>
                            <textarea
                              className="w-full min-h-[100px] rounded-md border border-slate-700 bg-slate-950 p-2 text-sm text-slate-100 outline-none focus:border-indigo-500 resize-y"
                              value={editingText}
                              onChange={(e) => setEditingText(e.target.value)}
                            />
                            <div className="mt-2 flex gap-2">
                              <button
                                type="button"
                                className="rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-500"
                                onClick={() => saveEditedLearned(item)}
                              >
                                Salvar
                              </button>
                              <button
                                type="button"
                                className="rounded-md bg-slate-800 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-700"
                                onClick={() => {
                                  setEditingId(null);
                                  setEditingText("");
                                }}
                              >
                                Cancelar
                              </button>
                            </div>
                          </div>
                        )}
                        {item.base_legal && (
                          <p className="mt-2 text-xs text-slate-400">
                            <span className="font-semibold text-slate-300">
                              Base legal:
                            </span>{" "}
                            {item.base_legal}
                          </p>
                        )}
                        {item.correcao && (
                          <p className="mt-2 text-xs text-slate-400 whitespace-pre-wrap">
                            <span className="font-semibold text-slate-300">
                              Correção sugerida:
                            </span>{" "}
                            {item.correcao}
                          </p>
                        )}
                        {item._raw && (
                          <details className="mt-3">
                            <summary className="cursor-pointer text-[11px] text-slate-500 hover:text-slate-400">
                              Ver todos os campos do JSON
                            </summary>
                            <pre className="mt-2 rounded-md bg-slate-950/60 p-2 text-[11px] text-slate-400 overflow-x-auto">
                              {JSON.stringify(item._raw, null, 2)}
                            </pre>
                          </details>
                        )}
                      </div>
                      <div className="flex gap-1 shrink-0">
                        <button
                          type="button"
                          className="p-2 rounded text-slate-400 hover:text-amber-300 hover:bg-slate-800"
                          title="Editar"
                          onClick={() => startEditLearned(item)}
                        >
                          <Pencil className="w-4 h-4" />
                        </button>
                        <button
                          type="button"
                          className="p-2 rounded text-slate-400 hover:text-rose-300 hover:bg-slate-800"
                          title="Excluir"
                          onClick={() => handleRemoveLearned(item)}
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      )}

      {/* Relatório inline */}
      {processoTrabalhista && (
        <section className="mt-6 rounded-xl border border-slate-700 bg-slate-900/40 p-4">
          <div className="flex items-center justify-between gap-2 mb-3">
            <h2 className="text-sm font-semibold text-slate-50">
              Relatório de Discrepância
            </h2>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="rounded-md bg-slate-800 px-2 py-1 text-[11px] text-slate-200 hover:bg-slate-700"
                onClick={() => setIsReportModalOpen(true)}
              >
                Abrir em modal
              </button>
              <button
                type="button"
                disabled={!processoTrabalhista}
                className="rounded-md bg-slate-800 px-2 py-1 text-[11px] text-slate-200 hover:bg-slate-700 disabled:opacity-50"
                onClick={handleGeneratePjc}
              >
                Gerar PJC
              </button>
              <button
                type="button"
                disabled={!processoTrabalhista}
                className="rounded-md bg-slate-800 px-2 py-1 text-[11px] text-slate-200 hover:bg-slate-700 disabled:opacity-50"
                onClick={handleGenerateExcel}
              >
                Gerar Excel
              </button>
              <button
                type="button"
                disabled={!processoTrabalhista}
                className="rounded-md bg-emerald-700 px-2 py-1 text-[11px] text-white hover:bg-emerald-600 disabled:opacity-50"
                onClick={handleGenerateDocx}
              >
                Gerar Parecer (Word)
              </button>
            </div>
          </div>
          <div className="max-h-[480px] overflow-y-auto rounded-lg bg-slate-950/60 p-3">
            <AnalysisReport processo={processoTrabalhista} raw={data} />
          </div>
        </section>
      )}

      {/* Modal tela cheia */}
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

      {/* Barra sticky */}
      <div className="fixed bottom-0 left-0 right-0 z-40 border-t border-slate-800 bg-slate-950/95 backdrop-blur">
        <div className="max-w-7xl mx-auto px-4 py-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold text-slate-100">
              Arquivos selecionados no Laboratório
            </p>
            <p className="text-xs text-slate-500">
              Os arquivos são mantidos apenas no navegador até você disparar a
              análise. Isso preserva o controle do perito sobre o envio.
            </p>
          </div>
          <div className="flex items-center gap-2 flex-wrap justify-end">
            <div className="w-11 h-11 rounded-full border-2 border-slate-700 bg-slate-900 flex items-center justify-center text-sm font-extrabold text-slate-100 shrink-0">
              {totalFilesSelected}
            </div>
            <button
              type="button"
              onClick={handleGlobalAnalysis}
              disabled={isLoading}
              className={`inline-flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-bold text-white transition-all ${
                isLoading
                  ? "bg-blue-600 animate-pulse cursor-wait"
                  : "bg-blue-600 hover:bg-blue-500 shadow-md shadow-blue-500/20"
              }`}
            >
              {isLoading ? (
                <>
                  <BrainCircuit className="w-4 h-4 animate-spin shrink-0" />
                  <span className="font-mono text-xs truncate max-w-[140px]">
                    &gt; {currentLog || "..."}
                  </span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 shrink-0" />
                  Analisar e Gerar Relatório
                </>
              )}
            </button>
            <button
              type="button"
              onClick={handleGeneratePjc}
              disabled={!processoTrabalhista}
              className="rounded-lg bg-slate-800 px-3 py-2.5 text-xs font-semibold text-slate-200 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Gerar PJC
            </button>
            <button
              type="button"
              onClick={handleGenerateExcel}
              disabled={!processoTrabalhista}
              className="rounded-lg bg-slate-800 px-3 py-2.5 text-xs font-semibold text-slate-200 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Gerar Excel
            </button>
            <button
              type="button"
              onClick={handleGenerateDocx}
              disabled={!data}
              className="rounded-lg bg-emerald-700 px-3 py-2.5 text-xs font-semibold text-white hover:bg-emerald-600 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Gerar Parecer (Word)
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
