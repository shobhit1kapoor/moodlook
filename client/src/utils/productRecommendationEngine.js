import { mockProducts } from "../data/mockProducts";

const concernCategoryMap = {
  moisture: ["hydrating primer", "moisturizer", "dewy foundation"],
  oiliness: ["matte primer", "oil-control powder"],
  dark_circle_v2: ["peach corrector", "brightening concealer"],
  eye_bag: ["cooling eye gel", "brightening concealer"],
  redness: ["calming primer", "green tint corrector"],
  texture: ["smoothing primer", "lightweight foundation"],
  pore: ["pore-blurring primer", "smoothing primer"],
  acne: ["non-comedogenic concealer"],
  age_spot: ["spot concealer", "brightening serum"],
  radiance: ["glow serum", "luminous base"],
  wrinkle: ["smoothing primer", "hydrating foundation"],
  firmness: ["lifting serum", "cream blush"]
};

function getMoodLookType(mood = "") {
  const normalized = mood.toLowerCase();
  if (normalized.includes("tired") || normalized.includes("dinner")) return "tired";
  if (normalized.includes("date")) return "date";
  if (normalized.includes("party")) return "party";
  if (normalized.includes("interview") || normalized.includes("professional") || normalized.includes("meeting")) {
    return "professional";
  }
  if (normalized.includes("glow")) return "glow";
  return "everyday";
}

export function getProductCategories(normalizedSkinResults) {
  const focusConcerns = normalizedSkinResults?.concerns
    ?.filter((concern) => concern.score < 75)
    .sort((a, b) => a.score - b.score)
    .slice(0, 5) || [];

  const categories = focusConcerns.flatMap((concern) => concernCategoryMap[concern.type] || []);
  return [...new Set(categories)];
}

export function getProductRecommendations(normalizedSkinResults, recommendation, mood) {
  const focusTypes = normalizedSkinResults?.concerns
    ?.filter((concern) => concern.score < 75)
    .map((concern) => concern.type) || [];

  const productCategories = recommendation?.productCategories?.length
    ? recommendation.productCategories
    : getProductCategories(normalizedSkinResults);

  const lookType = getMoodLookType(mood || recommendation?.beautyGoal || "");

  const matches = mockProducts
    .map((product) => {
      const concernMatch = product.concernTypes.some((type) => focusTypes.includes(type));
      const categoryMatch = productCategories.includes(product.category);
      const moodMatch = product.lookTypes.includes(lookType);
      return {
        product,
        rank: Number(concernMatch) * 3 + Number(categoryMatch) * 2 + Number(moodMatch)
      };
    })
    .filter((item) => item.rank > 0)
    .sort((a, b) => b.rank - a.rank)
    .map((item) => item.product);

  const fallback = mockProducts.filter((product) => product.lookTypes.includes(lookType));
  const combined = [...matches, ...fallback, ...mockProducts];
  const unique = new Map(combined.map((product) => [product.id, product]));

  return [...unique.values()].slice(0, 8);
}
