const LABELS = {
  hd_texture: "Texture",
  texture: "Texture",
  hd_oiliness: "Oiliness",
  oiliness: "Oiliness",
  hd_pore: "Pores",
  pore: "Pores",
  hd_radiance: "Radiance",
  radiance: "Radiance",
  hd_redness: "Redness",
  redness: "Redness",
  hd_dark_circle: "Dark Circles",
  dark_circle_v2: "Dark Circles",
  hd_age_spot: "Spots",
  age_spot: "Spots",
  hd_acne: "Acne",
  acne: "Acne",
  hd_firmness: "Firmness",
  firmness: "Firmness",
  hd_eye_bag: "Eye Bags",
  eye_bag: "Eye Bags",
  hd_wrinkle: "Wrinkles",
  wrinkle: "Wrinkles",
  hd_moisture: "Moisture",
  moisture: "Moisture"
};

const SUMMARY_TYPES = new Set(["all", "skin_age", "resize_image"]);

function toNumber(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

export function getSeverity(score) {
  if (score >= 90) return "excellent";
  if (score >= 75) return "good";
  if (score >= 60) return "moderate";
  return "needs_attention";
}

export function normalizeSkinResults(apiResponse) {
  const output = getOutputItems(apiResponse);

  if (!Array.isArray(output)) {
    return {
      overallScore: null,
      skinAge: null,
      analyzedImage: null,
      concerns: []
    };
  }

  const overallItem = output.find((item) => item?.type === "all");
  const skinAgeItem = output.find((item) => item?.type === "skin_age");
  const imageItem = output.find((item) => item?.type === "resize_image");

  const concerns = output
    .filter((item) => item?.type && !SUMMARY_TYPES.has(item.type))
    .map((item) => {
      const score = toNumber(item.ui_score ?? item.score);

      if (score === null) {
        return null;
      }

      return {
        type: item.type,
        label: LABELS[item.type] || item.type.replaceAll("_", " "),
        score: Math.round(score),
        rawScore: toNumber(item.raw_score),
        maskUrl: Array.isArray(item.mask_urls) ? item.mask_urls[0] || null : null,
        severity: getSeverity(score)
      };
    })
    .filter(Boolean);

  return {
    overallScore: toNumber(overallItem?.score ?? overallItem?.ui_score),
    skinAge: toNumber(skinAgeItem?.score ?? skinAgeItem?.ui_score),
    analyzedImage: Array.isArray(imageItem?.mask_urls) ? imageItem.mask_urls[0] || null : null,
    concerns
  };
}

export const skinTypeLabels = LABELS;

function getOutputItems(apiResponse) {
  const output = apiResponse?.data?.results?.output;

  if (Array.isArray(output)) {
    return output;
  }

  const results = apiResponse?.data?.results;
  const scoreInfo = results?.score_info || results?.skinanalysisResult?.score_info || results;

  if (!scoreInfo || Array.isArray(scoreInfo) || typeof scoreInfo !== "object") {
    return output;
  }

  return Object.entries(scoreInfo).map(([type, value]) => {
    if (typeof value === "number") {
      return { type, score: value, url: null };
    }

    const maskName = value?.output_mask_name;
    const maskUrl = value?.mask_url || value?.url || (maskName && results?.base_url ? `${results.base_url}/${maskName}` : null);

    return {
      type,
      ui_score: value?.ui_score,
      raw_score: value?.raw_score,
      score: value?.score,
      mask_urls: maskUrl ? [maskUrl] : undefined,
      url: null
    };
  });
}
