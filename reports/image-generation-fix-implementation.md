# 图片生成功能修复实施方案

## 快速修复指南（30分钟内完成）

### 第1步：更新Terraform IAM配置（5分钟）

创建新文件 `infrastructure/iam_image_fix.tf`：

```hcl
# 图片生成服务IAM权限补丁
resource "aws_iam_role_policy" "lambda_image_generation_policy" {
  name = "lambda-image-generation-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "BedrockImageGenerationAccess"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = [
          # Amazon Nova Canvas - 最新的图片生成模型
          "arn:aws:bedrock:${var.aws_region}:*:foundation-model/amazon.nova-canvas-v1*",
          # Stability AI SDXL - 高质量图片生成
          "arn:aws:bedrock:${var.aws_region}:*:foundation-model/stability.stable-diffusion-xl-v1*",
          # Amazon Titan Image Generator - 备选方案
          "arn:aws:bedrock:${var.aws_region}:*:foundation-model/amazon.titan-image-generator-v1*"
        ]
      },
      {
        Sid    = "BedrockModelDiscovery"
        Effect = "Allow"
        Action = [
          "bedrock:ListFoundationModels",
          "bedrock:GetFoundationModel"
        ]
        Resource = "*"
      }
    ]
  })
}
```

### 第2步：更新Lambda环境变量（5分钟）

在 `infrastructure/main.tf` 中更新Lambda函数配置：

```hcl
# 更新 generate_ppt Lambda函数
resource "aws_lambda_function" "generate_ppt" {
  filename         = "../lambda-packages/generate_ppt_complete.zip"
  function_name    = "ai-ppt-generate-${var.environment}"
  role            = aws_iam_role.lambda_role.arn
  handler         = "lambda_function.handler"
  runtime         = "python3.11"
  memory_size     = 2048
  timeout         = 300

  layers = [aws_lambda_layer_version.dependencies.arn]

  environment {
    variables = {
      S3_BUCKET = aws_s3_bucket.presentations.id
      ENVIRONMENT = var.environment
      # 新增图片生成相关环境变量
      IMAGE_MODEL_ID = "amazon.nova-canvas-v1:0"
      BEDROCK_REGION = var.aws_region
      IMAGE_GENERATION_SERVICE = "bedrock"
      ENABLE_IMAGE_GENERATION = "true"
      IMAGE_FALLBACK_MODE = "placeholder"
    }
  }

  tags = {
    Environment = var.environment
    Project     = "ai-ppt-assistant"
  }
}
```

### 第3步：实现Bedrock图片生成调用（10分钟）

创建新文件 `lambdas/bedrock_image_service.py`：

