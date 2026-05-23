import { Router } from "express";
import { upload } from "../middleware/upload.js";
import { uploadImageToCloudinary } from "../services/cloudinaryService.js";
import { analyzeSkinWithPerfectCorp } from "../services/perfectCorpService.js";

const router = Router();

router.post("/", upload.single("image"), async (req, res, next) => {
  try {
    if (!req.file) {
      return res.status(400).json({
        error: true,
        message: "Upload a face image using the image field."
      });
    }

    const uploadedImage = await uploadImageToCloudinary(req.file.buffer);
    const perfectCorpResponse = await analyzeSkinWithPerfectCorp(uploadedImage.analysis_url || uploadedImage.secure_url);

    res.json(perfectCorpResponse);
  } catch (error) {
    const status = error.status || error.response?.status || 500;
    const providerError = error.response?.data;
    const message =
      providerError?.message ||
      providerError?.error ||
      providerError?.error_message ||
      error.message ||
      "Skin analysis failed.";

    res.status(status).json({
      error: true,
      message,
      provider: providerError?.error_code ? "Perfect Corp" : undefined,
      providerErrorCode: providerError?.error_code
    });
  }
});

export default router;
