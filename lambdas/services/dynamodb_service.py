"""
统一的DynamoDB服务模块
提供DynamoDB操作的标准化接口
"""

import boto3
import logging
from typing import Dict, Any, Optional, List
from botocore.exceptions import ClientError
from datetime import datetime, timedelta
from decimal import Decimal
import json

logger = logging.getLogger(__name__)


class DynamoDBServiceError(Exception):
    """DynamoDB服务错误"""
    def __init__(self, message: str, error_code: str = None, details: Any = None):
        self.message = message
        self.error_code = error_code
        self.details = details
        super().__init__(message)


class DynamoDBService:
    """DynamoDB服务封装类"""

    def __init__(self, table_name: str, dynamodb_resource=None):
        """
        初始化DynamoDB服务

        Args:
            table_name: DynamoDB表名
            dynamodb_resource: 可选的DynamoDB资源实例
        """
        self.table_name = table_name
        self.dynamodb = dynamodb_resource or boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(table_name)
        self.logger = logging.getLogger(self.__class__.__name__)

    def put_item(self, item: Dict, condition_expression: str = None) -> Dict:
        """
        添加或更新项目

        Args:
            item: 要添加的项目数据
            condition_expression: 条件表达式（可选）

        Returns:
            DynamoDB响应

        Raises:
            DynamoDBServiceError: 操作失败时抛出
        """
        try:
            # 转换Python类型为DynamoDB类型
            item = self._convert_to_dynamodb_types(item)

            # 添加时间戳
            if 'created_at' not in item:
                item['created_at'] = datetime.utcnow().isoformat()
            item['updated_at'] = datetime.utcnow().isoformat()

            kwargs = {'Item': item}
            if condition_expression:
                kwargs['ConditionExpression'] = condition_expression

            response = self.table.put_item(**kwargs)
            self.logger.info(f"Successfully put item to {self.table_name}")
            return response

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ConditionalCheckFailedException':
                self.logger.warning(f"Condition check failed for put_item")
                raise DynamoDBServiceError("Item already exists or condition not met", 'CONDITION_FAILED', item)
            else:
                error_message = e.response['Error']['Message']
                self.logger.error(f"Failed to put item: {error_code} - {error_message}")
                raise DynamoDBServiceError(f"Failed to put item: {error_message}", error_code, item)

    def get_item(self, key: Dict, consistent_read: bool = False) -> Optional[Dict]:
        """
        获取单个项目

        Args:
            key: 主键值字典
            consistent_read: 是否使用强一致性读取

        Returns:
            项目数据或None

        Raises:
            DynamoDBServiceError: 操作失败时抛出
        """
        try:
            response = self.table.get_item(
                Key=key,
                ConsistentRead=consistent_read
            )

            if 'Item' in response:
                item = self._convert_from_dynamodb_types(response['Item'])
                self.logger.info(f"Successfully retrieved item from {self.table_name}")
                return item
            else:
                self.logger.info(f"Item not found in {self.table_name}: {key}")
                return None

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            self.logger.error(f"Failed to get item: {error_code} - {error_message}")
            raise DynamoDBServiceError(f"Failed to get item: {error_message}", error_code, key)

    def update_item(self, key: Dict, updates: Dict, condition_expression: str = None) -> Dict:
        """
        更新项目

        Args:
            key: 主键值字典
            updates: 要更新的属性字典
            condition_expression: 条件表达式（可选）

        Returns:
            更新后的项目

        Raises:
            DynamoDBServiceError: 操作失败时抛出
        """
        try:
            # 构建更新表达式
            update_expression_parts = []
            expression_attribute_names = {}
            expression_attribute_values = {}

            for attr_name, attr_value in updates.items():
                # 处理保留字
                safe_name = f"#{attr_name}"
                expression_attribute_names[safe_name] = attr_name

                # 处理值
                value_name = f":{attr_name}"
                expression_attribute_values[value_name] = self._convert_value_to_dynamodb(attr_value)

                update_expression_parts.append(f"{safe_name} = {value_name}")

            # 添加更新时间戳
            expression_attribute_names['#updated_at'] = 'updated_at'
            expression_attribute_values[':updated_at'] = datetime.utcnow().isoformat()
            update_expression_parts.append("#updated_at = :updated_at")

            update_expression = "SET " + ", ".join(update_expression_parts)

            kwargs = {
                'Key': key,
                'UpdateExpression': update_expression,
                'ExpressionAttributeNames': expression_attribute_names,
                'ExpressionAttributeValues': expression_attribute_values,
                'ReturnValues': 'ALL_NEW'
            }

            if condition_expression:
                kwargs['ConditionExpression'] = condition_expression

            response = self.table.update_item(**kwargs)
            self.logger.info(f"Successfully updated item in {self.table_name}")
            return self._convert_from_dynamodb_types(response['Attributes'])

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ConditionalCheckFailedException':
                self.logger.warning(f"Condition check failed for update_item")
                raise DynamoDBServiceError("Update condition not met", 'CONDITION_FAILED', {'key': key, 'updates': updates})
            elif error_code == 'ResourceNotFoundException':
                self.logger.warning(f"Item not found for update: {key}")
                raise DynamoDBServiceError("Item not found", 'NOT_FOUND', key)
            else:
                error_message = e.response['Error']['Message']
                self.logger.error(f"Failed to update item: {error_code} - {error_message}")
                raise DynamoDBServiceError(f"Failed to update item: {error_message}", error_code, {'key': key, 'updates': updates})

    def delete_item(self, key: Dict, condition_expression: str = None) -> bool:
        """
        删除项目

        Args:
            key: 主键值字典
            condition_expression: 条件表达式（可选）

        Returns:
            True如果删除成功

        Raises:
            DynamoDBServiceError: 操作失败时抛出
        """
        try:
            kwargs = {
                'Key': key,
                'ReturnValues': 'ALL_OLD'
            }

            if condition_expression:
                kwargs['ConditionExpression'] = condition_expression

            response = self.table.delete_item(**kwargs)

            if 'Attributes' in response:
                self.logger.info(f"Successfully deleted item from {self.table_name}")
                return True
            else:
                self.logger.info(f"Item not found for deletion in {self.table_name}: {key}")
                return False

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ConditionalCheckFailedException':
                self.logger.warning(f"Condition check failed for delete_item")
                raise DynamoDBServiceError("Delete condition not met", 'CONDITION_FAILED', key)
            else:
                error_message = e.response['Error']['Message']
                self.logger.error(f"Failed to delete item: {error_code} - {error_message}")
                raise DynamoDBServiceError(f"Failed to delete item: {error_message}", error_code, key)

    def query(self, key_condition: str, expression_attribute_values: Dict,
              index_name: str = None, limit: int = None,
              scan_forward: bool = True, filter_expression: str = None) -> List[Dict]:
        """
        查询项目

        Args:
            key_condition: 键条件表达式
            expression_attribute_values: 表达式属性值
            index_name: 索引名称（可选）
            limit: 返回结果限制（可选）
            scan_forward: 是否正向扫描（默认True）
            filter_expression: 过滤表达式（可选）

        Returns:
            项目列表

        Raises:
            DynamoDBServiceError: 操作失败时抛出
        """
        try:
            kwargs = {
                'KeyConditionExpression': key_condition,
                'ExpressionAttributeValues': self._convert_to_dynamodb_types(expression_attribute_values),
                'ScanIndexForward': scan_forward
            }

            if index_name:
                kwargs['IndexName'] = index_name
            if limit:
                kwargs['Limit'] = limit
            if filter_expression:
                kwargs['FilterExpression'] = filter_expression

            items = []
            last_evaluated_key = None

            while True:
                if last_evaluated_key:
                    kwargs['ExclusiveStartKey'] = last_evaluated_key

                response = self.table.query(**kwargs)

                for item in response.get('Items', []):
                    items.append(self._convert_from_dynamodb_types(item))

                last_evaluated_key = response.get('LastEvaluatedKey')

                # 如果没有更多数据或已达到限制，停止
                if not last_evaluated_key or (limit and len(items) >= limit):
                    break

            self.logger.info(f"Successfully queried {len(items)} items from {self.table_name}")
            return items[:limit] if limit else items

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            self.logger.error(f"Failed to query items: {error_code} - {error_message}")
            raise DynamoDBServiceError(f"Failed to query items: {error_message}", error_code)

    def scan(self, filter_expression: str = None, expression_attribute_values: Dict = None,
             limit: int = None) -> List[Dict]:
        """
        扫描表

        Args:
            filter_expression: 过滤表达式（可选）
            expression_attribute_values: 表达式属性值（可选）
            limit: 返回结果限制（可选）

        Returns:
            项目列表

        Raises:
            DynamoDBServiceError: 操作失败时抛出
        """
        try:
            kwargs = {}

            if filter_expression:
                kwargs['FilterExpression'] = filter_expression
            if expression_attribute_values:
                kwargs['ExpressionAttributeValues'] = self._convert_to_dynamodb_types(expression_attribute_values)

            items = []
            last_evaluated_key = None

            while True:
                if last_evaluated_key:
                    kwargs['ExclusiveStartKey'] = last_evaluated_key

                response = self.table.scan(**kwargs)

                for item in response.get('Items', []):
                    items.append(self._convert_from_dynamodb_types(item))

                last_evaluated_key = response.get('LastEvaluatedKey')

                # 如果没有更多数据或已达到限制，停止
                if not last_evaluated_key or (limit and len(items) >= limit):
                    break

            self.logger.info(f"Successfully scanned {len(items)} items from {self.table_name}")
            return items[:limit] if limit else items

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            self.logger.error(f"Failed to scan table: {error_code} - {error_message}")
            raise DynamoDBServiceError(f"Failed to scan table: {error_message}", error_code)

    def batch_write(self, items_to_put: List[Dict] = None, keys_to_delete: List[Dict] = None) -> Dict:
        """
        批量写入操作

        Args:
            items_to_put: 要添加的项目列表
            keys_to_delete: 要删除的键列表

        Returns:
            未处理的项目

        Raises:
            DynamoDBServiceError: 操作失败时抛出
        """
        try:
            with self.table.batch_writer() as batch:
                if items_to_put:
                    for item in items_to_put:
                        item = self._convert_to_dynamodb_types(item)
                        if 'created_at' not in item:
                            item['created_at'] = datetime.utcnow().isoformat()
                        item['updated_at'] = datetime.utcnow().isoformat()
                        batch.put_item(Item=item)

                if keys_to_delete:
                    for key in keys_to_delete:
                        batch.delete_item(Key=key)

            self.logger.info(f"Successfully completed batch write to {self.table_name}")
            return {}

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            self.logger.error(f"Failed to batch write: {error_code} - {error_message}")
            raise DynamoDBServiceError(f"Failed to batch write: {error_message}", error_code)

    def batch_get(self, keys: List[Dict]) -> List[Dict]:
        """
        批量获取项目

        Args:
            keys: 主键列表

        Returns:
            项目列表

        Raises:
            DynamoDBServiceError: 操作失败时抛出
        """
        try:
            response = self.dynamodb.batch_get_item(
                RequestItems={
                    self.table_name: {
                        'Keys': keys
                    }
                }
            )

            items = []
            for item in response['Responses'].get(self.table_name, []):
                items.append(self._convert_from_dynamodb_types(item))

            # 处理未处理的键
            unprocessed_keys = response.get('UnprocessedKeys', {})
            if unprocessed_keys:
                self.logger.warning(f"Some keys were not processed: {len(unprocessed_keys)} items")

            self.logger.info(f"Successfully batch retrieved {len(items)} items from {self.table_name}")
            return items

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            self.logger.error(f"Failed to batch get items: {error_code} - {error_message}")
            raise DynamoDBServiceError(f"Failed to batch get items: {error_message}", error_code)

    def set_ttl(self, ttl_attribute_name: str = 'ttl') -> None:
        """
        设置TTL属性

        Args:
            ttl_attribute_name: TTL属性名称

        Raises:
            DynamoDBServiceError: 操作失败时抛出
        """
        try:
            client = boto3.client('dynamodb')
            client.update_time_to_live(
                TableName=self.table_name,
                TimeToLiveSpecification={
                    'Enabled': True,
                    'AttributeName': ttl_attribute_name
                }
            )
            self.logger.info(f"Successfully enabled TTL on {self.table_name} with attribute {ttl_attribute_name}")

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            self.logger.error(f"Failed to set TTL: {error_code} - {error_message}")
            raise DynamoDBServiceError(f"Failed to set TTL: {error_message}", error_code)

    def _convert_to_dynamodb_types(self, data: Any) -> Any:
        """转换Python类型为DynamoDB类型"""
        if isinstance(data, dict):
            return {k: self._convert_to_dynamodb_types(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._convert_to_dynamodb_types(item) for item in data]
        elif isinstance(data, float):
            return Decimal(str(data))
        elif isinstance(data, set):
            return data  # DynamoDB原生支持集合
        else:
            return data

    def _convert_from_dynamodb_types(self, data: Any) -> Any:
        """转换DynamoDB类型为Python类型"""
        if isinstance(data, dict):
            return {k: self._convert_from_dynamodb_types(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._convert_from_dynamodb_types(item) for item in data]
        elif isinstance(data, Decimal):
            if data % 1 == 0:
                return int(data)
            else:
                return float(data)
        else:
            return data

    def _convert_value_to_dynamodb(self, value: Any) -> Any:
        """转换单个值为DynamoDB类型"""
        if isinstance(value, float):
            return Decimal(str(value))
        elif isinstance(value, dict) or isinstance(value, list):
            return self._convert_to_dynamodb_types(value)
        else:
            return value