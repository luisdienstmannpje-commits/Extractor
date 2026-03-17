import type { StatsResponse } from "../../services/api";

type ShadowRuleCandidate = StatsResponse["ultimas_regras"][number];

interface LearningPreviewProps {
  rule: ShadowRuleCandidate;
  onApprove?: (rule: ShadowRuleCandidate) => void;
  isApproving?: boolean;
}

export function LearningPreview({
  rule,
  onApprove,
  isApproving,
}: LearningPreviewProps) {
  if (!rule) return null;

  const handleApprove = () => {
    if (!onApprove) return;
    onApprove(rule);
  };

  const statusLabel =
    rule.status === "shadow"
      ? "Regra em teste (Shadow Rule)"
      : `Regra ${rule.status}`;

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-medium uppercase tracking-wide text-slate-400">
            IA Insight · Proposta de Regra
          </p>
          <p className="mt-1 text-xs text-slate-400">
            Analise a sugestão antes de ensinar ao cérebro isolado deste
            cliente.
          </p>
        </div>
        <span className="rounded-full bg-blue-500/10 px-2 py-0.5 text-[10px] font-medium text-blue-300">
          ID: {rule.rule_id}
        </span>
      </div>

      <div className="mt-3 space-y-1 text-xs text-slate-200">
        <p className="font-semibold text-slate-50">
          {rule.descricao || "Regra sem descrição detalhada."}
        </p>
        <p className="text-[11px] text-slate-400">{statusLabel}</p>
        <p className="text-[11px] text-slate-400">
          Confiança atual:{" "}
          <span className="font-medium text-slate-100">
            {rule.confidence_score.toFixed(2)}
          </span>
        </p>
      </div>

      <div className="mt-4 flex items-center justify-between gap-3 text-[11px]">
        <p className="max-w-xs text-slate-400">
          Ao aprovar, esta regra passa a integrar o conhecimento oficial do
          motor para este tenant.
        </p>
        <button
          type="button"
          disabled={!onApprove || isApproving}
          onClick={handleApprove}
          className="inline-flex items-center justify-center rounded-md bg-emerald-600 px-3 py-1.5 font-medium text-white shadow-sm hover:bg-emerald-500 disabled:cursor-not-allowed disabled:bg-slate-700"
        >
          {isApproving ? "Aprovando..." : "Aprovar e Ensinar ao Cérebro"}
        </button>
      </div>
    </div>
  );
}

