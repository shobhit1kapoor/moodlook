import { getConcernAction } from "../utils/skinRecommendationEngine";

const severityCopy = {
  excellent: "Excellent",
  good: "Good",
  moderate: "Focus area",
  needs_attention: "Focus area"
};

const severityClasses = {
  excellent: "bg-emerald-50 text-emerald-700 border-emerald-100",
  good: "bg-sky-50 text-sky-700 border-sky-100",
  moderate: "bg-amber-50 text-amber-700 border-amber-100",
  needs_attention: "bg-rose-50 text-rose-700 border-rose-100"
};

export default function SkinScoreCard({ concern }) {
  return (
    <article className="rounded-3xl border border-white/80 bg-white/80 p-5 shadow-soft">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-bold text-charcoal">{concern.label}</h3>
          <p className="mt-1 text-xs font-semibold uppercase tracking-[0.18em] text-charcoal/40">Score</p>
        </div>
        <span className={`rounded-full border px-3 py-1 text-xs font-bold ${severityClasses[concern.severity]}`}>
          {severityCopy[concern.severity]}
        </span>
      </div>
      <div className="mt-5 flex items-end gap-2">
        <span className="text-4xl font-bold text-charcoal">{concern.score}</span>
        <span className="pb-1 text-sm font-semibold text-charcoal/50">/100</span>
      </div>
      <div className="mt-4 h-2 overflow-hidden rounded-full bg-charcoal/8">
        <div className="h-full rounded-full bg-plum" style={{ width: `${Math.min(concern.score, 100)}%` }} />
      </div>
      <p className="mt-4 text-sm font-semibold text-charcoal/80">Recommended action</p>
      <p className="mt-2 text-sm leading-6 text-charcoal/60">{getConcernAction(concern.type)}</p>
    </article>
  );
}
