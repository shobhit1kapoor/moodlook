import { useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import Header from "./components/Header";
import UploadCard from "./components/UploadCard";
import MoodSelector from "./components/MoodSelector";
import SkinDashboard from "./components/SkinDashboard";
import MaskPreviewGrid from "./components/MaskPreviewGrid";
import RecommendationPanel from "./components/RecommendationPanel";
import LookPreview from "./components/LookPreview";
import ProductRecommendations from "./components/ProductRecommendations";
import { analyzeSkin, requestVirtualTryOn } from "./api";
import { sampleSkinResponse } from "./data/sampleSkinResponse";
import { normalizeSkinResults } from "./utils/normalizeSkinResults";
import { generateRecommendation } from "./utils/skinRecommendationEngine";
import { getProductRecommendations } from "./utils/productRecommendationEngine";

export default function App() {
  const scanRef = useRef(null);
  const [demoMode, setDemoMode] = useState(true);
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [selectedMood, setSelectedMood] = useState("I look tired");
  const [customMood, setCustomMood] = useState("I look tired and have a dinner tonight");
  const [loading, setLoading] = useState(false);
  const [tryOnLoading, setTryOnLoading] = useState(false);
  const [error, setError] = useState("");
  const [normalizedResults, setNormalizedResults] = useState(null);
  const [recommendation, setRecommendation] = useState(null);
  const [tryOnResult, setTryOnResult] = useState(null);

  const effectiveMood = useMemo(() => customMood.trim() || selectedMood, [customMood, selectedMood]);
  const products = useMemo(
    () => getProductRecommendations(normalizedResults, recommendation, effectiveMood),
    [normalizedResults, recommendation, effectiveMood]
  );

  function handleFileChange(file) {
    setSelectedFile(file);
    setTryOnResult(null);
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setPreviewUrl(file ? URL.createObjectURL(file) : "");
  }

  async function handleAnalyze() {
    setError("");
    setTryOnResult(null);

    if (!demoMode && !selectedFile) {
      setError("Choose a face image or turn on Demo Mode to continue.");
      return;
    }

    try {
      setLoading(true);
      const response = demoMode ? sampleSkinResponse : await analyzeSkin(selectedFile);

      if (response?.status && response.status !== 200) {
        throw new Error("The skin analysis service returned an unexpected response.");
      }

      const normalized = normalizeSkinResults(response);
      if (!normalized.concerns.length) {
        throw new Error("No skin concerns were returned. Try another image or use demo mode.");
      }

      const nextRecommendation = generateRecommendation(normalized, effectiveMood);
      setNormalizedResults(normalized);
      setRecommendation(nextRecommendation);
    } catch (err) {
      setError(err?.response?.data?.message || err.message || "Skin analysis failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  async function handleTryOn() {
    if (!recommendation) return;

    try {
      setTryOnLoading(true);
      const imageUrl = normalizedResults?.analyzedImage || previewUrl || "demo-mode-image";
      const response = await requestVirtualTryOn({
        imageUrl,
        lookConfig: recommendation.tryOnConfig,
        demoMode
      });
      setTryOnResult(response);
    } catch (err) {
      setTryOnResult({
        status: "error",
        message: err?.response?.data?.message || "Virtual try-on failed. Try a live analyzed image or use demo mode.",
        lookConfig: recommendation.tryOnConfig
      });
    } finally {
      setTryOnLoading(false);
    }
  }

  function scrollToScan() {
    scanRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <div className="min-h-screen bg-cream text-charcoal">
      <Header onStart={scrollToScan} />
      <main ref={scanRef} className="mx-auto flex max-w-7xl flex-col gap-6 px-5 py-10 md:px-8">
        <div className="grid gap-6 lg:grid-cols-[1.08fr_0.92fr]">
          <UploadCard
            demoMode={demoMode}
            onDemoModeChange={setDemoMode}
            selectedFile={selectedFile}
            previewUrl={previewUrl}
            onFileChange={handleFileChange}
            onAnalyze={handleAnalyze}
            loading={loading}
            error={error}
          />
          <MoodSelector
            selectedMood={selectedMood}
            customMood={customMood}
            onMoodChange={setSelectedMood}
            onCustomMoodChange={setCustomMood}
          />
        </div>

        <AnimatePresence>
          {normalizedResults && recommendation ? (
            <motion.div
              className="flex flex-col gap-6"
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 18 }}
              transition={{ duration: 0.35 }}
            >
              <SkinDashboard normalizedResults={normalizedResults} />
              <RecommendationPanel recommendation={recommendation} />
              <MaskPreviewGrid concerns={normalizedResults.concerns} />
              <LookPreview
                recommendation={recommendation}
                mood={effectiveMood}
                onTryOn={handleTryOn}
                tryOnResult={tryOnResult}
                loading={tryOnLoading}
              />
              <ProductRecommendations products={products} />
            </motion.div>
          ) : null}
        </AnimatePresence>
      </main>
    </div>
  );
}
