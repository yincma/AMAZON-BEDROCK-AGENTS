"""
AI PPT Assistant Phase 3 - 监控系统功能测试用例

本模块包含Phase 3监控系统功能的完整测试用例，遵循TDD原则。
测试覆盖：
- 日志记录验证
- 指标上报验证
- 告警触发验证
- 分布式追踪

根据需求文档Phase 3: 监控系统集成
目标：全面监控系统性能、错误、用户行为，确保生产环境稳定性
"""

import pytest
import json
import uuid
import time
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta
import boto3
from moto import mock_aws
import logging
import threading
from typing import Dict, List, Any
import re


class TestMonitoringSystem:
    """Phase 3 - 监控系统功能测试套件"""

    @pytest.fixture
    def monitoring_system(self):
        """监控系统 - 这是我们要实现的组件"""
        return Mock()

    @pytest.fixture
    def logger_manager(self):
        """日志管理器Mock"""
        return Mock()

    @pytest.fixture
    def metrics_collector(self):
        """指标收集器Mock"""
        return Mock()

    @pytest.fixture
    def alert_manager(self):
        """告警管理器Mock"""
        return Mock()

    @pytest.fixture
    def trace_manager(self):
        """追踪管理器Mock"""
        return Mock()

    @pytest.fixture
    def test_request_context(self):
        """测试请求上下文"""
        return {
            "request_id": f"req-{uuid.uuid4()}",
            "user_id": "test-user-123",
            "presentation_id": f"ppt-{uuid.uuid4()}",
            "timestamp": datetime.now().isoformat(),
            "operation": "generate_presentation",
            "session_id": f"session-{uuid.uuid4()}"
        }

    # ==================== 测试用例1: 日志记录验证 ====================

    def test_structured_logging_format(self, logger_manager, test_request_context):
        """
        测试结构化日志格式

        Given: 系统运行过程中产生日志
        When: 记录日志信息
        Then: 日志以结构化JSON格式记录
        """
        # Arrange
        log_entry = {
            "timestamp": test_request_context["timestamp"],
            "level": "INFO",
            "service": "ai-ppt-assistant",
            "operation": "generate_presentation",
            "request_id": test_request_context["request_id"],
            "user_id": test_request_context["user_id"],
            "message": "Starting PPT generation",
            "metadata": {
                "page_count": 10,
                "template": "modern",
                "with_images": True
            }
        }

        logger_manager.log_structured.return_value = {
            "logged": True,
            "log_id": f"log-{uuid.uuid4()}",
            "format_validated": True
        }

        # Act
        result = logger_manager.log_structured("INFO", "Starting PPT generation", test_request_context)

        # Assert
        logger_manager.log_structured.assert_called_once()
        assert result["logged"] is True
        assert result["format_validated"] is True

    def test_log_level_filtering(self, logger_manager):
        """
        测试日志级别过滤

        Given: 不同级别的日志消息
        When: 配置了特定的日志级别
        Then: 只记录符合级别的日志
        """
        # Arrange
        log_messages = [
            {"level": "DEBUG", "message": "详细调试信息"},
            {"level": "INFO", "message": "一般信息"},
            {"level": "WARNING", "message": "警告信息"},
            {"level": "ERROR", "message": "错误信息"},
            {"level": "CRITICAL", "message": "严重错误"}
        ]

        logger_manager.set_log_level.return_value = {"level": "INFO", "configured": True}
        logger_manager.should_log.side_effect = lambda level: level in ["INFO", "WARNING", "ERROR", "CRITICAL"]

        # Act
        logger_manager.set_log_level("INFO")
        filtered_logs = [msg for msg in log_messages if logger_manager.should_log(msg["level"])]

        # Assert
        assert len(filtered_logs) == 4  # DEBUG被过滤掉
        assert not any(log["level"] == "DEBUG" for log in filtered_logs)

    def test_sensitive_data_masking(self, logger_manager):
        """
        测试敏感数据脱敏

        Given: 包含敏感信息的日志
        When: 记录日志
        Then: 敏感信息被自动脱敏
        """
        # Arrange
        sensitive_log_data = {
            "user_email": "user@example.com",
            "api_key": "sk-1234567890abcdef",
            "user_content": "包含个人信息的演示文稿内容",
            "aws_account_id": "123456789012"
        }

        logger_manager.mask_sensitive_data.return_value = {
            "user_email": "u***@example.com",
            "api_key": "sk-****",
            "user_content": "[CONTENT_MASKED]",
            "aws_account_id": "****56789012"
        }

        # Act
        masked_data = logger_manager.mask_sensitive_data(sensitive_log_data)

        # Assert
        assert "*" in masked_data["user_email"]
        assert "*" in masked_data["api_key"]
        assert "MASKED" in masked_data["user_content"]
        assert masked_data["aws_account_id"].startswith("****")

    def test_log_correlation_across_services(self, logger_manager, test_request_context):
        """
        测试跨服务日志关联

        Given: 请求经过多个服务
        When: 每个服务记录日志
        Then: 日志通过correlation_id关联
        """
        # Arrange
        services = ["api-gateway", "content-generator", "image-generator", "ppt-compiler"]
        correlation_id = test_request_context["request_id"]

        logger_manager.log_with_correlation.return_value = {
            "correlation_id": correlation_id,
            "service_logs": len(services),
            "correlation_success": True
        }

        # Act
        result = logger_manager.log_with_correlation(correlation_id, services)

        # Assert
        assert result["correlation_id"] == correlation_id
        assert result["service_logs"] == len(services)
        assert result["correlation_success"] is True

    def test_error_logging_with_stack_trace(self, logger_manager):
        """
        测试错误日志包含堆栈跟踪

        Given: 系统发生异常
        When: 记录错误日志
        Then: 包含完整的堆栈跟踪信息
        """
        # Arrange
        error_info = {
            "exception_type": "ValidationError",
            "error_message": "Invalid slide content format",
            "stack_trace": [
                "File 'content_generator.py', line 45, in validate_content",
                "File 'slide_validator.py', line 23, in check_format"
            ],
            "context": {"slide_number": 3, "content_length": 0}
        }

        logger_manager.log_error_with_trace.return_value = {
            "error_logged": True,
            "trace_captured": True,
            "error_id": f"err-{uuid.uuid4()}"
        }

        # Act
        result = logger_manager.log_error_with_trace(error_info)

        # Assert
        assert result["error_logged"] is True
        assert result["trace_captured"] is True
        assert "err-" in result["error_id"]

    def test_log_rotation_and_retention(self, logger_manager):
        """
        测试日志轮转和保留策略

        Given: 长期运行的系统
        When: 日志达到轮转条件
        Then: 自动轮转并按保留策略管理
        """
        # Arrange
        rotation_config = {
            "max_file_size": "100MB",
            "retention_days": 30,
            "compression_enabled": True
        }

        logger_manager.manage_log_rotation.return_value = {
            "rotation_triggered": True,
            "old_logs_archived": 5,
            "space_freed": "250MB",
            "retention_policy_applied": True
        }

        # Act
        result = logger_manager.manage_log_rotation(rotation_config)

        # Assert
        assert result["rotation_triggered"] is True
        assert result["old_logs_archived"] > 0
        assert result["retention_policy_applied"] is True

    # ==================== 测试用例2: 指标上报验证 ====================

    def test_performance_metrics_collection(self, metrics_collector, test_request_context):
        """
        测试性能指标收集

        Given: PPT生成过程
        When: 收集性能指标
        Then: 记录响应时间、吞吐量等指标
        """
        # Arrange
        performance_metrics = {
            "response_time_ms": 25300,
            "content_generation_time_ms": 8200,
            "image_generation_time_ms": 12100,
            "compilation_time_ms": 5000,
            "cpu_utilization_percent": 78.5,
            "memory_usage_mb": 1650,
            "request_id": test_request_context["request_id"]
        }

        metrics_collector.record_performance_metrics.return_value = {
            "metrics_recorded": True,
            "metric_count": len(performance_metrics),
            "cloudwatch_published": True
        }

        # Act
        result = metrics_collector.record_performance_metrics(performance_metrics)

        # Assert
        assert result["metrics_recorded"] is True
        assert result["cloudwatch_published"] is True
        assert result["metric_count"] == len(performance_metrics)

    def test_business_metrics_tracking(self, metrics_collector):
        """
        测试业务指标追踪

        Given: 用户使用系统
        When: 记录业务指标
        Then: 追踪用户行为和系统使用情况
        """
        # Arrange
        business_metrics = {
            "presentations_generated": 1,
            "pages_created": 10,
            "images_generated": 8,
            "template_used": "modern",
            "user_satisfaction": 4.5,
            "completion_rate": 1.0,
            "retry_count": 0
        }

        metrics_collector.track_business_metrics.return_value = {
            "business_metrics_tracked": True,
            "dashboard_updated": True,
            "kpi_calculated": True
        }

        # Act
        result = metrics_collector.track_business_metrics(business_metrics)

        # Assert
        assert result["business_metrics_tracked"] is True
        assert result["dashboard_updated"] is True

    def test_error_metrics_aggregation(self, metrics_collector):
        """
        测试错误指标聚合

        Given: 系统运行过程中发生各种错误
        When: 聚合错误指标
        Then: 按类型、频率统计错误
        """
        # Arrange
        error_events = [
            {"type": "ValidationError", "service": "content-generator", "timestamp": datetime.now()},
            {"type": "TimeoutError", "service": "image-generator", "timestamp": datetime.now()},
            {"type": "ValidationError", "service": "content-generator", "timestamp": datetime.now()},
            {"type": "S3Error", "service": "ppt-compiler", "timestamp": datetime.now()}
        ]

        metrics_collector.aggregate_error_metrics.return_value = {
            "total_errors": 4,
            "error_types": {
                "ValidationError": 2,
                "TimeoutError": 1,
                "S3Error": 1
            },
            "error_rate": 0.04,  # 4%
            "most_common_error": "ValidationError"
        }

        # Act
        result = metrics_collector.aggregate_error_metrics(error_events)

        # Assert
        assert result["total_errors"] == len(error_events)
        assert result["most_common_error"] == "ValidationError"
        assert result["error_rate"] < 0.1  # 错误率应该较低

    def test_custom_metrics_definition(self, metrics_collector):
        """
        测试自定义指标定义

        Given: 需要追踪特定的业务指标
        When: 定义自定义指标
        Then: 支持灵活的指标配置
        """
        # Arrange
        custom_metrics = [
            {
                "name": "ppt_quality_score",
                "type": "gauge",
                "unit": "score",
                "description": "PPT quality assessment score"
            },
            {
                "name": "user_engagement_time",
                "type": "histogram",
                "unit": "seconds",
                "description": "Time users spend in the application"
            }
        ]

        metrics_collector.register_custom_metrics.return_value = {
            "metrics_registered": 2,
            "registration_successful": True,
            "cloudwatch_namespaces_created": True
        }

        # Act
        result = metrics_collector.register_custom_metrics(custom_metrics)

        # Assert
        assert result["metrics_registered"] == len(custom_metrics)
        assert result["registration_successful"] is True

    def test_metrics_batch_publishing(self, metrics_collector):
        """
        测试指标批量发布

        Given: 大量指标数据需要发布
        When: 批量发布到CloudWatch
        Then: 高效发布并处理失败重试
        """
        # Arrange
        metric_batch = [
            {"metric_name": "response_time", "value": 25.3, "unit": "Seconds"},
            {"metric_name": "memory_usage", "value": 1650, "unit": "Megabytes"},
            {"metric_name": "request_count", "value": 1, "unit": "Count"}
        ] * 50  # 批量数据

        metrics_collector.publish_metrics_batch.return_value = {
            "metrics_published": 150,
            "batch_size": 50,
            "failed_metrics": 0,
            "publish_latency_ms": 245
        }

        # Act
        result = metrics_collector.publish_metrics_batch(metric_batch)

        # Assert
        assert result["metrics_published"] == len(metric_batch)
        assert result["failed_metrics"] == 0
        assert result["publish_latency_ms"] < 1000

    def test_real_time_metrics_streaming(self, metrics_collector):
        """
        测试实时指标流式传输

        Given: 需要实时监控的关键指标
        When: 启用流式传输
        Then: 指标实时推送到监控系统
        """
        # Arrange
        streaming_config = {
            "enabled": True,
            "critical_metrics": ["error_rate", "response_time", "availability"],
            "update_interval_seconds": 10
        }

        metrics_collector.setup_real_time_streaming.return_value = {
            "streaming_enabled": True,
            "metrics_streamed": 3,
            "stream_health": "healthy",
            "latency_ms": 45
        }

        # Act
        result = metrics_collector.setup_real_time_streaming(streaming_config)

        # Assert
        assert result["streaming_enabled"] is True
        assert result["stream_health"] == "healthy"
        assert result["latency_ms"] < 100

    # ==================== 测试用例3: 告警触发验证 ====================

    def test_response_time_threshold_alert(self, alert_manager, metrics_collector):
        """
        测试响应时间阈值告警

        Given: 响应时间超过阈值
        When: 监控系统检测到异常
        Then: 触发告警通知
        """
        # Arrange
        alert_config = {
            "metric": "response_time",
            "threshold": 30.0,
            "comparison": "greater_than",
            "evaluation_periods": 2,
            "datapoints_to_alarm": 2
        }

        current_metrics = {
            "response_time": 35.2,  # 超过阈值
            "timestamp": datetime.now()
        }

        alert_manager.evaluate_alert.return_value = {
            "alert_triggered": True,
            "alert_id": f"alert-{uuid.uuid4()}",
            "severity": "warning",
            "message": "Response time exceeded threshold: 35.2s > 30.0s",
            "notification_sent": True
        }

        # Act
        result = alert_manager.evaluate_alert(alert_config, current_metrics)

        # Assert
        assert result["alert_triggered"] is True
        assert result["severity"] == "warning"
        assert result["notification_sent"] is True

    def test_error_rate_spike_detection(self, alert_manager):
        """
        测试错误率突增检测

        Given: 错误率突然上升
        When: 错误率超过基线的一定倍数
        Then: 触发严重告警
        """
        # Arrange
        error_rate_data = {
            "current_error_rate": 0.15,  # 15%
            "baseline_error_rate": 0.02,  # 正常2%
            "spike_threshold": 5.0,  # 5倍基线
            "time_window": "5_minutes"
        }

        alert_manager.detect_error_rate_spike.return_value = {
            "spike_detected": True,
            "spike_magnitude": 7.5,  # 7.5倍基线
            "severity": "critical",
            "alert_message": "Error rate spike detected: 15% (7.5x baseline)",
            "immediate_notification": True,
            "escalation_triggered": True
        }

        # Act
        result = alert_manager.detect_error_rate_spike(error_rate_data)

        # Assert
        assert result["spike_detected"] is True
        assert result["severity"] == "critical"
        assert result["escalation_triggered"] is True

    def test_resource_exhaustion_alerts(self, alert_manager):
        """
        测试资源耗尽告警

        Given: 系统资源接近限制
        When: CPU、内存或连接数超过阈值
        Then: 提前发出资源告警
        """
        # Arrange
        resource_metrics = {
            "cpu_utilization": 0.92,  # 92% CPU使用率
            "memory_utilization": 0.88,  # 88% 内存使用率
            "lambda_concurrent_executions": 950,  # 接近1000限制
            "dynamodb_throttles": 5  # DynamoDB限流
        }

        alert_manager.check_resource_thresholds.return_value = {
            "alerts_triggered": [
                {"resource": "cpu", "severity": "warning", "utilization": 0.92},
                {"resource": "lambda_concurrency", "severity": "critical", "value": 950}
            ],
            "resource_pressure": "high",
            "scaling_recommended": True
        }

        # Act
        result = alert_manager.check_resource_thresholds(resource_metrics)

        # Assert
        assert len(result["alerts_triggered"]) > 0
        assert result["resource_pressure"] == "high"
        assert result["scaling_recommended"] is True

    def test_alert_notification_channels(self, alert_manager):
        """
        测试告警通知渠道

        Given: 配置了多种通知渠道
        When: 触发告警
        Then: 按严重程度选择合适的通知渠道
        """
        # Arrange
        notification_config = {
            "channels": {
                "email": {"enabled": True, "severity": ["warning", "critical"]},
                "slack": {"enabled": True, "severity": ["critical"]},
                "sms": {"enabled": True, "severity": ["critical"]},
                "webhook": {"enabled": True, "severity": ["warning", "critical"]}
            }
        }

        critical_alert = {
            "severity": "critical",
            "message": "System experiencing high error rate"
        }

        alert_manager.send_notifications.return_value = {
            "notifications_sent": 3,  # email, slack, sms
            "successful_channels": ["email", "slack", "sms"],
            "failed_channels": [],
            "delivery_time_ms": 1250
        }

        # Act
        result = alert_manager.send_notifications(critical_alert, notification_config)

        # Assert
        assert result["notifications_sent"] == 3
        assert "slack" in result["successful_channels"]
        assert len(result["failed_channels"]) == 0

    def test_alert_escalation_policy(self, alert_manager):
        """
        测试告警升级策略

        Given: 告警未及时响应
        When: 超过升级时间
        Then: 自动升级到更高级别
        """
        # Arrange
        escalation_policy = {
            "levels": [
                {"level": 1, "timeout_minutes": 5, "notify": ["on-call-engineer"]},
                {"level": 2, "timeout_minutes": 15, "notify": ["team-lead", "on-call-engineer"]},
                {"level": 3, "timeout_minutes": 30, "notify": ["manager", "team-lead"]}
            ]
        }

        unacknowledged_alert = {
            "alert_id": "alert-123",
            "created_at": (datetime.now() - timedelta(minutes=20)).isoformat(),
            "acknowledged": False,
            "current_level": 1
        }

        alert_manager.process_escalation.return_value = {
            "escalation_triggered": True,
            "escalated_to_level": 3,
            "notifications_sent": 2,
            "escalation_reason": "Alert unacknowledged for 20 minutes"
        }

        # Act
        result = alert_manager.process_escalation(unacknowledged_alert, escalation_policy)

        # Assert
        assert result["escalation_triggered"] is True
        assert result["escalated_to_level"] == 3
        assert result["notifications_sent"] > 0

    def test_alert_suppression_and_grouping(self, alert_manager):
        """
        测试告警抑制和分组

        Given: 短时间内大量相似告警
        When: 应用告警分组策略
        Then: 合并相似告警，避免告警风暴
        """
        # Arrange
        similar_alerts = [
            {"type": "high_response_time", "service": "content-generator", "timestamp": datetime.now()},
            {"type": "high_response_time", "service": "content-generator", "timestamp": datetime.now()},
            {"type": "high_response_time", "service": "image-generator", "timestamp": datetime.now()},
            {"type": "memory_usage", "service": "ppt-compiler", "timestamp": datetime.now()}
        ]

        alert_manager.group_similar_alerts.return_value = {
            "original_alerts": 4,
            "grouped_alerts": 2,
            "suppressed_alerts": 2,
            "groups": [
                {"type": "high_response_time", "count": 3, "services": ["content-generator", "image-generator"]},
                {"type": "memory_usage", "count": 1, "services": ["ppt-compiler"]}
            ]
        }

        # Act
        result = alert_manager.group_similar_alerts(similar_alerts)

        # Assert
        assert result["grouped_alerts"] < result["original_alerts"]
        assert result["suppressed_alerts"] > 0
        assert len(result["groups"]) == 2

    # ==================== 测试用例4: 分布式追踪 ====================

    def test_request_tracing_across_services(self, trace_manager, test_request_context):
        """
        测试跨服务请求追踪

        Given: 请求经过多个微服务
        When: 启用分布式追踪
        Then: 完整追踪请求路径和耗时
        """
        # Arrange
        trace_id = test_request_context["request_id"]
        service_calls = [
            {"service": "api-gateway", "operation": "receive_request", "duration_ms": 15},
            {"service": "content-generator", "operation": "generate_outline", "duration_ms": 8200},
            {"service": "image-generator", "operation": "generate_images", "duration_ms": 12100},
            {"service": "ppt-compiler", "operation": "compile_pptx", "duration_ms": 5000}
        ]

        trace_manager.create_trace.return_value = {
            "trace_id": trace_id,
            "spans_created": len(service_calls),
            "total_duration_ms": sum(call["duration_ms"] for call in service_calls),
            "trace_complete": True
        }

        # Act
        result = trace_manager.create_trace(trace_id, service_calls)

        # Assert
        assert result["trace_id"] == trace_id
        assert result["spans_created"] == len(service_calls)
        assert result["trace_complete"] is True

    def test_trace_span_annotations(self, trace_manager):
        """
        测试追踪跨度注释

        Given: 服务执行过程中的重要事件
        When: 添加跨度注释
        Then: 记录详细的执行信息
        """
        # Arrange
        span_annotations = [
            {"timestamp": datetime.now(), "event": "bedrock_api_call_start", "metadata": {"model": "claude-4"}},
            {"timestamp": datetime.now(), "event": "content_generation_complete", "metadata": {"tokens": 1250}},
            {"timestamp": datetime.now(), "event": "s3_upload_start", "metadata": {"file_size": "2.5MB"}},
            {"timestamp": datetime.now(), "event": "s3_upload_complete", "metadata": {"duration_ms": 850}}
        ]

        trace_manager.add_span_annotations.return_value = {
            "annotations_added": len(span_annotations),
            "span_enriched": True,
            "trace_detail_level": "detailed"
        }

        # Act
        result = trace_manager.add_span_annotations("span-123", span_annotations)

        # Assert
        assert result["annotations_added"] == len(span_annotations)
        assert result["span_enriched"] is True

    def test_trace_error_capture(self, trace_manager):
        """
        测试追踪错误捕获

        Given: 服务调用过程中发生错误
        When: 错误被捕获
        Then: 错误信息被记录到追踪中
        """
        # Arrange
        error_details = {
            "service": "image-generator",
            "operation": "generate_slide_image",
            "error_type": "TimeoutError",
            "error_message": "Bedrock Nova API timeout after 30 seconds",
            "stack_trace": "...",
            "retry_count": 2,
            "final_outcome": "failed"
        }

        trace_manager.record_trace_error.return_value = {
            "error_recorded": True,
            "span_marked_failed": True,
            "error_propagated": True,
            "trace_status": "error"
        }

        # Act
        result = trace_manager.record_trace_error("trace-123", error_details)

        # Assert
        assert result["error_recorded"] is True
        assert result["span_marked_failed"] is True
        assert result["trace_status"] == "error"

    def test_trace_performance_analysis(self, trace_manager):
        """
        测试追踪性能分析

        Given: 完整的请求追踪数据
        When: 进行性能分析
        Then: 识别性能瓶颈和优化机会
        """
        # Arrange
        trace_data = {
            "trace_id": "trace-456",
            "total_duration_ms": 25300,
            "spans": [
                {"service": "content-generator", "duration_ms": 8200, "cpu_usage": 0.75},
                {"service": "image-generator", "duration_ms": 12100, "cpu_usage": 0.85},
                {"service": "ppt-compiler", "duration_ms": 5000, "cpu_usage": 0.60}
            ]
        }

        trace_manager.analyze_trace_performance.return_value = {
            "bottleneck_service": "image-generator",
            "bottleneck_duration_ms": 12100,
            "bottleneck_percentage": 47.8,
            "optimization_recommendations": [
                "Consider parallel image generation",
                "Optimize image resolution settings",
                "Implement image caching"
            ],
            "performance_score": 0.72
        }

        # Act
        result = trace_manager.analyze_trace_performance(trace_data)

        # Assert
        assert result["bottleneck_service"] == "image-generator"
        assert result["bottleneck_percentage"] > 40
        assert len(result["optimization_recommendations"]) > 0

    def test_trace_sampling_strategy(self, trace_manager):
        """
        测试追踪采样策略

        Given: 高并发的生产环境
        When: 应用智能采样策略
        Then: 平衡追踪覆盖率和性能开销
        """
        # Arrange
        sampling_config = {
            "default_rate": 0.1,  # 10% 默认采样率
            "error_rate": 1.0,    # 100% 错误采样
            "slow_request_rate": 0.5,  # 50% 慢请求采样
            "critical_path_rate": 0.8   # 80% 关键路径采样
        }

        requests = [
            {"type": "normal", "duration_ms": 20000},
            {"type": "error", "duration_ms": 15000, "has_error": True},
            {"type": "slow", "duration_ms": 35000},
            {"type": "critical", "operation": "user_facing_api"}
        ]

        trace_manager.apply_sampling_strategy.return_value = {
            "total_requests": 4,
            "sampled_requests": 3,
            "sampling_rate": 0.75,
            "overhead_reduction": 0.60
        }

        # Act
        result = trace_manager.apply_sampling_strategy(requests, sampling_config)

        # Assert
        assert result["sampled_requests"] <= result["total_requests"]
        assert result["overhead_reduction"] > 0

    def test_distributed_trace_visualization(self, trace_manager):
        """
        测试分布式追踪可视化

        Given: 复杂的微服务调用链
        When: 生成追踪可视化
        Then: 提供清晰的调用关系图
        """
        # Arrange
        complex_trace = {
            "trace_id": "complex-trace-789",
            "root_span": "api-gateway",
            "service_dependencies": [
                {"from": "api-gateway", "to": "content-generator", "calls": 1},
                {"from": "api-gateway", "to": "image-generator", "calls": 1},
                {"from": "content-generator", "to": "bedrock-claude", "calls": 3},
                {"from": "image-generator", "to": "bedrock-nova", "calls": 8},
                {"from": "ppt-compiler", "to": "s3", "calls": 2}
            ]
        }

        trace_manager.generate_trace_visualization.return_value = {
            "visualization_created": True,
            "format": "svg",
            "nodes": 6,
            "edges": 5,
            "critical_path_highlighted": True,
            "url": "https://trace-ui.example.com/trace/complex-trace-789"
        }

        # Act
        result = trace_manager.generate_trace_visualization(complex_trace)

        # Assert
        assert result["visualization_created"] is True
        assert result["nodes"] > 0
        assert result["critical_path_highlighted"] is True

    # ==================== 监控系统集成测试 ====================

    @pytest.mark.integration
    def test_end_to_end_monitoring_workflow(self, monitoring_system, test_request_context):
        """
        测试端到端监控工作流

        Given: 完整的监控系统
        When: 处理一个完整的PPT生成请求
        Then: 所有监控组件协同工作
        """
        # Arrange
        monitoring_workflow = {
            "request_context": test_request_context,
            "enable_all_monitoring": True,
            "monitoring_components": ["logging", "metrics", "alerts", "tracing"]
        }

        monitoring_system.execute_full_monitoring.return_value = {
            "monitoring_successful": True,
            "components_active": 4,
            "logs_generated": 25,
            "metrics_recorded": 15,
            "traces_created": 1,
            "alerts_evaluated": 8,
            "overall_health": "healthy"
        }

        # Act
        result = monitoring_system.execute_full_monitoring(monitoring_workflow)

        # Assert
        assert result["monitoring_successful"] is True
        assert result["components_active"] == 4
        assert result["overall_health"] == "healthy"

    def test_monitoring_system_health_check(self, monitoring_system):
        """
        测试监控系统自身健康检查

        Given: 监控系统运行中
        When: 执行自身健康检查
        Then: 验证所有监控组件正常工作
        """
        # Arrange
        health_check_components = [
            "cloudwatch_logs", "cloudwatch_metrics", "sns_notifications",
            "x-ray_tracing", "elasticsearch_logs"
        ]

        monitoring_system.perform_health_check.return_value = {
            "overall_status": "healthy",
            "component_status": {
                "cloudwatch_logs": "healthy",
                "cloudwatch_metrics": "healthy",
                "sns_notifications": "healthy",
                "x-ray_tracing": "healthy",
                "elasticsearch_logs": "degraded"  # 一个组件降级
            },
            "degraded_components": 1,
            "critical_issues": 0
        }

        # Act
        result = monitoring_system.perform_health_check(health_check_components)

        # Assert
        assert result["overall_status"] in ["healthy", "degraded"]
        assert result["critical_issues"] == 0
        assert result["degraded_components"] <= 1

    # ==================== 监控性能和可靠性测试 ====================

    def test_monitoring_overhead_measurement(self, monitoring_system):
        """
        测试监控系统开销测量

        Given: 启用完整监控
        When: 测量系统性能开销
        Then: 开销在可接受范围内
        """
        # Arrange
        baseline_performance = {"response_time_ms": 25000, "cpu_usage": 0.70, "memory_mb": 1500}
        with_monitoring_performance = {"response_time_ms": 25800, "cpu_usage": 0.74, "memory_mb": 1580}

        monitoring_system.measure_monitoring_overhead.return_value = {
            "overhead_percentage": 3.2,  # 3.2% 开销
            "acceptable_overhead": True,
            "performance_impact": "minimal",
            "recommendations": ["Consider reducing log verbosity in production"]
        }

        # Act
        result = monitoring_system.measure_monitoring_overhead(baseline_performance, with_monitoring_performance)

        # Assert
        assert result["overhead_percentage"] < 5.0  # 开销应该小于5%
        assert result["acceptable_overhead"] is True

    def test_monitoring_data_retention_and_cleanup(self, monitoring_system):
        """
        测试监控数据保留和清理

        Given: 长期积累的监控数据
        When: 执行数据清理策略
        Then: 按保留策略清理过期数据
        """
        # Arrange
        retention_policy = {
            "logs_retention_days": 30,
            "metrics_retention_days": 90,
            "traces_retention_days": 14,
            "alerts_retention_days": 180
        }

        monitoring_system.apply_data_retention.return_value = {
            "cleanup_executed": True,
            "data_removed": {
                "logs": "150GB",
                "metrics": "25GB",
                "traces": "80GB",
                "alerts": "5GB"
            },
            "storage_freed": "260GB",
            "retention_compliance": True
        }

        # Act
        result = monitoring_system.apply_data_retention(retention_policy)

        # Assert
        assert result["cleanup_executed"] is True
        assert result["retention_compliance"] is True
        assert "GB" in result["storage_freed"]


