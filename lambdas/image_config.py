"""
图片生成器配置管理模块
"""

import os
from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class ImageConfig:
    """图片生成配置类 - 使用不可变数据结构确保配置安全"""

    # AWS服务配置
    DEFAULT_BUCKET: str = "ai-ppt-presentations-test"
    NOVA_MODEL_ID: str = "amazon.nova-canvas-v1:0"

    # 图片尺寸配置
    DEFAULT_IMAGE_WIDTH: int = 1200
    DEFAULT_IMAGE_HEIGHT: int = 800

    # 颜色配置
    PLACEHOLDER_COLOR: Tuple[int, int, int] = (240, 240, 250)
    TEXT_COLOR: Tuple[int, int, int] = (100, 100, 100)

    # 性能配置
    MAX_RETRY_ATTEMPTS: int = 3
    RETRY_DELAY_SECONDS: int = 2
    BATCH_TIMEOUT_SECONDS: int = 60

    # 风格配置
    DEFAULT_STYLE_SCHEME: str = "blue_white_professional"
    DEFAULT_ART_STYLE: str = "modern_business"
    DEFAULT_COMPOSITION: str = "centered_balanced"

    @property
    def default_image_size(self) -> Tuple[int, int]:
        """返回默认图片尺寸"""
        return (self.DEFAULT_IMAGE_WIDTH, self.DEFAULT_IMAGE_HEIGHT)

    @classmethod
    def from_environment(cls) -> 'ImageConfig':
        """从环境变量创建配置实例"""
        return cls(
            DEFAULT_BUCKET=os.getenv('IMAGE_BUCKET', cls.DEFAULT_BUCKET),
            NOVA_MODEL_ID=os.getenv('NOVA_MODEL_ID', cls.NOVA_MODEL_ID),
            DEFAULT_IMAGE_WIDTH=int(os.getenv('IMAGE_WIDTH', cls.DEFAULT_IMAGE_WIDTH)),
            DEFAULT_IMAGE_HEIGHT=int(os.getenv('IMAGE_HEIGHT', cls.DEFAULT_IMAGE_HEIGHT)),
            MAX_RETRY_ATTEMPTS=int(os.getenv('MAX_RETRY_ATTEMPTS', cls.MAX_RETRY_ATTEMPTS)),
        )


# 全局配置实例
CONFIG = ImageConfig.from_environment()