import SkinScoreCard from "./SkinScoreCard";

export default function SkinDashboard({ normalizedResults }) {
  const concerns = normalizedResults?.concerns || [];
  const focusAreas = concerns
    .filter((concern) => concern.score < 75)
    .sort((a, b) => a.score - b.score)
    .slice(0, 4);

  if (!concerns.length) {
    return (
      <section className="card p-6">
        <h2 className="section-title">Skin profile</h2>
        <p className="section-copy">No skin concern scores were returned. Try another image or use demo mode.</p>
      </section>
    );
  }

  return (
    <section className="card p-5 md:p-6">
      <div className="grid gap-5 lg:grid-cols-[0.85fr_1.15fr]">
        <div>
          <p className="section-kicker">Skin profile</p>
          <h2 className="section-title">Today's visible skin state</h2>
          <p className="section-copy">Scores help tune the beauty routine. Lower-scoring areas become product and prep focus areas.</p>

          <div className="mt-6 grid grid-cols-2 gap-3">
            <div className="rounded-3xl bg-charcoal p-5 text-white shadow-soft">
              <p className="text-sm font-semibold text-white/60">Overall score</p>
              <p className="mt-3 text-4xl font-bold">
                {normalizedResults.overallScore ? Math.round(normalizedResults.overallScore) : "--"}
              </p>
            </div>
            <div className="rounded-3xl bg-white/80 p-5 shadow-soft">
              <p className="text-sm font-semibold text-charcoal/60">Skin age</p>
              <p className="mt-3 text-4xl font-bold text-charcoal">
                {normalizedResults.skinAge ? Math.round(normalizedResults.skinAge) : "--"}
              </p>
            </div>
          </div>

          <div className="mt-5 rounded-3xl border border-white/80 bg-white/70 p-5 shadow-soft">
            <p className="text-sm font-bold text-charcoal">Main visible focus areas</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {(focusAreas.length ? focusAreas : concerns.slice(0, 3)).map((concern) => (
                <span key={concern.type} className="rounded-full bg-plum/10 px-3 py-1 text-sm font-semibold text-plum">
                  {concern.label}
                </span>
              ))}
            </div>
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          {concerns.map((concern) => (
            <SkinScoreCard key={concern.type} concern={concern} />
          ))}
        </div>
      </div>
    </section>
  );
}
