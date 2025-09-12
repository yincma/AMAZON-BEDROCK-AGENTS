#!/bin/bash
# 应用永久修复的脚本
# Version: 1.0.0
# Date: 2025-09-12

set -e

echo "🔧 Applying permanent fixes for AI PPT Assistant..."
echo "=================================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 计数器
FIXES_APPLIED=0
ISSUES_FOUND=0

# 1. 修复 Terraform 配置中的层分配
echo ""
echo "📝 [1/5] Fixing Lambda layer assignments in Terraform..."

TF_FILE="infrastructure/modules/lambda/main.tf"
if [ -f "$TF_FILE" ]; then
    # 备份原始文件
    if [ ! -f "${TF_FILE}.original_backup" ]; then
        cp "$TF_FILE" "${TF_FILE}.original_backup"
        echo "  ✅ Created backup: ${TF_FILE}.original_backup"
    fi
    
    # 查找 modify_slide 函数配置并修复层
    if grep -q "api_modify_slide" "$TF_FILE"; then
        # 使用 sed 修复 modify_slide 的层配置
        # 查找从 resource "aws_lambda_function" "api_modify_slide" 到下一个 resource 的部分
        # 并替换其中的 minimal_dependencies 为 content_dependencies
        
        # 创建临时文件
        cp "$TF_FILE" "${TF_FILE}.tmp"
        
        # 使用 awk 进行精确替换
        awk '
        /resource "aws_lambda_function" "api_modify_slide"/ { in_modify_slide = 1 }
        in_modify_slide && /layers.*minimal_dependencies/ {
            sub(/minimal_dependencies/, "content_dependencies")
            FIXES_MADE++
        }
        /^resource / && !/resource "aws_lambda_function" "api_modify_slide"/ { in_modify_slide = 0 }
        { print }
        END { if (FIXES_MADE > 0) exit 0; else exit 1 }
        ' "$TF_FILE" > "${TF_FILE}.tmp"
        
        if [ $? -eq 0 ]; then
            mv "${TF_FILE}.tmp" "$TF_FILE"
            echo -e "  ${GREEN}✅ Fixed: modify_slide now uses content_dependencies layer${NC}"
            ((FIXES_APPLIED++))
        else
            rm -f "${TF_FILE}.tmp"
            # 检查是否已经修复
            if grep -A 10 "api_modify_slide" "$TF_FILE" | grep -q "content_dependencies"; then
                echo -e "  ${GREEN}✅ Already fixed: modify_slide uses content_dependencies layer${NC}"
            else
                echo -e "  ${YELLOW}⚠️ Warning: Could not fix modify_slide layer configuration${NC}"
                ((ISSUES_FOUND++))
            fi
        fi
    else
        echo -e "  ${RED}❌ Error: api_modify_slide not found in Terraform configuration${NC}"
        ((ISSUES_FOUND++))
    fi
else
    echo -e "  ${RED}❌ Error: Terraform file not found: $TF_FILE${NC}"
    ((ISSUES_FOUND++))
fi

# 2. 确保测试脚本使用正确的 API 契约
echo ""
echo "📝 [2/5] Updating test scripts to match API contract..."

