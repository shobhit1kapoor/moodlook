import { Router } from "express";
import { tryOnMakeupWithPerfectCorp } from "../services/perfectCorpService.js";

const router = Router();

router.post("/", async (req, res) => {
  const { imageUrl, lookConfig, demoMode } = req.body || {};

  if (!lookConfig) {
    return res.status(400).json({
      error: true,
      message: "Send a look configuration to prepare virtual try-on."
    });
  }

  if (demoMode || !isPublicUrl(imageUrl)) {
    return res.json(mockTryOnResponse(imageUrl, lookConfig));
  }

  try {
    const response = await tryOnMakeupWithPerfectCorp({ imageUrl, lookConfig });
    res.json(response);
  } catch (error) {
    const providerError = error.response?.data;

    res.status(error.status || error.response?.status || 500).json({
      error: true,
      message: providerError?.message || providerError?.error || providerError?.error_message || error.message || "Virtual try-on failed.",
      provider: providerError ? "Perfect Corp" : undefined,
      providerErrorCode: providerError?.error_code
    });
  }
});

function isPublicUrl(value) {
  return typeof value === "string" && /^https?:\/\//i.test(value);
}

function mockTryOnResponse(imageUrl, lookConfig) {
  return {
    status: "mock_ready",
    message: "Virtual try-on simulated for demo mode or local preview image.",
    provider: "Perfect Corp Makeup Virtual Try-On",
    imageUrl: imageUrl || null,
    lookConfig,
    moodlook: {
      provider: "Perfect Corp Makeup Virtual Try-On",
      resultImageUrl: null
    }
  };
}

export default router;
