"""
AI PPT Assistant Phase 3 - 告警管理器
====================================
响应时间阈值告警、错误率突增检测、告警升级策略、SNS通知集成

功能:
- 阈值告警评估
- 错误率突增检测
- 资源耗尽监控
- 多渠道通知
- 告警升级策略
- 告警分组和抑制
"""

import json
import os
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from collections import defaultdict, deque
import boto3
from botocore.exceptions import ClientError
import statistics
import hashlib
import uuid

# AWS 客户端
cloudwatch = boto3.client('cloudwatch')
sns = boto3.client('sns')
ses = boto3.client('ses')
lambda_client = boto3.client('lambda')

# 环境配置
SERVICE_NAME = os.environ.get('SERVICE_NAME', 'ai-ppt-assistant')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN', '')
ALERT_EMAIL = os.environ.get('ALERT_EMAIL', '')
SLACK_WEBHOOK = os.environ.get('SLACK_WEBHOOK', '')
ENABLE_ESCALATION = os.environ.get('ENABLE_ESCALATION', 'true').lower() == 'true'


class AlertSeverity(Enum):
    """告警严重级别"""
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4


class AlertState(Enum):
    """告警状态"""
    OK = 'OK'
    ALARM = 'ALARM'
    INSUFFICIENT_DATA = 'INSUFFICIENT_DATA'