TEST_FILE="comprehensive_backend_test.py"
if [ -f "$TEST_FILE" ]; then
    # 备份原始文件
    if [ ! -f "${TEST_FILE}.original_backup" ]; then
        cp "$TEST_FILE" "${TEST_FILE}.original_backup"
        echo "  ✅ Created backup: ${TEST_FILE}.original_backup"
    fi
    
    # 检查是否需要修复
    NEEDS_FIX=false
    
    if grep -q '"pages"' "$TEST_FILE"; then
        echo -e "  ${YELLOW}Found incorrect field 'pages'${NC}"
        NEEDS_FIX=true
    fi
    
    if ! grep -q '"title"' "$TEST_FILE"; then
        echo -e "  ${YELLOW}Missing required field 'title'${NC}"
        NEEDS_FIX=true
    fi
    
    if grep -q 'PUT.*presentations/slides' "$TEST_FILE"; then
        echo -e "  ${YELLOW}Found incorrect HTTP method for slide modification${NC}"
        NEEDS_FIX=true
    fi
    
    if [ "$NEEDS_FIX" = true ]; then
        # 使用固定版本替换
        if [ -f "comprehensive_backend_test_fixed.py" ]; then
            cp "comprehensive_backend_test_fixed.py" "$TEST_FILE"
            echo -e "  ${GREEN}✅ Test script updated with correct API contract${NC}"
            ((FIXES_APPLIED++))
        else
            echo -e "  ${YELLOW}⚠️ Fixed version not found, applying inline fixes...${NC}"
            
            # 应用内联修复
            sed -i.bak \
                -e 's/"pages"/"slide_count"/g' \
                -e 's/test_data = {/test_data = {\n        "title": "Test Presentation",/' \
                -e 's|PUT", data=modify_data|POST", data=modify_data|g' \
                "$TEST_FILE"
            
            echo -e "  ${GREEN}✅ Applied inline fixes to test script${NC}"
            ((FIXES_APPLIED++))
        fi
    else
        echo -e "  ${GREEN}✅ Test script already uses correct API contract${NC}"
    fi
else
    echo -e "  ${YELLOW}⚠️ Test file not found: $TEST_FILE${NC}"
    echo "  Creating new test file from fixed version..."
    
    if [ -f "comprehensive_backend_test_fixed.py" ]; then
        cp "comprehensive_backend_test_fixed.py" "$TEST_FILE"
        echo -e "  ${GREEN}✅ Created new test file with correct API contract${NC}"
        ((FIXES_APPLIED++))
    else
        echo -e "  ${RED}❌ Error: Fixed test script not available${NC}"
        ((ISSUES_FOUND++))
    fi
fi

# 3. 验证 Lambda 层包含必要的依赖
echo ""
echo "📝 [3/5] Verifying Lambda layer dependencies..."

CONTENT_REQ="lambdas/layers/requirements-content.txt"
MAIN_REQ="lambdas/layers/requirements.txt"

# 检查 content 层
if [ -f "$CONTENT_REQ" ]; then
    if ! grep -q "Pillow" "$CONTENT_REQ"; then
        echo "Pillow==10.4.0" >> "$CONTENT_REQ"
        echo -e "  ${GREEN}✅ Added Pillow to content layer requirements${NC}"
        ((FIXES_APPLIED++))
    else
        echo -e "  ${GREEN}✅ Content layer already includes Pillow${NC}"
    fi
else
    echo -e "  ${YELLOW}⚠️ Content requirements file not found, creating...${NC}"
    mkdir -p lambdas/layers
    cat > "$CONTENT_REQ" << 'EOF'
# Content processing Lambda Layer Dependencies
# For functions that need document/presentation processing

# Essential AWS SDK
boto3==1.35.0

# AWS Lambda Powertools
aws-lambda-powertools==2.38.0

# PowerPoint generation
python-pptx==0.6.23

# Image processing - Essential for visual content
Pillow==10.4.0

# JSON schema validation
jsonschema==4.23.0

# Data validation
pydantic==2.9.2
pydantic-core==2.23.4
EOF
    echo -e "  ${GREEN}✅ Created content layer requirements with Pillow${NC}"
    ((FIXES_APPLIED++))
fi

# 检查主 requirements.txt 中的版本问题
if [ -f "$MAIN_REQ" ]; then
    if grep -q "aws-lambda-powertools==2.39" "$MAIN_REQ"; then
        sed -i.bak 's/aws-lambda-powertools==2.39.0/aws-lambda-powertools==2.38.0/g' "$MAIN_REQ"
        echo -e "  ${GREEN}✅ Fixed aws-lambda-powertools version (2.39 -> 2.38)${NC}"
        ((FIXES_APPLIED++))
    else
        echo -e "  ${GREEN}✅ aws-lambda-powertools version is correct${NC}"
    fi
fi

# 4. 清理旧的 Lambda 包以强制重新打包
echo ""
echo "📝 [4/5] Cleaning old Lambda packages..."

