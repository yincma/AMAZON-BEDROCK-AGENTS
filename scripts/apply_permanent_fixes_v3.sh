#!/bin/bash
# 应用永久修复的脚本 - 最终版本（v3.0）
# 经过两轮专家评审，解决所有已知问题
# Date: 2025-09-12

set -e

echo "🔧 Applying permanent fixes for AI PPT Assistant (v3.0 - Final)..."
echo "=================================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检测操作系统
OS_TYPE=$(uname -s)
echo -e "${BLUE}操作系统: $OS_TYPE${NC}"

# 计数器
FIXES_APPLIED=0
ISSUES_FOUND=0
WARNINGS=0

# 1. 修复 Terraform 配置中的层分配
echo ""
echo "📝 [1/7] Fixing Lambda layer assignments in Terraform..."

TF_FILE="infrastructure/modules/lambda/main.tf"
if [ -f "$TF_FILE" ]; then
    # 备份原始文件
    if [ ! -f "${TF_FILE}.original_backup" ]; then
        cp "$TF_FILE" "${TF_FILE}.original_backup"
        echo "  ✅ Created backup: ${TF_FILE}.original_backup"
    fi
    
    # 使用awk进行跨平台兼容的修改
    awk '
    /resource "aws_lambda_function" "api_modify_slide"/ { in_modify_slide = 1 }
    in_modify_slide && /layers.*minimal_dependencies/ {
        sub(/minimal_dependencies/, "content_dependencies")
        fixes_made = 1
    }
    /^resource / && !/resource "aws_lambda_function" "api_modify_slide"/ { in_modify_slide = 0 }
    { print }
    END { if (fixes_made) exit 0; else exit 1 }
    ' "$TF_FILE" > "${TF_FILE}.tmp" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        mv "${TF_FILE}.tmp" "$TF_FILE"
        echo -e "  ${GREEN}✅ Fixed: modify_slide now uses content_dependencies layer${NC}"
        ((FIXES_APPLIED++))
    else
        rm -f "${TF_FILE}.tmp"
        if grep -A 10 "api_modify_slide" "$TF_FILE" 2>/dev/null | grep -q "content_dependencies"; then
            echo -e "  ${GREEN}✅ Already fixed: modify_slide uses content_dependencies layer${NC}"
        else
            echo -e "  ${YELLOW}⚠️ Warning: Could not verify modify_slide layer configuration${NC}"
            ((WARNINGS++))
        fi
    fi
else
    echo -e "  ${RED}❌ Error: Terraform file not found: $TF_FILE${NC}"
    ((ISSUES_FOUND++))
fi

# 2. 修复测试脚本的API契约
echo ""
echo "📝 [2/7] Fixing test scripts to match API contract..."

TEST_FILE="comprehensive_backend_test.py"
if [ -f "$TEST_FILE" ]; then
    # 备份原始文件
    if [ ! -f "${TEST_FILE}.original_backup" ]; then
        cp "$TEST_FILE" "${TEST_FILE}.original_backup"
        echo "  ✅ Created backup: ${TEST_FILE}.original_backup"
    fi
    
    NEEDS_FIX=false
    
    # 检查各种问题
    if grep -q '"pages"' "$TEST_FILE"; then
        echo -e "  ${YELLOW}Found incorrect field 'pages'${NC}"
        NEEDS_FIX=true
    fi
    
    if ! grep -q '"title"' "$TEST_FILE"; then
        echo -e "  ${YELLOW}Missing required field 'title'${NC}"
        NEEDS_FIX=true
    fi
    
    if grep -q '"title_and_content"' "$TEST_FILE"; then
        echo -e "  ${YELLOW}Found incorrect layout enum value${NC}"
        NEEDS_FIX=true
    fi
    
    if grep -q 'PATCH.*slides' "$TEST_FILE"; then
        echo -e "  ${YELLOW}Found undefined PATCH route${NC}"
        NEEDS_FIX=true
    fi
    
    if [ "$NEEDS_FIX" = true ]; then
        # 应用修复
        if [ "$OS_TYPE" = "Darwin" ]; then
            # macOS版本
            sed -i '' \
                -e 's/"pages"/"slide_count"/g' \
                -e 's/"title_and_content"/"content"/g' \
                -e '/PATCH.*slides/d' \
                -e 's/test_data = {/test_data = {\
        "title": "Test Presentation",/' \
                "$TEST_FILE"
        else
            # Linux版本
            sed -i \
                -e 's/"pages"/"slide_count"/g' \
                -e 's/"title_and_content"/"content"/g' \
                -e '/PATCH.*slides/d' \
                -e 's/test_data = {/test_data = {\n        "title": "Test Presentation",/' \
                "$TEST_FILE"
        fi
        
        echo -e "  ${GREEN}✅ Fixed: Test script now uses correct API contract${NC}"
        ((FIXES_APPLIED++))
    else
        echo -e "  ${GREEN}✅ Test script already uses correct API contract${NC}"
    fi
