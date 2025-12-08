# Verdant-Minds Test Suite

This directory contains unit tests and integration tests for the Unified Synthetic Mind cognitive architecture.

---

## Running Tests

### Install Test Dependencies

```bash
pip install pytest pytest-cov
```

Or install all development dependencies:

```bash
pip install -r requirements-dev.txt
```

### Run All Tests

```bash
# From project root
pytest tests/

# With verbose output
pytest tests/ -v

# With coverage report
pytest tests/ --cov=core --cov-report=term-missing
```

### Run Specific Test File

```bash
# Run CognitiveChunk tests
pytest tests/test_cognitive_chunk.py -v

# With coverage for specific module
pytest tests/test_cognitive_chunk.py --cov=core.CognitiveChunk --cov-report=term-missing
```

### Run Specific Test Class or Function

```bash
# Run all initialization tests
pytest tests/test_cognitive_chunk.py::TestInitialization -v

# Run single test function
pytest tests/test_cognitive_chunk.py::TestInitialization::test_init_with_auto_id -v
```

---

## Test Files

### `test_cognitive_chunk.py`

**Coverage: 100%** ✓

Comprehensive unit tests for the CognitiveChunk class, the core data structure for cognitive processing.

**Test Coverage:**
- ✓ Initialization and ID generation (6 tests)
- ✓ Section management: add, update, retrieve (8 tests)
- ✓ Processing log management (6 tests)
- ✓ Chunk merging operations (7 tests)
- ✓ Edge cases and validation (6 tests)
- ✓ Integration tests (3 tests)
- ✓ Performance tests (2 tests)

**Total: 38 tests** | **Status: All Passing** ✓

### `test_system_integration.py`

**Status: Ready for implementation completion**

Comprehensive integration tests for the entire Unified Synthetic Mind system, testing component interactions and data flow.

**Test Coverage:**
- System initialization with various configurations (9 tests)
- Complete data flow through all nine blocks (6 tests)
- Memory storage, retrieval, and ECWF bridge operations (7 tests)
- Ethical evaluation and Three Kings governance (7 tests)
- Block coordination and information flow (6 tests)
- Integration with existing IntegrationTestSuite (3 tests)
- Error handling and edge cases (5 tests)
- Performance and stress tests (3 tests)
- Integration workflows (5 tests)

**Total: 53 tests** | **Status: Awaiting source code completion**

**Note:** These tests are fully implemented and will pass once the source code blocks are completed. Currently failing due to missing method implementations in PatternRecognitionBlock and other blocks (expected behavior for incomplete codebase).

---

## Test Organization

Tests are organized by functionality using pytest classes:

```python
class TestInitialization:
    """Tests for basic initialization and properties"""

class TestSectionManagement:
    """Tests for section operations"""

class TestProcessingLog:
    """Tests for processing history"""

class TestMergeOperations:
    """Tests for chunk merging"""

class TestEdgeCases:
    """Tests for boundary conditions"""

class TestIntegration:
    """Integration tests simulating real usage"""

class TestPerformance:
    """Performance and stress tests"""
```

---

## Writing New Tests

### Test File Structure

```python
#!/usr/bin/env python3
"""
Unit Tests for YourComponent

Brief description of what's being tested.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "Verdant Source Codes" / "src"))

from your.module import YourClass

# Fixtures
@pytest.fixture
def your_fixture():
    """Fixture description."""
    return YourClass()

# Test classes
class TestYourFeature:
    """Tests for specific feature."""

    def test_something(self, your_fixture):
        """
        Test description.

        Explain what this test validates and why.
        """
        assert your_fixture.method() == expected_value
```

### Test Naming Conventions

- **Test files**: `test_<module_name>.py`
- **Test classes**: `Test<FeatureName>`
- **Test functions**: `test_<what_is_tested>`

### Documentation Requirements

Each test should include:

1. **Docstring** explaining what is being tested
2. **Clear assertion messages** when appropriate
3. **Comments** for non-obvious test logic
4. **Fixtures** for common setup

---

## Code Coverage Goals

- **Target**: >80% coverage for all modules
- **Critical modules**: Aim for 90-100% coverage
  - CognitiveChunk ✓ (100%)
  - UnifiedSyntheticMind
  - MemoryWeb
  - ECWFCore
  - Three Kings components

---

## Continuous Integration

Tests should pass before commits are merged. Run the full test suite before pushing:

```bash
# Run all tests with coverage
pytest tests/ -v --cov=core --cov=memory --cov=kings --cov-report=term-missing

# Generate HTML coverage report
pytest tests/ --cov=core --cov-report=html

# View HTML report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

---

## Test Categories

### Unit Tests

Test individual components in isolation:
- CognitiveChunk operations
- Memory Web graph operations
- ECWF wave function calculations
- Individual cognitive blocks

### Integration Tests

Test component interactions:
- Full pipeline processing
- Memory-ECWF Bridge operations
- Three Kings coordination
- End-to-end workflows

### Performance Tests

Test scalability and efficiency:
- Large graph operations
- Many concurrent chunks
- Memory usage patterns
- Processing speed benchmarks

---

## Troubleshooting

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'core'`

**Solution**:
```bash
# Install package in development mode
pip install -e .

# Or set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/path/to/Verdant-Minds/Verdant Source Codes/src"
```

### Test Discovery Issues

**Problem**: `pytest` doesn't find your tests

**Solution**:
- Ensure test files start with `test_`
- Ensure test functions start with `test_`
- Ensure test classes start with `Test`
- Run `pytest --collect-only` to see what pytest finds

### Slow Tests

Some tests may be slow due to:
- Graph operations on large networks
- Wave function calculations
- Integration tests with full pipeline

Use pytest markers to skip slow tests during development:

```python
@pytest.mark.slow
def test_large_graph_operations():
    # ...
```

Run without slow tests:
```bash
pytest -m "not slow"
```

---

## Contributing Tests

When adding new functionality:

1. **Write tests first** (TDD approach recommended)
2. **Ensure tests pass** before committing
3. **Maintain >80% coverage** for new code
4. **Document edge cases** in test docstrings
5. **Add fixtures** for reusable test setup
6. **Update this README** if adding new test categories

---

## Additional Resources

- **pytest Documentation**: https://docs.pytest.org/
- **Coverage.py**: https://coverage.readthedocs.io/
- **Testing Best Practices**: See main README.md
- **CI/CD Integration**: Coming soon

---

## License

These tests are part of the Verdant-Minds project and are licensed under the MIT License.
