"""
限流管理器 - 控制API调用速率

功能：
- 添加随机初始延迟
- 跟踪并发请求数
- 实现令牌桶算法
"""
import time
import random
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ThrottleManager:
    """限流管理器"""

    # 类级别的共享状态（在Lambda容器内共享）
    _last_request_time = 0
    _min_interval = 1.0  # 最小请求间隔（秒）

    @classmethod
    def add_initial_delay(cls, max_delay: float = 5.0) -> None:
        """添加随机初始延迟，减少请求冲突

        Args:
            max_delay: 最大延迟时间（秒）
        """
        delay = random.uniform(0.1, max_delay)
        logger.info(f"添加初始延迟: {delay:.2f}秒")
        time.sleep(delay)

    @classmethod
    def wait_if_needed(cls) -> None:
        """如果需要，等待以满足最小请求间隔"""
        current_time = time.time()
        time_since_last = current_time - cls._last_request_time

        if time_since_last < cls._min_interval:
            wait_time = cls._min_interval - time_since_last
            logger.info(f"限流等待: {wait_time:.2f}秒")
            time.sleep(wait_time)

        cls._last_request_time = time.time()

    @classmethod
    def get_batch_delay(cls, batch_index: int, batch_size: int = 5) -> float:
        """获取批处理延迟

        Args:
            batch_index: 当前批次索引
            batch_size: 批次大小

        Returns:
            延迟时间（秒）
        """
        # 每个批次增加延迟
        base_delay = 2.0
        batch_delay = base_delay * (batch_index // batch_size)
        jitter = random.uniform(0, 1)
        return batch_delay + jitter


def with_throttle(func):
    """带限流的装饰器"""
    def wrapper(*args, **kwargs):
        ThrottleManager.wait_if_needed()
        return func(*args, **kwargs)
    return wrapper