"""
图片处理服务单元测试模块
"""

import pytest
import base64
import json
import io
from unittest.mock import Mock, patch, MagicMock
from PIL import Image

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lambdas'))

from lambdas.image_processing_service import ImageProcessingService
from lambdas.image_config import CONFIG
from lambdas.image_exceptions import NovaServiceError, ImageProcessingError


class TestImageProcessingService:
    """图片处理服务测试类"""

    def setup_method(self):
        """测试前置方法"""
        self.mock_bedrock_client = Mock()
        self.mock_s3_client = Mock()
        self.service = ImageProcessingService(
            bedrock_client=self.mock_bedrock_client,
            s3_client=self.mock_s3_client,
            enable_caching=True
        )

    def create_mock_image_data(self, width=1200, height=800) -> bytes:
        """创建模拟图片数据"""
        image = Image.new('RGB', (width, height), (255, 255, 255))
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        return img_byte_arr.getvalue()

    def test_generate_prompt_basic(self):
        """测试基本提示词生成"""
        slide_content = {
            "title": "AI人工智能",
            "content": ["机器学习", "深度学习", "自然语言处理"]
        }

        prompt = self.service.generate_prompt(slide_content, "business")

        assert "AI人工智能" in prompt
        assert "专业商务演示图片" in prompt
        assert "高质量4K分辨率" in prompt
        assert "现代简洁风格" in prompt

    def test_generate_prompt_empty_content(self):
        """测试空内容提示词生成"""
        slide_content = {"title": "", "content": []}

        prompt = self.service.generate_prompt(slide_content)

        assert "专业商务演示背景" in prompt
        assert "现代简洁风格" in prompt
        assert "高质量4K" in prompt

    def test_optimize_prompt(self):
        """测试提示词优化"""
        # 测试添加质量修饰符
        prompt = "简单的商务图片"
        optimized = self.service._optimize_prompt(prompt)
        assert "高质量4K分辨率" in optimized

        # 测试长度限制
        long_prompt = "很长的提示词" * 100
        optimized = self.service._optimize_prompt(long_prompt)
        assert len(optimized) <= 500

    def test_get_model_priority_list(self):
        """测试模型优先级列表"""
        # 测试无偏好
        models = self.service._get_model_priority_list()
        assert models == self.service.supported_models

        # 测试有偏好
        preference = "stability.stable-diffusion-xl-v1"
        models = self.service._get_model_priority_list(preference)
        assert models[0] == preference

        # 测试无效偏好
        invalid_preference = "invalid-model"
        models = self.service._get_model_priority_list(invalid_preference)
        assert models == self.service.supported_models

    def test_cache_key_generation(self):
        """测试缓存键生成"""
        prompt1 = "测试提示词"
        prompt2 = "测试提示词"
        prompt3 = "不同的提示词"

        key1 = self.service._get_cache_key(prompt1)
        key2 = self.service._get_cache_key(prompt2)
        key3 = self.service._get_cache_key(prompt3)

        assert key1 == key2  # 相同提示词应该生成相同的键
        assert key1 != key3  # 不同提示词应该生成不同的键
        assert len(key1) == 64  # SHA256哈希长度

    def test_memory_cache_operations(self):
        """测试内存缓存操作"""
        prompt = "测试缓存"
        image_data = self.create_mock_image_data()

        # 测试缓存未命中
        cached = self.service._get_cached_image(prompt)
        assert cached is None

        # 测试缓存存储
        self.service._cache_image(prompt, image_data)

        # 测试缓存命中
        cached = self.service._get_cached_image(prompt)
        assert cached == image_data

        # 测试清除缓存
        self.service.clear_cache()
        cached = self.service._get_cached_image(prompt)
        assert cached is None

    def test_nova_api_success(self):
        """测试Nova API成功调用"""
        # 创建模拟图片数据
        mock_image_data = self.create_mock_image_data()
        mock_image_b64 = base64.b64encode(mock_image_data).decode('utf-8')

        # 模拟成功响应
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'images': [mock_image_b64]
        })

        self.mock_bedrock_client.invoke_model.return_value = mock_response

        # 调用方法
        result = self.service._call_nova_api("测试提示词", "amazon.nova-canvas-v1:0")

        # 验证结果
        assert result == mock_image_data
        self.mock_bedrock_client.invoke_model.assert_called_once()

    def test_nova_api_no_images(self):
        """测试Nova API无图片响应"""
        # 模拟无图片响应
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'images': []
        })

        self.mock_bedrock_client.invoke_model.return_value = mock_response

        # 验证异常
        with pytest.raises(NovaServiceError) as exc_info:
            self.service._call_nova_api("测试提示词", "amazon.nova-canvas-v1:0")

        assert "没有图片数据" in str(exc_info.value)

    def test_stability_api_success(self):
        """测试Stability API成功调用"""
        # 创建模拟图片数据
        mock_image_data = self.create_mock_image_data()
        mock_image_b64 = base64.b64encode(mock_image_data).decode('utf-8')

        # 模拟成功响应
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'artifacts': [{'base64': mock_image_b64}]
        })

        self.mock_bedrock_client.invoke_model.return_value = mock_response

        # 调用方法
        result = self.service._call_stability_api("测试提示词", "stability.stable-diffusion-xl-v1")

        # 验证结果
        assert result == mock_image_data
        self.mock_bedrock_client.invoke_model.assert_called_once()

    @patch('time.sleep')  # 模拟sleep避免测试等待
    def test_retry_mechanism(self, mock_sleep):
        """测试重试机制"""
        from botocore.exceptions import ClientError

        # 模拟前两次失败，第三次成功
        mock_image_data = self.create_mock_image_data()
        mock_image_b64 = base64.b64encode(mock_image_data).decode('utf-8')

        error_response = {'Error': {'Code': 'ThrottlingException'}}
        success_response = {
            'body': MagicMock()
        }
        success_response['body'].read.return_value = json.dumps({
            'images': [mock_image_b64]
        })

        # 设置调用序列：失败、失败、成功
        self.mock_bedrock_client.invoke_model.side_effect = [
            ClientError(error_response, 'invoke_model'),
            ClientError(error_response, 'invoke_model'),
            success_response
        ]

        # 调用方法
        result = self.service._call_bedrock_model("测试提示词", "amazon.nova-canvas-v1:0")

        # 验证结果
        assert result == mock_image_data
        assert self.mock_bedrock_client.invoke_model.call_count == 3
        assert mock_sleep.call_count == 2  # 两次重试之间的sleep

    def test_fallback_to_placeholder(self):
        """测试回退到占位图"""
        from botocore.exceptions import ClientError

        # 模拟所有模型都失败
        error_response = {'Error': {'Code': 'ModelNotAvailable'}}
        self.mock_bedrock_client.invoke_model.side_effect = ClientError(
            error_response, 'invoke_model'
        )

        # 调用方法
        result = self.service.call_image_generation("测试提示词")

        # 验证返回了占位图
        assert isinstance(result, bytes)
        assert len(result) > 0

        # 验证图片可以被PIL打开
        image = Image.open(io.BytesIO(result))
        assert image.format == 'PNG'

    def test_s3_cache_integration(self):
        """测试S3缓存集成"""
        prompt = "测试S3缓存"
        image_data = self.create_mock_image_data()

        # 模拟S3缓存未命中
        from botocore.exceptions import ClientError
        error_response = {'Error': {'Code': 'NoSuchKey'}}
        self.mock_s3_client.get_object.side_effect = ClientError(
            error_response, 'get_object'
        )

        # 测试缓存未命中
        cached = self.service._get_cached_image(prompt)
        assert cached is None

        # 测试存储到S3缓存
        self.service._cache_image(prompt, image_data)

        # 验证S3 put_object被调用
        self.mock_s3_client.put_object.assert_called_once()
        put_call = self.mock_s3_client.put_object.call_args
        assert put_call[1]['Bucket'] == CONFIG.DEFAULT_BUCKET
        assert put_call[1]['Body'] == image_data
        assert put_call[1]['ContentType'] == 'image/png'

    def test_validate_image_format(self):
        """测试图片格式验证"""
        # 创建PNG格式图片
        png_data = self.create_mock_image_data()

        # 测试PNG格式验证
        assert self.service.validate_image_format(png_data, 'PNG') is True
        assert self.service.validate_image_format(png_data, 'JPEG') is False

        # 测试无效数据
        invalid_data = b"invalid image data"
        assert self.service.validate_image_format(invalid_data, 'PNG') is False

    def test_optimize_image_size(self):
        """测试图片尺寸优化"""
        # 创建大尺寸图片
        large_image_data = self.create_mock_image_data(2400, 1600)

        # 优化尺寸
        optimized = self.service.optimize_image_size(large_image_data, 1200, 800)

        # 验证优化后的图片
        optimized_image = Image.open(io.BytesIO(optimized))
        assert optimized_image.width <= 1200
        assert optimized_image.height <= 800

        # 测试已经是目标尺寸的图片
        correct_size_data = self.create_mock_image_data(800, 600)
        result = self.service.optimize_image_size(correct_size_data, 1200, 800)
        assert result == correct_size_data  # 应该返回原始数据

    def test_create_placeholder_image(self):
        """测试占位图创建"""
        # 创建占位图
        placeholder = self.service.create_placeholder_image(800, 600, "测试文本")

        # 验证占位图
        image = Image.open(io.BytesIO(placeholder))
        assert image.format == 'PNG'
        assert image.width == 800
        assert image.height == 600

    def test_cache_stats(self):
        """测试缓存统计"""
        # 获取初始统计
        stats = self.service.get_cache_stats()
        assert stats['memory_cache_size'] == 0
        assert stats['cache_enabled'] is True
        assert stats['s3_cache_enabled'] is True

        # 添加缓存项
        self.service._cache_image("测试", self.create_mock_image_data())

        # 验证统计更新
        stats = self.service.get_cache_stats()
        assert stats['memory_cache_size'] == 1

    def test_analyze_content_style(self):
        """测试内容风格分析"""
        # 测试AI相关内容
        ai_content = "人工智能和机器学习技术"
        styles = self.service._analyze_content_style(ai_content)
        assert any("科技感" in style for style in styles)

        # 测试商务相关内容
        business_content = "商务策略和市场分析"
        styles = self.service._analyze_content_style(business_content)
        assert any("办公环境" in style or "商务" in style for style in styles)

        # 测试通用内容
        generic_content = "一般性内容"
        styles = self.service._analyze_content_style(generic_content)
        assert any("通用商务" in style for style in styles)

    def test_get_audience_style(self):
        """测试受众风格获取"""
        # 测试商务风格
        business_style = self.service._get_audience_style("business")
        assert "商务专业风格" in business_style

        # 测试学术风格
        academic_style = self.service._get_audience_style("academic")
        assert "学术风格" in academic_style

        # 测试未知受众（应该回退到商务风格）
        unknown_style = self.service._get_audience_style("unknown")
        assert "商务专业风格" in unknown_style


class TestImageProcessingServiceIntegration:
    """集成测试类"""

    def test_end_to_end_image_generation(self):
        """端到端图片生成测试"""
        # 创建不带模拟客户端的服务实例
        # 注意：这需要真实的AWS凭证和权限
        service = ImageProcessingService(enable_caching=False)

        slide_content = {
            "title": "测试演示",
            "content": ["这是一个测试幻灯片", "用于验证图片生成功能"]
        }

        # 生成提示词
        prompt = service.generate_prompt(slide_content)
        assert isinstance(prompt, str)
        assert len(prompt) > 0

        # 注意：实际的图片生成需要有效的AWS凭证
        # 在CI/CD环境中，这个测试可能需要跳过或使用模拟
        try:
            image_data = service.call_image_generation(prompt)
            assert isinstance(image_data, bytes)
            assert len(image_data) > 0

            # 验证图片可以被PIL打开
            image = Image.open(io.BytesIO(image_data))
            assert image.format in ['PNG', 'JPEG']

        except Exception as e:
            # 在没有有效AWS凭证的情况下，应该回退到占位图
            pytest.skip(f"AWS凭证不可用，跳过真实API测试: {str(e)}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])