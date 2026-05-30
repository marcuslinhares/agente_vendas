import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";

const MINIO_ENDPOINT = process.env.MINIO_ENDPOINT || "localhost:9000";
const MINIO_ACCESS_KEY = process.env.MINIO_ACCESS_KEY || "minioadmin";
const MINIO_SECRET_KEY = process.env.MINIO_SECRET_KEY || "minioadmin";

export const s3 = new S3Client({
  endpoint: `http://${MINIO_ENDPOINT}`,
  region: "us-east-1",
  credentials: {
    accessKeyId: MINIO_ACCESS_KEY,
    secretAccessKey: MINIO_SECRET_KEY,
  },
  forcePathStyle: true,
});

export async function uploadMedia(
  bucket: string,
  key: string,
  body: Buffer,
  contentType: string
): Promise<string> {
  await s3.send(
    new PutObjectCommand({
      Bucket: bucket,
      Key: key,
      Body: body,
      ContentType: contentType,
    })
  );
  return `http://${MINIO_ENDPOINT}/${bucket}/${key}`;
}
