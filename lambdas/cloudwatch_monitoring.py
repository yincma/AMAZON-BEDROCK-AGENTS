"""
CloudWatch监控和指标收集模块
提供全面的性能监控、告警和可视化支持
"""

import time
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import boto3
from botocore.exceptions import ClientError
import threading
from collections import deque
import statistics

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """指标类型枚举"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class Metric:
    """指标数据类"""
    name: str
    value: float
    unit: str
    timestamp: datetime
    dimensions: Dict[str, str]
    metric_type: MetricType


class CloudWatchMonitor:
    """CloudWatch监控器"""

    def __init__(self, namespace: str = "AI-PPT-Assistant",
                 client=None, batch_size: int = 20,
                 flush_interval: int = 60):
        """
        初始化CloudWatch监控器

        Args:
            namespace: CloudWatch命名空间
            client: CloudWatch客户端
            batch_size: 批量发送大小
            flush_interval: 刷新间隔（秒）
        """
        self.namespace = namespace
        self.client = client or boto3.client('cloudwatch')
        self.batch_size = batch_size
        self.flush_interval = flush_interval

        # 指标缓冲区
        self._metric_buffer = deque(maxlen=1000)
        self._buffer_lock = threading.Lock()

        # 启动后台刷新线程
        self._stop_flush = threading.Event()
        self._flush_thread = threading.Thread(target=self._flush_worker, daemon=True)
        self._flush_thread.start()

        # 性能统计
        self._stats = {
            'metrics_sent': 0,
            'metrics_failed': 0,
            'batch_count': 0,
            'last_flush': None
        }

    def record_metric(self, name: str, value: float, unit: str = 'Count',
                     dimensions: Optional[Dict[str, str]] = None,
                     metric_type: MetricType = MetricType.GAUGE) -> None:
        """
        记录单个指标

        Args:
            name: 指标名称
            value: 指标值
            unit: 单位
            dimensions: 维度
            metric_type: 指标类型
        """
        metric = Metric(
            name=name,
            value=value,
            unit=unit,
            timestamp=datetime.utcnow(),
            dimensions=dimensions or {},
            metric_type=metric_type
        )

        with self._buffer_lock:
            self._metric_buffer.append(metric)

        # 如果缓冲区满，立即刷新
        if len(self._metric_buffer) >= self.batch_size:
            self._flush_metrics()

    def record_timing(self, name: str, duration: float,
                     dimensions: Optional[Dict[str, str]] = None) -> None:
        """
        记录时间指标

        Args:
            name: 指标名称
            duration: 持续时间（秒）
            dimensions: 维度
        """
        self.record_metric(
            name=name,
            value=duration * 1000,  # 转换为毫秒
            unit='Milliseconds',
            dimensions=dimensions,
            metric_type=MetricType.TIMER
        )

    def increment_counter(self, name: str, value: int = 1,
                         dimensions: Optional[Dict[str, str]] = None) -> None:
        """
        增加计数器

        Args:
            name: 计数器名称
            value: 增加值
            dimensions: 维度
        """
        self.record_metric(
            name=name,
            value=value,
            unit='Count',
            dimensions=dimensions,
            metric_type=MetricType.COUNTER
        )

    def _flush_worker(self) -> None:
        """后台刷新工作线程"""
        while not self._stop_flush.is_set():
            try:
                time.sleep(self.flush_interval)
                self._flush_metrics()
            except Exception as e:
                logger.error(f"指标刷新失败: {str(e)}")

    def _flush_metrics(self) -> None:
        """刷新指标到CloudWatch"""
        with self._buffer_lock:
            if not self._metric_buffer:
                return

            metrics_to_send = list(self._metric_buffer)
            self._metric_buffer.clear()

        # 按批次发送
        for i in range(0, len(metrics_to_send), self.batch_size):
            batch = metrics_to_send[i:i + self.batch_size]
            self._send_batch(batch)

        self._stats['last_flush'] = datetime.utcnow()

    def _send_batch(self, metrics: List[Metric]) -> None:
        """
        发送一批指标到CloudWatch

        Args:
            metrics: 指标列表
        """
        try:
            metric_data = []
            for metric in metrics:
                data_point = {
                    'MetricName': metric.name,
                    'Value': metric.value,
                    'Unit': metric.unit,
                    'Timestamp': metric.timestamp
                }

                if metric.dimensions:
                    data_point['Dimensions'] = [
                        {'Name': k, 'Value': v}
                        for k, v in metric.dimensions.items()
                    ]

                metric_data.append(data_point)

            # 发送到CloudWatch
            self.client.put_metric_data(
                Namespace=self.namespace,
                MetricData=metric_data
            )

            self._stats['metrics_sent'] += len(metrics)
            self._stats['batch_count'] += 1

        except ClientError as e:
            logger.error(f"发送指标到CloudWatch失败: {str(e)}")
            self._stats['metrics_failed'] += len(metrics)

    def get_stats(self) -> Dict[str, Any]:
        """获取监控统计信息"""
        return {
            'metrics_sent': self._stats['metrics_sent'],
            'metrics_failed': self._stats['metrics_failed'],
            'batch_count': self._stats['batch_count'],
            'last_flush': self._stats['last_flush'].isoformat() if self._stats['last_flush'] else None,
            'buffer_size': len(self._metric_buffer)
        }

    def shutdown(self) -> None:
        """关闭监控器"""
        # 刷新剩余指标
        self._flush_metrics()

        # 停止后台线程
        self._stop_flush.set()
        self._flush_thread.join(timeout=5)

        logger.info("CloudWatch监控器已关闭")


class PerformanceTracker:
    """性能跟踪器"""

    def __init__(self, monitor: CloudWatchMonitor):
        """
        初始化性能跟踪器

        Args:
            monitor: CloudWatch监控器
        """
        self.monitor = monitor
        self._timings = {}
        self._lock = threading.Lock()

    def start_timing(self, operation: str) -> str:
        """
        开始计时

        Args:
            operation: 操作名称

        Returns:
            计时ID
        """
        timing_id = f"{operation}_{time.time()}"
        with self._lock:
            self._timings[timing_id] = {
                'operation': operation,
                'start_time': time.perf_counter()
            }
        return timing_id

    def end_timing(self, timing_id: str, dimensions: Optional[Dict[str, str]] = None) -> float:
        """
        结束计时并记录

        Args:
            timing_id: 计时ID
            dimensions: 额外维度

        Returns:
            耗时（秒）
        """
        with self._lock:
            if timing_id not in self._timings:
                logger.warning(f"未找到计时ID: {timing_id}")
                return 0

            timing = self._timings.pop(timing_id)

        duration = time.perf_counter() - timing['start_time']

        # 记录到CloudWatch
        self.monitor.record_timing(
            name=f"{timing['operation']}_duration",
            duration=duration,
            dimensions=dimensions
        )

        return duration

    def track_operation(self, operation: str):
        """
        装饰器：跟踪函数执行时间

        Args:
            operation: 操作名称
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                timing_id = self.start_timing(operation)
                try:
                    result = func(*args, **kwargs)
                    self.end_timing(timing_id, {'status': 'success'})
                    return result
                except Exception as e:
                    self.end_timing(timing_id, {'status': 'failed'})
                    raise
            return wrapper
        return decorator


class AlarmManager:
    """CloudWatch告警管理器"""

    def __init__(self, client=None):
        """
        初始化告警管理器

        Args:
            client: CloudWatch客户端
        """
        self.client = client or boto3.client('cloudwatch')

    def create_alarm(self, name: str, metric_name: str,
                    namespace: str, threshold: float,
                    comparison_operator: str = 'GreaterThanThreshold',
                    evaluation_periods: int = 1,
                    period: int = 300,
                    statistic: str = 'Average',
                    dimensions: Optional[List[Dict[str, str]]] = None,
                    alarm_actions: Optional[List[str]] = None) -> None:
        """
        创建CloudWatch告警

        Args:
            name: 告警名称
            metric_name: 指标名称
            namespace: 命名空间
            threshold: 阈值
            comparison_operator: 比较操作符
            evaluation_periods: 评估周期数
            period: 周期（秒）
            statistic: 统计方法
            dimensions: 维度
            alarm_actions: 告警动作
        """
        try:
            self.client.put_metric_alarm(
                AlarmName=name,
                ComparisonOperator=comparison_operator,
                EvaluationPeriods=evaluation_periods,
                MetricName=metric_name,
                Namespace=namespace,
                Period=period,
                Statistic=statistic,
                Threshold=threshold,
                ActionsEnabled=True,
                AlarmActions=alarm_actions or [],
                AlarmDescription=f'Alarm for {metric_name}',
                Dimensions=dimensions or []
            )
            logger.info(f"告警 {name} 创建成功")
        except ClientError as e:
            logger.error(f"创建告警失败: {str(e)}")

    def setup_default_alarms(self, namespace: str = "AI-PPT-Assistant",
                            sns_topic_arn: Optional[str] = None) -> None:
        """
        设置默认告警

        Args:
            namespace: 命名空间
            sns_topic_arn: SNS主题ARN
        """
        alarm_actions = [sns_topic_arn] if sns_topic_arn else []

        # API延迟告警
        self.create_alarm(
            name=f"{namespace}-HighAPILatency",
            metric_name="api_latency_amazon.nova-canvas-v1:0",
            namespace=namespace,
            threshold=5000,  # 5秒
            comparison_operator='GreaterThanThreshold',
            statistic='Average',
            alarm_actions=alarm_actions
        )

        # 错误率告警
        self.create_alarm(
            name=f"{namespace}-HighErrorRate",
            metric_name="generation_errors",
            namespace=namespace,
            threshold=10,
            comparison_operator='GreaterThanThreshold',
            statistic='Sum',
            period=300,
            alarm_actions=alarm_actions
        )

        # 缓存命中率告警
        self.create_alarm(
            name=f"{namespace}-LowCacheHitRate",
            metric_name="cache_hit_rate",
            namespace=namespace,
            threshold=0.3,  # 30%
            comparison_operator='LessThanThreshold',
            statistic='Average',
            alarm_actions=alarm_actions
        )

        logger.info("默认告警设置完成")