```python
"""
Amazon Bedrock图片生成服务
支持Nova Canvas和Stability AI SDXL
"""

import json
import base64
import logging
import os
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class BedrockImageService:
    """Bedrock图片生成服务封装"""

    def __init__(self, region_name: str = None):
        """初始化Bedrock客户端"""
        self.region = region_name or os.environ.get('BEDROCK_REGION', 'us-east-1')
        self.model_id = os.environ.get('IMAGE_MODEL_ID', 'amazon.nova-canvas-v1:0')
        self.bedrock_runtime = boto3.client(
            'bedrock-runtime',
            region_name=self.region
        )
        logger.info(f"BedrockImageService初始化: region={self.region}, model={self.model_id}")

    def generate_image(self, prompt: str, style: str = "photographic") -> bytes:
        """
        使用Bedrock生成图片

        Args:
            prompt: 图片描述提示词
            style: 图片风格（photographic, artistic, anime等）

        Returns:
            图片的字节数据
        """
        try:
            # 根据模型ID选择不同的请求格式
            if "nova-canvas" in self.model_id:
                return self._generate_with_nova(prompt, style)
            elif "stable-diffusion" in self.model_id:
                return self._generate_with_stability(prompt, style)
            elif "titan-image" in self.model_id:
                return self._generate_with_titan(prompt)
            else:
                raise ValueError(f"不支持的模型: {self.model_id}")

        except ClientError as e:
            logger.error(f"Bedrock API调用失败: {e}")
            if e.response['Error']['Code'] == 'ModelNotReadyException':
                logger.warning("模型未就绪，尝试使用备选模型")
                return self._fallback_generation(prompt)
            raise
        except Exception as e:
            logger.error(f"图片生成失败: {e}")
            raise

    def _generate_with_nova(self, prompt: str, style: str) -> bytes:
        """使用Amazon Nova Canvas生成图片"""
        request_body = {
            "taskType": "TEXT_IMAGE",
            "textToImageParams": {
                "text": prompt,
                "negativeText": "low quality, blurry, distorted, ugly",
            },
            "imageGenerationConfig": {
                "numberOfImages": 1,
                "height": 768,
                "width": 1024,
                "cfgScale": 8.0,
                "seed": 0
            }
        }

        response = self.bedrock_runtime.invoke_model(
            modelId=self.model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body)
        )

        response_body = json.loads(response['body'].read())

        # Nova返回base64编码的图片
        if 'images' in response_body and response_body['images']:
            image_base64 = response_body['images'][0]
            return base64.b64decode(image_base64)
        else:
            raise ValueError("Nova模型未返回图片数据")

    def _generate_with_stability(self, prompt: str, style: str) -> bytes:
        """使用Stability AI SDXL生成图片"""
        style_preset_map = {
            "photographic": "photographic",
            "artistic": "digital-art",
            "anime": "anime",
            "3d": "3d-model"
        }

        request_body = {
            "text_prompts": [
                {
                    "text": prompt,
                    "weight": 1.0
                }
            ],
            "cfg_scale": 10,
            "seed": 0,
            "steps": 50,
            "style_preset": style_preset_map.get(style, "photographic"),
            "height": 768,
            "width": 1024
        }

        response = self.bedrock_runtime.invoke_model(
            modelId="stability.stable-diffusion-xl-v1",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body)
        )

        response_body = json.loads(response['body'].read())

        # Stability AI返回base64编码的图片
        if 'artifacts' in response_body and response_body['artifacts']:
            image_base64 = response_body['artifacts'][0]['base64']
            return base64.b64decode(image_base64)
        else:
            raise ValueError("Stability模型未返回图片数据")

    def _generate_with_titan(self, prompt: str) -> bytes:
        """使用Amazon Titan Image Generator生成图片"""
        request_body = {
            "textToImageParams": {
                "text": prompt
            },
            "taskType": "TEXT_IMAGE",
            "imageGenerationConfig": {
                "cfgScale": 8.0,
                "seed": 0,
                "quality": "standard",
                "width": 1024,
                "height": 768,
                "numberOfImages": 1
            }
        }

        response = self.bedrock_runtime.invoke_model(
            modelId="amazon.titan-image-generator-v1",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body)
        )

        response_body = json.loads(response['body'].read())

        if 'images' in response_body:
            image_base64 = response_body['images'][0]
            return base64.b64decode(image_base64)
        else:
            raise ValueError("Titan模型未返回图片数据")

    def _fallback_generation(self, prompt: str) -> bytes:
        """备选方案：尝试其他模型"""
        fallback_models = [
            "stability.stable-diffusion-xl-v1",
            "amazon.titan-image-generator-v1"
        ]

        for model in fallback_models:
            try:
                logger.info(f"尝试备选模型: {model}")
                self.model_id = model

                if "stable-diffusion" in model:
                    return self._generate_with_stability(prompt, "photographic")
                elif "titan-image" in model:
                    return self._generate_with_titan(prompt)
            except Exception as e:
                logger.warning(f"备选模型 {model} 失败: {e}")
                continue

        raise RuntimeError("所有图片生成模型都失败了")

    def test_connection(self) -> bool:
        """测试Bedrock连接"""
        try:
            response = self.bedrock_runtime.list_foundation_models()
            logger.info(f"Bedrock连接成功，可用模型数: {len(response.get('modelSummaries', []))}")
            return True
        except Exception as e:
            logger.error(f"Bedrock连接失败: {e}")
            return False


# 单例实例
_bedrock_service = None

def get_bedrock_service() -> BedrockImageService:
    """获取Bedrock服务单例"""
    global _bedrock_service
    if _bedrock_service is None:
        _bedrock_service = BedrockImageService()
    return _bedrock_service
```

### 第4步：更新image_processing_service.py（5分钟）

修改 `lambdas/image_processing_service.py` 中的 `call_image_generation` 方法：

```python
def call_image_generation(self, prompt: str) -> bytes:
    """
    生成图片 - 集成Bedrock服务

    Args:
        prompt: 图片生成提示词

    Returns:
        生成的图片数据
    """
    import os

    # 检查是否启用真实图片生成
    if os.environ.get('ENABLE_IMAGE_GENERATION', 'false').lower() == 'true':
        try:
            # 导入Bedrock服务
            from .bedrock_image_service import get_bedrock_service

            logger.info(f"调用Bedrock生成图片: {prompt[:100]}...")
            bedrock_service = get_bedrock_service()

            # 生成图片
            image_data = bedrock_service.generate_image(prompt)

            logger.info(f"图片生成成功，大小: {len(image_data)} bytes")
            return image_data

        except ImportError as e:
            logger.error(f"无法导入Bedrock服务: {e}")
        except Exception as e:
            logger.error(f"Bedrock图片生成失败: {e}")

            # 检查降级模式
            fallback_mode = os.environ.get('IMAGE_FALLBACK_MODE', 'placeholder')
            if fallback_mode == 'placeholder':
                logger.info("降级到占位图模式")
                return self.create_placeholder_image(768, 512, prompt[:100])
            else:
                raise

    # 默认返回占位图
    logger.info("图片生成未启用，返回占位图")
    return self.create_placeholder_image(768, 512, prompt[:100])
```

