#!/bin/bash

# Korean Stock Trading System - Test Runner Script
# This script runs unit tests with coverage reporting

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Korean Stock Trading System - Test Runner${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}❌ pytest is not installed${NC}"
    echo -e "${YELLOW}Installing pytest and dependencies...${NC}"
    pip install pytest pytest-cov pytest-asyncio pytest-mock
fi

# Parse command line arguments
TEST_TYPE="unit"
VERBOSE=""
COVERAGE="yes"
SPECIFIC_TEST=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -i|--integration)
            TEST_TYPE="integration"
            shift
            ;;
        -a|--all)
            TEST_TYPE="all"
            shift
            ;;
        -v|--verbose)
            VERBOSE="-vv"
            shift
            ;;
        -nc|--no-coverage)
            COVERAGE="no"
            shift
            ;;
        -f|--file)
            SPECIFIC_TEST="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: ./run_tests.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -i, --integration    Run integration tests only"
            echo "  -a, --all           Run all tests (unit + integration)"
            echo "  -v, --verbose       Verbose output"
            echo "  -nc, --no-coverage  Skip coverage reporting"
            echo "  -f, --file <path>   Run specific test file"
            echo "  -h, --help          Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./run_tests.sh                        # Run unit tests with coverage"
            echo "  ./run_tests.sh -v                     # Run with verbose output"
            echo "  ./run_tests.sh -i                     # Run integration tests"
            echo "  ./run_tests.sh -f tests/test_*.py     # Run specific test file"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Set test directory based on test type
if [ "$SPECIFIC_TEST" != "" ]; then
    TEST_DIR="$SPECIFIC_TEST"
    echo -e "${BLUE}🎯 Running specific test: ${TEST_DIR}${NC}"
elif [ "$TEST_TYPE" == "integration" ]; then
    TEST_DIR="tests/integration/"
    echo -e "${BLUE}🔗 Running integration tests...${NC}"
elif [ "$TEST_TYPE" == "all" ]; then
    TEST_DIR="tests/"
    echo -e "${BLUE}🚀 Running all tests...${NC}"
else
    TEST_DIR="tests/"
    IGNORE_INTEGRATION="--ignore=tests/integration/"
    echo -e "${BLUE}🧪 Running unit tests...${NC}"
fi

echo ""

# Build pytest command
PYTEST_CMD="pytest $TEST_DIR $IGNORE_INTEGRATION $VERBOSE"

if [ "$COVERAGE" == "yes" ] && [ "$TEST_TYPE" != "integration" ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=services --cov=shared --cov-report=term-missing --cov-report=html --cov-report=xml"
fi

# Add other options
PYTEST_CMD="$PYTEST_CMD --tb=short"

echo -e "${YELLOW}Running command:${NC} $PYTEST_CMD"
echo ""

# Run tests
if eval $PYTEST_CMD; then
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✅ All tests passed!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    if [ "$COVERAGE" == "yes" ] && [ "$TEST_TYPE" != "integration" ]; then
        echo ""
        echo -e "${BLUE}📊 Coverage report generated:${NC}"
        echo -e "   ${YELLOW}HTML Report:${NC} htmlcov/index.html"
        echo -e "   ${YELLOW}XML Report:${NC} coverage.xml"
        echo ""

        # Check coverage threshold
        if [ -f coverage.xml ]; then
            COVERAGE_PCT=$(python3 -c "
import xml.etree.ElementTree as ET
try:
    tree = ET.parse('coverage.xml')
    root = tree.getroot()
    line_rate = float(root.attrib.get('line-rate', 0))
    print(f'{line_rate * 100:.1f}')
except:
    print('0')
" 2>/dev/null || echo "0")

            echo -e "${BLUE}📈 Coverage: ${COVERAGE_PCT}%${NC}"

            THRESHOLD=70
            if (( $(echo "$COVERAGE_PCT >= $THRESHOLD" | bc -l 2>/dev/null || echo "0") )); then
                echo -e "${GREEN}✅ Coverage meets threshold (${THRESHOLD}%)${NC}"
            else
                echo -e "${YELLOW}⚠️  Coverage below threshold (${THRESHOLD}%)${NC}"
            fi
        fi
    fi

    exit 0
else
    echo ""
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}❌ Tests failed!${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    exit 1
fi
