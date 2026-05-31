import boto3
from botocore.config import Config

from app.config import settings

client: boto3.client | None = None


def get_minio() -> boto3.client:
    global client
    if client is None:
        client = boto3.client(
            "s3",
            endpoint_url=f"http://{settings.minio_endpoint}",
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )
    return client


def download_media(bucket: str, key: str) -> bytes:
    s3 = get_minio()
    response = s3.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()
