import { useQuery } from "@tanstack/react-query";
import { api, type StatsResponse } from "../services/api";

export function Dashboard() {
  const {
    data,
    error,
    isLoading,
    isError
  } = useQuery<StatsResponse, Error>({
    queryKey: ["stats"],
    queryFn: async () => {
      const response = await api.get<StatsResponse>("/api/stats");
      return response.data;
    },
    staleTime: 30_000
  });

  if (isLoading) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-900 px-6 py-4 shadow-lg">
        <p className="text-sm text-slate-300">Carregando estatísticas do sistema…</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-xl border border-red-900/60 bg-red-950 px-6 py-4 shadow-lg">
        <h2 className="text-sm font-semibold text-red-100">
          Não foi possível carregar o Dashboard.
        </h2>
        <p className="mt-1 text-xs text-red-200/90">
          Verifique se o backend está em execução e tente novamente em alguns instantes.
        </p>
        <p className="mt-2 text-[11px] text-red-300/80">
          Detalhes técnicos: {(error as Error).message}
        </p>
      </div>
    );
  }

  const stats = data;

  if (!stats) {
    return (
      <div className="rounded-xl border border-amber-800 bg-amber-950 px-6 py-4 shadow-lg">
        <p className="text-sm text-amber-50">
          Nenhum dado de estatísticas foi retornado pelo servidor.
        </p>
      </div>
    );
  }

  const eficienciaLabel =
    stats.eficiencia_motor == null ? "—" : `${stats.eficiencia_motor.toFixed(1)}%`;

  return (
    <section className="space-y-4">
      <header>
        <h1 className="text-xl font-semibold tracking-tight text-slate-50">
          Dashboard de Inteligência
        </h1>
        <p className="mt-1 text-sm text-slate-400">
          Visão geral do uso do extrator e da eficiência do Cérebro de Regras.
        </p>
      </header>

      <div className="grid gap-4 grid-cols-1 sm:grid-cols-3">
        <div className="rounded-lg border border-slate-800 bg-slate-900/80 px-4 py-3 shadow-sm">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wide">
            Total de Extrações
          </p>
          <p className="mt-2 text-2xl font-semibold text-slate-50">
            {stats.processos_analisados}
          </p>
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-900/80 px-4 py-3 shadow-sm">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wide">
            Regras no Cérebro
          </p>
          <p className="mt-2 text-2xl font-semibold text-slate-50">
            {stats.regras_oficiais_ativas + stats.regras_em_teste_shadow}
          </p>
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-900/80 px-4 py-3 shadow-sm">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wide">
            Eficiência Média
          </p>
          <p className="mt-2 text-2xl font-semibold text-slate-50">{eficienciaLabel}</p>
        </div>
      </div>
    </section>
  );
}

