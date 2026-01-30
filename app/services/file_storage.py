# app/services/file_storage.py
import boto3
from botocore.exceptions import ClientError
from app.core.config import settings


class FileStorageService:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION_NAME
        )
        self.bucket_name = settings.AWS_S3_BUCKET_NAME

    async def upload_file(self, file_content: bytes, file_name: str, content_type: str) -> str:
        """Upload file to S3 and return public URL."""
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_name,
                Body=file_content,
                ContentType=content_type
            )
            return f"https://{self.bucket_name}.s3.{settings.AWS_REGION_NAME}.amazonaws.com/{file_name}"
        except ClientError as e:
            raise Exception(f"S3 upload failed: {str(e)}")

    async def remove_file(self, file_url: str) -> bool:
        """Remove file from S3 using the public URL."""
        try:
            # Extract the key from the URL
            # URL format: https://bucket-name.s3.region.amazonaws.com/key
            key = file_url.split('.amazonaws.com/')[-1]

            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return True
        except ClientError as e:
            raise Exception(f"S3 deletion failed: {str(e)}")


file_storage_service = FileStorageService()
