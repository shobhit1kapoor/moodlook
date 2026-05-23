import multer from "multer";
import path from "node:path";

const storage = multer.memoryStorage();
const allowedImageExtensions = new Set([".jpg", ".jpeg", ".png", ".webp", ".avif", ".heic", ".heif"]);

export const upload = multer({
  storage,
  limits: {
    fileSize: 8 * 1024 * 1024
  },
  fileFilter: (_req, file, callback) => {
    const extension = path.extname(file.originalname || "").toLowerCase();

    if (!file.mimetype.startsWith("image/") && !allowedImageExtensions.has(extension)) {
      callback(new Error("Please upload an image file."));
      return;
    }

    callback(null, true);
  }
});
