#!/bin/bash

# Test runner script for AI PPT Assistant

set -e  # Exit on error

echo "========================================="
echo "AI PPT Assistant - Test Suite"
echo "========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${GREEN}Activating virtual environment...${NC}"
source venv/bin/activate

# Install dependencies
echo -e "${GREEN}Installing test dependencies...${NC}"
pip install -q -r tests/requirements.txt
pip install -q -r lambdas/layers/requirements.txt

# Run linting
echo -e "\n${YELLOW}Running code quality checks...${NC}"
echo "Running flake8..."
flake8 lambdas --max-line-length=120 --exclude=__pycache__,venv || true

echo "Running black (check only)..."
black lambdas --check --diff || true

# Run type checking
echo -e "\n${YELLOW}Running type checking...${NC}"
mypy lambdas --ignore-missing-imports || true

# Run unit tests
echo -e "\n${YELLOW}Running unit tests...${NC}"
pytest tests/unit -v --cov=lambdas --cov-report=term-missing --cov-report=html

# Generate coverage report
echo -e "\n${YELLOW}Coverage Report:${NC}"
coverage report -m

# Check if coverage meets threshold
coverage_percentage=$(coverage report | grep TOTAL | awk '{print $4}' | sed 's/%//')
if (( $(echo "$coverage_percentage < 80" | bc -l) )); then
    echo -e "${RED}Warning: Code coverage is below 80% threshold (${coverage_percentage}%)${NC}"
else
    echo -e "${GREEN}Code coverage meets threshold (${coverage_percentage}%)${NC}"
fi

# Summary
echo -e "\n========================================="
echo -e "${GREEN}Test Summary:${NC}"
echo "- Linting: Complete"
echo "- Type checking: Complete"
echo "- Unit tests: Complete"
echo "- Coverage: ${coverage_percentage}%"
echo "- HTML coverage report: htmlcov/index.html"
echo "========================================="

# Run specific test categories if specified
if [ "$1" == "integration" ]; then
    echo -e "\n${YELLOW}Running integration tests...${NC}"
    pytest tests/integration -v -m integration
elif [ "$1" == "e2e" ]; then
    echo -e "\n${YELLOW}Running end-to-end tests...${NC}"
    pytest tests/e2e -v -m e2e
elif [ "$1" == "smoke" ]; then
    echo -e "\n${YELLOW}Running smoke tests...${NC}"
    pytest tests -v -m smoke
fi

# Deactivate virtual environment
deactivate

echo -e "\n${GREEN}All tests completed!${NC}"