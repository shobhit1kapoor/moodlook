const moods = [
  "I look tired",
  "Date night",
  "Job interview",
  "Casual day",
  "Party look",
  "Post-workout",
  "Soft everyday glow",
  "Professional meeting"
];

export default function MoodSelector({ selectedMood, customMood, onMoodChange, onCustomMoodChange }) {
  return (
    <section className="card p-5 md:p-6">
      <p className="section-kicker">Mood and occasion</p>
      <h2 className="section-title">What look do you need today?</h2>
      <p className="section-copy">Choose a moment or describe your own. MoodLook will tune the routine around it.</p>
      <div className="mt-5 flex flex-wrap gap-2">
        {moods.map((mood) => (
          <button
            key={mood}
            className={`rounded-full border px-4 py-2 text-sm font-semibold transition ${
              selectedMood === mood
                ? "border-plum bg-plum text-white shadow-soft"
                : "border-charcoal/10 bg-white/70 text-charcoal/70 hover:border-plum/40"
            }`}
            type="button"
            onClick={() => onMoodChange(mood)}
          >
            {mood}
          </button>
        ))}
      </div>
      <label className="mt-5 block">
        <span className="mb-2 block text-sm font-semibold text-charcoal">Describe your mood or occasion</span>
        <input
          className="w-full rounded-2xl border border-charcoal/10 bg-white/80 px-4 py-3 text-charcoal outline-none transition placeholder:text-charcoal/40 focus:border-plum/60 focus:ring-4 focus:ring-plum/10"
          value={customMood}
          onChange={(event) => onCustomMoodChange(event.target.value)}
          placeholder="I look tired and have a dinner tonight"
        />
      </label>
    </section>
  );
}
