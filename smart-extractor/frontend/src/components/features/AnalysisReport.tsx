import { useState } from "react";
import { api } from "../../services/api";
import type { ProcessoTrabalhista, Verba } from "../../types/api";

interface AnalysisReportProps {
  processo?: ProcessoTrabalhista | null;
  raw?: any;
}

export function AnalysisReport({ processo, raw }: AnalysisReportProps) {
  // Debug visual para inspeção de estrutura
  // eslint-disable-next-line no-console
  console.log("DADOS RECEBIDOS:", processo);

  // Fallback global quando ainda não há nada processado
  if (!processo && !raw) {
    return (
      <div className="p-10 text-white text-sm">
        Aguardando processamento...
      </div>
    );
  }

  if (!processo) {
    return (
      <p className="text-xs text-slate-500 max-w-4xl w-full mx-auto">
        Aguardando dados válidos para o relatório...
      </p>
    );
  }

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
  const verbasFromProcess: Verba[] = processo?.verbas_deferidas ?? [];
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
    try {
      const d = new Date(value);
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

  const [downloadingPjc, setDownloadingPjc] = useState(false);
  const [downloadingExcel, setDownloadingExcel] = useState(false);

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
              {numero_processo || "Número de processo não identificado"}
            </p>
            <p className="mt-1 text-xs text-slate-600">
              {vara_trabalho || "Vara não informada"}
            </p>
          </div>
          <div className="text-right text-xs text-slate-700">
            <p>
              <span className="text-slate-500">Reclamante: </span>
              <span className="font-medium text-slate-900">
                {reclamante || "Não identificada"}
              </span>
            </p>
            <p>
              <span className="text-slate-500">Reclamada: </span>
              <span className="font-medium text-slate-900">
                {reclamada || "Não identificada"}
              </span>
            </p>
          </div>
        </div>

        <div className="mt-3 grid gap-3 text-[11px] text-slate-700 sm:grid-cols-3">
          <div>
            <p className="text-slate-500">Data da sentença</p>
            <p className="font-medium text-slate-900">
              {formatDate(data_sentenca)}
            </p>
          </div>
          <div>
            <p className="text-slate-500">Ajuizamento</p>
            <p className="font-medium text-slate-900">
              {formatDate(data_ajuizamento)}
            </p>
          </div>
          <div>
            <p className="text-slate-500">Período contratual</p>
            <p className="font-medium text-slate-900">
              {formatDate(data_admissao)} ➝ {formatDate(data_demissao)}
            </p>
          </div>
          <div>
            <p className="text-slate-500">Salário base</p>
            <p className="font-medium text-slate-900">
              {formatCurrency(salario_base)}
            </p>
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
            Memorial de Análise da IA
          </p>
          <p className="text-[11px] text-slate-500 mb-3">
            Sumário redigido pela IA com base nos documentos enviados. Use como
            referência de auditoria, não como substituto do laudo oficial.
          </p>
          <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
            <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-800 font-serif">
              {memorialTexto}
            </p>
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

      {/* Ações de download dos artefatos de cálculo */}
      <section className="rounded-xl border border-slate-300 bg-slate-50 px-4 py-3 shadow-sm flex flex-wrap items-center justify-end gap-3">
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

        <button
          type="button"
          onClick={handleDownloadExcel}
          disabled={downloadingExcel}
          className="inline-flex items-center gap-2 rounded-md bg-slate-700 px-3 py-1.5 text-xs font-medium text-white shadow-sm hover:bg-slate-800 disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {downloadingExcel && (
            <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-white/70 border-t-transparent" />
          )}
          <span>Gerar Excel de Auditoria</span>
        </button>
      </section>

      {/* Quadro de Verbas Deferidas */}
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

        {safeAlertas.length === 0 ? (
          <p className="mt-2 text-xs text-emerald-300">
            Nenhum alerta crítico identificado. Liquidação aparentemente alinhada
            com a sentença.
          </p>
        ) : (
          <div className="mt-3 space-y-2 text-xs">
            {safeAlertas.map((alerta, idx) => (
              <div
                key={alerta?.id || idx}
                className="mb-4 p-4 bg-amber-50 border-l-4 border-amber-500 rounded-r-lg shadow-sm"
              >
                {/* Título seguro */}
                <h4 className="font-bold text-amber-900 text-sm">
                  {typeof alerta === "object"
                    ? alerta.titulo || "Alerta de Auditoria"
                    : "Ponto de atenção"}
                </h4>

                {/* Descrição segura */}
                <p className="text-xs text-amber-800 mt-1 leading-relaxed">
                  {typeof alerta === "object"
                    ? alerta.descricao || alerta.mensagem || ""
                    : alerta}
                </p>

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
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

