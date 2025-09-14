"""
Batch Processor - 批量处理器
负责管理批量PPT生成任务
"""
import json
import uuid
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import boto3


class BatchProcessor:
    """批量处理器"""

    def __init__(self):
        """初始化批量处理器"""
        self.max_batch_size = 10
        self.batch_storage = {}  # 内存中存储批量任务状态
        self.sqs_client = boto3.client('sqs', region_name='us-east-1')

    def validate_batch(self, batch_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证批量请求

        Args:
            batch_request: 批量请求

        Returns:
            验证结果
        """
        batch_size = batch_request.get("batch_size", 0)
        requests = batch_request.get("requests", [])

        # 检查批量大小
        if batch_size > self.max_batch_size or len(requests) > self.max_batch_size:
            return {
                "valid": False,
                "error": "batch_size_exceeded",
                "message": f"批量大小不能超过{self.max_batch_size}个请求"
            }

        # 检查请求格式
        for i, request in enumerate(requests):
            if not request.get("topic"):
                return {
                    "valid": False,
                    "error": "invalid_request",
                    "message": f"第{i+1}个请求缺少主题"
                }

        return {
            "valid": True,
            "batch_size": len(requests),
            "estimated_time": self._estimate_processing_time(len(requests))
        }

    def get_execution_strategy(self, batch: List[Dict[str, Any]]) -> str:
        """
        确定批量执行策略

        Args:
            batch: 批量任务列表

        Returns:
            执行策略: parallel | grouped | sequential
        """
        batch_size = len(batch)

        if batch_size <= 3:
            # 小批量：并行执行
            return "parallel"
        elif batch_size <= 6:
            # 中批量：分组执行
            return "grouped"
        else:
            # 大批量：顺序执行
            return "sequential"

    def init_batch(self, batch_id: str, tasks: List[Dict[str, Any]]) -> None:
        """
        初始化批量任务

        Args:
            batch_id: 批量ID
            tasks: 任务列表
        """
        self.batch_storage[batch_id] = {
            "id": batch_id,
            "created_at": datetime.now().isoformat(),
            "total": len(tasks),
            "tasks": {task["id"]: task for task in tasks},
            "status": "initialized"
        }

    def update_task_status(self, batch_id: str, task_id: str, status: str) -> None:
        """
        更新任务状态

        Args:
            batch_id: 批量ID
            task_id: 任务ID
            status: 新状态
        """
        if batch_id in self.batch_storage:
            if task_id in self.batch_storage[batch_id]["tasks"]:
                self.batch_storage[batch_id]["tasks"][task_id]["status"] = status
                self.batch_storage[batch_id]["updated_at"] = datetime.now().isoformat()

    def get_batch_progress(self, batch_id: str) -> Dict[str, Any]:
        """
        获取批量进度

        Args:
            batch_id: 批量ID

        Returns:
            进度信息
        """
        if batch_id not in self.batch_storage:
            return {
                "error": "batch_not_found",
                "batch_id": batch_id
            }

        batch = self.batch_storage[batch_id]
        tasks = batch["tasks"].values()

        completed = sum(1 for t in tasks if t["status"] == "completed")
        processing = sum(1 for t in tasks if t["status"] == "processing")
        pending = sum(1 for t in tasks if t["status"] == "pending")
        failed = sum(1 for t in tasks if t["status"] == "failed")

        total = batch["total"]
        percentage = (completed / total * 100) if total > 0 else 0

        return {
            "batch_id": batch_id,
            "total": total,
            "completed": completed,
            "processing": processing,
            "pending": pending,
            "failed": failed,
            "percentage": round(percentage),
            "status": self._get_batch_status(completed, processing, failed, total)
        }

    def execute_batch(self, batch_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行批量任务

        Args:
            batch_request: 批量请求

        Returns:
            执行结果
        """
        # 验证请求
        validation = self.validate_batch(batch_request)
        if not validation["valid"]:
            return validation

        # 创建批量ID
        batch_id = f"batch_{uuid.uuid4().hex[:8]}"
        requests = batch_request.get("requests", [])

        # 准备任务
        tasks = []
        for i, request in enumerate(requests):
            task_id = f"task_{i}"
            tasks.append({
                "id": task_id,
                "status": "pending",
                "request": request
            })

        # 初始化批量
        self.init_batch(batch_id, tasks)

        # 确定执行策略
        strategy = self.get_execution_strategy(requests)

        # 根据策略执行
        if strategy == "parallel":
            results = self._execute_parallel(batch_id, tasks)
        elif strategy == "grouped":
            results = self._execute_grouped(batch_id, tasks)
        else:
            results = self._execute_sequential(batch_id, tasks)

        return {
            "batch_id": batch_id,
            "strategy": strategy,
            "results": results,
            "progress": self.get_batch_progress(batch_id)
        }

    def _execute_parallel(self, batch_id: str, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """并行执行任务"""
        results = []

        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_task = {}

            for task in tasks:
                self.update_task_status(batch_id, task["id"], "processing")
                future = executor.submit(self._process_single_task, task)
                future_to_task[future] = task

            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result(timeout=60)
                    self.update_task_status(batch_id, task["id"], "completed")
                    results.append(result)
                except Exception as e:
                    self.update_task_status(batch_id, task["id"], "failed")
                    results.append({
                        "task_id": task["id"],
                        "status": "failed",
                        "error": str(e)
                    })

        return results

    def _execute_grouped(self, batch_id: str, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """分组执行任务"""
        results = []
        group_size = 3

        for i in range(0, len(tasks), group_size):
            group = tasks[i:i+group_size]
            group_results = self._execute_parallel(batch_id, group)
            results.extend(group_results)

        return results

    def _execute_sequential(self, batch_id: str, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """顺序执行任务"""
        results = []

        for task in tasks:
            self.update_task_status(batch_id, task["id"], "processing")
            try:
                result = self._process_single_task(task)
                self.update_task_status(batch_id, task["id"], "completed")
                results.append(result)
            except Exception as e:
                self.update_task_status(batch_id, task["id"], "failed")
                results.append({
                    "task_id": task["id"],
                    "status": "failed",
                    "error": str(e)
                })

        return results

    def _process_single_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理单个任务

        Args:
            task: 任务信息

        Returns:
            处理结果
        """
        # 这里模拟处理过程
        # 实际应该调用Content Generator等Agent
        request = task["request"]
        topic = request.get("topic", "未知主题")

        # 模拟生成PPT
        result = {
            "task_id": task["id"],
            "status": "completed",
            "topic": topic,
            "presentation_id": f"ppt_{uuid.uuid4().hex[:8]}",
            "page_count": request.get("page_count", 10),
            "generated_at": datetime.now().isoformat()
        }

        return result

    def _estimate_processing_time(self, batch_size: int) -> int:
        """
        估算处理时间

        Args:
            batch_size: 批量大小

        Returns:
            估计的秒数
        """
        # 基础时间 + 每个任务的时间
        base_time = 10
        per_task_time = 20

        strategy = self.get_execution_strategy([{} for _ in range(batch_size)])

        if strategy == "parallel":
            # 并行执行，时间较短
            return base_time + per_task_time
        elif strategy == "grouped":
            # 分组执行
            groups = (batch_size + 2) // 3
            return base_time + (per_task_time * groups)
        else:
            # 顺序执行
            return base_time + (per_task_time * batch_size)

    def _get_batch_status(self, completed: int, processing: int, failed: int, total: int) -> str:
        """确定批量状态"""
        if completed == total:
            return "completed"
        elif failed == total:
            return "failed"
        elif processing > 0:
            return "processing"
        elif completed + failed == total:
            return "completed_with_errors"
        else:
            return "pending"

    def queue_batch_request(self, batch_request: Dict[str, Any], queue_url: str) -> Dict[str, Any]:
        """
        将批量请求放入SQS队列

        Args:
            batch_request: 批量请求
            queue_url: SQS队列URL

        Returns:
            队列消息信息
        """
        try:
            message_body = json.dumps(batch_request)
            response = self.sqs_client.send_message(
                QueueUrl=queue_url,
                MessageBody=message_body,
                MessageAttributes={
                    'Type': {'StringValue': 'BatchRequest', 'DataType': 'String'},
                    'Priority': {'StringValue': batch_request.get('priority', 'normal'), 'DataType': 'String'}
                }
            )

            return {
                "success": True,
                "message_id": response['MessageId'],
                "queue_url": queue_url
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }