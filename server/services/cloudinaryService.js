import { v2 as cloudinary } from "cloudinary";

function assertCloudinaryEnv() {
  const required = ["CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET"];
  const missing = required.filter((key) => !process.env[key]);

  if (missing.length) {
    const error = new Error(`Missing Cloudinary environment variables: ${missing.join(", ")}`);
    error.status = 500;
    throw error;
  }
}

export async function uploadImageToCloudinary(fileBuffer) {
  assertCloudinaryEnv();

  cloudinary.config({
    cloud_name: process.env.CLOUDINARY_CLOUD_NAME,
    api_key: process.env.CLOUDINARY_API_KEY,
    api_secret: process.env.CLOUDINARY_API_SECRET
  });

  return new Promise((resolve, reject) => {
    const stream = cloudinary.uploader.upload_stream(
      {
        folder: "moodlook/uploads",
        resource_type: "image"
      },
      (error, result) => {
        if (error) {
          reject(error);
          return;
        }

        resolve({
          ...result,
          analysis_url: cloudinary.url(result.public_id, {
            secure: true,
            format: "jpg",
            transformation: [{ quality: "auto" }]
          })
        });
      }
    );

    stream.end(fileBuffer);
  });
}
