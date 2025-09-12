#!/usr/bin/env python3
"""
migrate_dynamodb_data.py - DynamoDB数据迁移脚本
统一数据到sessions表，确保数据一致性
"""

import boto3
import json
import sys
from datetime import datetime
from typing import Dict, List, Any
from decimal import Decimal

# 配置
REGION = 'us-east-1'
PROJECT = 'ai-ppt-assistant'
ENVIRONMENT = 'dev'

# 表名配置
TABLES = {
    'tasks': f'{PROJECT}-{ENVIRONMENT}-tasks',
    'sessions': f'{PROJECT}-{ENVIRONMENT}-sessions',
    'checkpoints': f'{PROJECT}-{ENVIRONMENT}-checkpoints'
}

# 目标表（统一到sessions表）
TARGET_TABLE = TABLES['sessions']

class DecimalEncoder(json.JSONEncoder):
    """处理DynamoDB的Decimal类型"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

class DynamoDBMigrator:
    def __init__(self):
        """初始化DynamoDB客户端"""
        self.dynamodb = boto3.resource('dynamodb', region_name=REGION)
        self.lambda_client = boto3.client('lambda', region_name=REGION)
        self.ssm = boto3.client('ssm', region_name=REGION)
        self.backup_data = {}
        self.migration_stats = {
            'total_scanned': 0,
            'migrated': 0,
            'skipped': 0,
            'failed': 0,
            'errors': []
        }
    
    def log(self, message: str, level: str = "INFO"):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prefix = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "DATA": "📊"
        }.get(level, "")
        
        print(f"{prefix} [{timestamp}] {message}")
    
    def check_table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        try:
            table = self.dynamodb.Table(table_name)
            table.load()
            return True
        except:
            return False
    
    def scan_table(self, table_name: str) -> List[Dict]:
        """扫描整个表"""
        items = []
        
        if not self.check_table_exists(table_name):
            self.log(f"表 {table_name} 不存在", "WARNING")
            return items
        
        table = self.dynamodb.Table(table_name)
        
        try:
            # 执行扫描
            response = table.scan()
            items.extend(response.get('Items', []))
            
            # 处理分页
            while 'LastEvaluatedKey' in response:
                response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
                items.extend(response.get('Items', []))
            
            self.log(f"从表 {table_name} 扫描了 {len(items)} 条记录", "DATA")
            self.migration_stats['total_scanned'] += len(items)
            
        except Exception as e:
            self.log(f"扫描表 {table_name} 失败: {str(e)}", "ERROR")
            self.migration_stats['errors'].append(f"Scan {table_name}: {str(e)}")
        
        return items
    
    def backup_tables(self) -> str:
        """备份所有表数据"""
        self.log("开始备份表数据...", "INFO")
        
        for table_key, table_name in TABLES.items():
            self.log(f"备份表: {table_name}", "INFO")
            items = self.scan_table(table_name)
            self.backup_data[table_key] = items
        
        # 保存备份到文件
        backup_file = f'dynamodb_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        with open(backup_file, 'w') as f:
            json.dump({
                'backup_time': datetime.now().isoformat(),
                'region': REGION,
                'tables': self.backup_data,
                'table_names': TABLES
            }, f, indent=2, cls=DecimalEncoder)
        
        self.log(f"备份已保存到: {backup_file}", "SUCCESS")
        return backup_file
    
    def migrate_data(self) -> bool:
        """执行数据迁移"""
        self.log("=" * 60, "INFO")
        self.log("开始数据迁移", "INFO")
        self.log("=" * 60, "INFO")
        
        # 确保目标表存在
        if not self.check_table_exists(TARGET_TABLE):
            self.log(f"目标表 {TARGET_TABLE} 不存在！", "ERROR")
            return False
        
        target_table = self.dynamodb.Table(TARGET_TABLE)
        
        # 从tasks表迁移数据
        self.log(f"\n迁移数据: tasks -> sessions", "INFO")
        
        tasks_items = self.backup_data.get('tasks', [])
        
        for item in tasks_items:
            try:
                # 检查记录是否已存在（基于taskId）
                task_id = item.get('taskId')
                
                if not task_id:
                    self.log(f"跳过无taskId的记录", "WARNING")
                    self.migration_stats['skipped'] += 1
                    continue
                
                # 查询是否已存在
                response = target_table.get_item(Key={'taskId': task_id})
                
                if 'Item' in response:
                    self.log(f"记录已存在，跳过: {task_id}", "INFO")
                    self.migration_stats['skipped'] += 1
                else:
                    # 准备数据（可能需要转换格式）
                    migrated_item = self.transform_item(item)
                    
                    # 写入目标表
                    target_table.put_item(Item=migrated_item)
                    self.log(f"迁移成功: {task_id}", "SUCCESS")
                    self.migration_stats['migrated'] += 1
                    
            except Exception as e:
                self.log(f"迁移记录失败: {str(e)}", "ERROR")
                self.migration_stats['failed'] += 1
                self.migration_stats['errors'].append(str(e))
        
        return True
    
    def transform_item(self, item: Dict) -> Dict:
        """转换数据格式（如果需要）"""
        # 添加迁移元数据
        item['migration_timestamp'] = datetime.now().isoformat()
        item['migration_source'] = 'tasks_table'
        
        # 确保必要字段存在
        if 'created_at' not in item:
            item['created_at'] = datetime.now().isoformat()
        
        if 'status' not in item:
            item['status'] = 'migrated'
        
        return item
    
    def update_lambda_configurations(self) -> int:
        """更新Lambda函数配置"""
        self.log("\n更新Lambda函数配置...", "INFO")
        
        functions_to_update = [
            'ai-ppt-assistant-api-generate-presentation',
            'ai-ppt-assistant-api-presentation-status',
            'ai-ppt-assistant-api-list-presentations',
            'ai-ppt-assistant-api-get-task',
            'ai-ppt-assistant-task-processor'
        ]
        
        updated_count = 0
        
        for func_name in functions_to_update:
            try:
                # 获取当前配置
                response = self.lambda_client.get_function_configuration(
                    FunctionName=func_name
                )
                
                env_vars = response.get('Environment', {}).get('Variables', {})
                
                # 更新表名
                env_vars['DYNAMODB_TABLE'] = TARGET_TABLE
                env_vars['DYNAMODB_REGION'] = REGION
                
                # 更新Lambda配置
                self.lambda_client.update_function_configuration(
                    FunctionName=func_name,
                    Environment={'Variables': env_vars}
                )
                
                self.log(f"更新Lambda函数 {func_name} 成功", "SUCCESS")
                updated_count += 1
                
            except self.lambda_client.exceptions.ResourceNotFoundException:
                self.log(f"Lambda函数 {func_name} 不存在", "WARNING")
            except Exception as e:
                self.log(f"更新Lambda函数 {func_name} 失败: {str(e)}", "ERROR")
        
        return updated_count
    
    def update_ssm_parameters(self) -> bool:
        """更新SSM参数"""
        self.log("\n更新SSM参数...", "INFO")
        
        try:
            # 更新DynamoDB表名参数
            self.ssm.put_parameter(
                Name=f"/{PROJECT}/{ENVIRONMENT}/dynamodb-table",
                Value=TARGET_TABLE,
                Type="String",
                Overwrite=True,
                Description="Primary DynamoDB table for AI PPT Assistant"
            )
            
            # 更新表配置
            self.ssm.put_parameter(
                Name=f"/{PROJECT}/{ENVIRONMENT}/dynamodb-tables",
                Value=json.dumps({
                    'primary': TARGET_TABLE,
                    'deprecated': {
                        'tasks': TABLES['tasks'],
                        'reason': 'Migrated to sessions table'
                    }
                }),
                Type="String",
                Overwrite=True
            )
            
            self.log("SSM参数更新成功", "SUCCESS")
            return True
            
        except Exception as e:
            self.log(f"更新SSM参数失败: {str(e)}", "ERROR")
            return False
    
    def verify_migration(self) -> bool:
        """验证迁移结果"""
        self.log("\n验证迁移结果...", "INFO")
        
        # 验证目标表记录数
        target_table = self.dynamodb.Table(TARGET_TABLE)
        
        try:
            response = target_table.scan(Select='COUNT')
            total_items = response['Count']
            
            # 处理分页
            while 'LastEvaluatedKey' in response:
                response = target_table.scan(
                    Select='COUNT',
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                total_items += response['Count']
            
            self.log(f"目标表 {TARGET_TABLE} 共有 {total_items} 条记录", "DATA")
            
            # 验证关键记录
            if len(self.backup_data.get('tasks', [])) > 0:
                # 抽样验证
                sample_item = self.backup_data['tasks'][0]
                task_id = sample_item.get('taskId')
                
                if task_id:
                    response = target_table.get_item(Key={'taskId': task_id})
                    if 'Item' in response:
                        self.log(f"抽样验证成功: 找到记录 {task_id}", "SUCCESS")
                    else:
                        self.log(f"抽样验证失败: 未找到记录 {task_id}", "ERROR")
                        return False
            
            return True
            
        except Exception as e:
            self.log(f"验证失败: {str(e)}", "ERROR")
            return False
    
    def generate_report(self):
        """生成迁移报告"""
        report = {
            'migration_time': datetime.now().isoformat(),
            'region': REGION,
            'target_table': TARGET_TABLE,
            'statistics': self.migration_stats,
            'backup_data_summary': {
                table: len(items) for table, items in self.backup_data.items()
            }
        }
        
        # 保存报告
        report_file = f'migration_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.log(f"\n报告已保存到: {report_file}", "SUCCESS")
        
        # 打印摘要
        print("\n" + "=" * 60)
        print("📊 迁移摘要")
        print("=" * 60)
        print(f"扫描记录总数: {self.migration_stats['total_scanned']}")
        print(f"✅ 成功迁移: {self.migration_stats['migrated']}")
        print(f"⏭️  跳过（已存在）: {self.migration_stats['skipped']}")
        print(f"❌ 失败: {self.migration_stats['failed']}")
        
        if self.migration_stats['errors']:
            print(f"\n错误列表:")
            for error in self.migration_stats['errors'][:5]:  # 只显示前5个错误
                print(f"  - {error}")
        
        print("=" * 60)
    
    def run(self) -> bool:
        """执行完整的迁移流程"""
        try:
            # 步骤1: 备份
            backup_file = self.backup_tables()
            
            # 步骤2: 迁移数据
            if not self.migrate_data():
                self.log("数据迁移失败", "ERROR")
                return False
            
            # 步骤3: 更新Lambda配置
            lambda_updated = self.update_lambda_configurations()
            self.log(f"更新了 {lambda_updated} 个Lambda函数", "INFO")
            
            # 步骤4: 更新SSM参数
            self.update_ssm_parameters()
            
            # 步骤5: 验证
            if not self.verify_migration():
                self.log("迁移验证失败", "WARNING")
            
            # 步骤6: 生成报告
            self.generate_report()
            
            return True
            
        except Exception as e:
            self.log(f"迁移过程出现异常: {str(e)}", "ERROR")
            return False

def main():
    """主函数"""
    print("🚀 DynamoDB数据迁移工具")
    print("=" * 60)
    print(f"目标表: {TARGET_TABLE}")
    print(f"区域: {REGION}")
    print("=" * 60)
    
    # 确认执行
    print("\n⚠️  此操作将:")
    print("  1. 备份所有DynamoDB表")
    print("  2. 将tasks表数据迁移到sessions表")
    print("  3. 更新所有Lambda函数配置")
    print("  4. 更新SSM参数")
    print("")
    
    response = input("是否继续？(yes/no): ")
    
    if response.lower() != 'yes':
        print("操作已取消")
        return 1
    
    # 执行迁移
    migrator = DynamoDBMigrator()
    
    if migrator.run():
        print("\n🎉 数据迁移成功完成！")
        print("\n下一步:")
        print("1. 运行: python3 setup_config_center.py")
        print("2. 运行: python3 test_all_backend_apis.py")
        print("3. 验证应用功能正常")
        return 0
    else:
        print("\n❌ 数据迁移失败，请检查错误日志")
        return 1

if __name__ == "__main__":
    sys.exit(main())