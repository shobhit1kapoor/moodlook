import { ImagePlus, Loader2, ScanFace } from "lucide-react";
import DemoModeToggle from "./DemoModeToggle";

export default function UploadCard({
  demoMode,
  onDemoModeChange,
  selectedFile,
  previewUrl,
  onFileChange,
  onAnalyze,
  loading,
  error
}) {
  return (
    <section id="scan" className="card p-5 md:p-6">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <p className="section-kicker">Face scan</p>
          <h2 className="section-title">Scan your skin state</h2>
          <p className="section-copy">Upload a clear face photo or use demo mode for the full hackathon flow.</p>
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-[1fr_0.86fr]">
        <label className="group grid min-h-[310px] cursor-pointer place-items-center overflow-hidden rounded-3xl border border-dashed border-plum/30 bg-cream/70 text-center transition hover:border-plum/60">
          {previewUrl ? (
            <img className="h-full max-h-[420px] w-full object-cover" src={previewUrl} alt="Selected face preview" />
          ) : (
            <span className="flex max-w-xs flex-col items-center px-8">
              <span className="mb-4 grid h-14 w-14 place-items-center rounded-full bg-white text-plum shadow-soft">
                <ImagePlus size={24} aria-hidden="true" />
              </span>
              <span className="text-base font-semibold text-charcoal">Upload face image</span>
              <span className="mt-2 text-sm leading-6 text-charcoal/60">
                Use a front-facing photo with even lighting for the clearest beauty recommendations.
              </span>
            </span>
          )}
          <input
            className="sr-only"
            type="file"
            accept="image/*"
            onChange={(event) => onFileChange(event.target.files?.[0] || null)}
          />
        </label>

        <div className="flex flex-col gap-4">
          <DemoModeToggle enabled={demoMode} onChange={onDemoModeChange} />
          <div className="rounded-3xl border border-white/70 bg-white/70 p-5 shadow-soft">
            <p className="text-sm font-semibold text-charcoal">Selected image</p>
            <p className="mt-2 text-sm text-charcoal/60">
              {demoMode
                ? "Demo mode will use a Perfect Corp-style sample response."
                : selectedFile
                  ? selectedFile.name
                  : "No image selected yet."}
            </p>
          </div>
          {error ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">
              {error}
            </div>
          ) : null}
          <button className="btn-primary mt-auto w-full justify-center" type="button" onClick={onAnalyze} disabled={loading}>
            {loading ? <Loader2 className="animate-spin" size={18} aria-hidden="true" /> : <ScanFace size={18} aria-hidden="true" />}
            {loading ? "Analyzing skin state" : "Analyze and Build My Look"}
          </button>
        </div>
      </div>
    </section>
  );
}
