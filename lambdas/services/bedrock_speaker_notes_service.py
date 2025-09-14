"""
Bedrock演讲者备注服务
处理与AWS Bedrock的交互，生成演讲者备注
"""

import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class BedrockSpeakerNotesService:
    """Bedrock演讲者备注服务类"""

    def __init__(self, bedrock_client):
        """
        初始化服务

        Args:
            bedrock_client: Bedrock客户端实例
        """
        self.bedrock_client = bedrock_client
        self.model_id = "anthropic.claude-3-sonnet-20240229-v1:0"

    def generate_speaker_notes(self, slide_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用Bedrock生成演讲者备注

        Args:
            slide_data: 幻灯片数据

        Returns:
            Dict: 包含生成的演讲者备注的响应
        """
        try:
            # 构建提示词
            prompt = self._build_prompt(slide_data)

            # 构建请求体
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 300,
                "temperature": 0.7,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }

            # 调用Bedrock API
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body),
                contentType='application/json',
                accept='application/json'
            )

            # 解析响应
            response_body = json.loads(response['body'].read())

            # 提取内容
            if 'content' in response_body and response_body['content']:
                completion = response_body['content'][0].get('text', '')
            elif 'completion' in response_body:
                completion = response_body['completion']
            else:
                completion = "这张幻灯片包含重要信息，请详细解释各个要点。"

            return {
                "completion": completion,
                "stop_reason": response_body.get('stop_reason', 'end_turn')
            }

        except Exception as e:
            logger.error(f"Bedrock服务调用失败: {str(e)}")
            from lambdas.exceptions.speaker_notes_exceptions import BedrockServiceError
            raise BedrockServiceError(f"Bedrock服务错误: {str(e)}")

    def _build_prompt(self, slide_data: Dict[str, Any]) -> str:
        """构建生成演讲者备注的提示词"""
        title = slide_data.get('title', '')
        content = slide_data.get('content', [])

        prompt = f"""为以下幻灯片生成演讲者备注：

标题：{title}
内容要点：
{chr(10).join(f"- {item}" for item in content)}

要求：
1. 生成100-200字的中文演讲者备注
2. 补充和扩展幻灯片内容，不要简单重复
3. 提供背景信息和关键洞察
4. 使用自然的演讲语言
5. 帮助演讲者更好地传达信息

演讲者备注："""

        return prompt