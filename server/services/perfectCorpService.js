import axios from "axios";
import crypto from "node:crypto";

const skinConcerns = [
  "acne",
  "dark_circle_v2",
  "eye_bag",
  "moisture",
  "pore",
  "redness",
  "texture",
  "firmness",
  "oiliness",
  "radiance",
  "age_spot",
  "wrinkle"
];

const pollDelayMs = 2500;
const maxPollAttempts = 18;
let cachedAccessToken = null;
let cachedAccessTokenExpiresAt = 0;

function assertPerfectCorpEnv() {
  const required = ["PERFECT_CORP_API_KEY", "PERFECT_CORP_SKIN_ANALYSIS_URL"];
  const missing = required.filter((key) => !process.env[key]);

  if (missing.length) {
    const error = new Error(`Missing Perfect Corp environment variables: ${missing.join(", ")}`);
    error.status = 500;
    throw error;
  }
}

export async function analyzeSkinWithPerfectCorp(imageUrl) {
  assertPerfectCorpEnv();

  const payload = {
    src_file_url: imageUrl,
    dst_actions: skinConcerns,
    format: "json",
    miniserver_args: {
      enable_mask_overlay: false
    }
  };

  const response = await postSkinAnalysisTask(payload);
  const body = response.data;
  const taskId = body?.data?.task_id;

  if (!taskId) {
    return body;
  }

  return pollSkinAnalysisTask(taskId);
}

export async function tryOnMakeupWithPerfectCorp({ imageUrl, lookConfig }) {
  assertPerfectCorpEnv();

  const payload = {
    src_file_url: imageUrl,
    effects: buildMakeupEffects(lookConfig),
    version: "1.0"
  };

  const response = await postPerfectCorpTask(makeupVtoTaskUrl(), payload);
  const body = response.data;
  const taskId = body?.data?.task_id;

  if (!taskId) {
    return withTryOnMetadata(body, payload);
  }

  const result = await pollPerfectCorpTask(makeupVtoTaskUrl(), taskId, "Perfect Corp makeup virtual try-on task failed.");
  return withTryOnMetadata(result, payload);
}

function perfectCorpClient() {
  return createPerfectCorpClient(process.env.PERFECT_CORP_API_KEY);
}

function createPerfectCorpClient(token) {
  return axios.create({
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json"
    },
    timeout: 45000
  });
}

async function postSkinAnalysisTask(payload) {
  return postPerfectCorpTask(skinAnalysisTaskUrl(), payload);
}

async function postPerfectCorpTask(url, payload) {
  try {
    return await perfectCorpClient().post(url, payload);
  } catch (error) {
    if (error.response?.data?.error_code !== "InvalidApiKey" || !process.env.PERFECT_CORP_API_SECRET) {
      throw error;
    }

    const accessToken = await getLegacyAccessToken();
    return createPerfectCorpClient(accessToken).post(url, payload);
  }
}

async function getLegacyAccessToken() {
  if (cachedAccessToken && Date.now() < cachedAccessTokenExpiresAt) {
    return cachedAccessToken;
  }

  const response = await axios.post(
    "https://yce-api-01.makeupar.com/s2s/v1.0/client/auth",
    {
      client_id: process.env.PERFECT_CORP_API_KEY,
      id_token: createPerfectCorpIdToken()
    },
    {
      headers: { "Content-Type": "application/json" },
      timeout: 20000
    }
  );

  const accessToken = response.data?.result?.access_token;

  if (!accessToken) {
    const error = new Error("Perfect Corp authentication did not return an access token.");
    error.status = 502;
    throw error;
  }

  cachedAccessToken = accessToken;
  cachedAccessTokenExpiresAt = Date.now() + 110 * 60 * 1000;
  return accessToken;
}

function createPerfectCorpIdToken() {
  const publicKey = crypto.createPublicKey({
    key: Buffer.from(process.env.PERFECT_CORP_API_SECRET, "base64"),
    format: "der",
    type: "spki"
  });
  const message = `client_id=${process.env.PERFECT_CORP_API_KEY}&timestamp=${Date.now()}`;

  return crypto
    .publicEncrypt({ key: publicKey, padding: crypto.constants.RSA_PKCS1_PADDING }, Buffer.from(message))
    .toString("base64");
}

