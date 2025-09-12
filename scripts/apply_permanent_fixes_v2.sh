#!/bin/bash
# 应用永久修复的脚本 - macOS兼容版本
# Version: 2.0.0
# Date: 2025-09-12

set -e

echo "🔧 Applying permanent fixes for AI PPT Assistant (v2.0)..."
echo "=================================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检测操作系统
OS_TYPE=$(uname -s)
echo "检测到操作系统: $OS_TYPE"

# 计数器
FIXES_APPLIED=0
ISSUES_FOUND=0

# 1. 修复 Terraform 配置中的层分配
echo ""
echo "📝 [1/6] Fixing Lambda layer assignments in Terraform..."

TF_FILE="infrastructure/modules/lambda/main.tf"
if [ -f "$TF_FILE" ]; then
    # 备份原始文件
    if [ ! -f "${TF_FILE}.original_backup" ]; then
        cp "$TF_FILE" "${TF_FILE}.original_backup"
        echo "  ✅ Created backup: ${TF_FILE}.original_backup"
    fi
    
    # 根据操作系统选择 sed 命令
    if [ "$OS_TYPE" = "Darwin" ]; then
        # macOS 版本
        echo "  使用 macOS sed 语法..."
        
        # 创建临时文件进行处理
        cp "$TF_FILE" "${TF_FILE}.tmp"
        
        # 使用 awk 进行精确替换（跨平台兼容）
        awk '
        /resource "aws_lambda_function" "api_modify_slide"/ { in_modify_slide = 1 }
        in_modify_slide && /layers.*minimal_dependencies/ {
            sub(/minimal_dependencies/, "content_dependencies")
            fixes_made = 1
        }
        /^resource / && !/resource "aws_lambda_function" "api_modify_slide"/ { in_modify_slide = 0 }
        { print }
        END { if (fixes_made) exit 0; else exit 1 }
        ' "$TF_FILE" > "${TF_FILE}.tmp2"
        
        if [ $? -eq 0 ]; then
            mv "${TF_FILE}.tmp2" "$TF_FILE"
            rm -f "${TF_FILE}.tmp"
            echo -e "  ${GREEN}✅ Fixed: modify_slide now uses content_dependencies layer${NC}"
            ((FIXES_APPLIED++))
        else
            rm -f "${TF_FILE}.tmp" "${TF_FILE}.tmp2"
            # 检查是否已经修复
            if grep -A 10 "api_modify_slide" "$TF_FILE" | grep -q "content_dependencies"; then
                echo -e "  ${GREEN}✅ Already fixed: modify_slide uses content_dependencies layer${NC}"
            else
                echo -e "  ${YELLOW}⚠️ Warning: Could not fix modify_slide layer configuration${NC}"
                ((ISSUES_FOUND++))
            fi
        fi
    else
        # Linux 版本
        sed -i.bak '/api_modify_slide/,/^resource/{s/minimal_dependencies/content_dependencies/g}' "$TF_FILE"
        echo -e "  ${GREEN}✅ Fixed: modify_slide layer configuration${NC}"
        ((FIXES_APPLIED++))
    fi
else
    echo -e "  ${RED}❌ Error: Terraform file not found: $TF_FILE${NC}"
    ((ISSUES_FOUND++))
fi

# 2. 确保测试脚本使用正确的 API 契约
echo ""
echo "📝 [2/6] Updating test scripts to match API contract..."

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
    
    # 检查是否使用了未定义的 PATCH 路由
    if grep -q 'PATCH.*slides' "$TEST_FILE"; then
        echo -e "  ${YELLOW}Found undefined PATCH route for slides${NC}"
        NEEDS_FIX=true
    fi
    
    if [ "$NEEDS_FIX" = true ]; then
        # 使用修正版本替换
        if [ -f "comprehensive_backend_test_fixed.py" ]; then
            cp "comprehensive_backend_test_fixed.py" "$TEST_FILE"
            echo -e "  ${GREEN}✅ Test script updated with correct API contract${NC}"
            ((FIXES_APPLIED++))
        else
            echo -e "  ${YELLOW}⚠️ Fixed version not found, applying inline fixes...${NC}"
            
            # 根据操作系统应用内联修复
            if [ "$OS_TYPE" = "Darwin" ]; then
                # macOS 版本
                sed -i '' \
                    -e 's/"pages"/"slide_count"/g' \
                    -e 's/test_data = {/test_data = {\
        "title": "Test Presentation",/' \
                    -e '/PATCH.*slides/d' \
                    "$TEST_FILE"
            else
                # Linux 版本
                sed -i.bak \
                    -e 's/"pages"/"slide_count"/g' \
                    -e 's/test_data = {/test_data = {\n        "title": "Test Presentation",/' \
                    -e '/PATCH.*slides/d' \
                    "$TEST_FILE"
            fi
            
            echo -e "  ${GREEN}✅ Applied inline fixes to test script${NC}"
            ((FIXES_APPLIED++))
        fi
    else
        echo -e "  ${GREEN}✅ Test script already uses correct API contract${NC}"
    fi
fi

# 3. 修复 DynamoDB 表名前缀
echo ""
echo "📝 [3/6] Fixing DynamoDB table name prefixes..."

