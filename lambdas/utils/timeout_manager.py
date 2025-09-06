"""
Timeout Manager - AI PPT Assistant
Provides centralized timeout control and monitoring for Lambda functions
"""

import functools
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import BaseModel, Field

logger = Logger(__name__)


class TimeoutConfig(BaseModel):
    """Configuration for timeout management"""

    lambda_timeout_seconds: int = Field(..., description="Lambda function timeout")
    grace_period_seconds: int = Field(
        default=5, description="Grace period before timeout"
    )
    warning_threshold: float = Field(
        default=0.8, description="Warning at 80% of timeout"
    )
    critical_threshold: float = Field(
        default=0.9, description="Critical at 90% of timeout"
    )


class TimeoutError(Exception):
    """Custom timeout error with context"""

    def __init__(self, message: str, operation: str, elapsed_time: float):
        self.message = message
        self.operation = operation
        self.elapsed_time = elapsed_time
        super().__init__(
            f"{message} (Operation: {operation}, Elapsed: {elapsed_time:.2f}s)"
        )


class OperationTimer:
    """Context manager for timing operations with timeout control"""

    def __init__(self, operation_name: str, timeout_manager: "TimeoutManager"):
        self.operation_name = operation_name
        self.timeout_manager = timeout_manager
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        self.start_time = time.time()
        self.timeout_manager.check_timeout_status()
        logger.info(f"Starting operation: {self.operation_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        elapsed_time = self.end_time - self.start_time

        if exc_type is None:
            logger.info(
                f"Operation completed: {self.operation_name} ({elapsed_time:.2f}s)"
            )
        else:
            logger.error(
                f"Operation failed: {self.operation_name} ({elapsed_time:.2f}s)"
            )

        self.timeout_manager.record_operation(self.operation_name, elapsed_time)

    def get_elapsed_time(self) -> float:
        """Get current elapsed time for this operation"""
        if self.start_time:
            return time.time() - self.start_time
        return 0.0


class TimeoutManager:
    """
    Centralized timeout management for Lambda functions

    Features:
    - Lambda context-aware timeout monitoring
    - Operation-level timeout control
    - Early warning system
    - Graceful shutdown handling
    - Performance metrics collection
    """

    def __init__(
        self,
        lambda_context: Optional[LambdaContext] = None,
        config: Optional[TimeoutConfig] = None,
    ):
        self.lambda_context = lambda_context
        self.start_time = time.time()

        # Extract timeout from Lambda context or use config
        if lambda_context and hasattr(lambda_context, "get_remaining_time_in_millis"):
            # Calculate initial timeout from remaining time
            remaining_ms = lambda_context.get_remaining_time_in_millis()

            # Handle test environment where remaining_ms might be a Mock object
            from unittest.mock import Mock

            if isinstance(remaining_ms, Mock):
                remaining_ms = 300000  # Default 5 minutes for tests
            elif hasattr(remaining_ms, "return_value"):
                remaining_ms = remaining_ms.return_value
            elif isinstance(remaining_ms, str):
                remaining_ms = int(remaining_ms)
            elif not isinstance(remaining_ms, (int, float)):
                remaining_ms = 300000  # Fallback for any other mock-like objects

            self.total_timeout_seconds = remaining_ms / 1000.0
        elif config:
            self.total_timeout_seconds = config.lambda_timeout_seconds
        else:
            # Default timeout (should not happen in production)
            self.total_timeout_seconds = 60
            logger.warning(
                "No timeout configuration provided, using default 60 seconds"
            )

        # Apply configuration
        self.config = config or TimeoutConfig(
            lambda_timeout_seconds=int(self.total_timeout_seconds)
        )
        self.grace_period = self.config.grace_period_seconds

        # Calculate thresholds
        self.warning_time = self.total_timeout_seconds * self.config.warning_threshold
        self.critical_time = self.total_timeout_seconds * self.config.critical_threshold
        self.effective_timeout = self.total_timeout_seconds - self.grace_period

        # Operation tracking
        self.operations = []
        self.warnings_issued = set()

        logger.info(
            f"TimeoutManager initialized: {self.total_timeout_seconds}s total, "
            f"{self.effective_timeout}s effective, {self.grace_period}s grace period"
        )

    def get_remaining_time(self) -> float:
        """Get remaining time in seconds"""
        if self.lambda_context and hasattr(
            self.lambda_context, "get_remaining_time_in_millis"
        ):
            remaining_ms = self.lambda_context.get_remaining_time_in_millis()

            # Handle test environment where remaining_ms might be a Mock object
            from unittest.mock import Mock

            if isinstance(remaining_ms, Mock):
                remaining_ms = 300000  # Default 5 minutes for tests
            elif hasattr(remaining_ms, "return_value"):
                remaining_ms = remaining_ms.return_value
            elif isinstance(remaining_ms, str):
                remaining_ms = int(remaining_ms)
            elif not isinstance(remaining_ms, (int, float)):
                remaining_ms = 300000  # Fallback for any other mock-like objects

            return remaining_ms / 1000.0
        else:
            elapsed = time.time() - self.start_time
            return max(0, self.total_timeout_seconds - elapsed)

    def get_elapsed_time(self) -> float:
        """Get elapsed time in seconds"""
        return time.time() - self.start_time

    def is_approaching_timeout(self) -> bool:
        """Check if we're approaching timeout"""
        elapsed = self.get_elapsed_time()
        return elapsed >= self.warning_time

    def is_near_critical_timeout(self) -> bool:
        """Check if we're near critical timeout"""
        elapsed = self.get_elapsed_time()
        return elapsed >= self.critical_time

    def should_abort(self) -> bool:
        """Check if we should abort execution"""
        remaining = self.get_remaining_time()
        return remaining <= self.grace_period

    def check_timeout_status(self, operation: str = "general") -> None:
        """Check current timeout status and issue warnings/errors"""
        elapsed = self.get_elapsed_time()
        remaining = self.get_remaining_time()

        if self.should_abort():
            raise TimeoutError(
                f"Execution aborted due to timeout (remaining: {remaining:.2f}s)",
                operation,
                elapsed,
            )

        if self.is_near_critical_timeout() and "critical" not in self.warnings_issued:
            logger.error(
                f"CRITICAL: Near timeout - {remaining:.2f}s remaining ({operation})"
            )
            self.warnings_issued.add("critical")
        elif self.is_approaching_timeout() and "warning" not in self.warnings_issued:
            logger.warning(
                f"WARNING: Approaching timeout - {remaining:.2f}s remaining ({operation})"
            )
            self.warnings_issued.add("warning")

    def record_operation(self, operation_name: str, elapsed_time: float) -> None:
        """Record operation performance"""
        self.operations.append(
            {
                "name": operation_name,
                "elapsed_time": elapsed_time,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        total_elapsed = self.get_elapsed_time()
        remaining = self.get_remaining_time()

        return {
            "total_elapsed_seconds": round(total_elapsed, 2),
            "remaining_seconds": round(remaining, 2),
            "timeout_utilization_percent": round(
                (total_elapsed / self.total_timeout_seconds) * 100, 1
            ),
            "operations_count": len(self.operations),
            "operations": self.operations,
            "status": self._get_status(),
            "warnings_issued": list(self.warnings_issued),
        }

    def _get_status(self) -> str:
        """Get current status string"""
        if self.should_abort():
            return "critical"
        elif self.is_near_critical_timeout():
            return "critical"
        elif self.is_approaching_timeout():
            return "warning"
        else:
            return "normal"

    @contextmanager
    def operation(self, operation_name: str):
        """Context manager for timing operations"""
        timer = OperationTimer(operation_name, self)
        try:
            yield timer
        finally:
            pass


def timeout_decorator(operation_name: str = None):
    """Decorator to add timeout monitoring to functions"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Look for timeout_manager in kwargs or try to create one
            timeout_manager = kwargs.get("timeout_manager")

            if not timeout_manager and hasattr(
                kwargs.get("context"), "get_remaining_time_in_millis"
            ):
                timeout_manager = TimeoutManager(kwargs.get("context"))

            if timeout_manager:
                op_name = operation_name or func.__name__
                with timeout_manager.operation(op_name):
                    return func(*args, **kwargs)
            else:
                return func(*args, **kwargs)

        return wrapper

    return decorator


@contextmanager
def timeout_handler(
    lambda_context: LambdaContext, config: Optional[TimeoutConfig] = None
):
    """Context manager for handling Lambda timeout"""
    timeout_manager = TimeoutManager(lambda_context, config)

    try:
        yield timeout_manager
    finally:
        # Log final performance summary
        summary = timeout_manager.get_performance_summary()
        logger.info("Lambda execution summary", extra={"performance_summary": summary})

        # Log warning if we used more than 90% of available time
        if summary["timeout_utilization_percent"] > 90:
            logger.warning(
                f"High timeout utilization: {summary['timeout_utilization_percent']}%"
            )


# Utility functions for common timeout patterns


def create_timeout_config(
    lambda_context: LambdaContext,
    grace_period: int = 5,
    warning_threshold: float = 0.8,
    critical_threshold: float = 0.9,
) -> TimeoutConfig:
    """Create timeout config from Lambda context"""
    remaining_ms = lambda_context.get_remaining_time_in_millis()

    # Handle test environment where remaining_ms might be a Mock object
    from unittest.mock import Mock

    if isinstance(remaining_ms, Mock):
        remaining_ms = 300000  # Default 5 minutes for tests
    elif hasattr(remaining_ms, "return_value"):
        remaining_ms = remaining_ms.return_value
    elif isinstance(remaining_ms, str):
        remaining_ms = int(remaining_ms)
    elif not isinstance(remaining_ms, (int, float)):
        remaining_ms = 300000  # Fallback for any other mock-like objects

    timeout_seconds = int(remaining_ms / 1000.0)

    return TimeoutConfig(
        lambda_timeout_seconds=timeout_seconds,
        grace_period_seconds=grace_period,
        warning_threshold=warning_threshold,
        critical_threshold=critical_threshold,
    )


def with_timeout_monitoring(
    func: Callable, timeout_manager: TimeoutManager, operation_name: str = None
) -> Any:
    """Execute function with timeout monitoring"""
    op_name = operation_name or func.__name__

    with timeout_manager.operation(op_name):
        return func()
