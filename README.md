# MoodLook - Skin-Aware AR Beauty Shopping Assistant

MoodLook is a full-stack hackathon MVP for the Perfect Corp challenge, "Building the Next Generation of AI-Driven Consumer Experiences."

The app helps a beauty shopper answer: "What makeup look should I wear today based on how my skin actually looks?" A user uploads a face photo, MoodLook analyzes visible skin concerns through Perfect Corp-style skin analysis, combines the result with the user's mood or occasion, creates a personalized beauty look, prepares an AR try-on handoff, and shows shoppable product recommendations.

MoodLook is not a medical app. It does not diagnose, treat, or cure anything. The experience uses consumer beauty language such as visible skin concerns, skin state, focus area, beauty goal, and product routine.

## Hackathon Alignment

- Uses Perfect Corp AI Skin Analysis as the core intelligence layer.
- Shows a clear consumer shopping journey: face scan, skin state, personalized look, AR try-on, product routine.
- Includes a placeholder endpoint and UI state ready for Perfect Corp Makeup Virtual Try-On.
- Demonstrates retail value with product cards tied to the user's skin state and occasion.

## APIs Used

- Perfect Corp AI Skin Analysis: `POST /api/analyze-skin` uploads an image to Cloudinary, then sends the hosted image URL to Perfect Corp through `src_file_url`.
- Perfect Corp Makeup Virtual Try-On: `POST /api/virtual-try-on` is implemented as a mock integration point until exact endpoint details are available.
- Cloudinary: temporary hosted image storage for the Perfect Corp request.

## Project Structure

```text
client/
  src/
    components/
    data/
    styles/
    utils/
server/
  middleware/
  routes/
  services/
```

## Environment Variables

Create `server/.env` from `server/.env.example`:

```bash
PORT=5000
PERFECT_CORP_API_KEY=your_perfect_corp_api_key
PERFECT_CORP_SKIN_ANALYSIS_URL=your_skin_analysis_endpoint
CLOUDINARY_CLOUD_NAME=your_cloudinary_cloud_name
CLOUDINARY_API_KEY=your_cloudinary_api_key
CLOUDINARY_API_SECRET=your_cloudinary_api_secret
```

Create `client/.env` from `client/.env.example`:

```bash
VITE_API_BASE_URL=http://localhost:5000
```

Do not put Perfect Corp keys in the frontend.

## Run Locally

Backend:

```bash
cd server
npm install
npm run dev
```

Frontend:

```bash
cd client
npm install
npm run dev
```

Open the Vite URL shown in the terminal, usually `http://localhost:5173`.

## Demo Mode

Demo Mode is enabled by default so the app can be shown without spending Perfect Corp API credits. It uses `client/src/data/sampleSkinResponse.js`, which mirrors the real response shape from the Perfect Corp Playground:

- Some records use `ui_score`.
- Summary records use `score`.
- Mask URLs may be present or missing.
- `all`, `skin_age`, and `resize_image` are normalized separately.

Turn Demo Mode off to upload a real photo and call the backend.

## 90-Second Demo Flow

1. Open MoodLook.
2. Keep Demo Mode enabled or upload a face image.
3. Select "I look tired" or type "I look tired and have a dinner tonight."
4. Click "Analyze and Build My Look."
5. Review the skin score dashboard and focus areas.
6. Review the personalized prep and makeup routine.
7. View mask previews.
8. Click "Try This Look with AR."
9. Show the virtual try-on integration placeholder.
10. End with "Shop this routine."

## Future Improvements

- Replace the virtual try-on mock with the live Perfect Corp Makeup Virtual Try-On endpoint.
- Add account-based saved routines and product carts.
- Connect product cards to a live retailer catalog.
- Add camera capture in addition to file upload.
- Add analytics events for scan, try-on, and product intent.
