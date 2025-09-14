"""
Orchestrator Agent - 主调度器
负责分析请求、调度子Agent、管理上下文
"""
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List
import boto3
from botocore.config import Config

# 统一使用的模型
MODEL_ID = "anthropic.claude-sonnet-4-20250514-v1:0"


class OrchestratorAgent:
    """主调度Agent"""

    def __init__(self):
        """初始化Orchestrator Agent"""
        self.bedrock_runtime = boto3.client(
            'bedrock-runtime',
            region_name='us-east-1',
            config=Config(read_timeout=30, retries={'max_attempts': 3})
        )
        self.bedrock_agent = boto3.client(
            'bedrock-agent-runtime',
            region_name='us-east-1'
        )
        self.agent_mappings = {
            "document_conversion": "document-analyzer-agent",
            "batch_generation": "batch-processor",
            "single_generation": "content-generator-agent"
        }

    def analyze_request(self, request: Dict[str, Any]) -> str:
        """
        分析请求类型

        Args:
            request: 用户请求

        Returns:
            请求类型: document_conversion | batch_generation | single_generation
        """
        action = request.get("action", "")

        if action == "convert_document" or "document_path" in request:
            return "document_conversion"
        elif action == "batch_generate" or "topics" in request:
            return "batch_generation"
        else:
            return "single_generation"

    def dispatch_task(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        分发任务到相应的Agent

        Args:
            request: 任务请求

        Returns:
            分发结果
        """
        request_type = self.analyze_request(request)
        agent_name = self.agent_mappings[request_type]
        task_id = str(uuid.uuid4())

        # 创建任务记录
        task = {
            "task_id": task_id,
            "agent_called": agent_name,
            "status": "dispatched",
            "created_at": datetime.now().isoformat(),
            "request": request,
            "request_type": request_type
        }

        # 实际调用子Agent（这里先返回模拟结果）
        if request_type == "document_conversion":
            # 调用Document Analyzer Agent
            task["next_step"] = "document_analysis"
        elif request_type == "batch_generation":
            # 启动批量处理
            task["batch_size"] = len(request.get("topics", []))
            task["next_step"] = "batch_processing"
        else:
            # 单个生成
            task["next_step"] = "content_generation"

        return task

    def create_context(self, session_id: str, user_id: str) -> Dict[str, Any]:
        """
        创建共享上下文

        Args:
            session_id: 会话ID
            user_id: 用户ID

        Returns:
            初始化的上下文
        """
        return {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "request_metadata": {
                "user_id": user_id,
                "priority": "normal"
            },
            "document_analysis": {},
            "generation_config": {
                "page_count": 10,
                "template": "modern",
                "language": "zh"
            },
            "intermediate_results": {
                "outline": {},
                "slides": [],
                "images": [],
                "notes": []
            },
            "quality_metrics": {
                "content_score": 0,
                "visual_score": 0,
                "coherence_score": 0
            }
        }

    def update_context(self, context: Dict[str, Any], key: str, value: Any) -> Dict[str, Any]:
        """
        更新共享上下文

        Args:
            context: 当前上下文
            key: 要更新的键
            value: 新值

        Returns:
            更新后的上下文
        """
        if key in context:
            if isinstance(context[key], dict) and isinstance(value, dict):
                context[key].update(value)
            else:
                context[key] = value
        else:
            # 如果键不存在，直接添加
            context[key] = value

        context["updated_at"] = datetime.now().isoformat()
        return context

    def invoke_agent(self, agent_alias: str, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用Bedrock Agent

        Args:
            agent_alias: Agent别名
            prompt: 提示词
            context: 上下文

        Returns:
            Agent响应
        """
        try:
            # 构建请求
            request_body = {
                "modelId": MODEL_ID,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "system": f"Context: {json.dumps(context)}",
                "max_tokens": 4096,
                "temperature": 0.7
            }

            # 调用Bedrock
            response = self.bedrock_runtime.invoke_model(
                modelId=MODEL_ID,
                body=json.dumps(request_body)
            )

            result = json.loads(response['body'].read())
            return {
                "success": True,
                "response": result.get("content", [{}])[0].get("text", ""),
                "agent": agent_alias
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "agent": agent_alias
            }

    def coordinate_workflow(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        协调整个工作流

        Args:
            request: 用户请求

        Returns:
            工作流执行结果
        """
        # 创建会话上下文
        session_id = str(uuid.uuid4())
        user_id = request.get("user_id", "anonymous")
        context = self.create_context(session_id, user_id)

        # 分析请求类型
        request_type = self.analyze_request(request)
        context = self.update_context(context, "request_type", request_type)

        # 根据类型执行不同的工作流
        if request_type == "document_conversion":
            return self._handle_document_conversion(request, context)
        elif request_type == "batch_generation":
            return self._handle_batch_generation(request, context)
        else:
            return self._handle_single_generation(request, context)

    def _handle_document_conversion(self, request: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """处理文档转换请求"""
        workflow_steps = [
            "document_analysis",
            "outline_generation",
            "content_generation",
            "visual_design",
            "quality_check",
            "ppt_compilation"
        ]

        result = {
            "session_id": context["session_id"],
            "type": "document_conversion",
            "status": "processing",
            "steps": workflow_steps,
            "document_path": request.get("document_path")
        }

        # 这里会实际调用各个Agent，现在返回模拟结果
        return result

    def _handle_batch_generation(self, request: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """处理批量生成请求"""
        topics = request.get("topics", [])
        batch_size = len(topics)

        # 决定执行策略
        if batch_size <= 3:
            strategy = "parallel"
        elif batch_size <= 6:
            strategy = "grouped"
        else:
            strategy = "sequential"

        result = {
            "session_id": context["session_id"],
            "type": "batch_generation",
            "status": "processing",
            "batch_size": batch_size,
            "strategy": strategy,
            "topics": topics
        }

        return result

    def _handle_single_generation(self, request: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """处理单个生成请求"""
        result = {
            "session_id": context["session_id"],
            "type": "single_generation",
            "status": "processing",
            "topic": request.get("topic"),
            "page_count": request.get("page_count", 10)
        }

        return result