#!/bin/bash

# ====================================================================
# 终极修复脚本 - 彻底解决所有部署问题
# ====================================================================

set -euo pipefail

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "======================================================================"
echo "🚀 终极部署修复流程"
echo "======================================================================"

# 1. 停止所有相关进程
log_info "停止所有相关进程..."
pkill -f "terraform" 2>/dev/null || true
pkill -f "make deploy" 2>/dev/null || true
pkill -f "python3 test" 2>/dev/null || true
sleep 2

# 2. 导入现有的DynamoDB表到Terraform状态
log_info "导入现有的DynamoDB表..."
cd infrastructure

# 导入DynamoDB表
tables=(
    "module.dynamodb.aws_dynamodb_table.sessions:ai-ppt-assistant-dev-sessions"
    "module.dynamodb.aws_dynamodb_table.tasks:ai-ppt-assistant-dev-tasks"
    "module.dynamodb.aws_dynamodb_table.checkpoints:ai-ppt-assistant-dev-checkpoints"
)

for table_spec in "${tables[@]}"; do
    IFS=':' read -r resource_addr table_name <<< "$table_spec"
    
    # 检查是否已在状态中
    if terraform state show "$resource_addr" &>/dev/null; then
        log_warning "表 $table_name 已在Terraform状态中"
    else
        # 检查表是否存在于AWS
        if aws dynamodb describe-table --table-name "$table_name" &>/dev/null; then
            log_info "导入表: $table_name"
            terraform import "$resource_addr" "$table_name" || {
                log_error "无法导入表 $table_name"
            }
        else
            log_warning "表 $table_name 在AWS中不存在"
        fi
    fi
done

# 3. 处理重复的VPC
log_info "处理重复的VPC..."
vpc_ids=$(aws ec2 describe-vpcs --filters "Name=tag:Name,Values=ai-ppt-assistant-dev-vpc" --region us-east-1 --query 'Vpcs[].VpcId' --output text)
vpc_count=$(echo "$vpc_ids" | wc -w)

if [ "$vpc_count" -gt 1 ]; then
    log_warning "发现 $vpc_count 个VPC，删除旧的VPC"
    
    # 获取Terraform状态中的VPC ID
    current_vpc=$(terraform state show module.vpc.aws_vpc.main 2>/dev/null | grep "^ *id" | cut -d'"' -f2 || echo "")
    
    for vpc_id in $vpc_ids; do
        if [ "$vpc_id" != "$current_vpc" ]; then
            log_info "删除旧VPC: $vpc_id"
            
            # 先删除依赖资源
            # 删除子网
            subnet_ids=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$vpc_id" --query 'Subnets[].SubnetId' --output text)
            for subnet_id in $subnet_ids; do
                aws ec2 delete-subnet --subnet-id "$subnet_id" 2>/dev/null || true
            done
            
            # 删除Internet Gateway
            igw_ids=$(aws ec2 describe-internet-gateways --filters "Name=attachment.vpc-id,Values=$vpc_id" --query 'InternetGateways[].InternetGatewayId' --output text)
            for igw_id in $igw_ids; do
                aws ec2 detach-internet-gateway --internet-gateway-id "$igw_id" --vpc-id "$vpc_id" 2>/dev/null || true
                aws ec2 delete-internet-gateway --internet-gateway-id "$igw_id" 2>/dev/null || true
            done
            
            # 删除路由表（非主路由表）
            rt_ids=$(aws ec2 describe-route-tables --filters "Name=vpc-id,Values=$vpc_id" --query 'RouteTables[?Associations[0].Main != `true`].RouteTableId' --output text)
            for rt_id in $rt_ids; do
                aws ec2 delete-route-table --route-table-id "$rt_id" 2>/dev/null || true
            done
            
            # 删除安全组（非默认）
            sg_ids=$(aws ec2 describe-security-groups --filters "Name=vpc-id,Values=$vpc_id" --query 'SecurityGroups[?GroupName != `default`].GroupId' --output text)
            for sg_id in $sg_ids; do
                aws ec2 delete-security-group --group-id "$sg_id" 2>/dev/null || true
            done
            
            # 删除VPC
            aws ec2 delete-vpc --vpc-id "$vpc_id" 2>/dev/null || {
                log_warning "无法删除VPC $vpc_id，可能有其他依赖"
            }
        fi
    done
fi

# 4. 刷新Terraform状态
log_info "刷新Terraform状态..."
terraform refresh

# 5. 应用Terraform配置（自动批准）
log_info "应用Terraform配置..."
terraform apply -auto-approve

# 6. 获取输出
API_URL=$(terraform output -raw api_gateway_url 2>/dev/null || echo "")
API_KEY=$(terraform output -raw api_gateway_api_key 2>/dev/null || echo "")

if [ -z "$API_URL" ] || [ -z "$API_KEY" ]; then
    log_error "无法获取API配置"
    exit 1
fi

cd ..

# 7. 更新所有配置文件
log_info "更新配置文件..."

# 更新api_config_info.json
cat > api_config_info.json <<EOF
{
  "project": "ai-ppt-assistant",
  "environment": "dev",
  "region": "us-east-1",
  "api_gateway_url": "${API_URL}",
  "api_key": "${API_KEY}",
  "updated_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "updated_by": "ultimate_fix.sh"
}
EOF

# 更新测试脚本
for file in test_backend_apis.py comprehensive_backend_test.py test_all_backend_apis.py system_health_check.py; do
    if [ -f "$file" ]; then
        log_info "更新 $file..."
        
        # 创建临时文件进行替换
        temp_file="${file}.tmp"
        
        # 更新API URL和Key
        sed "s|API_BASE_URL = .*|API_BASE_URL = \"${API_URL}\"|" "$file" > "$temp_file"
        sed -i.bak "s|API_KEY = .*|API_KEY = \"${API_KEY}\"|" "$temp_file"
        
        # 移动临时文件
        mv "$temp_file" "$file"
        rm -f "${file}.bak"
    fi
done

# 8. 验证部署
log_info "验证部署..."
response=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "x-api-key: ${API_KEY}" \
    "${API_URL}/health" 2>/dev/null || echo "000")

if [ "$response" = "200" ]; then
    log_success "✅ API健康检查通过"
else
    log_warning "⚠️ API健康检查返回: $response"
fi

# 9. 运行测试
log_info "运行API测试..."
python3 test_backend_apis.py

echo ""
echo "======================================================================"
log_success "✅ 终极修复完成！"
echo "======================================================================"
echo "API Gateway URL: ${API_URL}"
echo "API Key: ${API_KEY:0:20}..."
echo ""
echo "系统现在应该可以正常工作了。"
echo "======================================================================"