function skinAnalysisTaskUrl() {
  return process.env.PERFECT_CORP_SKIN_ANALYSIS_URL.replace(/\/$/, "");
}

function makeupVtoTaskUrl() {
  return (process.env.PERFECT_CORP_MAKEUP_VTO_URL || "https://yce-api-01.makeupar.com/s2s/v2.0/task/makeup-vto").replace(/\/$/, "");
}

function taskStatusUrl(taskId) {
  return `${skinAnalysisTaskUrl()}/${encodeURIComponent(taskId)}`;
}

function taskStatusUrlFor(baseUrl, taskId) {
  return `${baseUrl}/${encodeURIComponent(taskId)}`;
}

function wait(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

async function pollSkinAnalysisTask(taskId) {
  return pollPerfectCorpTask(skinAnalysisTaskUrl(), taskId, "Perfect Corp skin analysis task failed.");
}

async function pollPerfectCorpTask(baseUrl, taskId, fallbackErrorMessage) {
  for (let attempt = 0; attempt < maxPollAttempts; attempt += 1) {
    if (attempt > 0) {
      await wait(pollDelayMs);
    }

    const response = await getPerfectCorpTask(baseUrl, taskId);
    const body = response.data;
    const taskStatus = body?.data?.task_status;

    if (taskStatus === "success") {
      return body;
    }

    if (taskStatus === "error" || taskStatus === "failed") {
      const error = new Error(
          body?.data?.error_message ||
          body?.data?.error?.message ||
          body?.data?.error ||
          fallbackErrorMessage
      );
      error.status = 502;
      throw error;
    }
  }

  const error = new Error("Perfect Corp skin analysis is still processing. Try again with the same image in a moment.");
  error.status = 504;
  throw error;
}

async function getSkinAnalysisTask(taskId) {
  return getPerfectCorpTask(skinAnalysisTaskUrl(), taskId);
}

async function getPerfectCorpTask(baseUrl, taskId) {
  try {
    return await perfectCorpClient().get(taskStatusUrlFor(baseUrl, taskId));
  } catch (error) {
    if (error.response?.data?.error_code !== "InvalidApiKey" || !process.env.PERFECT_CORP_API_SECRET) {
      throw error;
    }

    const accessToken = await getLegacyAccessToken();
    return createPerfectCorpClient(accessToken).get(taskStatusUrlFor(baseUrl, taskId));
  }
}

function buildMakeupEffects(lookConfig = {}) {
  const lookType = lookConfig.lookType || "everyday";
  const lipColors = {
    tired: "#B64B4D",
    date: "#B84A62",
    party: "#B01854",
    professional: "#9B5C61",
    glow: "#C06074",
    everyday: "#C06074"
  };

  return [
    {
      category: "lip_color",
      shape: {
        name: "m-shaped"
      },
      style: {
        type: "full"
      },
      morphology: {
        fullness: 0,
        wrinkless: 0
      },
      palettes: [
        {
          color: lipColors[lookType] || lipColors.everyday,
          texture: lookType === "party" ? "gloss" : "matte",
          colorIntensity: lookType === "professional" ? 42 : 55
        }
      ]
    }
  ];
}

function withTryOnMetadata(response, requestPayload) {
  return {
    ...response,
    moodlook: {
      provider: "Perfect Corp Makeup Virtual Try-On",
      requestPayload,
      resultImageUrl: findFirstImageUrl(response)
    }
  };
}

function findFirstImageUrl(value) {
  if (!value) return null;

  if (typeof value === "string") {
    return /^https?:\/\/.+\.(png|jpe?g|webp)(\?|$)/i.test(value) ? value : null;
  }

  if (Array.isArray(value)) {
    for (const item of value) {
      const found = findFirstImageUrl(item);
      if (found) return found;
    }
    return null;
  }

  if (typeof value === "object") {
    for (const item of Object.values(value)) {
      const found = findFirstImageUrl(item);
      if (found) return found;
    }
  }

  return null;
}