LAMBDA_ZIPS_FOUND=$(find lambdas -name "*.zip" 2>/dev/null | wc -l)
if [ "$LAMBDA_ZIPS_FOUND" -gt 0 ]; then
    find lambdas -name "*.zip" -delete 2>/dev/null || true
    echo -e "  ${GREEN}✅ Removed $LAMBDA_ZIPS_FOUND old Lambda packages${NC}"
    ((FIXES_APPLIED++))
else
    echo "  ✅ No old Lambda packages to clean"
fi

# 5. 验证 IAM 权限配置
echo ""
echo "📝 [5/5] Checking IAM permissions configuration..."

IAM_FILE="infrastructure/modules/lambda/iam.tf"
if [ -f "$IAM_FILE" ]; then
    if grep -q "dynamodb:PutItem" "$IAM_FILE" && grep -q "dynamodb:DeleteItem" "$IAM_FILE"; then
        echo -e "  ${GREEN}✅ IAM permissions include DynamoDB write access${NC}"
    else
        echo -e "  ${YELLOW}⚠️ IAM permissions may need DynamoDB write access${NC}"
        echo "  Consider adding PutItem and DeleteItem permissions"
        ((ISSUES_FOUND++))
    fi
else
    # 检查主 Terraform 文件中的权限
    if grep -q "dynamodb:PutItem" infrastructure/modules/lambda/main.tf 2>/dev/null; then
        echo -e "  ${GREEN}✅ DynamoDB permissions found in main configuration${NC}"
    else
        echo -e "  ${YELLOW}⚠️ Could not verify DynamoDB permissions${NC}"
        echo "  Ensure Lambda functions have DynamoDB write access"
        ((ISSUES_FOUND++))
    fi
fi

# 创建预部署验证脚本（如果不存在）
echo ""
echo "📝 Creating pre-deployment validation script..."

if [ ! -f "scripts/pre_deploy_validate.py" ]; then
    cat > "scripts/pre_deploy_validate.py" << 'EOF'
#!/usr/bin/env python3
"""预部署验证脚本"""
import os
import sys
import re

def validate():
    issues = []
    
    # 检查 Terraform 配置
    tf_file = "infrastructure/modules/lambda/main.tf"
    if os.path.exists(tf_file):
        with open(tf_file, 'r') as f:
            content = f.read()
        if 'api_modify_slide' in content and 'minimal_dependencies' in content:
            if 'api_modify_slide' in content[:content.find('minimal_dependencies')]:
                issues.append("modify_slide using wrong layer")
    
    # 检查测试脚本
    test_file = "comprehensive_backend_test.py"
    if os.path.exists(test_file):
        with open(test_file, 'r') as f:
            content = f.read()
        if '"pages"' in content:
            issues.append("Test script using wrong field name")
        if '"title"' not in content:
            issues.append("Test script missing title field")
    
    if issues:
        print("❌ Validation failed:")
        for issue in issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("✅ All validations passed!")

if __name__ == "__main__":
    validate()
EOF
    chmod +x scripts/pre_deploy_validate.py
    echo -e "  ${GREEN}✅ Created pre-deployment validation script${NC}"
    ((FIXES_APPLIED++))
fi

# 总结
echo ""
echo "=================================================="
echo "📊 Summary"
echo "=================================================="

if [ $ISSUES_FOUND -eq 0 ]; then
    echo -e "${GREEN}✅ All permanent fixes applied successfully!${NC}"
    echo "   Fixes applied: $FIXES_APPLIED"
    echo ""
    echo "Next steps:"
    echo "  1. Run: make clean"
    echo "  2. Run: make build-layers-optimized"
    echo "  3. Run: make deploy-reliable"
    echo "  4. Run: python3 comprehensive_backend_test_fixed.py"
    exit 0
else
    echo -e "${YELLOW}⚠️ Some issues need manual attention${NC}"
    echo "   Fixes applied: $FIXES_APPLIED"
    echo "   Issues found: $ISSUES_FOUND"
    echo ""
    echo "Please review the warnings above and fix manually if needed."
    echo "After fixing, run: make deploy-reliable"
    exit 1
fi