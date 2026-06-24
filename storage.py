import boto3
import os
from botocore.exceptions import ClientError
from config import QAConfig

class S3Manager:
    _client = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            cfg = QAConfig.get_s3_config()
            if not (cfg["access_key"] and cfg["secret_key"]):
                return None
            
            kwargs = {
                "aws_access_key_id": cfg["access_key"],
                "aws_secret_access_key": cfg["secret_key"],
                "region_name": cfg["region"],
            }
            if cfg["endpoint_url"]:
                kwargs["endpoint_url"] = cfg["endpoint_url"]
                
            cls._client = boto3.client("s3", **kwargs)
        return cls._client

    @classmethod
    def upload_file(cls, local_path: str, s3_key: str) -> str:
        """Uploads a file to S3 and returns the S3 URL or key."""
        client = cls.get_client()
        if not client:
            raise RuntimeError("S3 client is not configured")
        
        cfg = QAConfig.get_s3_config()
        bucket = cfg["bucket"]
        
        try:
            client.upload_file(local_path, bucket, s3_key)
            if cfg["endpoint_url"]:
                endpoint = cfg["endpoint_url"].rstrip("/")
                url = f"{endpoint}/{bucket}/{s3_key}"
            else:
                url = f"https://{bucket}.s3.{cfg['region']}.amazonaws.com/{s3_key}"
            return url
        except ClientError as e:
            print(f"S3 Upload Error: {e}")
            raise

    @classmethod
    def download_file(cls, s3_key: str, local_path: str):
        """Downloads a file from S3 to local_path."""
        client = cls.get_client()
        if not client:
            raise RuntimeError("S3 client is not configured")
        
        cfg = QAConfig.get_s3_config()
        bucket = cfg["bucket"]
        
        try:
            client.download_file(bucket, s3_key, local_path)
        except ClientError as e:
            print(f"S3 Download Error: {e}")
            raise

    @classmethod
    def upload_bytes(cls, data: bytes, s3_key: str, content_type: str = "application/pdf") -> str:
        """Uploads raw bytes to S3 and returns the S3 URL."""
        client = cls.get_client()
        if not client:
            raise RuntimeError("S3 client is not configured")
        
        cfg = QAConfig.get_s3_config()
        bucket = cfg["bucket"]
        
        try:
            client.put_object(Body=data, Bucket=bucket, Key=s3_key, ContentType=content_type)
            if cfg["endpoint_url"]:
                endpoint = cfg["endpoint_url"].rstrip("/")
                url = f"{endpoint}/{bucket}/{s3_key}"
            else:
                url = f"https://{bucket}.s3.{cfg['region']}.amazonaws.com/{s3_key}"
            return url
        except ClientError as e:
            print(f"S3 Upload Bytes Error: {e}")
            raise

    @classmethod
    def generate_presigned_url(cls, s3_key: str, expiration: int = 3600) -> str:
        """Generates a secure pre-signed GET URL for a private S3 object (e.g. for audio/PDF)."""
        client = cls.get_client()
        if not client:
            return ""
        
        cfg = QAConfig.get_s3_config()
        bucket = cfg["bucket"]
        
        try:
            response = client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': s3_key},
                ExpiresIn=expiration
            )
            return response
        except ClientError as e:
            print(f"Error generating S3 pre-signed URL: {e}")
            return ""