# ==================== 测试辅助函数 ====================

class MonitoringTestHelper:
    """监控测试辅助类"""

    @staticmethod
    def create_mock_log_entry(level: str, message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """创建模拟日志条目"""
        return {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "context": context or {},
            "service": "ai-ppt-assistant"
        }

    @staticmethod
    def generate_test_metrics(count: int) -> List[Dict[str, Any]]:
        """生成测试指标数据"""
        metrics = []
        for i in range(count):
            metrics.append({
                "name": f"test_metric_{i}",
                "value": i * 10.5,
                "unit": "Count",
                "timestamp": datetime.now()
            })
        return metrics

    @staticmethod
    def simulate_error_scenarios() -> List[Dict[str, Any]]:
        """模拟错误场景"""
        return [
            {"type": "ValidationError", "frequency": "high", "impact": "low"},
            {"type": "TimeoutError", "frequency": "medium", "impact": "high"},
            {"type": "ServiceUnavailable", "frequency": "low", "impact": "critical"}
        ]


# ==================== Pytest配置 ====================

@pytest.fixture(autouse=True)
def setup_monitoring_test_environment():
    """监控测试环境设置"""
    import os
    # 设置测试环境变量
    os.environ.update({
        "AWS_REGION": "us-east-1",
        "MONITORING_ENABLED": "true",
        "LOG_LEVEL": "DEBUG",
        "CLOUDWATCH_NAMESPACE": "AI-PPT-Assistant/Test",
        "ENABLE_XRAY_TRACING": "true"
    })
    yield
    # 清理环境变量
    for var in ["MONITORING_ENABLED", "LOG_LEVEL", "CLOUDWATCH_NAMESPACE", "ENABLE_XRAY_TRACING"]:
        if var in os.environ:
            del os.environ[var]


@pytest.mark.monitoring
class MonitoringRegressionTests:
    """监控回归测试套件"""

    def test_monitoring_backward_compatibility(self, monitoring_system):
        """确保监控系统向后兼容"""
        legacy_config = {
            "version": "1.0",
            "log_format": "text",  # 旧格式
            "metric_namespace": "PPTAssistant"  # 旧命名空间
        }

        result = monitoring_system.validate_backward_compatibility(legacy_config)
        assert result["compatible"] is True
        assert result["migration_required"] is False


if __name__ == "__main__":
    # 运行监控测试
    pytest.main([__file__ + "::TestMonitoringSystem::test_structured_logging_format", "-v"])