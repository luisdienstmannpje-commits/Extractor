import { useEffect, useMemo, useState } from "react";
import { api } from "../../services/api";
import type {
  ProcessoTrabalhista,
  Verba,
  TeseDefesa,
  ItemComparativo,
  FonteExtracao,
} from "../../types/api";

interface AnalysisReportProps {
  processo?: Partial<ProcessoTrabalhista> | null;
  raw?: any;
  /** Se definido, vira botão de navegação para a página no visualizador de PDF. */
  onNavegar?: (pagina: number) => void;
  isLoading?: boolean;
}

function PaginaOrigemBadge({
  pagina,
  onNavegar,
}: {
  pagina: number;
  onNavegar?: (p: number) => void;
}) {
  if (onNavegar) {
    return (
      <button
        type="button"
        className="mt-1 block text-left text-[11px] font-medium text-indigo-600 hover:underline"
        onClick={() => onNavegar(pagina)}
      >
        🎯 pág. {pagina}
      </button>
    );
  }
  return (
    <span className="mt-1 block text-[11px] text-slate-500">p. {pagina}</span>
  );
}

/** Trecho presente mas sem match em --- PÁGINA N --- (OCR / divergência). */
function FonteNaoAncorada() {
  return (
    <span
      className="mt-1 block text-[10px] italic text-slate-500"
      title="Trecho extraído, mas não localizado no mapa de páginas do PDF."
    >
      Fonte não ancorada no PDF
    </span>
  );
}

function FonteCampo({
  fonte,
  onNavegar,
}: {
  fonte?: FonteExtracao;
  onNavegar?: (p: number) => void;
}) {
  if (!fonte) return null;
  const conf = typeof fonte.confianca === "number" ? fonte.confianca : null;
  const confLabel =
    conf == null ? null : conf >= 0.85 ? "alta" : conf >= 0.6 ? "média" : "baixa";
  const confClass =
    conf == null
      ? ""
      : conf >= 0.85
        ? "bg-emerald-100 text-emerald-800 border-emerald-200"
        : conf >= 0.6
          ? "bg-amber-100 text-amber-800 border-amber-200"
          : "bg-rose-100 text-rose-800 border-rose-200";
  if (fonte.pagina_origem != null) {
    return (
      <div className="mt-1 flex items-center gap-2">
        <PaginaOrigemBadge pagina={fonte.pagina_origem} onNavegar={onNavegar} />
        {confLabel ? (
          <span
            className={`rounded-full border px-2 py-0.5 text-[9px] font-medium ${confClass}`}
            title={`Confianca da inferencia: ${Math.round((conf || 0) * 100)}%`}
          >
            conf. {confLabel}
          </span>
        ) : null}
      </div>
    );
  }
  if (fonte.trecho?.trim()) {
    return <FonteNaoAncorada />;
  }
  return null;
}

