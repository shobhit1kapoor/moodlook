import { ArrowDown, ArrowRight, Camera, Play, ScanFace, ShoppingBag, Sparkles } from "lucide-react";

export default function Header({ onStart }) {
  return (
    <header className="relative min-h-screen overflow-hidden bg-cream">
      <div className="absolute inset-0 z-0">
        <img
          className="h-full w-full object-cover"
          src="/images/moodlook/hero-model.jpg"
          alt="MoodLook beauty model"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-cream via-cream/72 to-cream/12" />
        <div className="absolute inset-x-0 bottom-0 h-[42%] bg-gradient-to-t from-cream via-cream/80 to-transparent" />
      </div>

      <nav className="fixed left-0 right-0 top-4 z-50 px-5 md:px-8 lg:px-16">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <button className="group flex items-center gap-3" type="button" onClick={onStart}>
            <span className="grid h-12 w-12 place-items-center rounded-2xl bg-charcoal text-white shadow-boty">
              <Sparkles size={20} aria-hidden="true" />
            </span>
            <span className="hidden font-display text-2xl font-semibold italic text-charcoal sm:inline">MoodLook</span>
          </button>

          <div className="hero-pill hidden items-center gap-1 px-2 py-2 lg:flex">
            {["Home", "Skin Scan", "Looks", "AR Try-On"].map((item) => (
              <button
                key={item}
                className="rounded-full px-4 py-2 text-sm font-semibold text-charcoal/75 transition hover:bg-white/80 hover:text-charcoal"
                type="button"
                onClick={item === "Skin Scan" ? onStart : undefined}
              >
                {item}
              </button>
            ))}
            <button
              className="ml-1 inline-flex items-center gap-2 rounded-full bg-charcoal px-4 py-2 text-sm font-semibold text-white transition hover:bg-plum"
              type="button"
              onClick={onStart}
            >
              Start Scan
              <ArrowRight size={15} aria-hidden="true" />
            </button>
          </div>

          <button className="btn-primary px-4 py-2.5" type="button" onClick={onStart}>
            <ScanFace size={17} aria-hidden="true" />
            Scan
          </button>
        </div>
      </nav>

      <div className="relative z-10 mx-auto flex min-h-screen max-w-7xl flex-col justify-center px-5 pb-20 pt-28 md:px-8">
        <div className="max-w-2xl">
          <div className="hero-pill mb-5 inline-flex items-center gap-2 px-1 py-1 opacity-0 animate-blur-in" style={{ animationDelay: "0.12s" }}>
            <span className="rounded-full bg-white px-3 py-1 text-xs font-bold text-charcoal">Live AI</span>
            <span className="pr-3 text-sm font-medium text-charcoal/75">Skin-aware AR beauty shopping assistant</span>
          </div>

          <h1 className="font-display text-6xl font-semibold leading-[0.95] tracking-tight text-charcoal opacity-0 animate-blur-in md:text-7xl lg:text-8xl" style={{ animationDelay: "0.28s" }}>
            Your skin changes daily.
            <span className="block italic text-plum">Your look should too.</span>
          </h1>

          <p className="mt-6 max-w-xl text-base font-light leading-7 text-charcoal/72 opacity-0 animate-blur-in md:text-lg" style={{ animationDelay: "0.48s" }}>
            Scan your visible skin state, create a personalized makeup look, try it on with AR, and shop the routine in one polished flow.
          </p>

          <div className="mt-8 flex flex-col gap-4 opacity-0 animate-blur-in sm:flex-row" style={{ animationDelay: "0.68s" }}>
            <button className="btn-primary justify-center px-7 py-4" type="button" onClick={onStart}>
              <Camera size={18} aria-hidden="true" />
              Start Skin Scan
              <ArrowRight size={18} aria-hidden="true" />
            </button>
            <a className="btn-secondary justify-center px-7 py-4" href="#products">
              <ShoppingBag size={18} aria-hidden="true" />
              Shop the Routine
            </a>
            <button className="inline-flex items-center justify-center gap-2 rounded-full px-3 py-4 text-sm font-semibold text-charcoal/72 transition hover:text-plum" type="button" onClick={onStart}>
              <Play className="fill-current" size={16} aria-hidden="true" />
              View Demo Flow
            </button>
          </div>
        </div>

        <div className="mt-12 grid gap-4 opacity-0 animate-blur-in md:grid-cols-[0.8fr_1fr_0.8fr]" style={{ animationDelay: "0.88s" }}>
          <div className="glass-panel rounded-[2rem] p-5">
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-plum">Step 01</p>
            <p className="mt-3 text-lg font-semibold text-charcoal">Scan visible skin state</p>
          </div>
          <div className="relative overflow-hidden rounded-[2rem] border border-white/80 bg-white/55 p-3 shadow-glow backdrop-blur-xl">
            <img
              className="aspect-[16/9] w-full rounded-[1.45rem] object-cover"
              src="/images/moodlook/skincare-ritual.jpg"
              alt="Skincare and makeup ritual"
            />
            <div className="pointer-events-none absolute inset-x-3 top-3 h-16 rounded-t-[1.45rem] bg-gradient-to-b from-white/45 to-transparent" />
          </div>
          <div className="glass-panel rounded-[2rem] p-5">
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-plum">Step 03</p>
            <p className="mt-3 text-lg font-semibold text-charcoal">Try on and shop the look</p>
          </div>
        </div>

        <div className="mt-8 hidden flex-col items-center gap-2 text-charcoal/70 opacity-0 animate-blur-in md:flex" style={{ animationDelay: "1.04s" }}>
          <a className="hero-pill inline-flex items-center gap-2 px-4 py-2 text-xs font-bold uppercase tracking-[0.22em]" href="#scan">
            <ArrowDown size={16} aria-hidden="true" />
            Begin the 90-second flow
          </a>
          <div className="relative h-10 w-px overflow-hidden bg-charcoal/15">
            <div className="absolute left-0 top-0 h-1/2 w-full bg-plum animate-scan-line" />
          </div>
        </div>
      </div>
    </header>
  );
}
