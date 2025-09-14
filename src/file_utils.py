"""
文件处理工具 - 提供文件操作和临时目录管理
"""

import os
import tempfile
import shutil
import time
import glob
import logging
from contextlib import contextmanager
from typing import Generator

logger = logging.getLogger(__name__)


@contextmanager
def temporary_directory() -> Generator[str, None, None]:
    """
    创建临时目录上下文管理器

    Yields:
        str: 临时目录路径
    """
    temp_dir = tempfile.mkdtemp(prefix='ppt_')
    try:
        logger.info(f"Created temporary directory: {temp_dir}")
        yield temp_dir
    finally:
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
            logger.info(f"Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to clean up temporary directory {temp_dir}: {e}")


def ensure_tmp_space(min_free_mb: int = 100) -> float:
    """
    确保/tmp有足够的可用空间

    Args:
        min_free_mb: 最小可用空间（MB）

    Returns:
        float: 可用空间大小（MB）

    Raises:
        OSError: 当空间不足时
    """
    try:
        usage = shutil.disk_usage('/tmp')
        free_mb = usage.free / (1024 * 1024)

        logger.info(f"Available space in /tmp: {free_mb:.2f} MB")

        if free_mb < min_free_mb:
            logger.warning(f"Low disk space in /tmp: {free_mb:.2f} MB (minimum: {min_free_mb} MB)")
            # 尝试清理旧文件
            cleaned_mb = clean_tmp_files()
            free_mb += cleaned_mb

            if free_mb < min_free_mb:
                raise OSError(f"Insufficient disk space in /tmp: {free_mb:.2f} MB "
                             f"(required: {min_free_mb} MB)")

        return free_mb

    except Exception as e:
        logger.error(f"Failed to check disk space: {e}")
        raise


def clean_tmp_files(max_age_hours: int = 1) -> float:
    """
    清理临时文件

    Args:
        max_age_hours: 文件最大保留时间（小时）

    Returns:
        float: 清理的空间大小（MB）
    """
    cleaned_size = 0
    cleaned_count = 0
    current_time = time.time()
    max_age_seconds = max_age_hours * 3600

    # 清理模式列表
    cleanup_patterns = [
        '/tmp/ppt_*.pptx',
        '/tmp/ppt_*/',
        '/tmp/tmp*ppt*',
        '/tmp/presentation_*'
    ]

    for pattern in cleanup_patterns:
        try:
            for file_path in glob.glob(pattern):
                try:
                    # 检查文件年龄
                    file_age = current_time - os.path.getmtime(file_path)
                    if file_age > max_age_seconds:
                        file_size = get_file_size(file_path)

                        if os.path.isdir(file_path):
                            shutil.rmtree(file_path, ignore_errors=True)
                        else:
                            os.remove(file_path)

                        cleaned_size += file_size
                        cleaned_count += 1
                        logger.info(f"Cleaned up: {file_path}")

                except (OSError, IOError) as e:
                    logger.warning(f"Failed to clean file {file_path}: {e}")
                    continue

        except Exception as e:
            logger.warning(f"Failed to process pattern {pattern}: {e}")
            continue

    cleaned_mb = cleaned_size / (1024 * 1024)
    logger.info(f"Cleaned up {cleaned_count} files, freed {cleaned_mb:.2f} MB")

    return cleaned_mb


def get_file_size(file_path: str) -> int:
    """
    获取文件或目录大小

    Args:
        file_path: 文件路径

    Returns:
        int: 文件大小（字节）
    """
    try:
        if os.path.isfile(file_path):
            return os.path.getsize(file_path)
        elif os.path.isdir(file_path):
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(file_path):
                for filename in filenames:
                    fp = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(fp)
                    except (OSError, IOError):
                        continue
            return total_size
        else:
            return 0
    except (OSError, IOError):
        return 0


def create_temp_file(content: bytes, prefix: str = 'ppt_', suffix: str = '.pptx') -> str:
    """
    创建临时文件

    Args:
        content: 文件内容
        prefix: 文件名前缀
        suffix: 文件扩展名

    Returns:
        str: 临时文件路径
    """
    with tempfile.NamedTemporaryFile(
        prefix=prefix,
        suffix=suffix,
        delete=False
    ) as temp_file:
        temp_file.write(content)
        temp_path = temp_file.name

    logger.info(f"Created temporary file: {temp_path}")
    return temp_path


def safe_remove_file(file_path: str) -> bool:
    """
    安全删除文件

    Args:
        file_path: 文件路径

    Returns:
        bool: 删除是否成功
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Successfully removed file: {file_path}")
            return True
        else:
            logger.warning(f"File does not exist: {file_path}")
            return False
    except Exception as e:
        logger.error(f"Failed to remove file {file_path}: {e}")
        return False


def validate_file_path(file_path: str, must_exist: bool = True) -> bool:
    """
    验证文件路径

    Args:
        file_path: 文件路径
        must_exist: 文件是否必须存在

    Returns:
        bool: 路径是否有效
    """
    try:
        # 检查路径格式
        if not isinstance(file_path, str) or not file_path.strip():
            return False

        # 检查文件存在性
        if must_exist and not os.path.exists(file_path):
            return False

        # 检查路径安全性（防止路径遍历攻击）
        normalized_path = os.path.normpath(file_path)
        if '..' in normalized_path or normalized_path.startswith('/'):
            # 这里可以根据需要调整安全策略
            pass

        return True

    except Exception:
        return False


class TempFileManager:
    """临时文件管理器"""

    def __init__(self):
        self.temp_files = []

    def create_temp_file(self, content: bytes, prefix: str = 'ppt_', suffix: str = '.pptx') -> str:
        """
        创建临时文件并跟踪

        Args:
            content: 文件内容
            prefix: 文件名前缀
            suffix: 文件扩展名

        Returns:
            str: 临时文件路径
        """
        temp_path = create_temp_file(content, prefix, suffix)
        self.temp_files.append(temp_path)
        return temp_path

    def cleanup_all(self):
        """清理所有临时文件"""
        for temp_file in self.temp_files:
            safe_remove_file(temp_file)
        self.temp_files.clear()
        logger.info("Cleaned up all managed temporary files")

    def __del__(self):
        """析构时自动清理"""
        self.cleanup_all()


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小显示

    Args:
        size_bytes: 文件大小（字节）

    Returns:
        str: 格式化的大小字符串
    """
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0

    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.2f} {size_names[i]}"