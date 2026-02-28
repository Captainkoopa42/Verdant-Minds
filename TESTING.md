# Testing Guide for Verdant-Minds

This document provides comprehensive instructions for running tests in the Verdant-Minds project.

---

## Quick Start

### Using Test Runner Scripts (Recommended)

**Shell Script (Linux/macOS):**
```bash
./run_tests.sh
```

**Python Script (Cross-platform):**
```bash
python run_tests.py
```

### Direct pytest Command

```bash
pytest tests/ -v --cov=src --cov-report=term-missing
```

---

## Test Runner Scripts

We provide two test runner scripts for convenience:

### 1. Shell Script (`run_tests.sh`)

Best for Linux/macOS environments and CI/CD pipelines.

**Basic Usage:**
```bash
./run_tests.sh                    # Run all tests with coverage
./run_tests.sh --fast             # Skip slow tests
./run_tests.sh --unit             # Run only unit tests
./run_tests.sh --integration      # Run only integration tests
./run_tests.sh --html             # Generate HTML coverage report
./run_tests.sh --verbose          # Verbose output
./run_tests.sh --ci               # CI/CD optimized mode
./run_tests.sh --no-cov           # Skip coverage reporting
```

**Combined Options:**
```bash
./run_tests.sh --unit --html --verbose
./run_tests.sh --fast --no-cov
./run_tests.sh --ci --integration
```

### 2. Python Script (`run_tests.py`)

Cross-platform Python script, works on Windows, Linux, and macOS.

**Basic Usage:**
```bash
python run_tests.py                    # Run all tests with coverage
python run_tests.py --fast             # Skip slow tests
python run_tests.py --unit             # Run only unit tests
python run_tests.py --integration      # Run only integration tests
python run_tests.py --html             # Generate HTML coverage report
python run_tests.py --verbose          # Verbose output
python run_tests.py --ci               # CI/CD optimized mode
python run_tests.py --no-cov           # Skip coverage reporting
```

**Help:**
```bash
python run_tests.py --help
```

---

## Test Organization

### Test Files

```
tests/
├── __init__.py
├── README.md                        # Comprehensive testing documentation
├── test_cognitive_chunk.py          # Unit tests (38 tests, 100% coverage)
└── test_system_integration.py       # Integration tests (53 tests)
```

### Test Categories

**Unit Tests (`test_cognitive_chunk.py`):**
- ✅ All passing (38/38)
- ✅ 100% code coverage
- Fast execution (~1.2s)
- No external dependencies

**Integration Tests (`test_system_integration.py`):**
- 53 comprehensive tests
- Tests complete system workflows
- Includes slow tests (marked with `@pytest.mark.slow`)
- Ready for implementation completion

---

## Running Tests Manually

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test File

```bash
pytest tests/test_cognitive_chunk.py -v
pytest tests/test_system_integration.py -v
```

### Run Specific Test Class

```bash
pytest tests/test_cognitive_chunk.py::TestInitialization -v
pytest tests/test_system_integration.py::TestSystemInitialization -v
```

### Run Specific Test Function

```bash
pytest tests/test_cognitive_chunk.py::TestInitialization::test_init_with_auto_id -v
```

### Skip Slow Tests

```bash
pytest tests/ -m "not slow" -v
```

### Run Only Slow Tests

```bash
pytest tests/ -m "slow" -v
```

---

## Coverage Reporting

### Terminal Coverage Report

```bash
pytest tests/ --cov=src --cov-report=term-missing
```

### HTML Coverage Report

```bash
pytest tests/ --cov=src --cov-report=html
```

Then open `htmlcov/index.html` in your browser.

### XML Coverage Report (for CI/CD)

```bash
pytest tests/ --cov=src --cov-report=xml
```

### Coverage for Specific Module

```bash
pytest tests/test_cognitive_chunk.py --cov=src.core.CognitiveChunk --cov-report=term-missing
```

---

## CI/CD Integration

### GitHub Actions

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e .
          pip install pytest pytest-cov

      - name: Run tests
        run: |
          python run_tests.py --ci

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          fail_ci_if_error: true
```

### GitLab CI

```yaml
test:
  image: python:3.11
  script:
    - pip install -e .
    - pip install pytest pytest-cov
    - python run_tests.py --ci
  coverage: '/(?i)total.*? (100(?:\.0+)?\%|[1-9]?\d(?:\.\d+)?\%)$/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
```

### Jenkins

```groovy
pipeline {
    agent any

    stages {
        stage('Setup') {
            steps {
                sh 'pip install -e .'
                sh 'pip install pytest pytest-cov'
            }
        }

        stage('Test') {
            steps {
                sh './run_tests.sh --ci'
            }
        }

        stage('Coverage') {
            steps {
                publishHTML([
                    reportDir: 'htmlcov',
                    reportFiles: 'index.html',
                    reportName: 'Coverage Report'
                ])
            }
        }
    }
}
```

---

## Local Development Workflow

### 1. Install Dependencies

```bash
# Install project in development mode
pip install -e .

