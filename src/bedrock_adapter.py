"""
Bedrock模型适配器 - 统一处理不同模型的API格式差异
"""
import json
import logging

logger = logging.getLogger(__name__)


class BedrockAdapter:
    """Bedrock模型适配器"""

    @staticmethod
    def prepare_request(model_id: str, prompt: str, max_tokens: int = 4096, temperature: float = 0.7) -> dict:
        """根据模型ID准备请求体

        Args:
            model_id: 模型ID
            prompt: 提示词
            max_tokens: 最大token数
            temperature: 温度参数

        Returns:
            适配后的请求体
        """
        # Nova模型
        if 'nova' in model_id.lower():
            return {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "text": prompt
                            }
                        ]
                    }
                ],
                "inferenceConfig": {
                    "max_new_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": 0.9
                }
            }

        # Claude模型 (包括inference profile)
        elif 'claude' in model_id.lower():
            return {
                "anthropic_version": "bedrock-2023-05-31",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": 0.9,
                "top_k": 250
            }

        # 默认格式（兼容旧版模型）
        else:
            return {
                "prompt": f"\n\nHuman: {prompt}\n\nAssistant:",
                "max_tokens_to_sample": max_tokens,
                "temperature": temperature,
                "top_p": 0.9,
                "top_k": 250
            }

    @staticmethod
    def parse_response(model_id: str, response_body: dict) -> str:
        """解析模型响应

        Args:
            model_id: 模型ID
            response_body: 响应体

        Returns:
            提取的文本内容
        """
        try:
            # Nova模型
            if 'nova' in model_id.lower():
                output = response_body.get('output', {})
                message = output.get('message', {})
                content = message.get('content', [])
                if content and isinstance(content, list):
                    # 提取所有文本内容
                    texts = []
                    for item in content:
                        if isinstance(item, dict) and 'text' in item:
                            texts.append(item['text'])
                    return '\n'.join(texts)
                return ""

            # Claude模型 (Messages API)
            elif 'claude' in model_id.lower():
                content = response_body.get('content', [])
                if content and isinstance(content, list):
                    # Claude返回的是content列表
                    texts = []
                    for item in content:
                        if isinstance(item, dict) and 'text' in item:
                            texts.append(item['text'])
                        elif isinstance(item, str):
                            texts.append(item)
                    return '\n'.join(texts)
                return response_body.get('completion', '')

            # 默认格式
            else:
                return response_body.get('completion', '')

        except Exception as e:
            logger.error(f"解析响应失败: {str(e)}, 响应体: {response_body}")
            raise ValueError(f"无法解析模型响应: {str(e)}")