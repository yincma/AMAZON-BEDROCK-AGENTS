#!/bin/bash
# =============================================================================
# LAMBDA LAYER OPTIMIZATION BUILD SCRIPT
# =============================================================================
# This script builds optimized Lambda layers with minimal dependencies
# to improve cold start performance.

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAYERS_DIR="${PROJECT_ROOT}/lambdas/layers"
DIST_DIR="${LAYERS_DIR}/dist"
BUILD_DIR="${LAYERS_DIR}/build"

# Try to find the best available Python version
if command -v python3.12 &> /dev/null; then
    PYTHON_VERSION="3.12"
    PYTHON_CMD="python3.12"
elif command -v python3.11 &> /dev/null; then
    PYTHON_VERSION="3.11"
    PYTHON_CMD="python3.11"
    log_warning "Using Python 3.11 instead of 3.12. Consider upgrading for better compatibility."
elif command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    PYTHON_CMD="python3"
    log_warning "Using Python ${PYTHON_VERSION}. Lambda runtime is 3.12."
else
    log_error "No suitable Python version found."
    exit 1
fi

# Check dependencies
check_dependencies() {
    log_info "Checking dependencies..."
    
    if ! command -v ${PYTHON_CMD} &> /dev/null; then
        log_error "${PYTHON_CMD} is required but not installed."
        exit 1
    fi
    
    if ! command -v pip &> /dev/null; then
        log_error "pip is required but not installed."
        exit 1
    fi
    
    log_success "Dependencies check passed - using ${PYTHON_CMD} (${PYTHON_VERSION})"
}

# Clean build directories
clean_build_dirs() {
    log_info "Cleaning build directories..."
    rm -rf "${BUILD_DIR}"
    rm -rf "${DIST_DIR}"
    mkdir -p "${BUILD_DIR}"
    mkdir -p "${DIST_DIR}"
    log_success "Build directories cleaned"
}

# Build minimal layer for API functions
build_minimal_layer() {
    log_info "Building minimal layer for API functions..."
    
    local layer_name="ai-ppt-assistant-minimal"
    local build_path="${BUILD_DIR}/${layer_name}"
    local python_dir="${build_path}/python"
    
    mkdir -p "${python_dir}"
    
    # Install minimal dependencies
    pip install -r "${LAYERS_DIR}/requirements-minimal.txt" \
        --target "${python_dir}" \
        --python-version "${PYTHON_VERSION}" \
        --platform manylinux2014_aarch64 \
        --implementation cp \
        --only-binary=:all: \
        --upgrade
    
    # Remove unnecessary files to reduce size
    find "${python_dir}" -type f -name "*.pyc" -delete
    find "${python_dir}" -type d -name "__pycache__" -exec rm -rf {} +
    find "${python_dir}" -type f -name "*.pyo" -delete
    find "${python_dir}" -type f -name "*.dist-info" -exec rm -rf {} +
    find "${python_dir}" -name "tests" -type d -exec rm -rf {} +
    find "${python_dir}" -name "test" -type d -exec rm -rf {} +
    find "${python_dir}" -name "*.txt" -delete 2>/dev/null || true
    
    # Create zip file
    cd "${build_path}"
    zip -r "${DIST_DIR}/${layer_name}.zip" python/
    cd "${PROJECT_ROOT}"
    
    local size=$(stat -f%z "${DIST_DIR}/${layer_name}.zip" 2>/dev/null || stat -c%s "${DIST_DIR}/${layer_name}.zip")
    local size_mb=$((size / 1024 / 1024))
    
    log_success "Minimal layer built: ${size_mb}MB"
    
    if [ ${size_mb} -gt 10 ]; then
        log_warning "Minimal layer size (${size_mb}MB) exceeds target of 10MB"
    fi
}

# Build content processing layer
build_content_layer() {
    log_info "Building content processing layer..."
    
    local layer_name="ai-ppt-assistant-content"
    local build_path="${BUILD_DIR}/${layer_name}"
    local python_dir="${build_path}/python"
    
    mkdir -p "${python_dir}"
    
    # Install content processing dependencies
    pip install -r "${LAYERS_DIR}/requirements-content.txt" \
        --target "${python_dir}" \
        --python-version "${PYTHON_VERSION}" \
        --platform manylinux2014_aarch64 \
        --implementation cp \
        --only-binary=:all: \
        --upgrade
    
    # Remove unnecessary files to reduce size
    find "${python_dir}" -type f -name "*.pyc" -delete
    find "${python_dir}" -type d -name "__pycache__" -exec rm -rf {} +
    find "${python_dir}" -type f -name "*.pyo" -delete
    find "${python_dir}" -type f -name "*.dist-info" -exec rm -rf {} +
    find "${python_dir}" -name "tests" -type d -exec rm -rf {} +
    find "${python_dir}" -name "test" -type d -exec rm -rf {} +
    find "${python_dir}" -name "*.txt" -delete 2>/dev/null || true
    
    # Create zip file
    cd "${build_path}"
    zip -r "${DIST_DIR}/${layer_name}.zip" python/
    cd "${PROJECT_ROOT}"
    
    local size=$(stat -f%z "${DIST_DIR}/${layer_name}.zip" 2>/dev/null || stat -c%s "${DIST_DIR}/${layer_name}.zip")
    local size_mb=$((size / 1024 / 1024))
    
    log_success "Content layer built: ${size_mb}MB"
    
    if [ ${size_mb} -gt 25 ]; then
        log_warning "Content layer size (${size_mb}MB) exceeds target of 25MB"
    fi
}

