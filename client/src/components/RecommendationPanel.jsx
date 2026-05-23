import { CheckCircle2 } from "lucide-react";

function ListBlock({ title, items }) {
  return (
    <div className="rounded-3xl bg-white/70 p-5 shadow-soft">
      <h3 className="text-sm font-bold uppercase tracking-[0.16em] text-charcoal/50">{title}</h3>
      <ul className="mt-4 space-y-3">
        {items.map((item) => (
          <li key={item} className="flex gap-3 text-sm leading-6 text-charcoal/70">
            <CheckCircle2 className="mt-0.5 shrink-0 text-plum" size={17} aria-hidden="true" />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function RecommendationPanel({ recommendation }) {
  if (!recommendation) return null;

  return (
    <section className="card p-5 md:p-6">
      <p className="section-kicker">Personalized routine</p>
      <h2 className="section-title">Today's skin-aware beauty plan</h2>
      <div className="mt-5 grid gap-4 lg:grid-cols-3">
        <div className="rounded-3xl bg-charcoal p-6 text-white shadow-soft lg:col-span-1">
          <p className="text-sm font-semibold text-white/60">Today's Skin Profile</p>
          <p className="mt-4 text-xl font-bold leading-8">{recommendation.skinSummary}</p>
          <p className="mt-6 text-sm font-semibold text-white/60">Recommended Beauty Goal</p>
          <p className="mt-2 text-lg font-bold text-blush">{recommendation.beautyGoal}</p>
          <p className="mt-6 text-sm font-semibold text-white/60">Why this works</p>
          <p className="mt-2 text-sm leading-6 text-white/75">{recommendation.explanation}</p>
        </div>
        <ListBlock title="Prep Routine" items={recommendation.prepRoutine} />
        <ListBlock title="Makeup Look" items={recommendation.makeupSteps} />
      </div>
      <div className="mt-4 rounded-3xl border border-white/80 bg-white/70 p-5 shadow-soft">
        <h3 className="text-sm font-bold uppercase tracking-[0.16em] text-charcoal/50">Try-On Plan</h3>
        <p className="mt-3 text-sm leading-6 text-charcoal/70">
          Apply {recommendation.tryOnConfig.lookName} with a {recommendation.tryOnConfig.features.base} base,
          {` ${recommendation.tryOnConfig.features.underEye}`} under-eyes, {recommendation.tryOnConfig.features.cheek},
          and {recommendation.tryOnConfig.features.lip}.
        </p>
      </div>
    </section>
  );
}