### 第5步：部署和验证（5分钟）

```bash
# 1. 打包Lambda函数
cd /Users/umatoratatsu/Documents/AWS/AWS-Handson/ABA/AMAZON-BEDROCK-AGENTS
./scripts/package_lambdas.sh

# 2. 部署Terraform更新
cd infrastructure
terraform plan
terraform apply

# 3. 验证部署
aws lambda get-function-configuration --function-name ai-ppt-generate-dev | jq '.Environment.Variables'
```

## 验证测试脚本

创建 `test_image_generation.py`：

```python
"""测试图片生成功能"""

import json
import base64
import boto3

def test_bedrock_image_generation():
    """测试Bedrock图片生成"""

    # 初始化客户端
    bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

    # 测试提示词
    prompt = "A modern business presentation slide background with technology elements, blue gradient, professional style"

    # Nova Canvas请求
    request_body = {
        "taskType": "TEXT_IMAGE",
        "textToImageParams": {
            "text": prompt
        },
        "imageGenerationConfig": {
            "numberOfImages": 1,
            "height": 768,
            "width": 1024,
            "cfgScale": 8.0
        }
    }

    try:
        response = bedrock.invoke_model(
            modelId="amazon.nova-canvas-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body)
        )

        response_body = json.loads(response['body'].read())

        if 'images' in response_body:
            print("✅ 图片生成成功!")
            image_data = base64.b64decode(response_body['images'][0])

            # 保存测试图片
            with open('test_image.png', 'wb') as f:
                f.write(image_data)
            print(f"图片已保存: test_image.png (大小: {len(image_data)} bytes)")
        else:
            print("❌ 未收到图片数据")

    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    test_bedrock_image_generation()
```

## 监控和日志

### CloudWatch日志查询
```
fields @timestamp, @message
| filter @message like /图片生成/
| sort @timestamp desc
| limit 20
```

### 成本监控
```python
# 添加到Lambda函数中的成本追踪
def track_image_generation_cost(model_id: str):
    """追踪图片生成成本"""
    costs = {
        "amazon.nova-canvas-v1:0": 0.08,  # 每张图片
        "stability.stable-diffusion-xl-v1": 0.04,
        "amazon.titan-image-generator-v1": 0.01
    }

    cost = costs.get(model_id, 0)
    logger.info(f"图片生成成本: ${cost}")

    # 发送到CloudWatch Metrics
    cloudwatch = boto3.client('cloudwatch')
    cloudwatch.put_metric_data(
        Namespace='AI-PPT-Assistant',
        MetricData=[
            {
                'MetricName': 'ImageGenerationCost',
                'Value': cost,
                'Unit': 'None'
            }
        ]
    )
```

## 故障排除

### 常见问题和解决方案

1. **ModelNotReadyException**
   - 原因：模型未在该区域启用
   - 解决：在AWS控制台启用模型访问

2. **AccessDeniedException**
   - 原因：IAM权限不足
   - 解决：检查并更新IAM策略

3. **ThrottlingException**
   - 原因：请求速率过高
   - 解决：实现指数退避重试

4. **ValidationException**
   - 原因：请求参数错误
   - 解决：检查模型文档，确认参数格式

## 回滚计划

如果部署后出现问题：

```bash
# 1. 快速禁用图片生成
aws lambda update-function-configuration \
  --function-name ai-ppt-generate-dev \
  --environment Variables={ENABLE_IMAGE_GENERATION=false}

# 2. 回滚Terraform
cd infrastructure
terraform apply -target=aws_lambda_function.generate_ppt -var="previous_version=true"
```

## 成功标准

- [ ] Lambda函数成功调用Bedrock API
- [ ] 生成的图片成功保存到S3
- [ ] PPT中显示真实生成的图片而非占位符
- [ ] 错误时能正确降级到占位图
- [ ] CloudWatch日志显示正确的调用记录
- [ ] 成本在预期范围内

---
*实施时间：30分钟*
*风险等级：低*
*回滚时间：5分钟*