import { getProductCategories } from "./productRecommendationEngine";

const actionCopy = {
  moisture: "Layer hydration before base makeup and choose flexible, dewy textures.",
  oiliness: "Balance shine with a light matte primer and targeted powder.",
  dark_circle_v2: "Use peach correction and a brightening concealer for a lifted under-eye look.",
  eye_bag: "Start with cooling under-eye prep, then keep concealer thin and bright.",
  redness: "Calm the base with a neutralizing primer and soft neutral cheek color.",
  texture: "Choose smoothing prep and a breathable base instead of heavy layers.",
  pore: "Blur visible pores with primer and set only the center of the face.",
  acne: "Use precise non-comedogenic coverage and keep the rest of the base sheer.",
  age_spot: "Spot conceal where needed and add soft radiance across the high points.",
  radiance: "Bring glow back with luminous prep and a satin finish base.",
  wrinkle: "Use hydrating complexion products that move with the skin.",
  firmness: "Add a lifted cream blush placement and fresh radiance."
};

function moodProfile(mood = "") {
  const text = mood.toLowerCase();

  if (text.includes("tired") || text.includes("dinner")) {
    return {
      lookName: "Bright-Eyed Dinner Look",
      beautyGoal: "Bright-eyed soft dinner glow",
      style: "Fresh luminous skin, lifted eyes, soft blush, and a warm lip tint",
      palette: ["Champagne", "Petal", "Warm Taupe", "Rosewood"],
      lookType: "tired"
    };
  }

  if (text.includes("date")) {
    return {
      lookName: "Fresh Soft Glow",
      beautyGoal: "Soft-focus romantic glow",
      style: "Dewy base, cream blush, subtle shimmer, and a blurred rose lip",
      palette: ["Pearl", "Peach", "Soft Brown", "Rose"],
      lookType: "date"
    };
  }

  if (text.includes("interview") || text.includes("professional") || text.includes("meeting")) {
    return {
      lookName: "Matte Confidence Look",
      beautyGoal: "Polished balanced confidence",
      style: "Even soft-matte base, defined brows, neutral eyes, and a satin lip",
      palette: ["Ivory", "Taupe", "Soft Cocoa", "Mauve"],
      lookType: "professional"
    };
  }

  if (text.includes("party")) {
    return {
      lookName: "Glow After-Dark Look",
      beautyGoal: "Radiant party polish",
      style: "Satin base, luminous cheek, softly smoked eyes, and a glossy lip",
      palette: ["Gold", "Blush", "Bronze", "Berry"],
      lookType: "party"
    };
  }

  if (text.includes("workout")) {
    return {
      lookName: "Reset Fresh Look",
      beautyGoal: "Clean refreshed glow",
      style: "Light breathable base, calm cheeks, clear brow gel, and tinted balm",
      palette: ["Mist", "Peach", "Soft Coral", "Clear Gloss"],
      lookType: "everyday"
    };
  }

  return {
    lookName: "Hydrated Everyday Glow",
    beautyGoal: "Fresh everyday skin rhythm",
    style: "Hydrated base, soft cream cheek, natural definition, and easy lip color",
    palette: ["Cream", "Petal", "Soft Beige", "Tinted Rose"],
    lookType: "everyday"
  };
}

function getFocusConcerns(normalizedSkinResults) {
  return normalizedSkinResults?.concerns
    ?.filter((concern) => concern.score < 75)
    .sort((a, b) => a.score - b.score)
    .slice(0, 4) || [];
}

export function getConcernAction(type) {
  return actionCopy[type] || "Keep the base lightweight and adjust products to today's skin state.";
}

export function generateRecommendation(normalizedSkinResults, mood) {
  const focusConcerns = getFocusConcerns(normalizedSkinResults);
  const moodLook = moodProfile(mood);
  const focusLabels = focusConcerns.map((concern) => concern.label.toLowerCase());

  const has = (type) => focusConcerns.some((concern) => concern.type === type);

  const prepRoutine = [
    has("moisture") ? "Hydrating moisturizer" : "Lightweight skin prep",
    has("eye_bag") || has("dark_circle_v2") ? "Cooling under-eye prep" : "Soft eye-area prep",
    has("texture") || has("pore") ? "Smoothing primer" : "Comfort primer",
    has("oiliness") ? "Targeted matte primer on shine-prone areas" : null,
    has("redness") ? "Calming green-tint primer where needed" : null
  ].filter(Boolean);

  const makeupSteps = [
    has("dark_circle_v2") || has("eye_bag") ? "Peach corrector and brightening concealer under the eyes" : "Thin brightening concealer only where wanted",
    has("moisture") || has("radiance") ? "Lightweight luminous base" : "Breathable soft-focus base",
    has("texture") || has("pore") ? "Blur primer through the center of the face before foundation" : null,
    has("oiliness") ? "Oil-control powder only on the T-zone" : null,
    has("redness") ? "Neutral cheek color layered softly over a balanced base" : "Soft cream blush placed high on the cheeks",
    moodLook.lookType === "party" ? "Subtle shimmer across the lids and high points" : "Natural eye definition with lifted mascara",
    moodLook.lookType === "professional" ? "Satin neutral lip" : "Warm neutral lip tint"
  ].filter(Boolean);

  const skinSummary = focusLabels.length
    ? `Your skin profile suggests a ${focusLabels.join(", ")} focus for today's look.`
    : "Your skin profile looks balanced, so the routine can stay light, fresh, and flexible.";

  const explanation = focusLabels.length
    ? `This look supports ${focusLabels.join(", ")} while keeping the finish polished instead of heavy.`
    : "This look keeps the skin fresh and lets the mood drive the color story.";

  return {
    skinSummary,
    beautyGoal: moodLook.beautyGoal,
    prepRoutine,
    makeupSteps,
    tryOnConfig: {
      lookName: moodLook.lookName,
      lookType: moodLook.lookType,
      palette: moodLook.palette,
      style: moodLook.style,
      features: {
        base: has("oiliness") ? "soft matte" : "luminous natural",
        underEye: has("dark_circle_v2") || has("eye_bag") ? "brightened" : "natural",
        cheek: "soft lifted blush",
        lip: moodLook.lookType === "party" ? "gloss berry tint" : "warm neutral tint"
      }
    },
    productCategories: getProductCategories(normalizedSkinResults),
    explanation
  };
}
