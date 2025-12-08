#!/bin/bash
###############################################################################
# Verdant-Minds Test Runner Script
#
# This script runs the complete test suite with coverage reporting and
# provides a comprehensive summary of test results.
#
# Usage:
#   ./run_tests.sh [options]
#
# Options:
#   --unit          Run only unit tests
#   --integration   Run only integration tests (slow)
#   --no-cov        Skip coverage reporting
#   --html          Generate HTML coverage report
#   --verbose       Verbose output
#   --fast          Skip slow tests
#   --ci            CI/CD mode (optimized for automation)
#   --help          Show this help message
#
# Examples:
#   ./run_tests.sh                    # Run all tests with coverage
#   ./run_tests.sh --fast             # Run only fast tests
#   ./run_tests.sh --unit --html      # Unit tests with HTML report
#   ./run_tests.sh --ci               # CI/CD mode
#
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default options
RUN_UNIT=true
RUN_INTEGRATION=true
COVERAGE=true
HTML_REPORT=false
VERBOSE=false
FAST_MODE=false
CI_MODE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --unit)
            RUN_UNIT=true
            RUN_INTEGRATION=false
            shift
            ;;
        --integration)
            RUN_UNIT=false
            RUN_INTEGRATION=true
            shift
            ;;
        --no-cov)
            COVERAGE=false
            shift
            ;;
        --html)
            HTML_REPORT=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --fast)
            FAST_MODE=true
            shift
            ;;
        --ci)
            CI_MODE=true
            shift
            ;;
        --help)
            head -n 30 "$0" | tail -n 28
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

###############################################################################
# Helper Functions
###############################################################################

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

check_dependencies() {
    print_header "Checking Dependencies"

    # Check Python version
    if ! command -v python &> /dev/null; then
        print_error "Python not found"
        exit 1
    fi

    PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
    print_success "Python $PYTHON_VERSION"

    # Check pytest
    if ! python -m pytest --version &> /dev/null; then
        print_error "pytest not installed"
        echo "Install with: pip install pytest pytest-cov"
        exit 1
    fi

    PYTEST_VERSION=$(python -m pytest --version 2>&1 | head -n1)
    print_success "$PYTEST_VERSION"

    # Check pytest-cov if coverage is enabled
    if [ "$COVERAGE" = true ]; then
        if ! python -c "import pytest_cov" &> /dev/null; then
            print_warning "pytest-cov not installed, disabling coverage"
            COVERAGE=false
        else
            print_success "pytest-cov installed"
        fi
    fi
}

###############################################################################
# Main Test Execution
###############################################################################

print_header "Verdant-Minds Test Suite"
echo "Run Unit Tests: $RUN_UNIT"
echo "Run Integration Tests: $RUN_INTEGRATION"
echo "Coverage Reporting: $COVERAGE"
echo "HTML Report: $HTML_REPORT"
echo "Fast Mode: $FAST_MODE"
echo "CI Mode: $CI_MODE"
echo ""

# Check dependencies
check_dependencies

# Build pytest command
PYTEST_CMD="python -m pytest"
PYTEST_ARGS=""
TEST_FILES=""

# Add test files based on selection
if [ "$RUN_UNIT" = true ] && [ "$RUN_INTEGRATION" = true ]; then
    TEST_FILES="tests/"
elif [ "$RUN_UNIT" = true ]; then
    TEST_FILES="tests/test_cognitive_chunk.py"
elif [ "$RUN_INTEGRATION" = true ]; then
    TEST_FILES="tests/test_system_integration.py"
fi

# Add verbosity
if [ "$VERBOSE" = true ] || [ "$CI_MODE" = true ]; then
    PYTEST_ARGS="$PYTEST_ARGS -v"
else
    PYTEST_ARGS="$PYTEST_ARGS -q"
fi

# Add coverage options
if [ "$COVERAGE" = true ]; then
    PYTEST_ARGS="$PYTEST_ARGS --cov=src --cov-report=term-missing"

    if [ "$HTML_REPORT" = true ]; then
        PYTEST_ARGS="$PYTEST_ARGS --cov-report=html"
    fi

    if [ "$CI_MODE" = true ]; then
        PYTEST_ARGS="$PYTEST_ARGS --cov-report=xml"
    fi
fi

# Fast mode - skip slow tests
if [ "$FAST_MODE" = true ]; then
    PYTEST_ARGS="$PYTEST_ARGS -m \"not slow\""
fi

# CI mode - additional options
if [ "$CI_MODE" = true ]; then
    PYTEST_ARGS="$PYTEST_ARGS --tb=short --maxfail=5"
fi

# Run the tests
print_header "Running Tests"
echo "Command: $PYTEST_CMD $TEST_FILES $PYTEST_ARGS"
echo ""

# Capture exit code but don't exit immediately
set +e
$PYTEST_CMD $TEST_FILES $PYTEST_ARGS
TEST_EXIT_CODE=$?
set -e

###############################################################################
# Results Summary
###############################################################################

print_header "Test Results Summary"

if [ $TEST_EXIT_CODE -eq 0 ]; then
    print_success "All tests passed!"

    if [ "$HTML_REPORT" = true ]; then
        echo ""
        print_info "HTML coverage report generated: htmlcov/index.html"

        # Try to open in browser (non-CI mode)
        if [ "$CI_MODE" = false ]; then
            if command -v xdg-open &> /dev/null; then
                xdg-open htmlcov/index.html &> /dev/null &
                print_info "Opening coverage report in browser..."
            elif command -v open &> /dev/null; then
                open htmlcov/index.html &> /dev/null &
                print_info "Opening coverage report in browser..."
            fi
        fi
    fi

    echo ""
    print_success "Test run completed successfully"
    exit 0
else
    print_error "Some tests failed (exit code: $TEST_EXIT_CODE)"
    echo ""

    if [ "$VERBOSE" = false ]; then
        print_info "Run with --verbose for detailed output"
    fi

    if [ "$FAST_MODE" = true ]; then
        print_info "Running in fast mode - integration tests may have been skipped"
    fi

    echo ""
    print_error "Test run completed with failures"
    exit $TEST_EXIT_CODE
fi
