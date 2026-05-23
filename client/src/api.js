import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000";

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 45000
});

export async function analyzeSkin(file) {
  const formData = new FormData();
  formData.append("image", file);

  const response = await client.post("/api/analyze-skin", formData, {
    headers: { "Content-Type": "multipart/form-data" }
  });

  return response.data;
}

export async function requestVirtualTryOn(payload) {
  const response = await client.post("/api/virtual-try-on", payload);
  return response.data;
}

export async function fetchProducts(params = {}) {
  const response = await client.get("/api/products", { params });
  return response.data;
}