class AlertManager:
    """统一的告警管理器"""

    def __init__(self):
        """初始化告警管理器"""
        self.service_name = SERVICE_NAME
        self.environment = ENVIRONMENT

        # 告警配置
        self.alert_configs = {}
        self.load_default_configs()

        # 活跃告警
        self.active_alerts = {}
        self.alert_history = deque(maxlen=1000)

        # 错误率基线
        self.error_baseline = defaultdict(lambda: {
            'values': deque(maxlen=100),
            'baseline': 0.02,  # 2% 默认基线
            'last_update': datetime.utcnow()
        })

        # 告警分组
        self.alert_groups = defaultdict(list)
        self.suppression_rules = []

        # 升级策略
        self.escalation_policies = {}
        self.load_escalation_policies()

        # 通知渠道
        self.notification_channels = self._setup_notification_channels()

        # 统计信息
        self.stats = {
            'alerts_triggered': 0,
            'alerts_resolved': 0,
            'notifications_sent': 0,
            'escalations': 0,
            'suppressed': 0
        }

        # 启动监控线程
        self.monitoring_thread = None
        self._start_monitoring()

    def load_default_configs(self):
        """加载默认告警配置"""
        self.alert_configs = {
            'response_time': {
                'metric': 'ResponseTime',
                'threshold': 30000,  # 30秒
                'comparison': 'greater_than',
                'evaluation_periods': 2,
                'datapoints_to_alarm': 2,
                'severity': AlertSeverity.WARNING
            },
            'p99_response_time': {
                'metric': 'ResponseTime',
                'statistic': 'p99',
                'threshold': 60000,  # 60秒
                'comparison': 'greater_than',
                'evaluation_periods': 2,
                'datapoints_to_alarm': 2,
                'severity': AlertSeverity.CRITICAL
            },
            'error_rate': {
                'metric': 'ErrorRate',
                'threshold': 5,  # 5%
                'comparison': 'greater_than',
                'evaluation_periods': 2,
                'datapoints_to_alarm': 2,
                'severity': AlertSeverity.WARNING
            },
            'error_spike': {
                'metric': 'ErrorRate',
                'threshold': 15,  # 15%
                'comparison': 'greater_than',
                'evaluation_periods': 1,
                'datapoints_to_alarm': 1,
                'severity': AlertSeverity.CRITICAL
            },
            'lambda_concurrency': {
                'metric': 'ConcurrentExecutions',
                'namespace': 'AWS/Lambda',
                'threshold': 950,
                'comparison': 'greater_than',
                'evaluation_periods': 2,
                'datapoints_to_alarm': 2,
                'severity': AlertSeverity.CRITICAL
            },
            'cpu_utilization': {
                'metric': 'CPUUtilization',
                'threshold': 90,  # 90%
                'comparison': 'greater_than',
                'evaluation_periods': 3,
                'datapoints_to_alarm': 3,
                'severity': AlertSeverity.WARNING
            },
            'memory_utilization': {
                'metric': 'MemoryUtilization',
                'threshold': 85,  # 85%
                'comparison': 'greater_than',
                'evaluation_periods': 3,
                'datapoints_to_alarm': 3,
                'severity': AlertSeverity.WARNING
            }
        }

    def load_escalation_policies(self):
        """加载升级策略"""
        self.escalation_policies = {
            'default': {
                'levels': [
                    {
                        'level': 1,
                        'timeout_minutes': 5,
                        'notify': ['on-call-engineer'],
                        'channels': ['email', 'slack']
                    },
                    {
                        'level': 2,
                        'timeout_minutes': 15,
                        'notify': ['team-lead', 'on-call-engineer'],
                        'channels': ['email', 'slack', 'sms']
                    },
                    {
                        'level': 3,
                        'timeout_minutes': 30,
                        'notify': ['manager', 'team-lead'],
                        'channels': ['email', 'slack', 'sms', 'phone']
                    }
                ]
            },
            'critical': {
                'levels': [
                    {
                        'level': 1,
                        'timeout_minutes': 2,
                        'notify': ['on-call-engineer', 'team-lead'],
                        'channels': ['email', 'slack', 'sms']
                    },
                    {
                        'level': 2,
                        'timeout_minutes': 5,
                        'notify': ['manager', 'team-lead', 'on-call-engineer'],
                        'channels': ['email', 'slack', 'sms', 'phone']
                    }
                ]
            }
        }

    def evaluate_alert(self, config: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估告警条件

        Args:
            config: 告警配置
            metrics: 当前指标

        Returns:
            评估结果
        """
        try:
            metric_value = metrics.get(config['metric'])
            if metric_value is None:
                return {
                    'alert_triggered': False,
                    'reason': 'metric_not_found'
                }

            # 比较操作
            threshold = config['threshold']
            comparison = config['comparison']

            triggered = False
            if comparison == 'greater_than':
                triggered = metric_value > threshold
            elif comparison == 'less_than':
                triggered = metric_value < threshold
            elif comparison == 'greater_than_or_equal':
                triggered = metric_value >= threshold
            elif comparison == 'less_than_or_equal':
                triggered = metric_value <= threshold

            if triggered:
                # 创建告警
                alert_id = f"alert-{uuid.uuid4()}"
                severity = config.get('severity', AlertSeverity.WARNING)
                message = self._format_alert_message(config, metric_value, threshold)

                # 记录告警
                alert = {
                    'alert_id': alert_id,
                    'metric': config['metric'],
                    'value': metric_value,
                    'threshold': threshold,
                    'severity': severity.name.lower(),
                    'message': message,
                    'timestamp': datetime.utcnow(),
                    'acknowledged': False
                }

                self.active_alerts[alert_id] = alert
                self.alert_history.append(alert)
                self.stats['alerts_triggered'] += 1

                # 发送通知
                notification_result = self._send_alert_notification(alert)

                return {
                    'alert_triggered': True,
                    'alert_id': alert_id,
                    'severity': severity.name.lower(),
                    'message': message,
                    'notification_sent': notification_result['success']
                }

            return {
                'alert_triggered': False,
                'metric_value': metric_value,
                'threshold': threshold
            }

        except Exception as e:
            return {
                'alert_triggered': False,
                'error': str(e)
            }

    def detect_error_rate_spike(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        检测错误率突增

        Args:
            data: 错误率数据

        Returns:
            检测结果
        """
        try:
            current_rate = data['current_error_rate']
            baseline_rate = data.get('baseline_error_rate', self.error_baseline['default']['baseline'])
            spike_threshold = data.get('spike_threshold', 5.0)

            # 更新基线
            self._update_error_baseline(current_rate)

            # 计算突增倍数
            if baseline_rate > 0:
                spike_magnitude = current_rate / baseline_rate
            else:
                spike_magnitude = float('inf') if current_rate > 0 else 0

            # 检测突增
            spike_detected = spike_magnitude > spike_threshold

            if spike_detected:
                # 创建严重告警
                alert = {
                    'alert_id': f"spike-{uuid.uuid4()}",
                    'type': 'error_rate_spike',
                    'current_rate': current_rate,
                    'baseline_rate': baseline_rate,
                    'spike_magnitude': spike_magnitude,
                    'severity': AlertSeverity.CRITICAL,
                    'message': f"Error rate spike detected: {current_rate*100:.1f}% ({spike_magnitude:.1f}x baseline)",
                    'timestamp': datetime.utcnow()
                }

                self.active_alerts[alert['alert_id']] = alert

                # 立即通知和升级
                notification_result = self._send_critical_notification(alert)
                escalation_result = self._trigger_immediate_escalation(alert)

                return {
                    'spike_detected': True,
                    'spike_magnitude': spike_magnitude,
                    'severity': 'critical',
                    'alert_message': alert['message'],
                    'immediate_notification': notification_result['success'],
                    'escalation_triggered': escalation_result['triggered']
                }

            return {
                'spike_detected': False,
                'spike_magnitude': spike_magnitude,
                'current_rate': current_rate,
                'baseline_rate': baseline_rate
            }

        except Exception as e:
            return {
                'spike_detected': False,
                'error': str(e)
            }

    def check_resource_thresholds(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        检查资源阈值

        Args:
            metrics: 资源指标

        Returns:
            检查结果
        """
        try:
            alerts_triggered = []
            resource_pressure = 'normal'

            # CPU检查
            cpu_util = metrics.get('cpu_utilization', 0)
            if cpu_util > 0.9:
                alerts_triggered.append({
                    'resource': 'cpu',
                    'severity': 'warning' if cpu_util < 0.95 else 'critical',
                    'utilization': cpu_util
                })

            # 内存检查
            mem_util = metrics.get('memory_utilization', 0)
            if mem_util > 0.85:
                alerts_triggered.append({
                    'resource': 'memory',
                    'severity': 'warning' if mem_util < 0.9 else 'critical',
                    'utilization': mem_util
                })

            # Lambda并发检查
            lambda_concurrent = metrics.get('lambda_concurrent_executions', 0)
            if lambda_concurrent > 900:
                alerts_triggered.append({
                    'resource': 'lambda_concurrency',
                    'severity': 'critical',
                    'value': lambda_concurrent
                })

            # DynamoDB节流检查
            dynamodb_throttles = metrics.get('dynamodb_throttles', 0)
            if dynamodb_throttles > 0:
                alerts_triggered.append({
                    'resource': 'dynamodb',
                    'severity': 'warning',
                    'throttles': dynamodb_throttles
                })

            # 确定资源压力级别
            if any(alert['severity'] == 'critical' for alert in alerts_triggered):
                resource_pressure = 'critical'
            elif alerts_triggered:
                resource_pressure = 'high'

            # 是否建议扩容
            scaling_recommended = resource_pressure in ['high', 'critical']

            # 发送告警
            for alert in alerts_triggered:
                self._create_resource_alert(alert)

            return {
                'alerts_triggered': alerts_triggered,
                'resource_pressure': resource_pressure,
                'scaling_recommended': scaling_recommended
            }

        except Exception as e:
            return {
                'alerts_triggered': [],
                'error': str(e)
            }

    def send_notifications(self, alert: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送多渠道通知

        Args:
            alert: 告警信息
            config: 通知配置

        Returns:
            发送结果
        """
        try:
            channels = config.get('channels', {})
            severity = alert.get('severity', 'warning')
            successful_channels = []
            failed_channels = []
            start_time = time.time()

            # 根据严重程度选择渠道
            for channel_name, channel_config in channels.items():
                if not channel_config.get('enabled', False):
                    continue

                if severity not in channel_config.get('severity', []):
                    continue

                # 发送到该渠道
                result = self._send_to_channel(channel_name, alert)
                if result['success']:
                    successful_channels.append(channel_name)
                else:
                    failed_channels.append(channel_name)

            delivery_time = (time.time() - start_time) * 1000

            return {
                'notifications_sent': len(successful_channels),
                'successful_channels': successful_channels,
                'failed_channels': failed_channels,
                'delivery_time_ms': delivery_time
            }

        except Exception as e:
            return {
                'notifications_sent': 0,
                'error': str(e)
            }

    def process_escalation(self, alert: Dict[str, Any], policy: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理告警升级

        Args:
            alert: 未确认的告警
            policy: 升级策略

        Returns:
            升级结果
        """
        try:
            alert_age = datetime.utcnow() - alert.get('created_at', datetime.utcnow())
            alert_age_minutes = alert_age.total_seconds() / 60
            current_level = alert.get('current_level', 1)

            # 找到应该升级到的级别
            target_level = current_level
            escalation_reason = ""

            for level_config in policy['levels']:
                if alert_age_minutes > level_config['timeout_minutes'] and level_config['level'] > current_level:
                    target_level = level_config['level']
                    escalation_reason = f"Alert unacknowledged for {alert_age_minutes:.0f} minutes"
                    break

            if target_level > current_level:
                # 执行升级
                level_config = next(l for l in policy['levels'] if l['level'] == target_level)

                # 更新告警级别
                alert['current_level'] = target_level
                alert['escalated_at'] = datetime.utcnow()

                # 发送升级通知
                notifications_sent = 0
                for recipient in level_config['notify']:
                    result = self._notify_recipient(recipient, alert, escalation=True)
                    if result['success']:
                        notifications_sent += 1

                self.stats['escalations'] += 1

                return {
                    'escalation_triggered': True,
                    'escalated_to_level': target_level,
                    'notifications_sent': notifications_sent,
                    'escalation_reason': escalation_reason
                }

            return {
                'escalation_triggered': False,
                'current_level': current_level,
                'reason': 'no_escalation_needed'
            }

        except Exception as e:
            return {
                'escalation_triggered': False,
                'error': str(e)
            }

    def group_similar_alerts(self, alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分组相似告警

        Args:
            alerts: 告警列表

        Returns:
            分组结果
        """
        try:
            groups = defaultdict(list)
            suppressed_count = 0

            # 按类型和服务分组
            for alert in alerts:
                group_key = f"{alert.get('type', 'unknown')}_{alert.get('service', 'unknown')}"
                groups[group_key].append(alert)

            # 创建分组告警
            grouped_alerts = []
            for group_key, group_alerts in groups.items():
                if len(group_alerts) > 1:
                    # 合并为一个告警
                    alert_type, service = group_key.split('_')
                    grouped_alert = {
                        'type': alert_type,
                        'count': len(group_alerts),
                        'services': list(set(a.get('service', 'unknown') for a in group_alerts)),
                        'first_occurrence': min(a.get('timestamp', datetime.utcnow()) for a in group_alerts),
                        'last_occurrence': max(a.get('timestamp', datetime.utcnow()) for a in group_alerts)
                    }
                    grouped_alerts.append(grouped_alert)
                    suppressed_count += len(group_alerts) - 1
                else:
                    grouped_alerts.append(group_alerts[0])

            # 更新统计
            self.stats['suppressed'] += suppressed_count

            return {
                'original_alerts': len(alerts),
                'grouped_alerts': len(grouped_alerts),
                'suppressed_alerts': suppressed_count,
                'groups': [
                    {
                        'type': g.get('type'),
                        'count': g.get('count', 1),
                        'services': g.get('services', [])
                    }
                    for g in grouped_alerts
                ]
            }

        except Exception as e:
            return {
                'original_alerts': len(alerts),
                'grouped_alerts': len(alerts),
                'error': str(e)
            }

    def _setup_notification_channels(self) -> Dict[str, Any]:
        """设置通知渠道"""
        channels = {}

        # Email通道
        if ALERT_EMAIL:
            channels['email'] = {
                'type': 'email',
                'endpoint': ALERT_EMAIL,
                'enabled': True
            }

        # SNS通道
        if SNS_TOPIC_ARN:
            channels['sns'] = {
                'type': 'sns',
                'endpoint': SNS_TOPIC_ARN,
                'enabled': True
            }

        # Slack通道
        if SLACK_WEBHOOK:
            channels['slack'] = {
                'type': 'slack',
                'endpoint': SLACK_WEBHOOK,
                'enabled': True
            }

        return channels

    def _send_to_channel(self, channel_name: str, alert: Dict[str, Any]) -> Dict[str, Any]:
        """发送到特定渠道"""
        try:
            channel = self.notification_channels.get(channel_name)
            if not channel:
                return {'success': False, 'reason': 'channel_not_found'}

            if channel['type'] == 'email':
                return self._send_email_notification(alert, channel['endpoint'])
            elif channel['type'] == 'sns':
                return self._send_sns_notification(alert, channel['endpoint'])
            elif channel['type'] == 'slack':
                return self._send_slack_notification(alert, channel['endpoint'])
            else:
                return {'success': False, 'reason': 'unsupported_channel'}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _send_email_notification(self, alert: Dict[str, Any], recipient: str) -> Dict[str, Any]:
        """发送邮件通知"""
        try:
            subject = f"[{alert.get('severity', 'WARNING').upper()}] {self.service_name} Alert"
            body = self._format_email_body(alert)

            ses.send_email(
                Source=ALERT_EMAIL,
                Destination={'ToAddresses': [recipient]},
                Message={
                    'Subject': {'Data': subject},
                    'Body': {'Text': {'Data': body}}
                }
            )

            self.stats['notifications_sent'] += 1
            return {'success': True}

        except ClientError as e:
            return {'success': False, 'error': str(e)}

    def _send_sns_notification(self, alert: Dict[str, Any], topic_arn: str) -> Dict[str, Any]:
        """发送SNS通知"""
        try:
            message = json.dumps(alert, default=str)

            sns.publish(
                TopicArn=topic_arn,
                Subject=f"{self.service_name} Alert",
                Message=message,
                MessageAttributes={
                    'severity': {'DataType': 'String', 'StringValue': alert.get('severity', 'warning')},
                    'service': {'DataType': 'String', 'StringValue': self.service_name}
                }
            )

            self.stats['notifications_sent'] += 1
            return {'success': True}

        except ClientError as e:
            return {'success': False, 'error': str(e)}

    def _send_slack_notification(self, alert: Dict[str, Any], webhook_url: str) -> Dict[str, Any]:
        """发送Slack通知"""
        try:
            import requests

            severity_colors = {
                'info': '#36a64f',
                'warning': '#ff9900',
                'error': '#ff6600',
                'critical': '#ff0000'
            }

            color = severity_colors.get(alert.get('severity', 'warning'), '#808080')

            payload = {
                'attachments': [{
                    'color': color,
                    'title': f"{self.service_name} Alert",
                    'fields': [
                        {'title': 'Severity', 'value': alert.get('severity', 'warning').upper(), 'short': True},
                        {'title': 'Metric', 'value': alert.get('metric', 'unknown'), 'short': True},
                        {'title': 'Message', 'value': alert.get('message', 'No message'), 'short': False},
                        {'title': 'Time', 'value': str(alert.get('timestamp', datetime.utcnow())), 'short': True}
                    ]
                }]
            }

            response = requests.post(webhook_url, json=payload)
            if response.status_code == 200:
                self.stats['notifications_sent'] += 1
                return {'success': True}
            else:
                return {'success': False, 'status_code': response.status_code}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _format_alert_message(self, config: Dict[str, Any], value: float, threshold: float) -> str:
        """格式化告警消息"""
        metric = config.get('metric', 'unknown')
        comparison = config.get('comparison', 'exceeds')

        if comparison == 'greater_than':
            comparison_text = 'exceeded'
        elif comparison == 'less_than':
            comparison_text = 'fell below'
        else:
            comparison_text = 'crossed'

        return f"{metric} {comparison_text} threshold: {value} vs {threshold}"

    def _format_email_body(self, alert: Dict[str, Any]) -> str:
        """格式化邮件正文"""
        body = f"""
        Alert Details:
        ==============
        Service: {self.service_name}
        Environment: {self.environment}
        Severity: {alert.get('severity', 'warning').upper()}
        Time: {alert.get('timestamp', datetime.utcnow())}

        Message: {alert.get('message', 'No message')}

        Metric: {alert.get('metric', 'unknown')}
        Value: {alert.get('value', 'N/A')}
        Threshold: {alert.get('threshold', 'N/A')}

        Alert ID: {alert.get('alert_id', 'unknown')}

        Please investigate and take appropriate action.
        """
        return body

    def _send_alert_notification(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """发送告警通知"""
        results = []

        for channel_name, channel in self.notification_channels.items():
            if channel.get('enabled'):
                result = self._send_to_channel(channel_name, alert)
                results.append(result)

        return {
            'success': any(r.get('success') for r in results),
            'channels_notified': sum(1 for r in results if r.get('success'))
        }

    def _send_critical_notification(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """发送严重告警通知（所有渠道）"""
        results = []

        for channel_name, channel in self.notification_channels.items():
            result = self._send_to_channel(channel_name, alert)
            results.append(result)

        return {
            'success': any(r.get('success') for r in results),
            'channels_notified': sum(1 for r in results if r.get('success'))
        }

    def _trigger_immediate_escalation(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """触发立即升级"""
        if not ENABLE_ESCALATION:
            return {'triggered': False, 'reason': 'escalation_disabled'}

        policy = self.escalation_policies.get('critical', self.escalation_policies['default'])

        # 直接升级到最高级别
        highest_level = max(l['level'] for l in policy['levels'])
        alert['current_level'] = highest_level

        return {
            'triggered': True,
            'escalated_to': highest_level
        }

    def _create_resource_alert(self, resource_alert: Dict[str, Any]):
        """创建资源告警"""
        alert_id = f"resource-{uuid.uuid4()}"
        alert = {
            'alert_id': alert_id,
            'type': 'resource_alert',
            'resource': resource_alert['resource'],
            'severity': resource_alert['severity'],
            'timestamp': datetime.utcnow(),
            **resource_alert
        }

        self.active_alerts[alert_id] = alert
        self._send_alert_notification(alert)

    def _update_error_baseline(self, current_rate: float):
        """更新错误率基线"""
        baseline = self.error_baseline['default']
        baseline['values'].append(current_rate)

        # 每小时更新一次基线
        if datetime.utcnow() - baseline['last_update'] > timedelta(hours=1):
            if baseline['values']:
                # 使用中位数作为基线
                baseline['baseline'] = statistics.median(baseline['values'])
                baseline['last_update'] = datetime.utcnow()

    def _notify_recipient(self, recipient: str, alert: Dict[str, Any], escalation: bool = False) -> Dict[str, Any]:
        """通知特定接收者"""
        # 这里简化处理，实际应该有接收者配置
        return self._send_email_notification(alert, ALERT_EMAIL) if ALERT_EMAIL else {'success': False}

    def _start_monitoring(self):
        """启动监控线程"""
        def monitor_worker():
            while True:
                try:
                    # 检查活跃告警是否需要升级
                    if ENABLE_ESCALATION:
                        for alert_id, alert in self.active_alerts.items():
                            if not alert.get('acknowledged'):
                                policy = self.escalation_policies.get('default')
                                self.process_escalation(alert, policy)

                    # 清理旧告警
                    cutoff_time = datetime.utcnow() - timedelta(hours=24)
                    self.active_alerts = {
                        aid: alert for aid, alert in self.active_alerts.items()
                        if alert.get('timestamp', datetime.utcnow()) > cutoff_time
                    }

                    time.sleep(60)  # 每分钟检查一次

                except Exception as e:
                    print(f"Monitoring error: {e}")
                    time.sleep(60)

        self.monitoring_thread = threading.Thread(target=monitor_worker, daemon=True)
        self.monitoring_thread.start()

    def get_stats(self) -> Dict[str, Any]:
        """获取告警统计"""
        return {
            **self.stats,
            'active_alerts': len(self.active_alerts),
            'alert_history_size': len(self.alert_history)
        }


# 全局告警管理器实例
global_alert_manager = AlertManager()


# 便捷函数
def trigger_alert(metric: str, value: float, threshold: float, severity: str = 'warning'):
    """触发告警"""
    config = {
        'metric': metric,
        'threshold': threshold,
        'comparison': 'greater_than',
        'severity': AlertSeverity[severity.upper()]
    }
    metrics = {metric: value}
    return global_alert_manager.evaluate_alert(config, metrics)


def check_resources():
    """检查资源状态"""
    # 获取当前资源指标（这里简化处理）
    metrics = {
        'cpu_utilization': 0.75,
        'memory_utilization': 0.82,
        'lambda_concurrent_executions': 850
    }
    return global_alert_manager.check_resource_thresholds(metrics)


# 导出
__all__ = [
    'AlertManager',
    'AlertSeverity',
    'AlertState',
    'trigger_alert',
    'check_resources',
    'global_alert_manager'
]