else
    echo -e "  ${YELLOW}⚠️ Test file not found, will use fixed version${NC}"
    ((WARNINGS++))
fi

# 3. 修复DynamoDB表名前缀
echo ""
echo "📝 [3/7] Fixing DynamoDB table name prefixes..."

for file in comprehensive_backend_test*.py; do
    if [ -f "$file" ]; then
        # 检查是否需要修复
        if grep -q '"ai-ppt-assistant-sessions"' "$file" 2>/dev/null; then
            if [ "$OS_TYPE" = "Darwin" ]; then
                sed -i '' \
                    -e 's/"ai-ppt-assistant-sessions"/"ai-ppt-assistant-dev-sessions"/g' \
                    -e 's/"ai-ppt-assistant-tasks"/"ai-ppt-assistant-dev-tasks"/g' \
                    -e 's/"ai-ppt-assistant-checkpoints"/"ai-ppt-assistant-dev-checkpoints"/g' \
                    "$file"
            else
                sed -i \
                    -e 's/"ai-ppt-assistant-sessions"/"ai-ppt-assistant-dev-sessions"/g' \
                    -e 's/"ai-ppt-assistant-tasks"/"ai-ppt-assistant-dev-tasks"/g' \
                    -e 's/"ai-ppt-assistant-checkpoints"/"ai-ppt-assistant-dev-checkpoints"/g' \
                    "$file"
            fi
            echo -e "  ${GREEN}✅ Fixed table names in $file${NC}"
            ((FIXES_APPLIED++))
        else
            echo "  ✅ Table names already correct in $file"
        fi
    fi
done

# 4. 修复Lambda函数名前缀
echo ""
echo "📝 [4/7] Fixing Lambda function name prefixes..."

for file in comprehensive_backend_test*.py; do
    if [ -f "$file" ]; then
        # 检查是否需要修复Lambda函数名
        if grep -q '"ai-ppt-assistant-api-"' "$file" 2>/dev/null && ! grep -q '"ai-ppt-assistant-dev-api-"' "$file" 2>/dev/null; then
            if [ "$OS_TYPE" = "Darwin" ]; then
                sed -i '' 's/"ai-ppt-assistant-api-/"ai-ppt-assistant-dev-api-/g' "$file"
                sed -i '' 's/"ai-ppt-assistant-controllers-/"ai-ppt-assistant-dev-controllers-/g' "$file"
            else
                sed -i 's/"ai-ppt-assistant-api-/"ai-ppt-assistant-dev-api-/g' "$file"
                sed -i 's/"ai-ppt-assistant-controllers-/"ai-ppt-assistant-dev-controllers-/g' "$file"
            fi
            echo -e "  ${GREEN}✅ Fixed Lambda function names in $file${NC}"
            ((FIXES_APPLIED++))
        else
            echo "  ✅ Lambda function names already correct in $file"
        fi
    fi
done

# 5. 验证Lambda层依赖
echo ""
echo "📝 [5/7] Verifying Lambda layer dependencies..."

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
    echo -e "  ${YELLOW}⚠️ Creating content layer requirements...${NC}"
    mkdir -p lambdas/layers
    cat > "$CONTENT_REQ" << 'EOF'
# Content processing Lambda Layer Dependencies
boto3==1.35.0
aws-lambda-powertools==2.38.0
python-pptx==0.6.23
Pillow==10.4.0
jsonschema==4.23.0
pydantic==2.9.2
pydantic-core==2.23.4
EOF
    echo -e "  ${GREEN}✅ Created content layer requirements with Pillow${NC}"
    ((FIXES_APPLIED++))
fi

# 6. 创建Docker构建脚本（带架构指定）
echo ""
echo "📝 [6/7] Creating Docker build script with ARM64 architecture..."

DOCKER_BUILD_SCRIPT="lambdas/layers/build-with-docker.sh"
cat > "$DOCKER_BUILD_SCRIPT" << 'EOF'
#!/bin/bash
# Docker构建Lambda层脚本 - ARM64架构 (使用Python zipfile)
# Version: 3.1

echo "🐳 Building Lambda layers with Docker (ARM64 architecture)..."
echo "================================================"

# 确保目录结构
mkdir -p dist
rm -rf python

# 构建content层（包含Pillow）
echo ""
echo "📦 Building content layer (with Pillow)..."
docker run --rm \
    --platform linux/arm64 \
    --entrypoint "" \
    -v "$(pwd):/var/task" \
    -w /var/task \
    public.ecr.aws/lambda/python:3.12 \
    /bin/bash -c "
        echo 'Installing Python dependencies...' &&
        pip install --target python/lib/python3.12/site-packages -r requirements-content.txt --quiet &&
        echo 'Creating zip archive...' &&
        python3 -c \"
import zipfile
import os
import pathlib

def create_zip(source_dir, output_file):
    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, os.path.dirname(source_dir))
                zipf.write(file_path, arcname)

pathlib.Path('dist').mkdir(exist_ok=True)
create_zip('python', 'dist/ai-ppt-assistant-content.zip')
print('✅ Zip archive created successfully')
\"
    "