class MetricsAggregator:
    """指标聚合器"""

    def __init__(self, window_size: int = 60):
        """
        初始化指标聚合器

        Args:
            window_size: 时间窗口大小（秒）
        """
        self.window_size = window_size
        self._metrics = {}
        self._lock = threading.Lock()

    def add_value(self, metric_name: str, value: float) -> None:
        """
        添加指标值

        Args:
            metric_name: 指标名称
            value: 值
        """
        with self._lock:
            if metric_name not in self._metrics:
                self._metrics[metric_name] = deque(maxlen=100)

            self._metrics[metric_name].append({
                'value': value,
                'timestamp': time.time()
            })

    def get_statistics(self, metric_name: str) -> Dict[str, float]:
        """
        获取指标统计

        Args:
            metric_name: 指标名称

        Returns:
            统计信息
        """
        with self._lock:
            if metric_name not in self._metrics:
                return {}

            # 过滤时间窗口内的值
            current_time = time.time()
            values = [
                item['value'] for item in self._metrics[metric_name]
                if current_time - item['timestamp'] < self.window_size
            ]

            if not values:
                return {}

            return {
                'count': len(values),
                'sum': sum(values),
                'average': statistics.mean(values),
                'min': min(values),
                'max': max(values),
                'median': statistics.median(values),
                'stddev': statistics.stdev(values) if len(values) > 1 else 0
            }


# 全局监控实例
_global_monitor = None


def get_global_monitor() -> CloudWatchMonitor:
    """获取全局监控器实例"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = CloudWatchMonitor()
    return _global_monitor


def init_monitoring(namespace: str = "AI-PPT-Assistant",
                   setup_alarms: bool = True,
                   sns_topic_arn: Optional[str] = None) -> CloudWatchMonitor:
    """
    初始化监控

    Args:
        namespace: CloudWatch命名空间
        setup_alarms: 是否设置默认告警
        sns_topic_arn: SNS主题ARN

    Returns:
        CloudWatch监控器实例
    """
    global _global_monitor

    # 创建监控器
    _global_monitor = CloudWatchMonitor(namespace=namespace)

    # 设置默认告警
    if setup_alarms:
        alarm_manager = AlarmManager()
        alarm_manager.setup_default_alarms(namespace, sns_topic_arn)

    logger.info(f"监控初始化完成，命名空间: {namespace}")

    return _global_monitor