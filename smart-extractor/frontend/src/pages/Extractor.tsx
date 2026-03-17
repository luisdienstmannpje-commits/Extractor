import React, { useState } from "react";
import { api, type ExtractionResponseEnvelope } from "../services/api";
import { AnalysisReport } from "../components/features/AnalysisReport";
import type { ProcessoTrabalhista } from "../types/api";

type BaseFile = File;

type ExtractorResult = {
  bruto: ExtractionResponseEnvelope | any;
  processo: ProcessoTrabalhista | null;
};

export const Extractor: React.FC = () => {
  const [file, setFile] = useState<BaseFile | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ExtractorResult | null>(null);

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selected = event.target.files?.[0] ?? null;
    setFile(selected);
    setError(null);
    setResult(null);
  };

  const handleAnalyze = async () => {
    if (!file) return;
    setIsLoading(true);
    setError(null);

    try {
      const form = new FormData();
      form.append("file", file);

      const response = await api.post<ExtractionResponseEnvelope>("/api/extract", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      // Debug da estrutura real vinda do backend
      // eslint-disable-next-line no-console
      console.log("ESTRUTURA BRUTA DO BACKEND:", response.data);

      const raw = response.data as any;
      // Normalização de dados: tenta encontrar o ProcessoTrabalhista em diferentes formatos
      const processoValido: ProcessoTrabalhista | null =
        (raw?.data as ProcessoTrabalhista) ??
        (raw?.processo_trabalhista as ProcessoTrabalhista) ??
        (raw as ProcessoTrabalhista);

      setResult({
        bruto: raw,
        processo: processoValido ?? null,
      });
    } catch (e: any) {
      setError(e?.message ?? "Erro ao processar o documento.");
    } finally {
      setIsLoading(false);
    }
  };

  const processo = result?.processo ?? null;

  return (
    <div className="flex flex-col gap-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold text-slate-50">Extrator Rápido</h1>
        <p className="text-xs text-slate-400">
          Envie a Sentença ou Título Executivo em um único arquivo para obter o
          relatório pericial resumido.
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
          <p className="text-xs text-slate-400">Analisando documento...</p>
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

        {processo && (
          <AnalysisReport processo={processo} raw={result?.bruto ?? result} />
        )}
      </section>
    </div>
  );
};