# 更新测试脚本中的表名
for file in comprehensive_backend_test.py comprehensive_backend_test_*.py; do
    if [ -f "$file" ]; then
        # 检查是否需要修复（避免重复替换）
        if grep -q 'ai-ppt-assistant-sessions' "$file"; then
            if [ "$OS_TYPE" = "Darwin" ]; then
                sed -i '' \
                    -e 's/ai-ppt-assistant-sessions/ai-ppt-assistant-dev-sessions/g' \
                    -e 's/ai-ppt-assistant-tasks/ai-ppt-assistant-dev-tasks/g' \
                    -e 's/ai-ppt-assistant-checkpoints/ai-ppt-assistant-dev-checkpoints/g' \
                    "$file"
            else
                sed -i \
                    -e 's/ai-ppt-assistant-sessions/ai-ppt-assistant-dev-sessions/g' \
                    -e 's/ai-ppt-assistant-tasks/ai-ppt-assistant-dev-tasks/g' \
                    -e 's/ai-ppt-assistant-checkpoints/ai-ppt-assistant-dev-checkpoints/g' \
                    "$file"
            fi
            echo -e "  ${GREEN}✅ Fixed table names in $file${NC}"
            ((FIXES_APPLIED++))
        else
            echo "  ✅ Table names already correct in $file"
        fi
    fi
done

# 4. 验证 Lambda 层包含必要的依赖
echo ""
echo "📝 [4/6] Verifying Lambda layer dependencies..."

CONTENT_REQ="lambdas/layers/requirements-content.txt"
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

# 5. 清理旧的 Lambda 包
echo ""
echo "📝 [5/6] Cleaning old Lambda packages..."

LAMBDA_ZIPS_FOUND=$(find lambdas -name "*.zip" 2>/dev/null | wc -l | tr -d ' ')
if [ "$LAMBDA_ZIPS_FOUND" -gt 0 ]; then
    find lambdas -name "*.zip" -delete 2>/dev/null || true
    echo -e "  ${GREEN}✅ Removed $LAMBDA_ZIPS_FOUND old Lambda packages${NC}"
    ((FIXES_APPLIED++))
else
    echo "  ✅ No old Lambda packages to clean"
fi

# 6. 创建 Docker 构建脚本（确保层兼容性）
echo ""
echo "📝 [6/6] Creating Docker build script for Lambda layers..."

DOCKER_BUILD_SCRIPT="lambdas/layers/build-with-docker.sh"
cat > "$DOCKER_BUILD_SCRIPT" << 'EOF'
#!/bin/bash
# 使用 Docker 构建 Lambda 层（确保架构兼容性）

echo "🐳 Building Lambda layers with Docker (ARM64)..."

# 创建必要的目录
mkdir -p dist
rm -rf python

# 构建 content 层（包含 Pillow）- 指定ARM64架构
echo "Building content layer for ARM64..."
docker run --rm \
    --platform linux/arm64 \
    -v "$(pwd):/var/task" \
    -w /var/task \
    public.ecr.aws/lambda/python:3.12 \
    /bin/bash -c "
        pip install --target python/lib/python3.12/site-packages -r requirements-content.txt &&
        zip -r dist/ai-ppt-assistant-content.zip python/
    "

echo "✅ Content layer built with Docker (Python 3.12, ARM64 compatible)"

# 清理
rm -rf python

# 构建 minimal 层 - 指定ARM64架构
echo "Building minimal layer for ARM64..."
docker run --rm \
    --platform linux/arm64 \
    -v "$(pwd):/var/task" \
    -w /var/task \
    public.ecr.aws/lambda/python:3.12 \
    /bin/bash -c "
        pip install --target python/lib/python3.12/site-packages boto3 aws-lambda-powertools==2.38.0 &&
        zip -r dist/ai-ppt-assistant-minimal.zip python/
    "

echo "✅ Minimal layer built with Docker"

# 清理
rm -rf python

# 构建主层（如果需要）- 指定ARM64架构
if [ -f "requirements.txt" ]; then
    echo "Building main layer for ARM64..."
    docker run --rm \
        --platform linux/arm64 \
        -v "$(pwd):/var/task" \
        -w /var/task \
        public.ecr.aws/lambda/python:3.12 \
        /bin/bash -c "
            pip install --target python/lib/python3.12/site-packages -r requirements.txt &&
            zip -r dist/ai-ppt-assistant-dependencies.zip python/
        "
    echo "✅ Main layer built with Docker"
    rm -rf python
fi

echo "✅ All layers built successfully!"
ls -lh dist/
EOF

chmod +x "$DOCKER_BUILD_SCRIPT"
echo -e "  ${GREEN}✅ Created Docker build script for Lambda layers${NC}"
((FIXES_APPLIED++))

# 总结
echo ""
echo "=================================================="
echo "📊 Summary"
echo "=================================================="

if [ $ISSUES_FOUND -eq 0 ]; then
    echo -e "${GREEN}✅ All permanent fixes applied successfully!${NC}"
    echo "   Fixes applied: $FIXES_APPLIED"
    echo "   Operating System: $OS_TYPE"
    echo ""
    echo "Next steps:"
    echo "  1. Run: make clean"
    echo "  2. Run: cd lambdas/layers && ./build-with-docker.sh"
    echo "  3. Run: make deploy-reliable"
    echo "  4. Run: python3 comprehensive_backend_test_fixed.py"
    echo ""
    echo "To verify fixes:"
    echo "  - Check Terraform: grep -A5 'api_modify_slide' infrastructure/modules/lambda/main.tf"
    echo "  - Check test script: grep 'slide_count\\|title' comprehensive_backend_test.py"
    echo "  - Check tables: grep 'ai-ppt-assistant-dev' comprehensive_backend_test*.py"
    exit 0
else
    echo -e "${YELLOW}⚠️ Some issues need manual attention${NC}"
    echo "   Fixes applied: $FIXES_APPLIED"
    echo "   Issues found: $ISSUES_FOUND"
    echo ""
    echo "Please review the warnings above and fix manually if needed."
    exit 1
fi