# Install development dependencies
pip install pytest pytest-cov
```

### 2. Run Tests During Development

**Quick check (fast tests only):**
```bash
./run_tests.sh --fast
```

**Before committing:**
```bash
./run_tests.sh --verbose
```

**Check coverage:**
```bash
./run_tests.sh --html
```

### 3. Continuous Testing

Use `pytest-watch` for automatic test running:

```bash
pip install pytest-watch
ptw tests/ -- -v
```

---

## Troubleshooting

### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'src'`

**Solution:**
```bash
# Install package in development mode
pip install -e .

# Or set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:${PWD}/Verdant Source Codes"
```

### Missing Dependencies

**Problem:** `ModuleNotFoundError: No module named 'pytest'`

**Solution:**
```bash
pip install pytest pytest-cov
```

### Test Discovery Issues

**Problem:** pytest doesn't find tests

**Solution:**
- Ensure test files start with `test_`
- Ensure test functions start with `test_`
- Ensure test classes start with `Test`
- Run `pytest --collect-only` to see what pytest finds

### Slow Test Execution

**Problem:** Tests are taking too long

**Solution:**
```bash
# Skip slow tests
pytest tests/ -m "not slow"

# Or use fast mode
./run_tests.sh --fast
```

### Integration Tests Failing

**Problem:** Integration tests fail with `AttributeError`

**Explanation:** This is expected behavior. The integration tests are fully implemented and will pass once the source code blocks are completed. Currently, some blocks have missing method implementations.

**Current Status:**
- ✅ Test infrastructure: 100% complete
- ⏳ Source code: In development
- 📝 Tests document expected behavior

---

## Test Coverage Goals

| Module | Current | Target |
|--------|---------|--------|
| CognitiveChunk | 100% ✅ | 100% |
| UnifiedSystem | TBD | 90% |
| MemoryWeb | TBD | 90% |
| ECWFCore | TBD | 90% |
| Blocks | TBD | 80% |
| Three Kings | TBD | 85% |
| **Overall** | TBD | **85%** |

---

## Performance Benchmarks

### Current Performance

**Unit Tests:**
- Total: 38 tests
- Duration: ~1.2s
- Status: ✅ All passing

**Integration Tests:**
- Total: 53 tests
- Duration: ~varies (some slow tests)
- Status: ⏳ Awaiting implementation completion

### Performance Tips

1. **Use fast mode during development:**
   ```bash
   ./run_tests.sh --fast
   ```

2. **Run only changed tests:**
   ```bash
   pytest tests/test_cognitive_chunk.py -v
   ```

3. **Parallel execution (with pytest-xdist):**
   ```bash
   pip install pytest-xdist
   pytest tests/ -n auto
   ```

---

## Writing New Tests

### Test Structure

```python
import pytest

@pytest.fixture
def sample_data():
    """Fixture providing test data."""
    return {"key": "value"}

class TestMyFeature:
    """Tests for my feature."""

    def test_something(self, sample_data):
        """
        Test that something works correctly.

        Explain what this test validates and why.
        """
        assert sample_data["key"] == "value"
```

### Best Practices

1. **Use descriptive names:**
   - ✅ `test_chunk_initialization_with_custom_id`
   - ❌ `test_1`

2. **Write clear docstrings:**
   - Explain what the test validates
   - Explain why it's important
   - Document expected behavior

3. **Use fixtures for setup:**
   - Keep tests DRY (Don't Repeat Yourself)
   - Share common setup across tests

4. **Test one thing at a time:**
   - Each test should validate one specific behavior
   - Makes failures easier to diagnose

5. **Mark slow tests:**
   ```python
   @pytest.mark.slow
   def test_expensive_operation():
       # ...
   ```

---

## Getting Help

**Documentation:**
- Main README: `README.md`
- Test Documentation: `tests/README.md`
- API Documentation: `docs/api.md`
- Architecture: `docs/architecture.md`

**Running Help:**
```bash
./run_tests.sh --help
python run_tests.py --help
pytest --help
```

**Issues:**
Report issues at: https://github.com/captainkoopa42/Verdant-Minds/issues

---

## Summary of Commands

```bash
# Quick test runs
./run_tests.sh                      # All tests
./run_tests.sh --fast               # Fast tests only
./run_tests.sh --unit               # Unit tests only

# With coverage
./run_tests.sh --html               # Generate HTML report
./run_tests.sh --verbose            # Detailed output

# CI/CD
./run_tests.sh --ci                 # Optimized for automation

# Python (cross-platform)
python run_tests.py                 # All tests
python run_tests.py --fast          # Fast tests only
python run_tests.py --ci            # CI/CD mode

# Direct pytest
pytest tests/ -v                    # All tests, verbose
pytest tests/ -m "not slow"         # Skip slow tests
pytest tests/ --cov=src --cov-report=html  # With coverage
```

---

**Last Updated:** 2025-12-08
**Test Suite Version:** 1.0.0
**Maintained By:** Verdant-Minds Development Team
