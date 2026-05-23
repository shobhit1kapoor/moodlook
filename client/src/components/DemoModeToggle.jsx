import { Sparkles } from "lucide-react";

export default function DemoModeToggle({ enabled, onChange }) {
  return (
    <label className="flex cursor-pointer items-center justify-between gap-4 rounded-2xl border border-white/70 bg-white/70 px-4 py-3 shadow-soft backdrop-blur">
      <span className="flex items-center gap-3">
        <span className="grid h-10 w-10 place-items-center rounded-full bg-plum text-white">
          <Sparkles size={18} aria-hidden="true" />
        </span>
        <span>
          <span className="block text-sm font-semibold text-charcoal">Demo Mode</span>
          <span className="block text-xs text-charcoal/60">Use sample skin analysis without API credits.</span>
        </span>
      </span>
      <input
        className="peer sr-only"
        type="checkbox"
        checked={enabled}
        onChange={(event) => onChange(event.target.checked)}
      />
      <span className="relative h-7 w-12 rounded-full bg-charcoal/15 transition peer-checked:bg-plum">
        <span className="absolute left-1 top-1 h-5 w-5 rounded-full bg-white shadow transition peer-checked:translate-x-5" />
      </span>
    </label>
  );
}
