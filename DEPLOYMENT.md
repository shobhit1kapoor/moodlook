# MoodLook Deployment

Recommended hackathon setup:

- Backend: Render Web Service, Railway, or any Node host
- Frontend: Vercel Static/Vite project

## Backend Environment Variables

Set these on the backend host:

```bash
PORT=5000
CORS_ORIGIN=https://your-frontend-domain.vercel.app
PERFECT_CORP_API_KEY=your_perfect_corp_api_key
PERFECT_CORP_API_SECRET=your_optional_perfect_corp_secret_key
PERFECT_CORP_SKIN_ANALYSIS_URL=https://yce-api-01.makeupar.com/s2s/v2.1/task/skin-analysis
PERFECT_CORP_MAKEUP_VTO_URL=https://yce-api-01.makeupar.com/s2s/v2.0/task/makeup-vto
CLOUDINARY_CLOUD_NAME=your_cloudinary_cloud_name
CLOUDINARY_API_KEY=your_cloudinary_api_key
CLOUDINARY_API_SECRET=your_cloudinary_api_secret
```

Backend commands:

```bash
cd server
npm install
npm start
```

Health check:

```text
https://your-backend-domain/api/health
```

## Frontend Environment Variables

Set this on the frontend host:

```bash
VITE_API_BASE_URL=https://your-backend-domain
```

Frontend commands:

```bash
cd client
npm install
npm run build
```

Build output directory:

```text
dist
```

## Vercel Frontend Settings

If importing the repo into Vercel:

- Root Directory: `client`
- Framework Preset: `Vite`
- Build Command: `npm run build`
- Output Directory: `dist`
- Environment Variable: `VITE_API_BASE_URL`

## Render Backend Settings

If importing the repo into Render:

- Root Directory: `server`
- Runtime: `Node`
- Build Command: `npm install`
- Start Command: `npm start`
- Health Check Path: `/api/health`
- Environment Variables: use the backend list above

After the frontend deploys, copy the frontend URL into backend `CORS_ORIGIN`.