export function AnalysisReport({
  processo,
  raw,
  onNavegar,
  isLoading = false,
}: AnalysisReportProps) {
  // Debug visual para inspeção de estrutura
  // eslint-disable-next-line no-console
  console.log("DADOS RECEBIDOS:", processo);

  // Fallback global quando ainda não há nada processado
  if (!processo && !raw && !isLoading) {
    return (
      <div className="p-10 text-white text-sm">
        Aguardando processamento...
      </div>
    );
  }

  if (!processo && !isLoading) {
    return (
      <p className="text-xs text-slate-500 max-w-4xl w-full mx-auto">
        Aguardando dados válidos para o relatório...
      </p>
    );
  }

  const loadingSkeleton = (
    <span className="inline-block h-4 w-32 bg-slate-800 animate-pulse rounded" />
  );

  const raiox = raw?.raiox ?? raw?.data?.raiox ?? {};
  const rawData = raw?.data ?? {};

  const numero_processo_base = processo?.numero_processo ?? null;
  const reclamanteBase = processo?.reclamante ?? null;
  const reclamadaBase = processo?.reclamada ?? null;
  const varaBase = processo?.vara_trabalho ?? null;
  const data_sentenca = processo?.data_sentenca ?? null;
  const data_ajuizamento = processo?.data_ajuizamento ?? null;
  const data_admissao = processo?.data_admissao ?? null;
  const data_demissao = processo?.data_demissao ?? null;
  const salario_base = processo?.salario_base ?? null;

  // Fallback de verbas: se o objeto principal vier vazio, tenta raw.data.verbas_deferidas
  const verbasFromProcess: Verba[] = (processo?.verbas_deferidas as Verba[] | undefined) ?? [];
  const verbasFromRaw: Verba[] = (rawData as any)?.verbas_deferidas ?? [];
  const verbas: Verba[] =
    (verbasFromProcess && verbasFromProcess.length > 0
      ? verbasFromProcess
      : verbasFromRaw) || [];

  // Alertas podem vir como strings simples ou objetos enriquecidos em alguns fluxos
  const alertasBrutos: any[] = (processo as any)?.alertas_juridicos ?? [];

  // Normalização ultra-defensiva do memorial / parecer vindo da IA
  const memorialBruto =
    raw?.memorial_juridico ?? raw?.explicacoes ?? (processo as any)?.memorial_juridico;
  let memorialTexto = "";

  if (typeof memorialBruto === "string") {
    memorialTexto = memorialBruto;
  } else if (Array.isArray(memorialBruto)) {
    memorialTexto = memorialBruto
      .map(
        (m: any) =>
          m?.descricao || m?.titulo || m?.explicacao || JSON.stringify(m),
      )
      .filter(Boolean)
      .join("\n\n");
  } else if (memorialBruto && typeof memorialBruto === "object") {
    memorialTexto =
      memorialBruto.descricao ||
      memorialBruto.titulo ||
      memorialBruto.explicacao ||
      JSON.stringify(memorialBruto);
  }

  const formatDate = (value?: string | null) => {
    if (!value) return "Pendente de validação";
    const raw = String(value).trim();
    const br = raw.match(/^(\d{1,2})[\/.-](\d{1,2})[\/.-](\d{4})$/);
    try {
      if (br) {
        const day = Number(br[1]);
        const month = Number(br[2]);
        const year = Number(br[3]);
        const d = new Date(year, month - 1, day);
        if (
          d.getFullYear() !== year ||
          d.getMonth() !== month - 1 ||
          d.getDate() !== day
        ) {
          return "Pendente de validação";
        }
        return d.toLocaleDateString("pt-BR");
      }

      const d = new Date(raw);
      if (Number.isNaN(d.getTime())) return "Pendente de validação";
      return d.toLocaleDateString("pt-BR");
    } catch {
      return "Pendente de validação";
    }
  };

  const formatCurrency = (value?: string | null) => {
    if (!value) return "Pendente de validação";
    try {
      const numeric = Number(
        String(value)
          .replace(/\./g, "")
          .replace(",", ".")
          .replace(/[^\d.-]/g, ""),
      );
      if (!Number.isFinite(numeric)) return "Pendente de validação";
      return numeric.toLocaleString("pt-BR", {
        style: "currency",
        currency: "BRL",
      });
    } catch {
      return "Pendente de validação";
    }
  };

  const isDeferida = (verba: Verba) =>
    (verba?.status_final || "").toLowerCase().includes("deferida");

  // Numero de processo: tenta corrigir a partir do raiox quando vem "desconhecido"
  const numero_processo =
    !numero_processo_base || numero_processo_base.toLowerCase() === "desconhecido"
      ? raiox?.numero_processo ?? numero_processo_base
      : numero_processo_base;

  const isNumeroDesconhecido =
    (numero_processo ?? "").toLowerCase() === "desconhecido";

  // Tentativa de enriquecimento usando o "raiox" bruto quando campos vêm como "desconhecido"
  const reclamante =
    !reclamanteBase || reclamanteBase.toLowerCase() === "desconhecido"
      ? raiox?.reclamante ?? reclamanteBase
      : reclamanteBase;
  const reclamada =
    !reclamadaBase || reclamadaBase.toLowerCase() === "desconhecido"
      ? raiox?.reclamada ?? reclamadaBase
      : reclamadaBase;
  const vara_trabalho =
    !varaBase || varaBase.toLowerCase() === "desconhecido"
      ? raiox?.vara_trabalho ?? varaBase
      : varaBase;

  const safeVerbas: Verba[] = verbas ?? [];
  const safeAlertas: any[] = alertasBrutos ?? [];

  const isPeticaoInicial =
    (raw as { doc_type?: string })?.doc_type === "peticao_inicial" ||
    processo?._meta_doc_type === "peticao_inicial";

  const isContestacao =
    (raw as { doc_type?: string })?.doc_type === "contestacao" ||
    processo?._meta_doc_type === "contestacao";

  const tesesDefesa: TeseDefesa[] =
    ((processo?.teses_defesa as TeseDefesa[] | undefined) &&
    (processo?.teses_defesa as TeseDefesa[]).length > 0
      ? (processo?.teses_defesa as TeseDefesa[])
      : (rawData as { teses_defesa?: TeseDefesa[] }).teses_defesa) ?? [];

  const quadroComparativo: ItemComparativo[] =
    ((processo?.quadro_comparativo as ItemComparativo[] | undefined) &&
    (processo?.quadro_comparativo as ItemComparativo[]).length > 0
      ? (processo?.quadro_comparativo as ItemComparativo[])
      : (rawData as { quadro_comparativo?: ItemComparativo[] })
          .quadro_comparativo) ?? [];

  const fontesExtracao: FonteExtracao[] =
    ((processo?.fontes_extracao as FonteExtracao[] | undefined) &&
    (processo?.fontes_extracao as FonteExtracao[]).length > 0
      ? (processo?.fontes_extracao as FonteExtracao[])
      : ((rawData as { fontes_extracao?: FonteExtracao[] }).fontes_extracao ?? [])) ||
    [];

  const getFonteCampo = (campo: string): FonteExtracao | undefined =>
    fontesExtracao.find((f) => f?.campo === campo);

  const docTypeNorm = (
    (raw as { doc_type?: string })?.doc_type ||
    processo?._meta_doc_type ||
    ""
  )
    .toString()
    .toLowerCase();

  const [downloadingPjc, setDownloadingPjc] = useState(false);
  const [downloadingExcel, setDownloadingExcel] = useState(false);
  const [alertaFiltro, setAlertaFiltro] = useState<"todos" | "alta">(() => {
    try {
      const saved = window.localStorage.getItem("analysis_alerta_filtro");
      return saved === "alta" ? "alta" : "todos";
    } catch {
      return "todos";
    }
  });
  const [alertasExpandidos, setAlertasExpandidos] = useState<Record<string, boolean>>(
    () => {
      try {
        const saved = window.localStorage.getItem("analysis_alertas_expandidos");
        if (!saved) return {};
        const parsed = JSON.parse(saved) as Record<string, boolean>;
        return parsed && typeof parsed === "object" ? parsed : {};
      } catch {
        return {};
      }
    },
  );

  const alertasComIndice = safeAlertas.map((alerta, idx) => ({ alerta, idx }));
  const alertasAltaConfianca = alertasComIndice.filter(({ idx }) => {
    const f = getFonteCampo(`alertas_juridicos[${idx}]`);
    return typeof f?.confianca === "number" && f.confianca >= 0.85;
  });
  const alertasVisiveis =
    alertaFiltro === "alta" ? alertasAltaConfianca : alertasComIndice;

  useEffect(() => {
    try {
      window.localStorage.setItem("analysis_alerta_filtro", alertaFiltro);
    } catch {
      // no-op: ambiente sem localStorage
    }
  }, [alertaFiltro]);

  useEffect(() => {
    try {
      window.localStorage.setItem(
        "analysis_alertas_expandidos",
        JSON.stringify(alertasExpandidos),
      );
    } catch {
      // no-op: ambiente sem localStorage
    }
  }, [alertasExpandidos]);

  const alertasMapeados = useMemo(
    () =>
      alertasVisiveis.map(({ alerta, idx }) => {
        const key =
          typeof alerta === "object" && alerta?.id
            ? String(alerta.id)
            : `${idx}:${typeof alerta === "string" ? alerta : JSON.stringify(alerta)}`;
        return { alerta, idx, key };
      }),
    [alertasVisiveis],
  );

  const handleDownloadPjc = async () => {
    if (!processo) return;
    try {
      setDownloadingPjc(true);
      const response = await api.post("/api/export/pjc", processo, {
        responseType: "blob",
      });

      const blob = new Blob([response.data], { type: "application/octet-stream" });
      const url = window.URL.createObjectURL(blob);

      const contentDisposition =
        (response.headers as any)["content-disposition"] ??
        (response.headers as any)["Content-Disposition"];

      let filename = "manifestacao.pjc";
      if (typeof contentDisposition === "string") {
        const match = contentDisposition.match(/filename="?([^"]+)"?/i);
        if (match && match[1]) {
          filename = match[1];
        }
      }

      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error("Erro ao gerar PJC:", error);
    } finally {
      setDownloadingPjc(false);
    }
  };

  const handleDownloadExcel = async () => {
    if (!processo) return;
    try {
      setDownloadingExcel(true);
      const response = await api.post("/api/export/excel", processo, {
        responseType: "blob",
      });

      const blob = new Blob([response.data], {
        type:
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      });
      const url = window.URL.createObjectURL(blob);

      const cnjSafe =
        (numero_processo && String(numero_processo).replace(/[^\d]/g, "")) ||
        "sem_numero";

      const fallbackName = `Auditoria_Cálculo_${cnjSafe}.xlsx`;

      const contentDisposition =
        (response.headers as any)["content-disposition"] ??
        (response.headers as any)["Content-Disposition"];

      let filename = fallbackName;
      if (typeof contentDisposition === "string") {
        const match = contentDisposition.match(/filename="?([^"]+)"?/i);
        if (match && match[1]) {
          filename = match[1];
        }
      }

      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error("Erro ao gerar Excel:", error);
    } finally {
      setDownloadingExcel(false);
    }
  };

  return (
    <div className="space-y-6 text-slate-900 max-w-4xl w-full mx-auto">
      {/* Header de identificação */}
      <section className="rounded-xl border border-slate-300 bg-slate-50 p-4 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-[11px] font-medium uppercase tracking-wide text-slate-500">
              Processo trabalhista
            </p>
            <p className="text-sm font-semibold text-slate-900">
              {numero_processo || (isLoading ? loadingSkeleton : "Número de processo não identificado")}
            </p>
            <FonteCampo fonte={getFonteCampo("numero_processo")} onNavegar={onNavegar} />
            <p className="mt-1 text-xs text-slate-600">
              {vara_trabalho || (isLoading ? loadingSkeleton : "Vara não informada")}
            </p>
          </div>
          <div className="text-right text-xs text-slate-700">
            <p>
              <span className="text-slate-500">Reclamante: </span>
              <span className="font-medium text-slate-900">
                {reclamante || (isLoading ? loadingSkeleton : "Não identificada")}
              </span>
            </p>
            <div className="flex justify-end">
              <FonteCampo fonte={getFonteCampo("reclamante")} onNavegar={onNavegar} />
            </div>
            <p>
              <span className="text-slate-500">Reclamada: </span>
              <span className="font-medium text-slate-900">
                {reclamada || (isLoading ? loadingSkeleton : "Não identificada")}
              </span>
            </p>
            <div className="flex justify-end">
              <FonteCampo fonte={getFonteCampo("reclamada")} onNavegar={onNavegar} />
            </div>
          </div>
        </div>

        <div className="mt-3 grid gap-3 text-[11px] text-slate-700 sm:grid-cols-3">
          <div>
            <p className="text-slate-500">Data da sentença</p>
            <p className="font-medium text-slate-900">
              {data_sentenca || !isLoading ? formatDate(data_sentenca) : loadingSkeleton}
            </p>
            <FonteCampo fonte={getFonteCampo("data_sentenca")} onNavegar={onNavegar} />
          </div>
          <div>
            <p className="text-slate-500">Ajuizamento</p>
            <p className="font-medium text-slate-900">
              {data_ajuizamento || !isLoading ? formatDate(data_ajuizamento) : loadingSkeleton}
            </p>
            <FonteCampo fonte={getFonteCampo("data_ajuizamento")} onNavegar={onNavegar} />
          </div>
          <div>
            <p className="text-slate-500">Período contratual</p>
            <p className="font-medium text-slate-900">
              {data_admissao || data_demissao || !isLoading ? (
                <>
                  {formatDate(data_admissao)} ➝ {formatDate(data_demissao)}
                </>
              ) : (
                loadingSkeleton
              )}
            </p>
            <FonteCampo fonte={getFonteCampo("data_admissao")} onNavegar={onNavegar} />
            <FonteCampo fonte={getFonteCampo("data_demissao")} onNavegar={onNavegar} />
          </div>
          <div>
            <p className="text-slate-500">Salário base</p>
            <p className="font-medium text-slate-900">
              {salario_base || !isLoading ? formatCurrency(salario_base) : loadingSkeleton}
            </p>
            <FonteCampo fonte={getFonteCampo("salario_base")} onNavegar={onNavegar} />
          </div>
        </div>
      </section>

      {isNumeroDesconhecido && (
        <section className="rounded-xl border border-amber-500/60 bg-amber-50 p-3 text-[11px] text-amber-900">
          <p className="font-semibold">
            Aviso: Número de processo não identificado com precisão.
          </p>
          <p className="mt-0.5">
            Para melhorar a identificação, considere enviar também a{" "}
            <span className="font-medium">capa do processo</span> no
            Laboratório.
          </p>
        </section>
      )}

      {/* Memorial de Análise da IA / Parecer */}
      {memorialBruto && memorialTexto && (
        <section className="rounded-xl border border-slate-300 bg-white px-6 py-5 shadow-sm">
          <p className="text-[11px] font-medium uppercase tracking-wide text-slate-600 mb-2">
            {isContestacao
              ? "Memorial — teses de defesa"
              : "Memorial de Análise da IA"}
          </p>
          <p className="text-[11px] text-slate-500 mb-3">
            {isContestacao
              ? "Resumo dos argumentos de defesa extraídos da contestação. Use como apoio à análise de risco."
              : "Sumário redigido pela IA com base nos documentos enviados. Use como referência de auditoria, não como substituto do laudo oficial."}
          </p>
          <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
            <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-800 font-serif">
              {memorialTexto}
            </p>
          </div>
        </section>
      )}

      {quadroComparativo.length > 0 && (
        <section className="rounded-xl border border-indigo-200 bg-indigo-50/30 p-4 shadow-sm">
          <div className="mb-4">
            <p className="text-[11px] font-medium uppercase tracking-wide text-indigo-900">
              Dossiê: cruzamento de teses
            </p>
            <p className="text-xs text-indigo-900/85">
              Pedido (inicial) · Defesa (contestação) · Decisão —{" "}
              {docTypeNorm === "completo"
                ? "documento composto"
                : `contexto ${docTypeNorm || "misto"}`}
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-xs text-left border-collapse text-slate-900">
              <thead>
                <tr className="text-[10px] uppercase tracking-wide text-indigo-800/80 border-b-2 border-indigo-200">
                  <th className="px-3 py-2 font-medium w-[14%]">Verba / Pedido</th>
                  <th className="px-3 py-2 font-medium w-[22%] border-l border-indigo-100">
                    Petição
                  </th>
                  <th className="px-3 py-2 font-medium w-[22%] border-l border-indigo-100">
                    Contestação
                  </th>
                  <th className="px-3 py-2 font-medium w-[22%] border-l border-indigo-100">
                    Decisão
                  </th>
                </tr>
              </thead>
              <tbody>
                {quadroComparativo.map((item, i) => {
                  const st = (item.status_final || "").toLowerCase();
                  const deferida =
                    st.includes("defer") && !st.includes("indefer");
                  return (
                    <tr
                      key={`${item.verba_alvo}-${i}`}
                      className="border-b border-indigo-100 hover:bg-white/80 transition-colors"
                    >
                      <td className="px-3 py-3 align-top font-semibold text-slate-900">
                        {item.verba_alvo}
                        {item.status_final ? (
                          <span
                            className={`mt-1 inline-block px-2 py-0.5 rounded text-[9px] font-semibold ${
                              deferida
                                ? "bg-emerald-100 text-emerald-800"
                                : "bg-slate-200 text-slate-700"
                            }`}
                          >
                            {item.status_final}
                          </span>
                        ) : null}
                      </td>
                      <td className="px-3 py-3 align-top text-slate-700 border-l border-indigo-50 bg-sky-50/30">
                        {item.resumo_pedido || "—"}
                      </td>
                      <td className="px-3 py-3 align-top text-slate-700 border-l border-indigo-50 bg-orange-50/25">
                        {item.resumo_defesa || "—"}
                      </td>
                      <td className="px-3 py-3 align-top text-slate-700 border-l border-indigo-50 bg-emerald-50/25">
                        {item.resumo_decisao || "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-[10px] text-indigo-900/70">
            Resumo gerado por IA a partir dos documentos enviados; conferir sempre
            com o PDF.
          </p>
        </section>
      )}

      {isContestacao && tesesDefesa.length > 0 && (
        <section className="rounded-xl border border-orange-200 bg-orange-50/40 p-4 shadow-sm">
          <div className="flex items-center justify-between gap-2 mb-4">
            <div>
              <p className="text-[11px] font-medium uppercase tracking-wide text-orange-800">
                Teses de defesa (contestação)
              </p>
              <p className="text-xs text-orange-800/90">
                Argumentos da reclamada em relação aos pedidos tratados na peça.
              </p>
            </div>
            <span className="rounded-full bg-orange-100 px-2 py-0.5 text-[11px] text-orange-900 border border-orange-200">
              {tesesDefesa.length} tese(s)
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-xs text-left text-slate-900">
              <thead>
                <tr className="text-[10px] uppercase tracking-wide text-orange-700/80 border-b border-orange-200">
                  <th className="px-2 py-2 font-medium">Pedido alvo</th>
                  <th className="px-2 py-2 font-medium">Tese principal</th>
                  <th className="px-2 py-2 font-medium">Fundamentação</th>
                </tr>
              </thead>
              <tbody>
                {tesesDefesa.map((tese, i) => (
                  <tr
                    key={`${tese.verba_alvo}-${tese.tese_principal}-${i}`}
                    className="border-b border-orange-100 hover:bg-orange-100/50 align-top"
                  >
                    <td className="px-2 py-3 font-semibold text-orange-950">
                      {tese.verba_alvo}
                      {tese.pagina_origem != null ? (
                        <PaginaOrigemBadge
                          pagina={tese.pagina_origem}
                          onNavegar={onNavegar}
                        />
                      ) : tese.trecho_fundamentacao?.trim() ? (
                        <FonteNaoAncorada />
                      ) : null}
                    </td>
                    <td className="px-2 py-3 text-orange-950">
                      {tese.incontroversa ? (
                        <span className="inline-block rounded bg-red-100 text-red-800 text-[9px] px-1.5 py-0.5 mr-2 font-medium">
                          Incontroverso
                        </span>
                      ) : null}
                      {tese.tese_principal}
                    </td>
                    <td className="px-2 py-3 text-orange-900/90 italic text-[11px]">
                      {tese.trecho_fundamentacao
                        ? `“${tese.trecho_fundamentacao}”`
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Pedidos identificados na Inicial */}
      {safeVerbas.length > 0 && (
        <section className="rounded-xl border border-slate-300 bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between gap-2">
            <div>
              <p className="text-[11px] font-medium uppercase tracking-wide text-slate-600">
                Pedidos identificados na Inicial
              </p>
              <p className="text-xs text-slate-600">
                Lista de verbas que, na petição inicial, representam os pedidos
                formulados pela parte reclamante.
              </p>
            </div>
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-700 border border-slate-300">
              {safeVerbas.length} pedido(s)
            </span>
          </div>

          <div className="mt-3 overflow-x-auto text-xs text-slate-900">
            <table className="min-w-full border border-slate-200 text-left">
              <thead className="bg-slate-50">
                <tr className="text-[11px] uppercase tracking-wide text-slate-500">
                  <th className="px-2 py-1 border-b border-slate-200 font-medium">
                    Pedido / Verba
                  </th>
                  <th className="px-2 py-1 border-b border-slate-200 font-medium">
                    Período alegado
                  </th>
                  <th className="px-2 py-1 border-b border-slate-200 font-medium">
                    Observações
                  </th>
                </tr>
              </thead>
              <tbody>
                {safeVerbas.map((verba) => (
                  <tr key={verba.nome} className="align-top">
                    <td className="px-2 py-1 border-b border-slate-100">
                      <span className="font-semibold">{verba.nome}</span>
                      {verba.pagina_origem != null ? (
                        <PaginaOrigemBadge
                          pagina={verba.pagina_origem}
                          onNavegar={onNavegar}
                        />
                      ) : verba.trecho_fundamentacao?.trim() ? (
                        <FonteNaoAncorada />
                      ) : null}
                    </td>
                    <td className="px-2 py-1 border-b border-slate-100">
                      {verba.periodo ? (
                        <span>{verba.periodo}</span>
                      ) : (
                        <span className="text-slate-400">
                          Não identificado no documento atual
                        </span>
                      )}
                    </td>
                    <td className="px-2 py-1 border-b border-slate-100">
                      {verba.observacoes ? (
                        <span>{verba.observacoes}</span>
                      ) : (
                        <span className="text-slate-400">
                          Não identificado no documento atual
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Ações de download: PJC só após sentença/liquidação; Excel também para pedidos da inicial */}
      <section className="rounded-xl border border-slate-300 bg-slate-50 px-4 py-3 shadow-sm flex flex-wrap items-center justify-end gap-3">
        {!isPeticaoInicial && !isContestacao ? (
          <button
            type="button"
            onClick={handleDownloadPjc}
            disabled={downloadingPjc}
            className="inline-flex items-center gap-2 rounded-md bg-slate-800 px-3 py-1.5 text-xs font-medium text-white shadow-sm hover:bg-slate-900 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {downloadingPjc && (
              <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-white/70 border-t-transparent" />
            )}
            <span>Gerar PJC (PJeCalc)</span>
          </button>
        ) : null}

        <button
          type="button"
          onClick={handleDownloadExcel}
          disabled={downloadingExcel}
          className="inline-flex items-center gap-2 rounded-md bg-slate-700 px-3 py-1.5 text-xs font-medium text-white shadow-sm hover:bg-slate-800 disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {downloadingExcel && (
            <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-white/70 border-t-transparent" />
          )}
          <span>
            {isPeticaoInicial
              ? "Exportar pedidos (Excel)"
              : isContestacao
                ? "Exportar teses (Excel)"
                : "Gerar Excel de Auditoria"}
          </span>
        </button>
      </section>

      {/* Quadro de Verbas Deferidas (omitir no fluxo contestação — sem condenação) */}
      {!isContestacao ? (
      <section className="rounded-xl border border-slate-300 bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between gap-2">
          <div>
            <p className="text-[11px] font-medium uppercase tracking-wide text-slate-600">
              Quadro de verbas deferidas
            </p>
            <p className="text-xs text-slate-600">
              Comparativo de status e reflexos extraídos da sentença.
            </p>
          </div>
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-700 border border-slate-300">
            {safeVerbas.length} verba(s)
          </span>
        </div>

        {!safeVerbas.length ? (
          <p className="mt-3 text-xs text-slate-600">
            A IA identificou o mérito, mas não conseguiu listar parcelas
            individuais. Verifique o Memorial de Análise abaixo.
          </p>
        ) : (
          <div className="mt-3 overflow-x-auto">
            <table className="min-w-full border-separate border-spacing-y-1 text-xs">
              <thead>
                <tr className="text-left text-[11px] uppercase tracking-wide text-slate-400">
                  <th className="px-2 py-1 font-medium">Verba</th>
                  <th className="px-2 py-1 font-medium">Status</th>
                  <th className="px-2 py-1 font-medium">Reflexos</th>
                  <th className="px-2 py-1 font-medium">Observações</th>
                </tr>
              </thead>
              <tbody>
                {safeVerbas.map((verba) => {
                  const deferida = isDeferida(verba);
                  return (
                    <tr key={verba.nome} className="rounded-lg bg-slate-50 text-slate-900">
                      <td className="rounded-l-lg px-2 py-2 align-top">
                        <div className="font-medium">{verba.nome}</div>
                        {verba.periodo && (
                          <div className="mt-0.5 text-[11px] text-slate-400">
                            Período: {verba.periodo}
                          </div>
                        )}
                        {verba.pagina_origem != null ? (
                          <PaginaOrigemBadge
                            pagina={verba.pagina_origem}
                            onNavegar={onNavegar}
                          />
                        ) : verba.trecho_fundamentacao?.trim() ? (
                          <FonteNaoAncorada />
                        ) : null}
                        {verba.trecho_fundamentacao ? (
                          <p className="mt-1 text-[10px] leading-snug text-slate-600 border-l-2 border-slate-200 pl-2">
                            {verba.trecho_fundamentacao}
                          </p>
                        ) : null}
                      </td>
                      <td className="px-2 py-2 align-top">
                        <span
                          className={[
                            "inline-flex rounded-full px-2 py-0.5 text-[10px] font-medium",
                            deferida
                              ? "bg-emerald-500/10 text-emerald-300 border border-emerald-500/40"
                              : "bg-rose-500/10 text-rose-300 border border-rose-500/40",
                          ].join(" ")}
                        >
                          {verba.status_final}
                        </span>
                      </td>
                      <td className="px-2 py-2 align-top">
                        {verba.reflexos?.length === 0 ? (
                          <span className="text-[11px] text-slate-500">
                            Nenhum reflexo mapeado
                          </span>
                        ) : (
                          <div className="flex flex-wrap gap-1">
                            {verba.reflexos?.map((ref) => (
                              <span
                                key={ref}
                                className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] text-slate-800 border border-slate-300"
                              >
                                {ref}
                              </span>
                            ))}
                          </div>
                        )}
                      </td>
                      <td className="rounded-r-lg px-2 py-2 align-top">
                        {verba.observacoes ? (
                          <p className="text-[11px] text-slate-700">
                            {verba.observacoes}
                          </p>
                        ) : (
                          <span className="text-[11px] text-slate-400">
                            Não identificado no documento atual
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
      ) : null}

      {/* Painel de alertas jurídicos */}
      <section className="rounded-xl border border-slate-300 bg-white p-4 shadow-sm">
        <div className="mb-2 flex items-center justify-between gap-2">
          <div>
            <p className="text-[11px] font-medium uppercase tracking-wide text-slate-600">
              Alertas jurídicos
            </p>
            <p className="text-xs text-slate-600">
              Pontos de atenção identificados pelo motor jurídico.
            </p>
          </div>
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-700 border border-slate-300">
            {safeAlertas.length} alerta(s)
          </span>
        </div>
        {safeAlertas.length > 0 ? (
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => setAlertaFiltro("todos")}
              className={[
                "rounded-full border px-2 py-0.5 text-[10px] font-medium",
                alertaFiltro === "todos"
                  ? "border-slate-400 bg-slate-100 text-slate-800"
                  : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50",
              ].join(" ")}
            >
              Todos ({safeAlertas.length})
            </button>
            <button
              type="button"
              onClick={() => setAlertaFiltro("alta")}
              className={[
                "rounded-full border px-2 py-0.5 text-[10px] font-medium",
                alertaFiltro === "alta"
                  ? "border-emerald-300 bg-emerald-100 text-emerald-800"
                  : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50",
              ].join(" ")}
              title="Mostra apenas alertas com fonte de alta confiança."
            >
              Somente conf. alta ({alertasAltaConfianca.length})
            </button>
            <button
              type="button"
              onClick={() =>
                setAlertasExpandidos((prev) => {
                  const next = { ...prev };
                  alertasMapeados.forEach(({ key }) => {
                    next[key] = true;
                  });
                  return next;
                })
              }
              className="rounded-full border border-slate-200 bg-white px-2 py-0.5 text-[10px] font-medium text-slate-600 hover:bg-slate-50"
              title="Expande todos os alertas visíveis no filtro atual."
            >
              Expandir todos
            </button>
            <button
              type="button"
              onClick={() =>
                setAlertasExpandidos((prev) => {
                  const next = { ...prev };
                  alertasMapeados.forEach(({ key }) => {
                    next[key] = false;
                  });
                  return next;
                })
              }
              className="rounded-full border border-slate-200 bg-white px-2 py-0.5 text-[10px] font-medium text-slate-600 hover:bg-slate-50"
              title="Recolhe todos os alertas visíveis no filtro atual."
            >
              Recolher todos
            </button>
          </div>
        ) : null}

        {safeAlertas.length === 0 ? (
          <p className="mt-2 text-xs text-emerald-700">
            {isContestacao
              ? "Nenhum alerta do motor de sentença (fluxo contestação — motor não aplicado)."
              : "Nenhum alerta crítico identificado. Liquidação aparentemente alinhada com a sentença."}
          </p>
        ) : alertasVisiveis.length === 0 ? (
          <p className="mt-2 text-xs text-slate-600">
            Nenhum alerta com fonte de alta confiança neste relatório.
          </p>
        ) : (
          <div className="mt-3 space-y-2 text-xs">
            {alertasMapeados.map(({ alerta, idx, key }) => {
              const expandido = alertasExpandidos[key] ?? true;
              return (
              <div
                key={key}
                className="mb-4 p-4 bg-amber-50 border-l-4 border-amber-500 rounded-r-lg shadow-sm"
              >
                <div className="flex items-start justify-between gap-2">
                  <h4 className="font-bold text-amber-900 text-sm">
                    {typeof alerta === "object"
                      ? alerta.titulo || "Alerta de Auditoria"
                      : "Ponto de atenção"}
                  </h4>
                  <button
                    type="button"
                    onClick={() =>
                      setAlertasExpandidos((prev) => ({
                        ...prev,
                        [key]: !expandido,
                      }))
                    }
                    className="rounded border border-amber-300 bg-white px-2 py-0.5 text-[10px] font-medium text-amber-800 hover:bg-amber-50"
                  >
                    {expandido ? "Recolher" : "Expandir"}
                  </button>
                </div>

                {expandido ? (
                  <>
                    {/* Descrição segura */}
                    <p className="text-xs text-amber-800 mt-1 leading-relaxed">
                      {typeof alerta === "object"
                        ? alerta.descricao || alerta.mensagem || ""
                        : alerta}
                    </p>
                    <FonteCampo
                      fonte={getFonteCampo(`alertas_juridicos[${idx}]`)}
                      onNavegar={onNavegar}
                    />

                    {/* Base Legal segura */}
                    {alerta?.base_legal && (
                      <div className="mt-2 pt-2 border-t border-amber-200">
                        <span className="text-[10px] font-semibold text-amber-600 uppercase tracking-wider">
                          Fundamento Legal:
                        </span>
                        <p className="text-[11px] text-amber-700 italic">
                          {alerta.base_legal}
                        </p>
                      </div>
                    )}
                  </>
                ) : null}
              </div>
            );
            })}
          </div>
        )}
      </section>
    </div>
  );
}

