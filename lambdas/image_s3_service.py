"""
S3服务处理
"""
import boto3
import uuid
from typing import Optional

class S3Service:
    def __init__(self, bucket_name: str):
        self.s3_client = boto3.client('s3')
        self.bucket_name = bucket_name
    
    def upload_image(self, image_data: bytes, key: Optional[str] = None) -> str:
        """上传图片到S3"""
        if not key:
            key = f"images/{uuid.uuid4()}.png"
        
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=image_data,
            ContentType='image/png'
        )
        
        return f"s3://{self.bucket_name}/{key}"
    
    def get_image_url(self, key: str, expiry: int = 3600) -> str:
        """获取预签名URL"""
        return self.s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.bucket_name, 'Key': key},
            ExpiresIn=expiry
        )