# Build legacy layer for backward compatibility
build_legacy_layer() {
    log_info "Building legacy layer for backward compatibility..."
    
    local layer_name="ai-ppt-assistant-dependencies"
    local build_path="${BUILD_DIR}/${layer_name}"
    local python_dir="${build_path}/python"
    
    mkdir -p "${python_dir}"
    
    # Install all dependencies (legacy)
    pip install -r "${LAYERS_DIR}/requirements.txt" \
        --target "${python_dir}" \
        --python-version "${PYTHON_VERSION}" \
        --platform manylinux2014_aarch64 \
        --implementation cp \
        --only-binary=:all: \
        --upgrade
    
    # Basic cleanup
    find "${python_dir}" -type f -name "*.pyc" -delete
    find "${python_dir}" -type d -name "__pycache__" -exec rm -rf {} +
    
    # Create zip file
    cd "${build_path}"
    zip -r "${DIST_DIR}/${layer_name}.zip" python/
    cd "${PROJECT_ROOT}"
    
    local size=$(stat -f%z "${DIST_DIR}/${layer_name}.zip" 2>/dev/null || stat -c%s "${DIST_DIR}/${layer_name}.zip")
    local size_mb=$((size / 1024 / 1024))
    
    log_success "Legacy layer built: ${size_mb}MB"
}

# Generate layer analysis report
generate_analysis_report() {
    log_info "Generating layer analysis report..."
    
    local report_file="${PROJECT_ROOT}/docs/lambda-layer-analysis.md"
    
    cat > "${report_file}" << EOF
# Lambda Layer Analysis Report

Generated on: $(date)

## Layer Size Comparison

| Layer Name | Size (MB) | Target (MB) | Status | Purpose |
|------------|-----------|-------------|--------|---------|
EOF
    
    for zip_file in "${DIST_DIR}"/*.zip; do
        if [ -f "${zip_file}" ]; then
            local filename=$(basename "${zip_file}")
            local size=$(stat -f%z "${zip_file}" 2>/dev/null || stat -c%s "${zip_file}")
            local size_mb=$((size / 1024 / 1024))
            
            case "${filename}" in
                "*minimal*")
                    local target=10
                    local purpose="Fast cold start for API functions"
                    ;;
                "*content*")
                    local target=25
                    local purpose="Content processing functions"
                    ;;
                *)
                    local target="N/A"
                    local purpose="Legacy compatibility"
                    ;;
            esac
            
            local status="✅ Good"
            if [ "${target}" != "N/A" ] && [ ${size_mb} -gt ${target} ]; then
                status="⚠️ Exceeds target"
            fi
            
            echo "| ${filename} | ${size_mb} | ${target} | ${status} | ${purpose} |" >> "${report_file}"
        fi
    done
    
    cat >> "${report_file}" << EOF

## Optimization Recommendations

### For Minimal Layer (API Functions)
- Keep dependencies to absolute minimum
- Target: < 10MB for optimal cold start performance
- Remove all unnecessary packages

### For Content Layer (Processing Functions)
- Include only content processing dependencies
- Target: < 25MB for reasonable cold start performance
- Optimize large packages like PIL, python-pptx

### Performance Impact
- Reduced layer size directly improves cold start time
- Smaller layers download faster during Lambda initialization
- Combined with provisioned concurrency for optimal performance

## Next Steps
1. Deploy optimized layers
2. Monitor cold start metrics
3. Adjust provisioned concurrency based on usage patterns
4. Consider further optimization based on performance data
EOF
    
    log_success "Analysis report generated: ${report_file}"
}

# Main execution
main() {
    log_info "Starting Lambda layer optimization build..."
    
    check_dependencies
    clean_build_dirs
    build_minimal_layer
    build_content_layer
    build_legacy_layer
    generate_analysis_report
    
    log_success "Lambda layer optimization build completed!"
    
    # Display summary
    echo ""
    log_info "Build Summary:"
    for zip_file in "${DIST_DIR}"/*.zip; do
        if [ -f "${zip_file}" ]; then
            local filename=$(basename "${zip_file}")
            local size=$(stat -f%z "${zip_file}" 2>/dev/null || stat -c%s "${zip_file}")
            local size_mb=$((size / 1024 / 1024))
            echo "  - ${filename}: ${size_mb}MB"
        fi
    done
}

# Run main function
main "$@"