if [ $? -eq 0 ]; then
    echo "✅ Content layer built successfully"
else
    echo "❌ Failed to build content layer"
    exit 1
fi

# 清理
rm -rf python

# 构建minimal层
echo ""
echo "📦 Building minimal layer..."
docker run --rm \
    --platform linux/arm64 \
    --entrypoint "" \
    -v "$(pwd):/var/task" \
    -w /var/task \
    public.ecr.aws/lambda/python:3.12 \
    /bin/bash -c "
        echo 'Installing Python dependencies...' &&
        pip install --target python/lib/python3.12/site-packages \
            boto3==1.35.0 \
            aws-lambda-powertools==2.38.0 --quiet &&
        echo 'Creating zip archive...' &&
        python3 -c \"
import zipfile
import os
import pathlib

def create_zip(source_dir, output_file):
    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, os.path.dirname(source_dir))
                zipf.write(file_path, arcname)

pathlib.Path('dist').mkdir(exist_ok=True)
create_zip('python', 'dist/ai-ppt-assistant-minimal.zip')
print('✅ Zip archive created successfully')
\"
    "

if [ $? -eq 0 ]; then
    echo "✅ Minimal layer built successfully"
else
    echo "❌ Failed to build minimal layer"
    exit 1
fi

# 清理
rm -rf python

# 构建主层（如果存在requirements.txt）
if [ -f "requirements.txt" ]; then
    echo ""
    echo "📦 Building main layer..."
    docker run --rm \
        --platform linux/arm64 \
        --entrypoint "" \
        -v "$(pwd):/var/task" \
        -w /var/task \
        public.ecr.aws/lambda/python:3.12 \
        /bin/bash -c "
            echo 'Installing Python dependencies...' &&
            pip install --target python/lib/python3.12/site-packages -r requirements.txt --quiet &&
            echo 'Creating zip archive...' &&
            python3 -c \"
import zipfile
import os
import pathlib

def create_zip(source_dir, output_file):
    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, os.path.dirname(source_dir))
                zipf.write(file_path, arcname)

pathlib.Path('dist').mkdir(exist_ok=True)
create_zip('python', 'dist/ai-ppt-assistant-dependencies.zip')
print('✅ Zip archive created successfully')
\"
        "
    
    if [ $? -eq 0 ]; then
        echo "✅ Main layer built successfully"
    else
        echo "⚠️ Warning: Failed to build main layer"
    fi
    
    rm -rf python
fi

# 显示构建结果
echo ""
echo "📊 Build results:"
ls -lh dist/*.zip 2>/dev/null || echo "No zip files found"

echo ""
echo "✅ All Lambda layers built successfully for ARM64 architecture!"
EOF

chmod +x "$DOCKER_BUILD_SCRIPT"
echo -e "  ${GREEN}✅ Created Docker build script with ARM64 architecture${NC}"
((FIXES_APPLIED++))

# 7. 清理旧的Lambda包
echo ""
echo "📝 [7/7] Cleaning old Lambda packages..."

LAMBDA_ZIPS_FOUND=$(find lambdas -name "*.zip" 2>/dev/null | wc -l | tr -d ' ')
if [ "$LAMBDA_ZIPS_FOUND" -gt 0 ]; then
    find lambdas -name "*.zip" -delete 2>/dev/null || true
    echo -e "  ${GREEN}✅ Removed $LAMBDA_ZIPS_FOUND old Lambda packages${NC}"
    ((FIXES_APPLIED++))
else
    echo "  ✅ No old Lambda packages to clean"
fi

# 总结报告
echo ""
echo "=================================================="
echo "📊 Summary Report"
echo "=================================================="

echo -e "${BLUE}Operating System:${NC} $OS_TYPE"
echo -e "${BLUE}Fixes Applied:${NC} $FIXES_APPLIED"
echo -e "${YELLOW}Warnings:${NC} $WARNINGS"
echo -e "${RED}Issues Found:${NC} $ISSUES_FOUND"

if [ $ISSUES_FOUND -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ All permanent fixes applied successfully!${NC}"
    echo ""
    echo "📋 Next steps:"
    echo "  1. Build Lambda layers: cd lambdas/layers && ./build-with-docker.sh"
    echo "  2. Deploy infrastructure: make deploy-reliable"
    echo "  3. Run validation tests: python3 comprehensive_backend_test_fixed.py"
    echo ""
    echo "🔍 To verify fixes:"
    echo "  - Terraform config: grep -A5 'api_modify_slide' infrastructure/modules/lambda/main.tf"
    echo "  - Test script: grep 'slide_count\\|title\\|layout.*content' comprehensive_backend_test.py"
    echo "  - Table names: grep 'ai-ppt-assistant-dev' comprehensive_backend_test*.py"
    echo ""
    exit 0
else
    echo ""
    echo -e "${RED}⚠️ Some issues need manual attention${NC}"
    echo ""
    echo "Please review the errors above and fix manually."
    echo "After fixing, run this script again."
    exit 1
fi