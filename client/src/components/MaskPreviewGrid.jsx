export default function MaskPreviewGrid({ concerns }) {
  const masks = concerns?.filter((concern) => concern.maskUrl) || [];

  if (!masks.length) {
    return null;
  }

  return (
    <section className="card p-5 md:p-6">
      <p className="section-kicker">Perfect Corp outputs</p>
      <h2 className="section-title">Mask previews</h2>
      <p className="section-copy">Visible maps help explain why the routine focuses on specific areas.</p>
      <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {masks.map((concern) => (
          <article key={concern.type} className="overflow-hidden rounded-3xl border border-white/80 bg-white/75 shadow-soft">
            <img className="aspect-[4/3] w-full object-cover" src={concern.maskUrl} alt={`${concern.label} preview`} />
            <div className="flex items-center justify-between gap-3 p-4">
              <span className="text-sm font-bold text-charcoal">{concern.label}</span>
              <span className="rounded-full bg-charcoal px-3 py-1 text-xs font-bold text-white">{concern.score}</span>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
