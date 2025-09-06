#!/usr/bin/env python3
"""
Test Enhancement Strategy - Phase 2 Implementation
根据技术债务消除计划，提升测试覆盖率从29%到70%+
"""

import pytest
import json
import os
from unittest.mock import Mock, patch, MagicMock
from moto import mock_aws
import boto3

# 测试覆盖率提升策略
TEST_COVERAGE_STRATEGY = {
    "current_coverage": "29%",
    "target_coverage": "70%+",
    "priority_files": [
        {
            "file": "lambdas/factories/presentation_factory.py",
            "current": "0%",
            "target": "80%",
            "priority": "high",
            "reason": "Core business logic, 87 statements"
        },
        {
            "file": "lambdas/interfaces/presentation_controller_interface.py", 
            "current": "0%",
            "target": "70%",
            "priority": "high",
            "reason": "Controller interface, 114 statements"
        },
        {
            "file": "lambdas/utils/enhanced_config_manager.py",
            "current": "44%",
            "target": "85%",
            "priority": "medium",
            "reason": "Already partially covered, critical utility"
        },
        {
            "file": "lambdas/utils/image_processor.py",
            "current": "40%",
            "target": "75%",
            "priority": "medium", 
            "reason": "Image processing logic, 236 statements"
        }
    ]
}

class TestPresentationFactory:
    """
    Tests for presentation_factory.py (0% -> 80% coverage)
    重点测试核心业务逻辑
    """
    
    @pytest.fixture
    def mock_factory(self):
        """Mock presentation factory dependencies"""
        with mock_aws():
            # Mock AWS services
            s3 = boto3.client('s3', region_name='us-east-1')
            s3.create_bucket(Bucket='test-bucket')
            
            dynamodb = boto3.client('dynamodb', region_name='us-east-1')
            dynamodb.create_table(
                TableName='test-table',
                KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST'
            )
            
            yield {
                's3': s3,
                'dynamodb': dynamodb
            }
    
    @patch('lambdas.factories.presentation_factory.get_bedrock_manager')
    def test_create_presentation_success(self, mock_bedrock, mock_factory):
        """测试成功创建演示文稿"""
        # Setup
        mock_bedrock.return_value.invoke_model.return_value = {
            'body': Mock(read=Mock(return_value=json.dumps({
                'title': 'Test Presentation',
                'slides': [
                    {'title': 'Slide 1', 'content': ['Point 1', 'Point 2']},
                    {'title': 'Slide 2', 'content': ['Point 3', 'Point 4']}
                ]
            }).encode()))
        }
        
        # Import here to avoid circular imports in test setup
        from lambdas.factories.presentation_factory import PresentationFactory
        
        factory = PresentationFactory()
        
        # Execute
        result = factory.create_presentation(
            topic="AI and Machine Learning",
            audience="Technical Professionals", 
            duration=30,
            language="en"
        )
        
        # Assert
        assert result['status'] == 'success'
        assert 'presentation_id' in result
        assert result['slide_count'] >= 2
        assert result['title'] == 'Test Presentation'
    
    def test_create_presentation_invalid_input(self):
        """测试无效输入处理"""
        from lambdas.factories.presentation_factory import PresentationFactory
        
        factory = PresentationFactory()
        
        # Test missing topic
        with pytest.raises(ValueError, match="Topic is required"):
            factory.create_presentation(topic="", audience="test", duration=30)
        
        # Test invalid duration
        with pytest.raises(ValueError, match="Duration must be positive"):
            factory.create_presentation(topic="test", audience="test", duration=0)
    
    @patch('lambdas.factories.presentation_factory.get_bedrock_manager')
    def test_create_presentation_bedrock_error(self, mock_bedrock, mock_factory):
        """测试Bedrock服务错误处理"""
        # Setup - simulate Bedrock error
        mock_bedrock.return_value.invoke_model.side_effect = Exception("Bedrock service error")
        
        from lambdas.factories.presentation_factory import PresentationFactory
        factory = PresentationFactory()
        
        # Execute & Assert
        with pytest.raises(Exception, match="Failed to generate presentation"):
            factory.create_presentation(
                topic="Test Topic",
                audience="Test Audience",
                duration=30
            )


