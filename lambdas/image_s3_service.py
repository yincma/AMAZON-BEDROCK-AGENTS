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

    def save_image(self, image_data: bytes, presentation_id: str, slide_number: int) -> str:
        """保存图片到S3，兼容旧接口"""
        key = f"presentations/{presentation_id}/slides/{slide_number}/image.png"
        return self.upload_image(image_data, key)

    def save_image_with_retry(self, image_data: bytes, presentation_id: str, slide_number: int, max_retries: int = 3) -> dict:
        """带重试机制保存图片"""
        import time

        for attempt in range(max_retries):
            try:
                url = self.save_image(image_data, presentation_id, slide_number)
                return {'success': True, 'url': url, 'attempts': attempt + 1}
            except Exception as e:
                if attempt == max_retries - 1:
                    return {'success': False, 'error': str(e), 'attempts': max_retries}
                time.sleep(2 ** attempt)  # 指数退避

    def save_image_with_metadata(self, image_data: bytes, metadata: dict, presentation_id: str, slide_number: int) -> dict:
        """保存带元数据的图片"""
        key = f"presentations/{presentation_id}/slides/{slide_number}/image.png"

        # 将元数据作为标签添加到S3对象
        tags = '&'.join([f"{k}={v}" for k, v in metadata.items()])

        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=image_data,
            ContentType='image/png',
            Tagging=tags
        )

        return {
            'success': True,
            'url': f"s3://{self.bucket_name}/{key}",
            'metadata': metadata
        }
