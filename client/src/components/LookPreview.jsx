import { Camera, Sparkles } from "lucide-react";

export default function LookPreview({ recommendation, mood, onTryOn, tryOnResult, loading }) {
  if (!recommendation) return null;

  const look = recommendation.tryOnConfig;
  const resultImageUrl = tryOnResult?.moodlook?.resultImageUrl;
  const isRealTryOn = Boolean(resultImageUrl);
  const isTryOnError = tryOnResult?.status === "error";

  return (
    <section className="card overflow-hidden p-0">
      <div className="grid gap-0 lg:grid-cols-[0.95fr_1.05fr]">
        <div className="relative min-h-[340px] bg-charcoal">
          <img
            className="absolute inset-0 h-full w-full object-cover opacity-80"
            src="https://images.unsplash.com/photo-1516975080664-ed2fc6a32937?auto=format&fit=crop&w=1100&q=85"
            alt="Recommended makeup look"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-charcoal via-charcoal/25 to-transparent" />
          <div className="absolute bottom-0 left-0 right-0 p-6 text-white">
            <p className="inline-flex items-center gap-2 rounded-full bg-white/20 px-3 py-1 text-xs font-bold backdrop-blur">
              <Sparkles size={14} aria-hidden="true" />
              Recommended look
            </p>
            <h2 className="mt-4 text-4xl font-bold">{look.lookName}</h2>
            <p className="mt-2 text-sm text-white/70">{mood || "Soft everyday glow"}</p>
          </div>
        </div>
        <div className="p-5 md:p-7">
          <p className="section-kicker">AR look preview</p>
          <h2 className="section-title">{recommendation.beautyGoal}</h2>
          <p className="section-copy">{look.style}</p>
          <div className="mt-6">
            <p className="text-sm font-bold text-charcoal">Color palette</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {look.palette.map((color) => (
                <span key={color} className="rounded-full border border-charcoal/10 bg-white px-3 py-2 text-sm font-semibold text-charcoal/70">
                  {color}
                </span>
              ))}
            </div>
          </div>
          <button className="btn-primary mt-7 w-full justify-center md:w-auto" type="button" onClick={onTryOn} disabled={loading}>
            <Camera size={18} aria-hidden="true" />
            {loading ? "Preparing AR look" : "Try This Look with AR"}
          </button>
          <div className={`mt-5 rounded-3xl border p-5 ${isTryOnError ? "border-rose-200 bg-rose-50" : "border-white/80 bg-cream/80"}`}>
            {resultImageUrl ? (
              <img
                className="mb-4 aspect-[4/3] w-full rounded-2xl object-cover"
                src={resultImageUrl}
                alt="Perfect Corp virtual try-on result"
              />
            ) : null}
            <p className="text-sm font-bold text-charcoal">
              {isRealTryOn
                ? "Virtual try-on applied"
                : isTryOnError
                  ? "Virtual try-on needs attention"
                  : tryOnResult
                    ? "Virtual try-on ready"
                    : "Virtual try-on placeholder"}
            </p>
            <p className="mt-2 text-sm leading-6 text-charcoal/60">
              {isRealTryOn
                ? "Perfect Corp applied the recommended lip color effect to your analyzed image."
                : isTryOnError
                  ? tryOnResult.message
                : tryOnResult
                  ? tryOnResult.message || "The app prepared your look configuration for virtual try-on."
                : "Click the AR button to simulate the handoff to Perfect Corp Makeup Virtual Try-On."}
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
