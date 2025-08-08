"""
S3 utility functions for media asset management
"""

import os
import boto3
from pathlib import Path
from typing import Optional, BinaryIO
from botocore.exceptions import ClientError, NoCredentialsError


class S3Manager:
    """S3 manager for media asset uploads and retrieval"""
    
    def __init__(self):
        self.bucket_name = os.getenv("S3_BUCKET_NAME", "story-skeleton-media")
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.endpoint_url = os.getenv("S3_ENDPOINT_URL")  # For minio/local development
        
        # Initialize S3 client
        if self.endpoint_url:
            # Local development with minio
            self.s3_client = boto3.client(
                's3',
                endpoint_url=self.endpoint_url,
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "minioadmin"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "minioadmin"),
                region_name=self.region
            )
        else:
            # Production AWS S3
            self.s3_client = boto3.client('s3', region_name=self.region)
    
    def upload_file(self, file_path: str, s3_key: str, content_type: Optional[str] = None) -> str:
        """Upload a file to S3 and return the URL"""
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            
            self.s3_client.upload_file(file_path, self.bucket_name, s3_key, ExtraArgs=extra_args)
            
            if self.endpoint_url:
                # Local minio URL
                return f"{self.endpoint_url}/{self.bucket_name}/{s3_key}"
            else:
                # AWS S3 URL
                return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"
                
        except (ClientError, NoCredentialsError) as e:
            print(f"❌ S3 upload failed: {e}")
            raise
    
    def upload_bytes(self, data: bytes, s3_key: str, content_type: Optional[str] = None) -> str:
        """Upload bytes data to S3 and return the URL"""
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=data,
                **extra_args
            )
            
            if self.endpoint_url:
                # Local minio URL
                return f"{self.endpoint_url}/{self.bucket_name}/{s3_key}"
            else:
                # AWS S3 URL
                return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"
                
        except (ClientError, NoCredentialsError) as e:
            print(f"❌ S3 upload failed: {e}")
            raise
    
    def file_exists(self, s3_key: str) -> bool:
        """Check if a file exists in S3"""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError:
            return False
    
    def delete_file(self, s3_key: str) -> bool:
        """Delete a file from S3"""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            print(f"❌ S3 delete failed: {e}")
            return False


# Global S3 manager instance
s3_manager = S3Manager() 

if __name__ == "__main__":
    # Minimal test: upload a file to MinIO
    import sys
    test_file = "test_minio_upload.txt"
    with open(test_file, "w") as f:
        f.write("Hello MinIO!\n")
    s3_key = "test_uploads/test_minio_upload.txt"
    try:
        url = s3_manager.upload_file(test_file, s3_key, content_type="text/plain")
        print(f"✅ Upload succeeded! S3 URL: {url}")
    except Exception as e:
        print(f"❌ Upload failed: {e}")

    # Test uploading a binary file (e.g., a small JPEG)
    img_path = "uploads/placeholder.jpg"
    if os.path.exists(img_path):
        with open(img_path, "rb") as f:
            data = f.read()
        try:
            url = s3_manager.upload_bytes(data, "test_uploads/placeholder.jpg", content_type="image/jpeg")
            print(f"✅ Binary upload succeeded! S3 URL: {url}")
        except Exception as e:
            print(f"❌ Binary upload failed: {e}")
    else:
        print("No placeholder.jpg found for binary upload test.") 