import express from "express";
import cors from "cors";
import skinAnalysisRouter from "./routes/skinAnalysis.js";
import virtualTryOnRouter from "./routes/virtualTryOn.js";
import productsRouter from "./routes/products.js";

const app = express();
const allowedOrigins = (process.env.CORS_ORIGIN || "")
  .split(",")
  .map((origin) => origin.trim())
  .filter(Boolean);

app.use(cors({
  origin(origin, callback) {
    if (!allowedOrigins.length || !origin || allowedOrigins.includes(origin)) {
      callback(null, true);
      return;
    }

    callback(new Error("This origin is not allowed by the MoodLook API."));
  }
}));
app.use(express.json({ limit: "2mb" }));

app.get("/api/health", (_req, res) => {
  res.json({ status: "ok", service: "MoodLook API" });
});

app.use("/api/analyze-skin", skinAnalysisRouter);
app.use("/api/virtual-try-on", virtualTryOnRouter);
app.use("/api/products", productsRouter);

app.use((err, _req, res, _next) => {
  console.error(err);
  const status = err.status || 500;
  res.status(status).json({
    error: true,
    message: err.message || "Something went wrong in the MoodLook API."
  });
});

export default app;