class TestEnhancedConfigManager:
    """
    Tests for enhanced_config_manager.py (44% -> 85% coverage)  
    重点测试未覆盖的配置管理功能
    """
    
    @pytest.fixture
    def config_manager(self):
        """Create config manager for testing"""
        with mock_aws():
            from lambdas.utils.enhanced_config_manager import EnhancedConfigManager
            return EnhancedConfigManager(environment='dev')
    
    def test_get_value_default(self, config_manager):
        """测试获取默认值"""
        result = config_manager.get_value('nonexistent.key', 'default_value')
        assert result == 'default_value'
    
    def test_get_value_with_fallback_env_var(self, config_manager, monkeypatch):
        """测试使用环境变量作为后备"""
        monkeypatch.setenv('TEST_FALLBACK', 'env_value')
        
        result = config_manager.get_value('nonexistent.key', 'default', 'TEST_FALLBACK')
        assert result == 'env_value'
    
    def test_get_aws_config(self, config_manager):
        """测试获取AWS配置"""
        aws_config = config_manager.get_aws_config()
        assert aws_config is not None
        assert aws_config.region is not None
    
    def test_get_s3_config(self, config_manager):
        """测试获取S3配置"""
        s3_config = config_manager.get_s3_config()
        assert s3_config is not None
        assert hasattr(s3_config, 'bucket')
    
    def test_get_dynamodb_config(self, config_manager):
        """测试获取DynamoDB配置"""
        db_config = config_manager.get_dynamodb_config()
        assert db_config is not None
        # Check for actual attribute in DynamoDBConfig
        assert hasattr(db_config, 'table')
    
    def test_get_bedrock_config(self, config_manager):
        """测试获取Bedrock配置"""
        bedrock_config = config_manager.get_bedrock_config()
        assert bedrock_config is not None
        assert hasattr(bedrock_config, 'model_id')
    
    def test_get_performance_config(self, config_manager):
        """测试获取性能配置"""
        perf_config = config_manager.get_performance_config()
        assert perf_config is not None
        # Check for actual performance attributes
        assert hasattr(perf_config, 'lambda_config') and hasattr(perf_config, 'max_concurrent_downloads')
    
    def test_get_security_config(self, config_manager):
        """测试获取安全配置"""
        security_config = config_manager.get_security_config()
        assert security_config is not None
        # Check for actual security attributes
        assert hasattr(security_config, 'vpc_enabled') or hasattr(security_config, 'api_rate_limit')
    
    def test_get_feature_flags(self, config_manager):
        """测试获取特性标志"""
        feature_flags = config_manager.get_feature_flags()
        assert feature_flags is not None
    
    def test_get_project_metadata(self, config_manager):
        """测试获取项目元数据"""
        metadata = config_manager.get_project_metadata()
        assert metadata is not None
        assert hasattr(metadata, 'project_name')
    
    def test_validate_configuration(self, config_manager):
        """测试配置验证"""
        result = config_manager.validate_configuration()
        assert isinstance(result, dict)
        # Should contain validation results
        assert len(result) >= 0
    
    def test_get_all_config(self, config_manager):
        """测试获取所有配置"""
        all_config = config_manager.get_all_config()
        assert isinstance(all_config, dict)
        assert len(all_config) > 0
    
    def test_reload_configuration(self, config_manager):
        """测试重新加载配置"""
        # This should not raise an exception
        config_manager.reload_configuration()
        
        # Verify config is still accessible
        all_config = config_manager.get_all_config()
        assert isinstance(all_config, dict)


class TestImageProcessor:
    """
    Tests for image_processor.py (40% -> 75% coverage)
    重点测试图片处理逻辑
    """
    
    @pytest.fixture
    def image_processor(self):
        """Create image processor for testing"""
        from lambdas.utils.image_processor import ImageProcessor
        return ImageProcessor()
    
    @patch('lambdas.utils.image_processor.get_bedrock_manager')
    def test_generate_image_success(self, mock_bedrock, image_processor):
        """测试图片生成成功"""
        # Setup
        mock_bedrock.return_value.invoke_model.return_value = {
            'body': Mock(read=Mock(return_value=b'fake_image_data'))
        }
        
        # Execute
        result = image_processor.generate_image(
            prompt="A professional business chart",
            style="realistic",
            quality="high"
        )
        
        # Assert
        assert result['success'] is True
        assert 'image_data' in result
        assert result['format'] == 'png'
    
    def test_optimize_prompt(self, image_processor):
        """测试提示词优化"""
        original_prompt = "chart"
        optimized = image_processor.optimize_prompt(original_prompt, style="professional")
        
        assert len(optimized) > len(original_prompt)
        assert "professional" in optimized.lower()
    
    @patch('lambdas.utils.image_processor.get_bedrock_manager')
    def test_generate_image_with_fallback(self, mock_bedrock, image_processor):
        """测试图片生成失败时的回退机制"""
        # Setup - first call fails, second succeeds
        mock_bedrock.return_value.invoke_model.side_effect = [
            Exception("Primary model failed"),
            {'body': Mock(read=Mock(return_value=b'fallback_image_data'))}
        ]
        
        # Execute
        result = image_processor.generate_image_with_fallback(
            prompt="test prompt",
            primary_model="nova",
            fallback_model="stable-diffusion"
        )
        
        # Assert
        assert result['success'] is True
        assert result['model_used'] == 'fallback_model'
    
    def test_validate_image_parameters(self, image_processor):
        """测试图片参数验证"""
        # Valid parameters
        valid_params = {
            'prompt': 'A beautiful landscape',
            'style': 'realistic',
            'quality': 'high',
            'size': '1024x1024'
        }
        assert image_processor.validate_parameters(valid_params) is True
        
        # Invalid parameters
        invalid_params = {
            'prompt': '',  # Empty prompt
            'style': 'invalid_style',
            'quality': 'invalid_quality'
        }
        assert image_processor.validate_parameters(invalid_params) is False


# Test execution strategy
def run_coverage_improvement_tests():
    """
    运行覆盖率改进测试套件
    按优先级顺序执行测试
    """
    import subprocess
    
    print("🚀 开始Phase 2测试覆盖率提升...")
    
    # Run specific test classes with coverage
    test_classes = [
        "TestPresentationFactory",
        "TestEnhancedConfigManager", 
        "TestImageProcessor"
    ]
    
    for test_class in test_classes:
        print(f"\n📊 运行 {test_class} 测试...")
        result = subprocess.run([
            'python', '-m', 'pytest', 
            f'tests/test_enhancement_strategy.py::{test_class}',
            '-v', '--cov=lambdas', '--cov-report=term-missing'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ {test_class} 测试通过")
        else:
            print(f"❌ {test_class} 测试失败:")
            print(result.stdout)
            print(result.stderr)


if __name__ == "__main__":
    run_coverage_improvement_tests()